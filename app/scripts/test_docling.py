from pathlib import Path

from app.report.extractor import (
    load_docling_document,
    extract_figures,
)

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
PDF_PATH = Path("store/uploads/Three-versus-six-sessions-of-problem-solving-train.pdf")
OUTPUT_DIR = Path("tmp/test_figures")

# --------------------------------------------------
# TEST
# --------------------------------------------------
def main():
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF not found: {PDF_PATH}")

    print("📄 Loading document with Docling...")
    doc = load_docling_document(PDF_PATH)

    print("📊 Docling document loaded")

    # --- sanity check ---
    if not hasattr(doc, "pictures"):
        print("❌ Doc has no 'pictures' attribute")
        return

    print(f"🖼 Pictures detected by Docling: {len(doc.pictures)}")

    if not doc.pictures:
        print("⚠️ No figures found in document")
        return

    # --- extract ---
    print("📤 Extracting figures...")
    image_paths = extract_figures(doc, OUTPUT_DIR)

    print(f"✅ Extracted {len(image_paths)} images")

    for p in image_paths:
        print(" -", p.resolve())


if __name__ == "__main__":
    main()