import json
import pickle
from pathlib import Path

from app.memory.utils import DOCS_PATH, STORE_DIR


CACHE_PATH = STORE_DIR / "section_cache.json"


def _cache_key(file_path: Path) -> str:
    stat = file_path.stat()
    return f"{file_path.name}:{stat.st_size}:{stat.st_mtime_ns}"


def _read_cache() -> dict:
    if not CACHE_PATH.exists():
        return {}

    try:
        with CACHE_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _write_cache(cache: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CACHE_PATH.open("w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


def normalize_sections(sections: list[str]) -> list[str]:
    normalized = []
    seen = set()

    for section in sections:
        title = " ".join(str(section).strip().split())
        title_l = title.lower()

        if not title or title_l == "unknown":
            continue
        if len(title) > 140:
            continue
        if title_l in seen:
            continue

        normalized.append(title)
        seen.add(title_l)

    return normalized


def sections_from_chunks(chunks: list[dict]) -> list[str]:
    return normalize_sections([
        chunk.get("section", "")
        for chunk in chunks
    ])


def get_cached_sections(file_path: Path) -> list[str] | None:
    if not file_path.exists():
        return None

    cache = _read_cache()
    sections = cache.get(_cache_key(file_path))
    if not sections:
        return None

    return normalize_sections(sections)


def set_cached_sections(file_path: Path, sections: list[str]) -> None:
    clean_sections = normalize_sections(sections)
    if not clean_sections or not file_path.exists():
        return

    cache = _read_cache()
    cache[_cache_key(file_path)] = clean_sections
    _write_cache(cache)


def get_sections_from_doc_store(source: str) -> list[str]:
    if not DOCS_PATH.exists():
        return []

    with DOCS_PATH.open("rb") as f:
        docs = pickle.load(f)

    return sections_from_chunks([
        doc for doc in docs
        if doc.get("source") == source
    ])


def get_section_text_from_doc_store(source: str, section: str) -> str:
    if not DOCS_PATH.exists():
        return ""

    section_l = section.lower().strip()

    with DOCS_PATH.open("rb") as f:
        docs = pickle.load(f)

    matches = [
        doc.get("text", "")
        for doc in docs
        if doc.get("source") == source
        and str(doc.get("section", "")).lower().strip() == section_l
    ]

    return "\n\n".join(text for text in matches if text).strip()
