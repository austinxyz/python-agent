import httpx
import pytest
from unittest.mock import MagicMock, patch, call
from qdrant_client.http.exceptions import UnexpectedResponse
from app.services.qdrant_service import QdrantService, VECTOR_SIZE


def _not_found() -> UnexpectedResponse:
    return UnexpectedResponse(
        status_code=404,
        reason_phrase="Not Found",
        content=b"",
        headers=httpx.Headers(),
    )


class TestQdrantServiceCollectionInit:
    def test_creates_knowledge_collection_when_missing(self):
        with patch("app.services.qdrant_service.QdrantClient") as MockClient:
            client = MockClient.return_value
            client.get_collection.side_effect = _not_found()
            QdrantService(host="localhost", port=6333)
            names = [c.kwargs["collection_name"] for c in client.create_collection.call_args_list]
            assert "knowledge" in names

    def test_creates_private_collection_when_missing(self):
        with patch("app.services.qdrant_service.QdrantClient") as MockClient:
            client = MockClient.return_value
            client.get_collection.side_effect = _not_found()
            QdrantService(host="localhost", port=6333)
            names = [c.kwargs["collection_name"] for c in client.create_collection.call_args_list]
            assert "private" in names

    def test_collections_use_correct_vector_size(self):
        with patch("app.services.qdrant_service.QdrantClient") as MockClient:
            client = MockClient.return_value
            client.get_collection.side_effect = _not_found()
            QdrantService(host="localhost", port=6333)
            for c in client.create_collection.call_args_list:
                assert c.kwargs["vectors_config"].size == 1536

    def test_non_404_qdrant_error_propagates(self):
        with patch("app.services.qdrant_service.QdrantClient") as MockClient:
            client = MockClient.return_value
            client.get_collection.side_effect = UnexpectedResponse(
                status_code=503,
                reason_phrase="Service Unavailable",
                content=b"",
                headers=httpx.Headers(),
            )
            with pytest.raises(UnexpectedResponse):
                QdrantService(host="localhost", port=6333)

    def test_does_not_recreate_existing_collections(self):
        with patch("app.services.qdrant_service.QdrantClient") as MockClient:
            client = MockClient.return_value
            client.get_collection.return_value = MagicMock()
            QdrantService(host="localhost", port=6333)
            client.create_collection.assert_not_called()


def _make_scroll_page(points, next_offset=None):
    """Helper: mimics (points, next_page_offset) returned by Qdrant scroll."""
    return points, next_offset


def _point(domain: str, source_file_id: str):
    p = MagicMock()
    p.payload = {"domain": domain, "source_file_id": source_file_id}
    return p


class TestQdrantServiceGetTree:
    def _svc(self, client):
        client.get_collection.return_value = MagicMock()
        return QdrantService(host="localhost", port=6333)

    def test_empty_collection_returns_empty_dict(self):
        with patch("app.services.qdrant_service.QdrantClient") as MockClient:
            client = MockClient.return_value
            svc = self._svc(client)
            client.scroll.return_value = _make_scroll_page([])
            result = svc.get_tree()
            assert result == {}

    def test_groups_file_ids_by_domain(self):
        with patch("app.services.qdrant_service.QdrantClient") as MockClient:
            client = MockClient.return_value
            svc = self._svc(client)
            points = [
                _point("退休规划", "file-a"),
                _point("退休规划", "file-b"),
                _point("税务策略", "file-c"),
            ]
            client.scroll.return_value = _make_scroll_page(points)
            result = svc.get_tree()
            assert set(result.keys()) == {"退休规划", "税务策略"}
            assert set(result["退休规划"]) == {"file-a", "file-b"}
            assert result["税务策略"] == ["file-c"]

    def test_deduplicates_chunks_from_same_file(self):
        with patch("app.services.qdrant_service.QdrantClient") as MockClient:
            client = MockClient.return_value
            svc = self._svc(client)
            # 15 chunks, all from file-x in same domain
            points = [_point("退休规划", "file-x") for _ in range(15)]
            client.scroll.return_value = _make_scroll_page(points)
            result = svc.get_tree()
            assert result == {"退休规划": ["file-x"]}

    def test_paginates_until_no_next_offset(self):
        with patch("app.services.qdrant_service.QdrantClient") as MockClient:
            client = MockClient.return_value
            svc = self._svc(client)
            page1 = ([_point("退休规划", "file-a")], "cursor-1")
            page2 = ([_point("税务策略", "file-b")], None)
            client.scroll.side_effect = [page1, page2]
            result = svc.get_tree()
            assert set(result.keys()) == {"退休规划", "税务策略"}
            assert client.scroll.call_count == 2


class TestQdrantServiceSearchPrivate:
    def test_search_private_requires_user_id(self):
        with patch("app.services.qdrant_service.QdrantClient") as MockClient:
            client = MockClient.return_value
            client.get_collection.return_value = MagicMock()
            svc = QdrantService(host="localhost", port=6333)
            with pytest.raises(TypeError):
                svc.search_private([0.0] * 1536)

    def test_search_private_applies_user_id_filter(self):
        with patch("app.services.qdrant_service.QdrantClient") as MockClient:
            client = MockClient.return_value
            client.get_collection.return_value = MagicMock()
            client.search.return_value = []
            svc = QdrantService(host="localhost", port=6333)
            svc.search_private([0.0] * 1536, user_id="default")
            call_kwargs = client.search.call_args.kwargs
            filter_conditions = call_kwargs["query_filter"].must
            user_id_conditions = [
                c for c in filter_conditions if c.key == "user_id"
            ]
            assert len(user_id_conditions) == 1
            assert user_id_conditions[0].match.value == "default"
