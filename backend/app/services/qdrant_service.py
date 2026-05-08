import os
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

VECTOR_SIZE = 1536
DISTANCE = models.Distance.COSINE
KNOWLEDGE_COLLECTION = "knowledge"
PRIVATE_COLLECTION = "private"


class QdrantService:
    def __init__(self, host: str | None = None, port: int | None = None):
        self._client = QdrantClient(
            host=host or os.environ.get("QDRANT_HOST", "localhost"),
            port=int(port or os.environ.get("QDRANT_PORT", 6333)),
        )
        self._ensure_collections()

    def _ensure_collections(self) -> None:
        for name in (KNOWLEDGE_COLLECTION, PRIVATE_COLLECTION):
            try:
                self._client.get_collection(name)
            except UnexpectedResponse as e:
                if e.status_code != 404:
                    raise
                self._client.create_collection(
                    collection_name=name,
                    vectors_config=models.VectorParams(
                        size=VECTOR_SIZE,
                        distance=DISTANCE,
                    ),
                )

    @property
    def client(self) -> QdrantClient:
        return self._client

    def search_knowledge(
        self, query_vector: list[float], limit: int = 5, **filters
    ) -> list:
        conditions = [
            models.FieldCondition(key=k, match=models.MatchValue(value=v))
            for k, v in filters.items()
        ]
        return self._client.search(
            collection_name=KNOWLEDGE_COLLECTION,
            query_vector=query_vector,
            limit=limit,
            query_filter=models.Filter(must=conditions) if conditions else None,
        )

    def search_private(
        self, query_vector: list[float], user_id: str, limit: int = 5, **filters
    ) -> list:
        conditions = [
            models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id))
        ]
        for k, v in filters.items():
            conditions.append(
                models.FieldCondition(key=k, match=models.MatchValue(value=v))
            )
        return self._client.search(
            collection_name=PRIVATE_COLLECTION,
            query_vector=query_vector,
            limit=limit,
            query_filter=models.Filter(must=conditions),
        )

    def get_tree(self, page_size: int = 100) -> dict[str, list[str]]:
        # TODO: for large collections, replace with a SQLite materialized view
        # of (file_id, domain) pairs to avoid O(n) scroll cost.
        seen: dict[str, set[str]] = {}  # domain -> set of source_file_ids
        offset = None
        first = True
        while first or offset is not None:
            first = False
            points, offset = self._client.scroll(
                collection_name=KNOWLEDGE_COLLECTION,
                limit=page_size,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for point in points:
                domain = (point.payload or {}).get("domain", "")
                file_id = (point.payload or {}).get("source_file_id", "")
                if domain and file_id:
                    seen.setdefault(domain, set()).add(file_id)
        return {domain: sorted(ids) for domain, ids in seen.items()}

    def upsert_knowledge(self, points: list[models.PointStruct]) -> None:
        self._client.upsert(collection_name=KNOWLEDGE_COLLECTION, points=points)

    def upsert_private(self, points: list[models.PointStruct]) -> None:
        self._client.upsert(collection_name=PRIVATE_COLLECTION, points=points)

    def delete_private(self, point_ids: list[str]) -> None:
        self._client.delete(
            collection_name=PRIVATE_COLLECTION,
            points_selector=models.PointIdsList(points=point_ids),
        )
