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


# ----------------------------
# Block startup until API ready
# ----------------------------
with st.spinner("Starting backend…"):
    if not wait_for_api():
        st.error("Backend is not ready. Please refresh in a few seconds.")
        st.stop()


# ----------------------------
# UI
# ----------------------------
st.title("Medical RAG based Chatbot")

st.divider()
st.subheader("📤 Upload documents for ingestion")

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
# File upload
# ----------------------------
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
                    timeout=300
                )

                if resp.status_code != 200:
                    st.error("Document ingestion failed.")
                else:
                    result = resp.json()
                    st.success("Ingestion completed successfully!")

                    for f in result.get("files", []):
                        st.write(
                            f"📄 **{f['filename']}** — {f['status']}"
                        )

                    # ✅ RESET chat ONLY after successful ingestion
                    st.session_state.messages = []
                    st.session_state.session_id = str(uuid.uuid4())

            except Exception as e:
                st.error(f"Ingestion error: {e}")

        st.session_state.ingesting = False


# ----------------------------
# Render chat history
# ----------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])


# ----------------------------
# Chat input
# ----------------------------
user_query = st.chat_input("Ask a question about the uploaded documents")

if user_query:
    # Store & render user message
    st.session_state.messages.append({
        "role": "user",
        "content": user_query
    })

    with st.chat_message("user"):
        st.write(user_query)

    # Assistant response
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
                st.error("Failed to contact backend API.")
                st.stop()

        if resp.status_code != 200:
            st.error("Backend returned an error.")
            st.stop()

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

                full_text.append(text)
                st.write(text)

                if doc:
                    st.caption(f"📄 {doc} · page {page}")

            reply = " ".join(full_text)

    # Store assistant reply
    st.session_state.messages.append({
        "role": "assistant",
        "content": reply
    })
