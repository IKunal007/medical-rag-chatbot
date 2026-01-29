import tempfile, os

from fastapi import APIRouter, UploadFile, File, HTTPException
from app.schemas import ChatRequest, ChatResponse
from app.rag.retriever import retrieve
from app.rag.prompt import build_prompt
from app.rag.llm import call_llm

from app.rag.ingest import ingest_text, ingest_pages
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
    sources = list({
        f'{c["source"]}' if c["page"] is None
        else f'{c["source"]} (page {c["page"]})'
        for c in chunks
    })

    return {
        "answer": answer,
        "sources": sources
    }

@router.get("/health")
def health():
    return {"status": "ok"}

@router.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    name = file.filename.lower()

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        path = tmp.name

    try:
        if name.endswith(".txt"):
            text = content.decode("utf-8")
            chunks = ingest_text(text, source=file.filename)

        elif name.endswith(".pdf"):
            pages = extract_pdf_text(path)
            if not pages:
                raise HTTPException(400, "No extractable text found in PDF")
            chunks = ingest_pages(pages, source=file.filename)

        elif name.endswith(".docx"):
            pages = extract_docx_text(path)
            chunks = ingest_pages(pages, source=file.filename)

        elif name.endswith(".xlsx"):
            pages = extract_excel_text(path)
            chunks = ingest_pages(pages, source=file.filename)

        else:
            raise HTTPException(400, "Supported types: .txt, .pdf, .docx, .xlsx")

        return {
            "message": "Ingestion successful",
            "filename": file.filename,
            "chunks_created": chunks
        }

    finally:
        os.remove(path)