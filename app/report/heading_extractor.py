import re
from app.report.extractor import extract_exact_section

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

    # Capture markdown headings
    pattern = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)
    matches = pattern.findall(md)

    cleaned = []

    for _, raw_title in matches:
        title = raw_title.strip()

        # Normalize
        title_l = title.lower()

        if title_l in SKIP_TITLES:
            continue  # skip non-content sections

        # Extract text for this section
        text = extract_exact_section(doc, title)

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
