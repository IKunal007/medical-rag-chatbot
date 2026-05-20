import streamlit as st
import requests
import uuid
import time
import html

# ----------------------------
# Page config MUST come first
# ----------------------------
st.set_page_config(
    page_title="IntelliDoc Chatbot",
    layout="centered"
)

# ----------------------------
# API configuration
# ----------------------------
API_BASE = "http://api:8000"
CHAT_URL = f"{API_BASE}/chat"
REPORT_URL = f"{API_BASE}/report"
REPORT_DOWNLOAD_URL = f"{API_BASE}/report/download"

# ----------------------------
# Backend readiness check
# ----------------------------
def wait_for_api(timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(f"{API_BASE}/health", timeout=1)
            if r.status_code == 200:
                return True
        except Exception:
            time.sleep(1)
    return False


with st.spinner("Loading..."):
    if not wait_for_api():
        st.error("Backend is not ready. Please refresh.")
        st.stop()

# ----------------------------
# Session state
# ----------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "ingesting" not in st.session_state:
    st.session_state.ingesting = False

# ----------------------------
# Sidebar navigation
# ----------------------------
# ----------------------------
# Sidebar navigation (custom)
# ----------------------------
st.sidebar.markdown("### Navigation")

if "page" not in st.session_state:
    st.session_state.page = "Chat"


def nav_button(label, value):
    clicked = st.sidebar.button(
        label,
        use_container_width=True
    )
    if clicked:
        st.session_state.page = value


nav_button(" Chat", "Chat")
nav_button(" Upload Documents", "Upload")
nav_button(" Report Generation", "Report")

st.sidebar.divider()
st.sidebar.caption("Medical RAG System • v2.3")


CHAT_CSS = """
<style>
    .main .block-container {
        max-width: 920px;
        padding-top: 2rem;
        padding-bottom: 5rem;
    }

    .chat-hero {
        border-bottom: 1px solid rgba(148, 163, 184, 0.22);
        margin-bottom: 1.2rem;
        padding-bottom: 1rem;
    }

    .chat-title {
        font-size: 2rem;
        font-weight: 750;
        line-height: 1.15;
        margin: 0;
        color: #f8fafc;
    }

    .chat-status-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin-top: 0.75rem;
    }

    .chat-pill {
        border: 1px solid rgba(148, 163, 184, 0.24);
        border-radius: 999px;
        color: #cbd5e1;
        font-size: 0.78rem;
        padding: 0.22rem 0.62rem;
        background: rgba(15, 23, 42, 0.62);
    }

    .chat-window {
        display: flex;
        flex-direction: column;
        gap: 1.35rem;
        margin-top: 1.2rem;
    }

    .message-row {
        display: flex;
        gap: 0.65rem;
        align-items: flex-start;
        margin-bottom: 0.15rem;
    }

    .message-row.user {
        justify-content: flex-end;
        margin-top: 0.35rem;
        margin-bottom: 0.1rem;
    }

    .message-row.user + .message-row.assistant {
        margin-top: 0.65rem;
    }

    .avatar {
        width: 2rem;
        height: 2rem;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.78rem;
        font-weight: 700;
        flex: 0 0 2rem;
        margin-top: 0.1rem;
    }

    .assistant .avatar {
        background: #64748b;
        color: #f8fafc;
    }

    .user .avatar {
        background: #475569;
        color: #f8fafc;
        order: 2;
    }

    .bubble {
        max-width: min(720px, 82%);
        border-radius: 8px;
        padding: 0.78rem 0.95rem;
        line-height: 1.55;
        font-size: 0.98rem;
        border: 1px solid rgba(148, 163, 184, 0.18);
    }

    .assistant .bubble {
        background: rgba(31, 41, 55, 0.82);
        color: #f1f5f9;
        border-color: rgba(148, 163, 184, 0.24);
    }

    .user .bubble {
        background: rgba(71, 85, 105, 0.92);
        color: #f8fafc;
        border-color: rgba(203, 213, 225, 0.24);
    }

    .sources {
        display: flex;
        flex-wrap: wrap;
        gap: 0.42rem;
        margin-top: 0.68rem;
    }

    .source-chip {
        display: inline-flex;
        align-items: center;
        min-height: 1.65rem;
        border-radius: 999px;
        border: 1px solid rgba(148, 163, 184, 0.32);
        color: #cbd5e1 !important;
        background: rgba(51, 65, 85, 0.54);
        padding: 0.18rem 0.58rem;
        font-size: 0.78rem;
        text-decoration: none !important;
    }

    .empty-chat {
        border: 1px dashed rgba(148, 163, 184, 0.28);
        border-radius: 8px;
        padding: 1.1rem;
        color: #94a3b8;
        background: rgba(15, 23, 42, 0.42);
        margin-top: 0.75rem;
    }

    div[data-testid="stChatInput"] {
        border-top: 1px solid rgba(148, 163, 184, 0.16);
        background: rgba(2, 6, 23, 0.76);
    }
</style>
"""


def render_chat_message(role, content, answers=None):
    safe_content = html.escape(content or "").replace("\n", "<br>")
    row_class = "user" if role == "user" else "assistant"
    avatar = "You" if role == "user" else "AI"

    sources_html = ""
    if answers:
        chips = []
        seen = set()
        for answer in answers:
            doc = answer.get("document")
            link = answer.get("link")
            page = answer.get("page")

            if not doc or not link:
                continue

            label = f"{doc}"
            if page is not None:
                label = f"{label} · page {page}"

            key = (label, link)
            if key in seen:
                continue
            seen.add(key)

            chips.append(
                f'<a class="source-chip" href="{html.escape(link)}" target="_blank">'
                f'{html.escape(label)}</a>'
            )

        if chips:
            sources_html = f'<div class="sources">{"".join(chips)}</div>'

    st.markdown(
        f"""
        <div class="message-row {row_class}">
            <div class="avatar">{avatar}</div>
            <div class="bubble">{safe_content}{sources_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ==========================================================
# 📤 UPLOAD PAGE
# ==========================================================
def render_upload_page():
    st.title(" Upload & Ingest Documents")

    if st.session_state.get("upload_success"):
        st.success("Document uploaded successfully")
        del st.session_state.upload_success


    uploaded_files = st.file_uploader(
        "Upload medical documents",
        type=["pdf", "docx", "txt", "xlsx"],
        accept_multiple_files=True
    )

    if uploaded_files and not st.session_state.ingesting:
        if st.button("Ingest documents"):
            st.session_state.ingesting = True

            with st.spinner("Ingesting documents…"):
                try:
                    files = [
                        ("files", (f.name, f.getvalue(), f.type))
                        for f in uploaded_files
                    ]

                    resp = requests.post(
                        f"{API_BASE}/ingest",
                        files=files,
                        data={"session_id": st.session_state.session_id},
                        timeout=300
                    )

                    if resp.status_code != 200:
                        st.error("Document ingestion failed.")
                    else:
                        result = resp.json()
                        st.success("Ingestion completed!")

                        for f in result.get("files", []):
                            st.write(f"📄 **{f['filename']}** — {f['status']}")

                        # Reset chat after ingestion
                        st.session_state.messages = []

                except Exception as e:
                    st.error(f"Ingestion error: {e}")

            st.session_state.ingesting = False


# ==========================================================
# 💬 CHAT PAGE
# ==========================================================
def render_chat_page():
    st.markdown(CHAT_CSS, unsafe_allow_html=True)
    st.markdown(
        """
        <div class="chat-hero">
            <h1 class="chat-title">IntelliDoc Chat</h1>
            <div class="chat-status-row">
                <span class="chat-pill">Ready</span>
                <span class="chat-pill">Session active</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="chat-window">', unsafe_allow_html=True)
    if not st.session_state.messages:
        st.markdown(
            '<div class="empty-chat">No messages yet.</div>',
            unsafe_allow_html=True,
        )
    else:
        for msg in st.session_state.messages:
            render_chat_message(
                msg["role"],
                msg["content"],
                answers=msg.get("answers")
            )
    st.markdown('</div>', unsafe_allow_html=True)

    user_query = st.chat_input("Ask a question about the uploaded documents")

    if user_query:
        st.session_state.messages.append({
            "role": "user",
            "content": user_query
        })

        render_chat_message("user", user_query)

        with st.spinner("Thinking…"):
            try:
                resp = requests.post(
                    CHAT_URL,
                    json={
                        "query": user_query,
                        "session_id": st.session_state.session_id
                    },
                    timeout=120
                )
            except Exception:
                st.error("Backend unavailable.")
                return

        if resp.status_code != 200:
            st.error("Backend error.")
            return

        data = resp.json()
        answers = data.get("answer", [])

        if not answers:
            reply = "I don't know. The information is not available in the uploaded documents."
            answers = []
        else:
            full_text = []
            for a in answers:
                text = a["text"]
                full_text.append(text)

            reply = " ".join(full_text)

        render_chat_message("assistant", reply, answers=answers)

        st.session_state.messages.append({
            "role": "assistant",
            "content": reply,
            "answers": answers
        })


# ==========================================================
# 📄 REPORT PAGE
# ==========================================================
def render_report_page():

    if "report_doc_uploaded" not in st.session_state:
        st.session_state.report_doc_uploaded = False

    if "available_sections" not in st.session_state:
        st.session_state.available_sections = []

    if "report_generated" not in st.session_state:
        st.session_state.report_generated = False


    st.title("Report Generation")
    st.divider()
    
    # ----------------------------------
    # Upload document (inline)
    # ----------------------------------
    if not st.session_state.report_doc_uploaded and not st.session_state.report_generated:
        st.subheader("Upload Document To Generate Report")
    
        uploaded_files = st.file_uploader(
            "Upload PDF & DOCX files",
            type=["pdf", "docx"],
            accept_multiple_files=False
        )
    
        if uploaded_files:
            with st.spinner("Uploading & ingesting document…"):
                files = [
                    ("files", (uploaded_files.name, uploaded_files.getvalue(), uploaded_files.type))
                ]

                resp = requests.post(
                    f"{API_BASE}/ingest",
                    files=files,
                    data={"session_id": st.session_state.session_id},
                    timeout=300
                )

    
            if resp.status_code != 200:
                st.error("Failed to ingest document")
                st.stop()
    
            st.session_state.report_doc_uploaded = True
            st.session_state.upload_success = True
            st.success("Document uploaded successfully")
    
            # ⬇️ AUTO-load sections immediately
            with st.spinner("Loading available sections…"):
                sec_resp = requests.get(
                    f"{API_BASE}/report/sections",
                    params={"session_id": st.session_state.session_id}
                )
    
            if sec_resp.status_code == 200:
                st.session_state.available_sections = sec_resp.json()["sections"]
            else:
                st.error("Could not load sections")
    
    # --------------------------------------------------
    # 2️⃣ Report mode
    # --------------------------------------------------
    mode = st.radio(
        "Report mode",
        ["Structured sections", "Describe in plain English"]
    )

    sections = []
    user_prompt = None

    # --------------------------------------------------
    # 3️⃣ Structured mode (dropdown-based, dynamic)
    # --------------------------------------------------
    if mode == "Structured sections":
        if not st.session_state.available_sections:
            st.warning("No sections found in document.")

        st.subheader("Select sections from document")

        selected_sections = st.multiselect(
            "Document sections",
            options=st.session_state.available_sections
        )

        for name in selected_sections:
            sections.append({
                "name": name,
                "action": "extract_exact"
            })

        st.divider()

        # Optional extras
        col1, col2 = st.columns(2)

        with col1:
            if st.checkbox("Include tables"):
                sections.append({
                    "name": "Tables",
                    "action": "extract_tables"
                })

            if st.checkbox("Include figures"):
                sections.append({
                    "name": "Figures",
                    "action": "extract_figures"
                })

        with col2:
            if st.checkbox("Add summary"):
                if not selected_sections:
                    st.warning("Select at least one section before adding a summary.")
                else:
                    source = st.selectbox(
                        "Summarize which section?",
                        options=selected_sections
                    )

                    sections.append({
                        "name": "Summary",
                        "action": "summarize",
                        "source_section": source
                    })


    # --------------------------------------------------
    # 4️⃣ Free-text report mode
    # --------------------------------------------------


    else:
        user_prompt = st.text_area(
            "Describe the report you want",
            placeholder="Generate a report with Introduction, Methods, Results and a Summary"
        )

    # --------------------------------------------------
    # 5️⃣ Generate report
    # --------------------------------------------------
    if st.button("Generate Report"):

        if mode == "Structured sections":
            if not sections:
                st.error("Select at least one section.")
                return

            payload = {
                "session_id": st.session_state.session_id,
                "sections": sections
            }
            endpoint = f"{API_BASE}/report"   # deterministic path

        else:  # Describe in plain English
            if not user_prompt:
                st.error("Please describe the report.")
                return

            payload = {
                "session_id": st.session_state.session_id,
                "user_prompt": user_prompt
            }
            endpoint = f"{API_BASE}/report/plan"  # 🔑 LLM planner path

        with st.spinner("Generating report…"):
            resp = requests.post(endpoint, json=payload)

        if resp.status_code != 200:
            st.error(resp.text)
            return

        st.success("Report generated successfully!")
        st.session_state.report_generated = True

        download_resp = requests.get(
            "http://api:8000/report/download",
            params={"session_id": st.session_state.session_id},
            timeout=30
        )

        if download_resp.status_code == 200:
            st.download_button(
                label="⬇ Download report",
                data=download_resp.content,
                file_name="medical_report.pdf",
                mime="application/pdf",
            )
        else:
            st.error("Could not download report from backend")


        # ----------------------------------
        # Reset / New report button
        # ----------------------------------
        st.divider()

    if st.button("🔄 Start New Report"):

        # 1️⃣ Reset backend
        requests.post(
            f"{API_BASE}/report/reset",
            json={"session_id": st.session_state.session_id},
            timeout=10
        )

        # 2️⃣ Clear frontend state
        st.session_state.clear()

        # 3️⃣ Reinitialize required keys
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.page = "Report"
        st.session_state.report_doc_uploaded = False
        st.session_state.available_sections = []
        st.session_state.report_generated = False

        st.rerun()


# ==========================================================
# Page routing
# ==========================================================
if st.session_state.page == "Upload":
    render_upload_page()

elif st.session_state.page == "Chat":
    render_chat_page()

elif st.session_state.page == "Report":
    render_report_page()
