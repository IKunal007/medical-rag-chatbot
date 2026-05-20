import tempfile, os, shutil, re

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import List
from pathlib import Path
from app.schemas import (
    ChatResponse,
    ChatRequest,
    ReportRequest,
    ReportResponse,
    ResetRequest,
    ReportPlanRequest
)
from app.report.assembler import assemble_pdf
from app.report.extractor import (
    load_docling_document,
    load_docling_document_for_headings,
    extract_exact_section,
    extract_docx_sections,
    summarize_text
)
from app.report.table_extractor import extract_pdf_tables, extract_docx_tables
from app.report.figure_extractor import extract_pdf_figures
from app.report.planner import plan_report_sections, REPORT_PLAN_SCHEMA, validate_and_normalize_plan
from app.report.heading_extractor import extract_markdown_headings
from app.report.section_cache import (
    get_cached_sections,
    get_section_text_from_doc_store,
    get_sections_from_doc_store,
    sections_from_chunks,
    set_cached_sections,
)

from app.rag.retriever import retrieve
from app.rag.prompt import (
    build_prompt,
    build_report_planner_prompt,
    get_rule_based_chat_reply,
)
from app.rag.llm import call_llm, call_llm_function
from app.rag.utils import chunk_text, hash_text
from app.rag.ingest import ingest_chunks
from app.rag.loaders.pdf_loader import extract_pdf_sections, extract_pdf_section_titles
from app.rag.loaders.docx_loader import extract_docx_text
from app.rag.loaders.excel_loader import extract_excel_text

from app.memory.session_store import set_session_value, get_session_value
from app.memory.store import add_turn, get_memory
from app.storage.file_resolver import get_uploaded_pdf
from app.memory.utils import build_memory_aware_query, UPLOAD_DIR
from fastapi.responses import FileResponse

from app.report.executor import execute_plan
from app.report.assembler import assemble_pdf


UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


router = APIRouter()

@router.get("/files/{filename}")
def get_uploaded_file(filename: str):
    file_path = os.path.join("app/store/uploads", filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path, filename=filename)


def refusal_response():
    return {
        "answer": [
            {
                "text": "I don't know. The information is not available in the uploaded documents.",
                "document": None,
                "page": None,
                "link": None
            }
        ]
    }


def build_reference_link(location: str | None):
    if not location:
        return None

    # Google Drive file
    if location.startswith("gdrive:"):
        file_id = location.replace("gdrive:", "")
        return f"https://drive.google.com/file/d/{file_id}/view"

    # Already a valid URL (uploaded PDFs, etc.)
    if location.startswith("http"):
        return location

    return None


def answer_from_chunk(sentence: str, chunk: dict):
    return {
        "text": sentence,
        "document": chunk["source"],
        "page": chunk.get("page"),
        "link": build_reference_link(chunk.get("location"))
    }


def clean_chunk_id(chunk_id) -> str:
    cleaned = str(chunk_id or "").strip()
    cleaned = cleaned.strip("[](){} ")

    # Some local models return ids like "[file_p4_s0]_p1_l1_c1".
    bracketed = re.search(r"\[([^\]]+)\]", str(chunk_id or ""))
    if bracketed:
        return bracketed.group(1).strip()

    return cleaned


