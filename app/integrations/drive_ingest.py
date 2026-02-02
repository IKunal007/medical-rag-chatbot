import os, json, tempfile
from app.integrations.google_drive import (
    get_drive_service,
    list_files_in_folder,
    download_file
)
from app.rag.ingest import ingest_text
from app.rag.loaders.pdf_loader import extract_pdf_sections
from app.rag.loaders.docx_loader import extract_docx_text
from app.rag.loaders.excel_loader import extract_excel_text

INGESTED_TRACKER = "app/store/ingested_drive_files.json"


def load_ingested():
    if os.path.exists(INGESTED_TRACKER):
        with open(INGESTED_TRACKER, "r") as f:
            return json.load(f)
    return {}


def save_ingested(data):
    os.makedirs("app/store", exist_ok=True)
    with open(INGESTED_TRACKER, "w") as f:
        json.dump(data, f, indent=2)


def ingest_from_drive_folder(folder_id: str, creds_path: str):
    service = get_drive_service(creds_path)
    files = list_files_in_folder(service, folder_id)

    ingested = load_ingested()
    new_files = 0

    for f in files:
        if f["id"] in ingested:
            continue

        name = f["name"].lower()
        if not name.endswith((".txt", ".pdf", ".docx", ".xlsx")):
            continue

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = download_file(service, f["id"], tmp.name)

        try:
            pages = []

            if name.endswith(".txt"):
                with open(tmp_path, "r", encoding="utf-8") as fp:
                    pages = [{"text": fp.read(), "page": None}]

            elif name.endswith(".pdf"):
                pages = extract_pdf_sections(
                    file_path=tmp_path,
                    source_name=f["name"]
                )

            elif name.endswith(".docx"):
                pages = extract_docx_text(tmp_path)

            elif name.endswith(".xlsx"):
                pages = extract_excel_text(tmp_path)

            for p in pages:
                ingest_text(
                    text=p["text"],
                    source=f["name"],
                    page=p["page"],
                    location=f"gdrive:{f['id']}",  
                )

            ingested[f["id"]] = f["name"]
            new_files += 1

        finally:
            os.remove(tmp_path)

    save_ingested(ingested)
    return new_files
