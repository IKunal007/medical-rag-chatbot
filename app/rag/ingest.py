import os
import faiss
import pickle
from app.rag.chunking import clean_extracted_text, chunk_by_sections
from app.rag.utils import hash_text
from app.memory.utils import DOCS_PATH, INDEX_PATH

_model = None


def get_embedding_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _model


def load_or_create_index(dim: int):
    if INDEX_PATH.exists():
        return faiss.read_index(str(INDEX_PATH))
    return faiss.IndexFlatL2(dim)



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
            "section_level": chunk.get("level", 1),
            "chunk_hash": hash_text(chunk["text"]),
            "source": source,
            "page": page,
            "location": location,
            "chunk_id": f"{source}_p{page}_s{i}" if page is not None else f"{source}_s{i}",
        })

    return ingest_chunks(chunks_with_meta)


def ingest_chunks(chunks_with_meta: list[dict]) -> int:
    if not chunks_with_meta:
        return 0

    os.makedirs("store", exist_ok=True)

    existing_docs = load_existing_docs()
    existing_hashes = {
        d["chunk_hash"]
        for d in existing_docs
        if d.get("chunk_hash") and d.get("source") == chunks_with_meta[0].get("source")
    }


    new_chunks = []
    new_texts = []

    for c in chunks_with_meta:
        chunk_hash = c.get("chunk_hash")
        if chunk_hash and chunk_hash in existing_hashes:
            continue
        new_chunks.append(c)
        new_texts.append(c["text"])

    if not new_chunks:
        return 0

    model = get_embedding_model()
    embeddings = model.encode(
        new_texts,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True,
    )

    index = load_or_create_index(embeddings.shape[1])
    index.add(embeddings)

    existing_docs.extend(new_chunks)

    faiss.write_index(index, str(INDEX_PATH))
    with open(DOCS_PATH, "wb") as f:
        pickle.dump(existing_docs, f)
    
    index = faiss.read_index(str(INDEX_PATH))
    print("FAISS index size:", index.ntotal)
    print("Docs stored:", len(load_existing_docs()))


    return len(new_chunks)