def resolve_chunk_reference(chunk_id, chunk_map: dict, chunks: list[dict]):
    cleaned = clean_chunk_id(chunk_id)

    if cleaned in chunk_map:
        return chunk_map[cleaned]

    for known_id, chunk in chunk_map.items():
        if known_id in cleaned or cleaned in known_id:
            return chunk

    # Fallback for ids where the model got the suffix wrong, e.g.
    # "0028.pdf_p4_s0" when the retrieved chunk id is "0028.pdf_p4_c1".
    match = re.match(r"(.+)_p([^_]+)_", cleaned)
    if not match:
        return None

    source, page = match.groups()
    candidates = [
        chunk for chunk in chunks
        if str(chunk.get("source")) == source
        and str(chunk.get("page")) == str(page)
    ]

    if candidates:
        return candidates[0]

    return None


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    # -----------------------------
    # 1. Resolve session + memory
    # -----------------------------
    session_id = req.session_id or "default"

    rule_based_reply = get_rule_based_chat_reply(req.query)
    if rule_based_reply:
        add_turn(session_id, "user", req.query)
        add_turn(session_id, "assistant", rule_based_reply)
        return {
            "answer": [{
                "text": rule_based_reply,
                "document": None,
                "page": None,
                "link": None
            }]
        }

    memory = get_memory(session_id)

    memory_query = build_memory_aware_query(req.query, memory)
    query_for_retrieval = memory_query.strip() or req.query

    # -----------------------------
    # 2. Retrieve chunks (no gating)
    # -----------------------------
    chunks = retrieve(query_for_retrieval)

    if not chunks:
        add_turn(session_id, "user", req.query)
        return refusal_response()

    # -----------------------------
    # 3. Build chunk lookup
    # -----------------------------
    chunk_map = {}
    for i, c in enumerate(chunks):
        cid = c.get("chunk_id") or f'{c["source"]}_p{c.get("page")}_c{i}'
        c["chunk_id"] = cid
        chunk_map[cid] = c

    # -----------------------------
    # 4. Build prompt
    # -----------------------------
    context = "\n\n".join(
        "\n".join([
            f"[{c['chunk_id']}]",
            f"Document: {c.get('source')}",
            f"Page: {c.get('page')}",
            f"Section: {c.get('section', 'Unknown')}",
            f"Retrieval score: {c.get('retrieval_score')}",
            c["text"],
        ])
        for c in chunks
    )
    prompt = build_prompt(context, req.query)

    # -----------------------------
    # 5. Call LLM
    # -----------------------------
    llm_output = call_llm(prompt)
    answers = llm_output.get("answer")

    if not answers:
        return refusal_response()

    # -----------------------------
    # 6. Normalize LLM output ONCE
    # -----------------------------
    if isinstance(answers, str):
        answers = [{"sentence": answers, "chunk_ids": []}]
    elif isinstance(answers, dict):
        answers = [answers]
    elif isinstance(answers, list) and answers and isinstance(answers[0], str):
        answers = [{"sentence": a, "chunk_ids": []} for a in answers]
    elif not isinstance(answers, list):
        return refusal_response()

    # -----------------------------
    # 7. Build response STRICTLY from LLM
    # -----------------------------
    answer_chunks = []

    for item in answers:
        sentence = item.get("sentence", "").strip()
        chunk_ids = item.get("chunk_ids", [])

        # If LLM says "I don't know", return it directly
        if sentence.lower().startswith("i don't know"):
            return {
                "answer": [{
                    "text": sentence,
                    "document": None,
                    "page": None,
                    "link": None
                }]
            }

        if not sentence:
            continue

        if not chunk_ids and len(chunks) > 0:
            print("LLM answer missing chunk_ids; using top retrieved chunk.")
            c = chunks[0]
        else:
            c = None
            for chunk_id in chunk_ids:
                c = resolve_chunk_reference(chunk_id, chunk_map, chunks)
                if c:
                    break

        if not c:
            print("LLM returned unknown chunk_ids:", chunk_ids)
            c = chunks[0] if chunks else None

        if not c:
            continue

        answer_chunks.append(answer_from_chunk(sentence, c))

    if not answer_chunks:
        return refusal_response()

    # -----------------------------
    # 8. Store memory
    # -----------------------------
    add_turn(session_id, "user", req.query)
    add_turn(session_id, "assistant", " ".join(a["text"] for a in answer_chunks))

    # -----------------------------
    # 9. Return
    # -----------------------------
    return {"answer": answer_chunks}


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/ingest")
async def ingest(
    session_id: str = Form(...),
    files: List[UploadFile] = File(...)
):
    results = []


    # Ensure upload directory exists

    for file in files:
        filename = file.filename
        name = filename.lower()

        # Final, absolute path to saved file
        saved_path = UPLOAD_DIR / filename

        try:
            # --------------------------------------------------
            # 1️⃣ Save RAW file permanently (single source of truth)
            # --------------------------------------------------
            with saved_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            print("Saved file to:", saved_path.resolve())
            print("Exists after write:", saved_path.exists())


            # Reset file pointer (important if reused)
            await file.seek(0)

            # --------------------------------------------------
            # 2️⃣ Create temp file ONLY for parsing
            # --------------------------------------------------
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                shutil.copyfileobj(file.file, tmp)
                tmp_path = tmp.name

            # --------------------------------------------------
            # 3️⃣ INGEST FROM TEMP FILE (unchanged logic)
            # --------------------------------------------------
            if name.endswith(".pdf"):
                chunks_with_meta = extract_pdf_sections(
                    file_path=tmp_path,
                    source_name=filename
                )
                print("PDF EXTRACT RESULT TYPE:", type(chunks_with_meta))
                print("PDF EXTRACT COUNT:", len(chunks_with_meta))
                if chunks_with_meta:
                    print("FIRST EXTRACT SAMPLE:", chunks_with_meta[0].get("text", "")[:300])              

                if not chunks_with_meta:
                    raise HTTPException(400, "No extractable text found in PDF")

                for c in chunks_with_meta:
                    c["location"] = f"http://api:8000/files/{filename}"

                count = ingest_chunks(chunks_with_meta)
                print("CHUNKS BEFORE INGEST:", len(chunks_with_meta))
                print("INGESTED CHUNKS:", count)
                print("SOURCE:", filename)

                # ✅ Set active PDF for this session
                set_session_value(session_id, "active_pdf", filename)
                set_session_value(session_id, "active_doc_type", "pdf")

                available_sections = sections_from_chunks(chunks_with_meta)
                set_session_value(session_id, "available_sections", available_sections)
                set_cached_sections(saved_path, available_sections)

                set_session_value(
                    session_id=session_id,
                    key="active_pdf",
                    value=filename
                )
                results.append({
                    "filename": filename,
                    "status": "ingested",
                    "chunks_created": count
                })
                continue

            pages = []

            if name.endswith(".txt"):
                with open(tmp_path, "r", encoding="utf-8") as f:
                    pages = [{"text": f.read(), "page": None}]

            elif name.endswith(".docx"):
                pages = extract_docx_text(tmp_path)
                sections = extract_docx_sections(tmp_path)

                set_session_value(session_id, "active_pdf", filename)
                set_session_value(session_id, "active_docx", str(saved_path))
                set_session_value(session_id, "docx_sections", sections)
                set_session_value(session_id, "active_doc_type", "docx")

            elif name.endswith(".xlsx"):
                pages = extract_excel_text(tmp_path)

            else:
                results.append({
                    "filename": filename,
                    "status": "skipped",
                    "reason": "Unsupported file type"
                })
                continue

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
            if "tmp_path" in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)

    return {
        "message": "Batch ingestion completed",
        "files": results
    }


