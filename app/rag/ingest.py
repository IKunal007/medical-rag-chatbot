import os
import faiss
import pickle
from sentence_transformers import SentenceTransformer

INDEX_PATH = "app/store/index.faiss"
DOCS_PATH = "app/store/docs.pkl"

model = SentenceTransformer("all-MiniLM-L6-v2")


def chunk_text(text: str, chunk_size=300, overlap=50):
    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)

    return chunks


def ingest_text(text: str, source: str, page: int | None = None) -> int:
    os.makedirs("app/store", exist_ok=True)

    raw_chunks = chunk_text(text)

    # 🔑 attach metadata to each chunk
    chunks_with_meta = [
        {
            "text": chunk,
            "source": source,
            "page": page
        }
        for chunk in raw_chunks
    ]

    embeddings = model.encode([c["text"] for c in chunks_with_meta])

    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)

    faiss.write_index(index, INDEX_PATH)

    with open(DOCS_PATH, "wb") as f:
        pickle.dump(chunks_with_meta, f)

    return len(chunks_with_meta)


def ingest_pages(pages, source: str) -> int:
    os.makedirs("app/store", exist_ok=True)

    chunks_with_meta = []

    for p in pages:
        raw_chunks = chunk_text(p["text"])
        for ch in raw_chunks:
            chunks_with_meta.append({
                "text": ch,
                "source": source,
                "page": p["page"]
            })

    embeddings = model.encode([c["text"] for c in chunks_with_meta])

    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    faiss.write_index(index, INDEX_PATH)

    with open(DOCS_PATH, "wb") as f:
        pickle.dump(chunks_with_meta, f)

    return len(chunks_with_meta)
