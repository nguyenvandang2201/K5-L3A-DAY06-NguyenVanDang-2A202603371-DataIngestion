"""Real local sentence embedding model, shared by all strategies."""
from typing import Protocol


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text, in the same order."""
        ...

    def embed_query(self, question: str) -> list[float]:
        """Return a query vector compatible with the stored document vectors."""
        ...


class MyEmbedder:
    """Sentence Transformers adapter; failures propagate instead of using mock vectors."""

    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.dimensions = self.model.get_embedding_dimension()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, batch_size=32, normalize_embeddings=True,
                                 show_progress_bar=False).tolist()

    def embed_query(self, question: str) -> list[float]:
        return self.model.encode([question], normalize_embeddings=True,
                                 show_progress_bar=False)[0].tolist()