@router.post("/report", response_model=ReportResponse)
def generate_report(req: ReportRequest):

    # -----------------------------
    # 1. Resolve report plan
    # -----------------------------
    if req.sections:
        sections_plan = req.sections
    elif req.user_prompt:
        plan = plan_report_sections(req.user_prompt)
        sections_plan = plan["sections"]
    else:
        raise HTTPException(
            status_code=400,
            detail="Either sections or user_prompt must be provided",
        )

    # -----------------------------
    # 2. Resolve document type
    # -----------------------------
    doc_type = get_session_value(req.session_id, "active_doc_type")

    doc = None
    pdf_path = None
    filename = None

    if doc_type == "pdf":
        filename = get_session_value(req.session_id, "active_pdf")
        if not filename:
            raise HTTPException(400, "No PDF uploaded in this session")

        pdf_path = get_uploaded_pdf(filename)

    elif doc_type == "docx":
        docx_sections = get_session_value(req.session_id, "docx_sections")
        if not docx_sections:
            raise HTTPException(400, "No DOCX content available in this session")

        doc = None  # no Docling for DOCX

    else:
        raise HTTPException(400, "Unsupported document type")

    # -----------------------------
    # 3. Execute extraction plan
    # -----------------------------
    report_state = {}
    figures_dir = Path("tmp/images")
    figures_dir.mkdir(parents=True, exist_ok=True)
    needs_tables = any(section.action == "extract_tables" for section in sections_plan)
    needs_figures = any(section.action == "extract_figures" for section in sections_plan)

    full_docling_doc = None
    light_docling_doc = None

    def get_pdf_doc(full: bool = False):
        nonlocal full_docling_doc, light_docling_doc

        if full:
            if full_docling_doc is None:
                full_docling_doc = load_docling_document(
                    pdf_path,
                    include_tables=needs_tables,
                    include_images=needs_figures,
                )
            return full_docling_doc

        if full_docling_doc is not None:
            return full_docling_doc

        if light_docling_doc is None:
            light_docling_doc = load_docling_document_for_headings(pdf_path)
        return light_docling_doc

    for section in sections_plan:

        # -------- TEXT EXTRACTION --------
        if section.action == "extract_exact":

            if doc_type == "pdf":
                content = get_section_text_from_doc_store(filename, section.name)
                if not content:
                    content = extract_exact_section(get_pdf_doc(full=False), section.name)

            elif doc_type == "docx":
                docx_sections = get_session_value(req.session_id, "docx_sections") or {}
                content = docx_sections.get(section.name, "")

            report_state[section.name] = {
                "type": "text",
                "content": content,
            }

        # -------- TABLES (PDF ONLY) --------
        elif section.action == "extract_tables":
            if doc_type == "pdf":
                tables = extract_pdf_tables(get_pdf_doc(full=True))

            elif doc_type == "docx":
                docx_path = get_session_value(req.session_id, "active_docx")
                tables = extract_docx_tables(docx_path)

            else:
                tables = []

            report_state[section.name] = {
                "type": "tables",
                "content": tables,
            }

        # -------- FIGURES (PDF ONLY) --------
        elif section.action == "extract_figures":
            if doc_type != "pdf":
                continue

            report_state[section.name] = {
                "type": "images",
                "content": extract_pdf_figures(get_pdf_doc(full=True), figures_dir),
            }

        # -------- SUMMARY --------
        elif section.action == "summarize":
            source = section.source_section
            if not source or source not in report_state:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid source_section for summary: {source}",
                )

            base_text = report_state[source]["content"]
            report_state[section.name] = {
                "type": "text",
                "content": summarize_text(base_text),
            }

    # -----------------------------
    # 4. Assemble PDF
    # -----------------------------
    REPORT_DIR = Path("app/store/reports")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    output_path = REPORT_DIR / f"{req.session_id}.pdf"

    assemble_pdf(report_state, output_path)

    set_session_value(
        session_id=req.session_id,
        key="report_path",
        value=str(output_path)
    )

    return {"report_path": str(output_path)}


