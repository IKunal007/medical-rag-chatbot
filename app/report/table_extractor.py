import re
from docx import Document

def extract_pdf_tables(doc):
    """
    Extract tables from Docling markdown.
    Returns list of tables with rows preserved exactly.
    """

    md = doc.export_to_markdown()

    tables = []

    table_blocks = re.findall(
        r"((?:\|.+\|\n)+)",
        md
    )

    for block in table_blocks:
        lines = [l.strip() for l in block.splitlines() if l.strip()]

        # Skip malformed tables
        if len(lines) < 2:
            continue

        rows = []

        for line in lines:
            # Skip separator row
            if re.match(r"^\|\s*-+", line):
                continue

            cells = [c.strip() for c in line.strip("|").split("|")]
            rows.append(cells)

        if rows:
            tables.append({
                "rows": rows
            })

    return tables


def extract_docx_tables(docx_path):
    """
    Extract tables from DOCX into a PDF-friendly format.
    Returns: List[{"rows": [[...]]}]
    """
    doc = Document(docx_path)
    tables = []

    for table in doc.tables:
        rows = []

        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            rows.append(cells)

        # Skip empty tables
        if len(rows) < 2:
            continue

        tables.append({"rows": rows})

    return tables
