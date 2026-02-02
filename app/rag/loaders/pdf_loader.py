import pdfplumber
import re
from app.rag.utils import hash_text


# -------------------------------------------------
# Heuristic: detect section headings
# -------------------------------------------------
def is_heading(line: str) -> bool:
    line = line.strip()

    if len(line) < 5:
        return False

    # ALL CAPS headings
    if line.isupper():
        return True

    # Title Case / sentence-less headings
    if (
        re.match(r"^[A-Z][A-Za-z0-9 ,\-–()]{5,}$", line)
        and not line.endswith(".")
    ):
        return True

    return False


# -------------------------------------------------
# Section-aware PDF text extraction
# -------------------------------------------------
def extract_pdf_sections(file_path: str, source_name: str):
    """
    Extract text from PDF while preserving section structure.
    Returns chunks ready for ingest_chunks().
    """
    chunks_with_meta = []

    with pdfplumber.open(file_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            raw_text = page.extract_text()

            if not raw_text:
                continue

            # Preserve line structure
            lines = [
                l.strip()
                for l in raw_text.split("\n")
                if l.strip()
            ]

            current_section = "Unknown"
            buffer = []

            for line in lines:
                if is_heading(line):
                    # Flush previous section
                    if buffer:
                        text_block = " ".join(buffer).strip()
                        if text_block:
                            chunks_with_meta.append({
                                "text": text_block,
                                "section": current_section,
                                "page": page_idx + 1,
                                "source": source_name,
                                "chunk_hash": hash_text(text_block),
                            })
                        buffer = []

                    current_section = line
                else:
                    buffer.append(line)

            # Flush remaining text on page
            if buffer:
                text_block = " ".join(buffer).strip()
                if text_block:
                    chunks_with_meta.append({
                        "text": text_block,
                        "section": current_section,
                        "page": page_idx + 1,
                        "source": source_name,
                        "chunk_hash": hash_text(text_block),
                    })

    return chunks_with_meta