@router.get("/report/sections")
def get_report_sections(session_id: str):
    # ---------------------------------------
    # 1️⃣ Check cache first
    # ---------------------------------------
    cached = get_session_value(session_id, "available_sections")
    if cached:
        return {"sections": cached}

    # ---------------------------------------
    # 2️⃣ Resolve active document + type
    # ---------------------------------------
    filename = get_session_value(session_id, "active_pdf")  # keep name for backward compatibility
    doc_type = get_session_value(session_id, "active_doc_type")

    if not filename or not doc_type:
        raise HTTPException(
            status_code=400,
            detail="No document uploaded for this session"
        )

    # ---------------------------------------
    # 3️⃣ Extract headings based on type
    # ---------------------------------------
    if doc_type == "pdf":
        pdf_path = get_uploaded_pdf(filename)
        cached_sections = get_cached_sections(pdf_path)
        if cached_sections:
            set_session_value(session_id, "available_sections", cached_sections)
            return {"sections": cached_sections}

        file_sections = sections_from_chunks([
            {"section": title}
            for title in extract_pdf_section_titles(str(pdf_path))
        ])
        if file_sections:
            set_cached_sections(pdf_path, file_sections)
            set_session_value(session_id, "available_sections", file_sections)
            return {"sections": file_sections}

        stored_sections = get_sections_from_doc_store(filename)
        if stored_sections:
            set_cached_sections(pdf_path, stored_sections)
            set_session_value(session_id, "available_sections", stored_sections)
            return {"sections": stored_sections}

        doc = load_docling_document_for_headings(pdf_path)
        headings = extract_markdown_headings(doc)
        set_cached_sections(pdf_path, headings)

    elif doc_type == "docx":
        sections = get_session_value(session_id, "docx_sections")
        if not sections:
            raise HTTPException(
                status_code=500,
                detail="DOCX sections not found in session"
            )
        headings = list(sections.keys())

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported document type: {doc_type}"
        )

    # ---------------------------------------
    # 4️⃣ Cache result
    # ---------------------------------------
    set_session_value(
        session_id=session_id,
        key="available_sections",
        value=headings
    )

    return {"sections": headings}


@router.get("/report/download")
def download_report(session_id: str):
    report_path = get_session_value(session_id, "report_path")

    if not report_path:
        raise HTTPException(
            status_code=404,
            detail="No report found for this session"
        )

    path = Path(report_path)

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Report file missing on server"
        )

    return FileResponse(
        path=path,
        media_type="application/pdf",
        filename="medical_report.pdf"
    )


@router.post("/report/reset")
def reset_report_session(req: ResetRequest):
    from app.memory.session_store import clear_session

    clear_session(req.session_id)

    return {"status": "reset"}

#Endpoint to serve uploaded files
@router.get("/files/{filename}")
def serve_uploaded_file(filename: str):
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(file_path)

@router.post("/report/plan")
def plan_report(req: ReportPlanRequest):
    session_id = req.session_id
    user_prompt = req.user_prompt

    # 0️⃣ Load document (THIS was missing)
    filename = get_session_value(session_id, "active_pdf")
    if not filename:
        raise HTTPException(400, "No PDF uploaded in this session")

    pdf_path = get_uploaded_pdf(filename)
    doc = load_docling_document(pdf_path)

    # 1️⃣ LLM planner (planning ONLY)
    plan_json = call_llm_function(
        system_prompt=build_report_planner_prompt(user_prompt),
        user_prompt=user_prompt,
        tools=REPORT_PLAN_SCHEMA
    )

    # 2️⃣ Validate & normalize
    plan = validate_and_normalize_plan(plan_json)

    assert isinstance(plan["sections"], list)
    assert isinstance(plan["sections"][0], dict)

    # 3️⃣ Deterministic execution (REAL data)
    sections = execute_plan(plan, doc)
    REPORT_DIR = Path("app/store/reports")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    output_path = REPORT_DIR / f"{req.session_id}.pdf"
    # 4️⃣ Assemble PDF
    assemble_pdf(sections, output_path)

    set_session_value(session_id, "report_path", str(output_path))

    return {"status": "ok"}
