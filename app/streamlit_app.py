import streamlit as st
import requests
import uuid
import time

# ----------------------------
# Page config MUST come first
# ----------------------------
st.set_page_config(
    page_title="Medical RAG Chatbot",
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


with st.spinner("Starting backend…"):
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
st.sidebar.caption("Medical RAG System • v1.0")

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
    st.title(" Medical RAG Chatbot")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_query = st.chat_input("Ask a question about the uploaded documents")

    if user_query:
        st.session_state.messages.append({
            "role": "user",
            "content": user_query
        })

        with st.chat_message("user"):
            st.write(user_query)

        with st.chat_message("assistant"):
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
                st.write(reply)
            else:
                full_text = []
                for a in answers:
                    text = a["text"]
                    doc = a.get("document")
                    page = a.get("page")
                    link = a.get("link")

                    st.write(text)
                    full_text.append(text)

                    if doc and link:
                        st.markdown(f" [{doc} · page {page}]({link})")

                reply = " ".join(full_text)

        st.session_state.messages.append({
            "role": "assistant",
            "content": reply
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
    if not st.session_state.report_doc_uploaded:
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
    
            st.rerun()   # 🔑 refresh UI
    
    # --------------------------------------------------
    # 2️⃣ Report mode
    # --------------------------------------------------
    mode = st.radio(
        "Report mode",
        ["Structured sections"]
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
    
    # Later add user defined free-text mode where they can describe the report they want in their own words,
    # and we use an LLM to parse it and decide which sections to extract/summarize.

    # # --------------------------------------------------
    # # 4️⃣ Free-text report mode
    # # --------------------------------------------------
    # else:
    #     user_prompt = st.text_area(
    #         "Describe the report you want",
    #         placeholder="Generate a report with Introduction, Methods, Results and a Summary"
    #     )

    # --------------------------------------------------
    # 5️⃣ Generate report
    # --------------------------------------------------
    if st.button("Generate Report"):
        payload = {
            "session_id": st.session_state.session_id
        }

        if mode == "Structured sections":
            if not sections:
                st.error("Select at least one section.")
                return
            payload["sections"] = sections
        else:
            if not user_prompt:
                st.error("Please describe the report.")
                return
            payload["user_prompt"] = user_prompt

        with st.spinner("Generating report…"):
            resp = requests.post(REPORT_URL, json=payload)

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
        # 1️⃣ Reset backend session
        requests.post(
            f"{API_BASE}/report/reset",
            json={"session_id": st.session_state.session_id},
            timeout=10
        )
    
        # 2️⃣ Reset frontend state
        st.session_state.report_doc_uploaded = False
        st.session_state.available_sections = []
        st.session_state.upload_success = False
    
        # 3️⃣ New session ID (important)
        st.session_state.session_id = str(uuid.uuid4())
    
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
