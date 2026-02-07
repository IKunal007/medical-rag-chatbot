from pathlib import Path
from typing import List
import re
from app.rag.llm import call_llm_raw
from docx import Document


def load_docling_document(pdf_path: Path):
    """
    Loads a PDF into a Docling document object.
    Heavy imports are done lazily.
    """

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import (
        PdfPipelineOptions,
        TableStructureOptions,
    )
    from docling.datamodel.accelerator_options import (
        AcceleratorOptions,
        AcceleratorDevice,
    )

    pipeline = PdfPipelineOptions()
    pipeline.do_ocr = False
    pipeline.do_table_structure = True
    pipeline.generate_picture_images = True
    pipeline.images_scale = 3.0
    pipeline.table_structure_options = TableStructureOptions(
        do_cell_matching=True
    )
    pipeline.accelerator_options = AcceleratorOptions(
        num_threads=4,
        device=AcceleratorDevice.AUTO,
    )

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline
            )
        }
    )

    result = converter.convert(pdf_path)

    if result.status != "success":
        raise RuntimeError("Docling conversion failed")

    return result.document


def extract_exact_section(doc, section_name: str) -> str:
    """
    Extracts a section by heading from Docling markdown.
    Preserves exact text. No rewriting.
    """

    md = doc.export_to_markdown()
    section = section_name.lower().strip()

    # Match headings like:
    # ## Introduction
    # ### Introduction
    pattern = re.compile(
        rf"(#+\s*{re.escape(section)}\b.*?)(?=\n#+\s|\Z)",
        flags=re.IGNORECASE | re.DOTALL
    )

    match = pattern.search(md)
    if not match:
        return ""

    block = match.group(1)

    # Remove heading line, keep body verbatim
    lines = block.splitlines()
    body = "\n".join(lines[1:]).strip()

    return body


def extract_docx_sections(path: str) -> dict[str, str]:
    """
    Returns:
    {
        "Introduction": "...",
        "Methods": "...",
        ...
    }
    """
    doc = Document(path)

    sections = {}
    current_heading = None
    buffer = []

    for p in doc.paragraphs:
        if p.style.name.startswith("Heading"):
            if current_heading and buffer:
                sections[current_heading] = "\n".join(buffer).strip()

            current_heading = p.text.strip()
            buffer = []
        else:
            if current_heading:
                buffer.append(p.text)

    if current_heading and buffer:
        sections[current_heading] = "\n".join(buffer).strip()

    return sections


def summarize_text(text: str) -> str:
    if not text or not text.strip():
        return ""

    prompt = f"""
You are summarizing medical text.

STRICT RULES:
- Use ONLY the provided text
- Do NOT add facts, interpretations, or conclusions
- Do NOT use external knowledge
- Preserve medical meaning exactly
- Keep the summary concise

TEXT:
{text}
"""

    try:
        summary = call_llm_raw(prompt)
        return summary.strip()
    except Exception as e:
        raise RuntimeError(
            "LLM summarization failed. Ensure the LLM service is running."
        ) from e
