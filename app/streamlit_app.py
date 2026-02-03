import streamlit as st
import requests
import uuid

API_URL = "http://api:8000/chat"


st.set_page_config(
    page_title="Medical RAG Chatbot",
    layout="centered"
)

st.title("Medical RAG based Chatbot")

# ----------------------------
# Session state
# ----------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

# ----------------------------
# Render history
# ----------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# ----------------------------
# Chat input
# ----------------------------
user_query = st.chat_input("Ask a question about the uploaded documents")

if user_query:
    # Show user message
    st.session_state.messages.append({
        "role": "user",
        "content": user_query
    })

    with st.chat_message("user"):
        st.write(user_query)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            resp = requests.post(
                API_URL,
                json={
                    "query": user_query,
                    "session_id": st.session_state.session_id
                },
                timeout=120
            )

        if resp.status_code != 200:
            st.error("API error")
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
