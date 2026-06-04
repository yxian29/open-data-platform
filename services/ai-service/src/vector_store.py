"""ChromaDB embedded vector store — seeded from Neo4j ontology and PostgreSQL schemas."""
import chromadb
from chromadb.utils import embedding_functions
from src.config import settings

_client: chromadb.Client | None = None
_ef = None


def get_client() -> chromadb.Client:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.chroma_path)
    return _client


def get_embedding_fn():
    global _ef
    if _ef is None:
        # Uses chromadb's built-in onnxruntime embedding (all-MiniLM-L6-v2 via onnx).
        # No torch / sentence-transformers needed.
        _ef = embedding_functions.DefaultEmbeddingFunction()
    return _ef


def get_collection(name: str):
    return get_client().get_or_create_collection(name=name, embedding_function=get_embedding_fn())


def upsert(collection_name: str, ids: list[str], documents: list[str], metadatas: list[dict]):
    col = get_collection(collection_name)
    col.upsert(ids=ids, documents=documents, metadatas=metadatas)


def query(collection_name: str, text: str, n_results: int = 5) -> list[dict]:
    col = get_collection(collection_name)
    results = col.query(query_texts=[text], n_results=n_results)
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    return [{"document": d, "metadata": m} for d, m in zip(docs, metas)]
