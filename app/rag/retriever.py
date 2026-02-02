import os
import faiss
import pickle
from sentence_transformers import SentenceTransformer

_model = None
_index = None
_docs = None

INDEX_PATH = "app/store/index.faiss"
DOCS_PATH = "app/store/docs.pkl"


def load_resources():
    global _model, _index, _docs

    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")

    if _index is None:
        if not os.path.exists(INDEX_PATH):
            raise RuntimeError("Vector index not initialized. Please ingest documents first.")
        _index = faiss.read_index(INDEX_PATH)

    if _docs is None:
        if not os.path.exists(DOCS_PATH):
            raise RuntimeError("Document store not found. Please ingest documents first.")
        with open(DOCS_PATH, "rb") as f:
            _docs = pickle.load(f)


def retrieve(query: str, k: int = 8):
    load_resources()
    q_emb = _model.encode([query])
    distances, ids = _index.search(q_emb, k)
    if distances[0][0] > 1.8:   # threshold, tune later
        return []
    return [_docs[i] for i in ids[0]]
