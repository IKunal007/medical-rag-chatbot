# app/report/docling_converter.py

from pathlib import Path
import time
from typing import Dict

def convert_pdf_to_markdown_bundle(
    pdf_path: Path,
    output_dir: Path,
) -> Dict[str, Path]:
    """
    Converts a PDF into markdown + extracted images using docling.
    Heavy dependencies are imported lazily.
    """

    # 🔒 Lazy imports (VERY important)
    from docling.datamodel.accelerator_options import (
        AcceleratorDevice,
        AcceleratorOptions,
    )
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import (
        PdfPipelineOptions,
        TableStructureOptions,
    )
    from docling.document_converter import (
        DocumentConverter,
        PdfFormatOption,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)

    # -----------------------------
    # Pipeline Configuration
    # -----------------------------
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False
    pipeline_options.do_table_structure = True
    pipeline_options.generate_picture_images = True
    pipeline_options.images_scale = 3.0
    pipeline_options.table_structure_options = TableStructureOptions(
        do_cell_matching=True
    )
    pipeline_options.accelerator_options = AcceleratorOptions(
        num_threads=4,
        device=AcceleratorDevice.AUTO,
    )

    doc_converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options
            )
        }
    )

    # -----------------------------
    # Run Conversion
    # -----------------------------
    start = time.time()
    conv_result = doc_converter.convert(pdf_path)

    if conv_result.status != "success":
        raise RuntimeError("Docling conversion failed")

    doc = conv_result.document

    # -----------------------------
    # Export Markdown
    # -----------------------------
    md_path = output_dir / "document.md"
    md_path.write_text(doc.export_to_markdown(), encoding="utf-8")

    strict_md_path = output_dir / "document_strict.txt"
    strict_md_path.write_text(
        doc.export_to_markdown(strict_text=True),
        encoding="utf-8",
    )

    # -----------------------------
    # Extract Images
    # -----------------------------
    image_paths = []
    if hasattr(doc, "pictures"):
        for i, pic in enumerate(doc.pictures):
            if pic.image and hasattr(pic.image, "pil_image"):
                img_path = images_dir / f"image_{i}.png"
                pic.image.pil_image.save(img_path)
                image_paths.append(img_path)

    return {
        "markdown": md_path,
        "strict_text": strict_md_path,
        "images": image_paths,
        "elapsed_sec": round(time.time() - start, 2),
    }
