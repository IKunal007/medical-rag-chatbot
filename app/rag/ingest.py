import os
import faiss
import pickle
from sentence_transformers import SentenceTransformer
from app.rag.chunking import clean_extracted_text, chunk_by_sections
from app.rag.utils import hash_text 

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



def ingest_text(
    text: str,
    source: str,
    page: int | None = None,
    location: str | None = None,
):
    """
    Convert raw text into paragraph-based chunks with metadata,
    then ingest them into FAISS.
    """
    clean_text = clean_extracted_text(text)
    section_chunks = chunk_by_sections(clean_text)

    chunks_with_meta = []

    for i, chunk in enumerate(section_chunks):
        text = chunk["text"].strip()
        if not text:
            continue

        chunks_with_meta.append({
            "text": chunk["text"],
            "section": chunk["section"],
            "section_level": chunk.get("level", 1),  # heuristic, optional
            "chunk_hash": hash_text(chunk["text"]),
            "source": source,
            "page": page,
            "location": location,
            "chunk_id": f"{source}_p{page}_s{i}" if page is not None else f"{source}_s{i}",
        })

    return ingest_chunks(chunks_with_meta)


# Ingest chunks with metadata
def ingest_chunks(chunks_with_meta: list[dict]) -> int:
    if not chunks_with_meta:
        return 0

    os.makedirs("app/store", exist_ok=True)

    # Load existing docs + hashes
    existing_docs = load_existing_docs()
    existing_hashes = {
        d["chunk_hash"] for d in existing_docs if "chunk_hash" in d
    }

    # Deduplicate
    new_chunks = []
    new_texts = []

    for c in chunks_with_meta:
        chunk_hash = c.get("chunk_hash")
        if chunk_hash and chunk_hash in existing_hashes:
            continue
    
        new_chunks.append(c)
        new_texts.append(c["text"])

    if not new_chunks:
        return 0  # nothing new

    # Embed ONLY new chunks
    embeddings = model.encode(
        new_texts,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True,
    )


    # Load or create FAISS index
    index = load_or_create_index(embeddings.shape[1])
    assert index.d == embeddings.shape[1]

    index.add(embeddings)

    # Persist
    existing_docs.extend(new_chunks)

    faiss.write_index(index, INDEX_PATH)
    with open(DOCS_PATH, "wb") as f:
        pickle.dump(existing_docs, f)

    return len(new_chunks)
