from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parents[2]  # project root
STORE_DIR = BASE_DIR / "app" / "store"

DOCS_PATH = STORE_DIR / "docs.pkl"
INDEX_PATH = STORE_DIR / "index.faiss"
UPLOAD_DIR = STORE_DIR / "uploads"
OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434"  # fallback for local non-Docker runs
)
MODEL_NAME = os.getenv(
    "OLLAMA_MODEL",
    "llama3.1:8b"
)
def build_memory_aware_query(query: str, memory: list):
    if not memory:
        return query

    q = query.lower().strip()
    followup_markers = {
        "it",
        "its",
        "this",
        "that",
        "they",
        "them",
        "these",
        "those",
        "same",
        "above",
        "previous",
    }
    words = set(q.replace("?", "").split())

    # Only add conversation memory for short follow-up questions. Adding every
    # previous user turn pollutes retrieval when the topic changes.
    if len(words) > 10 or not words.intersection(followup_markers):
        return query

    last_user_turns = [
        m["content"] for m in memory if m["role"] == "user"
    ]

    context = " ".join(last_user_turns[-1:])
    return f"{context}\nCurrent question: {query}"



