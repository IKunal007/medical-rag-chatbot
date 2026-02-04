import tempfile, os

from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List

from app.schemas import ChatResponse, ChatRequest

from app.rag.retriever import retrieve
from app.rag.prompt import build_prompt
from app.rag.llm import call_llm
from app.rag.utils import chunk_text, hash_text
from app.rag.ingest import ingest_chunks
from app.rag.loaders.pdf_loader import extract_pdf_sections
from app.rag.loaders.docx_loader import extract_docx_text
from app.rag.loaders.excel_loader import extract_excel_text

from app.memory.store import add_turn, get_memory
from app.memory.utils import build_memory_aware_query
from fastapi.responses import FileResponse


router = APIRouter()

@router.get("/files/{filename}")
def get_uploaded_file(filename: str):
    file_path = os.path.join("app/store/uploads", filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path, filename=filename)


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    # -----------------------------
    # 1. Resolve session + memory
    # -----------------------------
    session_id = req.session_id or "default"
    memory = get_memory(session_id)

    memory_query = build_memory_aware_query(req.query, memory)

    # -----------------------------
    # 2. Retrieve relevant chunks
    # -----------------------------
    chunks = retrieve(memory_query)

    if not chunks:
        refusal = "I don't know. The information is not available in the uploaded documents."

        add_turn(session_id, "user", req.query)
        add_turn(session_id, "assistant", refusal)
        return {
            "answer": [
                {
                    "text": refusal,
                    "document": None,
                    "page": None,
                    "link": None
                }
            ]
        }

    # -----------------------------
    # 3. Build chunk lookup (safe)
    # -----------------------------
    chunk_map = {}

    for i, c in enumerate(chunks):
        cid = c.get("chunk_id")
        if not cid:
            cid = f'{c["source"]}_p{c.get("page")}_c{i}'
            c["chunk_id"] = cid
        chunk_map[cid] = c

    # -----------------------------
    # 4. Build prompt
    # -----------------------------
    context = "\n\n".join(
        f"[{c['chunk_id']}]\n{c['text']}" for c in chunks
    )

    prompt = build_prompt(context, req.query)

    # -----------------------------
    # 5. Call LLM (JSON output)
    # -----------------------------
    llm_output = call_llm(prompt)
    
    if (
        "answer" not in llm_output
        or not llm_output["answer"]
    ):
        refusal = "I don't know. The information is not available in the provided documents."
    
        add_turn(session_id, "user", req.query)
        add_turn(session_id, "assistant", refusal)
    
        return {
            "answer": [
                {
                    "sentence": refusal,
                    "citations": []
                }
            ]
        }
    
    
    # -----------------------------
    # 6. Helper: Drive link
    # -----------------------------
    def build_drive_url(location: str | None):
        if not location:
            return None

        if location.startswith("gdrive:"):
            file_id = location.replace("gdrive:", "")
            return f"https://drive.google.com/file/d/{file_id}/view"

        if location.startswith("http"):
            return location

        return None


    # -----------------------------
    # 7. Build FINAL answer chunks
    # -----------------------------
    answer_chunks = []

    for item in llm_output["answer"]:
        sentence = item.get("sentence", "").strip()
        chunk_ids = item.get("chunk_ids", [])

        if not sentence or not chunk_ids:
            continue

        # Anchor to first supporting chunk
        c = chunk_map.get(chunk_ids[0])
        if not c:
            continue

        answer_chunks.append({
            "text": sentence,
            "document": c["source"],
            "page": c.get("page"),
            "link": build_drive_url(c.get("location"))
        })

    # -----------------------------
    # 8. Store memory
    # -----------------------------
    add_turn(session_id, "user", req.query)
    add_turn(
        session_id,
        "assistant",
        " ".join(a["text"] for a in answer_chunks)
    )

    # -----------------------------
    # 9. Return response
    # -----------------------------
    return {
        "answer": answer_chunks
    }


@router.get("/health")
def health():
    return {"status": "ok"}

@router.post("/ingest")
async def ingest(files: List[UploadFile] = File(...)):
    results = []

    UPLOAD_DIR = "app/store/uploads"
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    for file in files:
        filename = file.filename
        name = filename.lower()

        # Read file content
        content = await file.read()

        # Save permanently for serving later
        saved_path = os.path.join(UPLOAD_DIR, filename)
        with open(saved_path, "wb") as f:
            f.write(content)

        # Create temp file ONLY for parsing
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # ---------------- PDF (SECTION-AWARE) ----------------
            if name.endswith(".pdf"):
                chunks_with_meta = extract_pdf_sections(
                    file_path=tmp_path,
                    source_name=filename
                )

                if not chunks_with_meta:
                    raise HTTPException(400, "No extractable text found in PDF")

                # 🔗 add clickable location to all chunks
                for c in chunks_with_meta:
                    c["location"] = f"http://api:8000/files/{filename}"

                count = ingest_chunks(chunks_with_meta)

                results.append({
                    "filename": filename,
                    "status": "ingested",
                    "chunks_created": count
                })
                continue

            # ---------------- OTHER FILE TYPES ----------------
            pages = []

            if name.endswith(".txt"):
                text = content.decode("utf-8")
                pages = [{"text": text, "page": None}]

            elif name.endswith(".docx"):
                pages = extract_docx_text(tmp_path)

            elif name.endswith(".xlsx"):
                pages = extract_excel_text(tmp_path)

            else:
                results.append({
                    "filename": filename,
                    "status": "skipped",
                    "reason": "Unsupported file type"
                })
                continue

            # ---------------- GENERIC CHUNKING ----------------
            chunks_with_meta = []
            for p in pages:
                for c_idx, ch in enumerate(chunk_text(p["text"])):
                    chunks_with_meta.append({
                        "chunk_id": f"{filename}_p{p.get('page')}_c{c_idx}",
                        "chunk_hash": hash_text(
                            f"{filename}|{p.get('page')}|{ch}"
                        ),
                        "text": ch,
                        "source": filename,
                        "page": p.get("page"),
                        "location": f"http://api:8000/files/{filename}"
                    })

            count = ingest_chunks(chunks_with_meta)

            results.append({
                "filename": filename,
                "status": "ingested",
                "chunks_created": count
            })

        except Exception as e:
            results.append({
                "filename": filename,
                "status": "failed",
                "error": str(e)
            })

        finally:
            os.remove(tmp_path)

    return {
        "message": "Batch ingestion completed",
        "files": results
    }
