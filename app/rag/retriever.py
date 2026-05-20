import os
import faiss
import pickle
import re
from sentence_transformers import SentenceTransformer
from app.memory.utils import DOCS_PATH, INDEX_PATH

_model = None
_index = None
_docs = None

INDEX_PATH = "app/store/index.faiss"
DOCS_PATH = "app/store/docs.pkl"

MEDICAL_EXPANSIONS = {
    "dka": "diabetic ketoacidosis",
    "diabeties": "diabetes",
    "diabetis": "diabetes",
    "diabete": "diabetes",
}

QUESTION_EXPANSIONS = {
    "symptom": "symptoms signs presentation clinical features nausea vomiting abdominal pain thirst dehydration",
    "symptoms": "symptoms signs presentation clinical features nausea vomiting abdominal pain thirst dehydration",
    "cause": "causes risk factors precipitating factors etiology trigger",
    "causes": "causes risk factors precipitating factors etiology trigger",
    "diagnosis": "diagnostic criteria diagnosis criteria",
    "diagnostic": "diagnostic criteria diagnosis criteria",
    "treatment": "treatment management therapy",
}


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


def normalize_query_text(query: str) -> str:
    q = " ".join(query.strip().split())
    words = re.findall(r"\b[\w-]+\b", q.lower())

    additions = []
    for word in words:
        if word in MEDICAL_EXPANSIONS:
            additions.append(MEDICAL_EXPANSIONS[word])
        if word in QUESTION_EXPANSIONS:
            additions.append(QUESTION_EXPANSIONS[word])

    if additions:
        return f"{q} {' '.join(additions)}"

    return q


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"\b[a-zA-Z][a-zA-Z0-9-]{2,}\b", text.lower()))


def lexical_overlap(query: str, chunk: dict) -> float:
    query_terms = tokenize(normalize_query_text(query))
    if not query_terms:
        return 0.0

    chunk_text = " ".join(
        str(chunk.get(key, ""))
        for key in ("text", "section", "source")
    )
    chunk_terms = tokenize(chunk_text)
    overlap = query_terms.intersection(chunk_terms)

    return len(overlap) / max(len(query_terms), 1)


def retrieve(query: str, k: int = 5):
    if not query or not query.strip():
        return []

    load_resources()

    expanded_query = normalize_query_text(query)
    initial_k = min(max(k * 5, 20), len(_docs))

    # Stored embeddings are normalized at ingest time. Normalize the query too,
    # otherwise L2 distances become much less meaningful.
    q_emb = _model.encode([expanded_query], normalize_embeddings=True)
    distances, ids = _index.search(q_emb, initial_k)

    results = []
    for dist, idx in zip(distances[0], ids[0]):
        if idx < 0:
            continue
        chunk = _docs[idx].copy()      # flatten chunk
        chunk["distance"] = float(dist)
        vector_score = 1.0 / (1.0 + float(dist))
        keyword_score = lexical_overlap(query, chunk)
        chunk["retrieval_score"] = vector_score + (0.25 * keyword_score)
        results.append(chunk)

    results.sort(key=lambda c: c.get("retrieval_score", 0), reverse=True)
    results = results[:k]

    print("RETRIEVE:", len(results), "chunks")
    for r in results[:3]:
        print(
            " -",
            r["source"],
            "dist=",
            r["distance"],
            "score=",
            round(r.get("retrieval_score", 0), 4),
        )

    return results
