import os
import faiss
import pickle
from sentence_transformers import SentenceTransformer

INDEX_PATH = "app/store/index.faiss"
DOCS_PATH = "app/store/docs.pkl"

model = SentenceTransformer("all-MiniLM-L6-v2")

# Load or create FAISS index
def load_or_create_index(dim: int):
    if os.path.exists(INDEX_PATH):
        return faiss.read_index(INDEX_PATH)
    return faiss.IndexFlatL2(dim)

# Load existing documents
def load_existing_docs():
    if os.path.exists(DOCS_PATH):
        with open(DOCS_PATH, "rb") as f:
            return pickle.load(f)
    return []

# Ingest chunks with metadata
def ingest_chunks(chunks_with_meta: list[dict]) -> int:

    if not chunks_with_meta:
        return 0

    os.makedirs("app/store", exist_ok=True)
    texts = [c["text"] for c in chunks_with_meta]
    embeddings = model.encode(texts, normalize_embeddings=True)

    # Load or create index
    index = load_or_create_index(embeddings.shape[1])
    assert index.d == embeddings.shape[1]

    index.add(embeddings)

    # Append metadata
    docs = load_existing_docs()
    docs.extend(chunks_with_meta)

    # Persist
    faiss.write_index(index, INDEX_PATH)
    with open(DOCS_PATH, "wb") as f:
        pickle.dump(docs, f)

    return len(chunks_with_meta)
