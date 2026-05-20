import re

def extract_markdown_headings(doc):
    """
    Returns a list of meaningful section titles found in Docling markdown.
    Example: ["Introduction", "Methods", "Outcomes"]
    """

    md = doc.export_to_markdown()

    SKIP_TITLES = {
        "references",
        "acknowledgements",
        "acknowledgments",
        "appendix",
        "supplementary",
        "funding",
        "conflicts of interest",
    }

    heading_pattern = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)
    matches = list(heading_pattern.finditer(md))

    cleaned = []

    for idx, match in enumerate(matches):
        raw_title = match.group(2)
        title = raw_title.strip()

        # Normalize
        title_l = title.lower()

        if title_l in SKIP_TITLES:
            continue  # skip non-content sections

        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(md)
        text = md[start:end].strip()

        if not text:
            continue

        if len(text.strip()) < 100:
            continue  # ignore trivial sections

        cleaned.append(title)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for t in cleaned:
        if t.lower() not in seen:
            unique.append(t)
            seen.add(t.lower())

    return unique
