import tempfile, os

from fastapi import APIRouter, UploadFile, File, HTTPException
from app.schemas import ChatRequest, ChatResponse
from app.rag.retriever import retrieve
from app.rag.prompt import build_prompt
from app.rag.llm import call_llm

from app.rag.utils import chunk_text
from app.rag.ingest import ingest_chunks
from app.rag.loaders.pdf_loader import extract_pdf_text
from app.rag.loaders.docx_loader import extract_docx_text
from app.rag.loaders.excel_loader import extract_excel_text


router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    chunks = retrieve(req.query)

    # Safety: nothing relevant found
    if not chunks:
        return {
            "answer": "I don't know. The information is not available in the uploaded documents.",
            "sources": []
        }

    # Build context for the LLM
    context = "\n".join([c["text"] for c in chunks])
    prompt = build_prompt(context, req.query)
    answer = call_llm(prompt)

    # Build clean, deduplicated sources for the user
    def build_drive_url(location: str):
        if location and location.startswith("gdrive:"):
            file_id = location.replace("gdrive:", "")
            return f"https://drive.google.com/file/d/{file_id}/view"
        return None
    

    sources = []
    seen_chunks = set()

    for idx, c in enumerate(chunks):
        # Stable chunk id (works even if you didn’t store one earlier)
        chunk_id = c.get(
            "chunk_id",
            f'{c["source"]}_p{c.get("page")}_c{idx}'
        )

        if chunk_id in seen_chunks:
            continue
        seen_chunks.add(chunk_id)

        sources.append({
            "document": c["source"],
            "page": c.get("page"),
            "url": build_drive_url(c.get("location")),
            "chunk_id": chunk_id,
            "chunk_text": c["text"]
        })
    
    for c in chunks:
        print(c["source"], c.get("page"))
        print(c["text"][:200])

    return {
        "answer": answer,
        "sources": sources
    }

@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    filename = file.filename
    name = filename.lower()

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        path = tmp.name

    try:
        pages = []

        if name.endswith(".txt"):
            text = content.decode("utf-8")
            pages = [{"text": text, "page": None}]

        elif name.endswith(".pdf"):
            pages = extract_pdf_text(path)
            if not pages:
                raise HTTPException(400, "No extractable text found in PDF")

        elif name.endswith(".docx"):
            pages = extract_docx_text(path)

        elif name.endswith(".xlsx"):
            pages = extract_excel_text(path)

        else:
            raise HTTPException(400, "Supported types: .txt, .pdf, .docx, .xlsx")

        # 🔑 Build chunks WITH metadata
        chunks_with_meta = []
        for p in pages:
            for ch in chunk_text(p["text"]):
                chunks_with_meta.append({
                    "chunk_id": f"{filename}_p{page}_c{idx}",
                    "text": ch,
                    "source": filename,
                    "page": p["page"],
                    "location": f"uploads/{filename}"
                })

        count = ingest_chunks(chunks_with_meta)

        return {
            "message": "Ingestion successful",
            "filename": filename,
            "chunks_created": count
        }

    finally:
        os.remove(path)
