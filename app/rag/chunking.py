import re

def split_into_paragraphs(text: str) -> list[str]:
    """
    Split raw text into paragraphs using blank lines.
    Filters out very short fragments.
    """
    paragraphs = re.split(r"\n\s*\n", text)

    cleaned = []
    for p in paragraphs:
        p = p.strip()
        if len(p.split()) >= 30:  # ignore noise
            cleaned.append(p)

    return cleaned


def chunk_by_paragraphs(
    text: str,
    target_words: int = 250,
    overlap_paragraphs: int = 1
) -> list[str]:
    """
    Build chunks by grouping paragraphs until target size is reached.
    """
    paragraphs = split_into_paragraphs(text)
    chunks = []

    current_chunk = []
    current_word_count = 0

    for p in paragraphs:
        p_words = len(p.split())

        if current_word_count + p_words > target_words and current_chunk:
            chunks.append("\n\n".join(current_chunk))

            # paragraph-level overlap
            current_chunk = current_chunk[-overlap_paragraphs:]
            current_word_count = sum(len(x.split()) for x in current_chunk)

        current_chunk.append(p)
        current_word_count += p_words

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks


def clean_extracted_text(text: str) -> str:
    # 1. Fix hyphenated line breaks: "pre-\ncipitating" → "precipitating"
    text = re.sub(r"-\s*\n\s*", "", text)

    # 2. Replace newlines within paragraphs with spaces
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

    # 3. Collapse multiple spaces
    text = re.sub(r"\s{2,}", " ", text)

    # 4. Fix common missing-space issues between words/numbers
    text = re.sub(r"(?<=\D)(?=\d)", " ", text)
    text = re.sub(r"(?<=\d)(?=\D)", " ", text)

    return text.strip()


def is_heading(line: str) -> bool:
    """
    Heuristic to detect section headings.
    """
    line = line.strip()

    if len(line) < 5:
        return False

    # Title Case or ALL CAPS
    if line.isupper():
        return True

    if re.match(r"^[A-Z][A-Za-z0-9\- ,]{5,}$", line):
        return True

    return False


def chunk_by_sections(text: str):
    """
    Splits text into chunks while tracking section headings.
    """
    lines = text.split("\n")

    current_section = "Unknown"
    current_buffer = []

    chunks = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Detect section
        if is_heading(line):
            # Flush previous section
            if current_buffer:
                chunks.append({
                    "section": current_section,
                    "text": "\n".join(current_buffer),
                })
                current_buffer = []

            current_section = line
            continue

        current_buffer.append(line)

    # Flush last
    if current_buffer:
        chunks.append({
            "section": current_section,
            "text": "\n".join(current_buffer),
        })

    return chunks

def chunk_sections_safely(text):
    section_chunks = chunk_by_sections(text)
    final_chunks = []

    for sc in section_chunks:
        sub_chunks = chunk_by_paragraphs(
            sc["text"],
            target_words=250,
            overlap_paragraphs=1
        )
        for ch in sub_chunks:
            final_chunks.append({
                "section": sc["section"],
                "text": ch
            })

    return final_chunks
