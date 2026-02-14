# app/store/file_resolver.py
from pathlib import Path
from app.memory.utils import UPLOAD_DIR


def get_uploaded_pdf(filename: str) -> Path:
    """
    Backend-only helper.
    Resolves an uploaded PDF filename to a filesystem path.
    """

    pdf_path = UPLOAD_DIR / filename

    if not pdf_path.exists():
        raise FileNotFoundError(f"File not found: {filename}")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported for report generation")

    return pdf_path
