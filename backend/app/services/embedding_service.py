import os
import openai


class EmbeddingService:
    def __init__(self) -> None:
        self._model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
        self._client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def embed(self, text: str) -> list[float]:
        response = self._client.embeddings.create(model=self._model, input=text)
        return response.data[0].embedding
