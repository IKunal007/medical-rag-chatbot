from pathlib import Path
from typing import List
import re
from PIL import Image as PILImage
from app.rag.llm import call_llm_raw


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


def extract_tables(doc):
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

def is_useful_image(path: Path) -> bool:
    img = PILImage.open(path)
    w, h = img.size

    # 🚫 tiny images (logos, icons)
    if w < 300 or h < 300:
        return False

    # 🚫 extreme aspect ratios (lines, separators)
    if w / h > 5 or h / w > 5:
        return False

    return True


def extract_figures(doc, output_dir: Path) -> List[Path]:
    """
    Extracts useful figures/images and saves them as PNG files.
    Filters out logos, icons, and decorative images.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    image_paths: List[Path] = []

    if not hasattr(doc, "pictures") or not doc.pictures:
        return image_paths

    for i, pic in enumerate(doc.pictures):
        if not pic.image or not hasattr(pic.image, "pil_image"):
            continue

        img_path = output_dir / f"figure_{i}.png"

        try:
            # Save image first
            pic.image.pil_image.save(img_path)

            # ✅ Keep only meaningful figures
            if is_useful_image(img_path):
                image_paths.append(img_path)
            else:
                img_path.unlink(missing_ok=True)

        except Exception:
            # Safety: never break report generation because of one bad image
            if img_path.exists():
                img_path.unlink()

    return image_paths


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
