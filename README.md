# Medical Document Chatbot (RAG-Based)

## Overview

This project implements a medical document chatbot using a **Retrieval-Augmented Generation (RAG)** architecture.

The system answers user questions **strictly from uploaded medical documents**, ensuring grounded, citation-backed responses with explicit refusal when information is not present.

The design prioritizes **determinism, safety, and architectural clarity**, with a strict separation between frontend and backend responsibilities

In addition to question answering, the system supports structured medical report generation from uploaded documents only.

Report generation is strictly grounded in retrieved content and follows the same safety, determinism, and citation principles as chat-based Q&A.

---

## Problem Statement

Large language models are prone to hallucination when answering medical questions.  
This project addresses that issue by ensuring:

- Answers are generated only from retrieved document content
- No access to full documents by the LLM
- Deterministic retrieval and citation enforcement
- Explicit refusal when relevant information is missing

---

## Core Capabilities

### What the system does

- Accepts medical documents in PDF, DOCX, TXT, and XLSX formats
- Chunks and embeds documents into a FAISS vector index
- Allows users to ask questions via a chat interface
- Retrieves relevant document chunks deterministically
- Generates grounded answers with citations
- Maintains session-based conversational memory
- Generates structured medical reports from uploaded documents
- Supports section-based report creation (e.g., Introduction, Findings, Summary)
- Uses the same retrieval pipeline for both chat and reports
- Ensures reports are grounded strictly in document content

### What the system does not do

- No hallucinated or speculative answers
- No free-form summarization beyond retrieved text
- No direct LLM access to full documents
- No business logic in the frontend

---

## Architecture Overview

The system follows a clean frontend-backend separation.

---

## Components

### Streamlit Frontend

- Provides chat-based user interface
- Handles document upload and message display
- Sends user queries to backend via HTTP
- Displays answers and citations
- Contains no retrieval, prompt, or LLM logic

### FastAPI Backend

- Single source of truth for all logic
- Manages:
  - Session memory
  - Query rewriting
  - Retrieval from vector store
  - Prompt construction
  - LLM calls
  - Citation enforcement
- Exposes a `/chat` endpoint

### RAG Pipeline

- Section- and paragraph-aware chunking
- Sentence-transformer embeddings
- FAISS CPU-based vector store
- Deterministic similarity search
- Memory-aware query rewriting

### LLM

- Runs locally via Ollama on the host machine
- Accessed via HTTP
- Used only to compose grounded answers
- Never receives full documents directly

## Request Flow

1. User submits a question in the Streamlit UI
2. Streamlit sends a request to the backend
3. Backend augments the query with session memory
4. Relevant chunks are retrieved from FAISS
5. A grounded prompt is constructed using retrieved chunks
6. Backend calls the local LLM via Ollama
7. Answer sentences are mapped back to source chunks
8. Backend returns answer with citations
9. Streamlit renders the response

## Report Generation Flow

1. User uploads a medical document
2. Backend ingests and indexes the document
3. User selects report mode (structured sections or free-text)
4. Backend retrieves relevant chunks per section
5. A structured, grounded prompt is constructed
6. LLM generates report sections with citations
7. Backend assembles the final report
8. Report is returned as a downloadable PDF


## Report Generation

Beyond conversational Q&A, the system supports **structured report generation** from uploaded medical documents.

### Key Characteristics

- Reports are generated **only from retrieved document content**
- Users can request specific sections such as:
  - Introduction
  - Clinical Findings
  - Tables
  - Figures
  - Summary
- The LLM never sees full documents
- Each report section is backed by retrieved chunks
- If requested information is missing, the system explicitly refuses

### How It Works

1. User uploads a document
2. Backend ingests and indexes the document
3. User selects report sections or provides a free-text report request
4. Backend retrieves relevant chunks per section
5. LLM generates section-wise content grounded in retrieval
6. Final report is returned as a downloadable PDF

Report generation reuses the **same retrieval, chunking, and safety logic** as chat-based answering.

### Example Request Payload

```json
{
  "query": "What are the symptoms of diabetes?",
  "session_id": "session_123"
}
```

Example Response Payload

```json
{
  "answer": [
    {
      "text": "Common symptoms include increased thirst and frequent urination.",
      "document": "medical_guide.pdf",
      "page": 3,
      "link": null
    }
  ]
}
```

## Technology Stack

### Language and Runtime

- Python 3.11 (intentionally pinned)

### Backend

- FastAPI
- Uvicorn
- Pydantic
- docling

### Frontend

- Streamlit

### RAG and Document Processing

- Sentence-Transformers
- FAISS (CPU)
- pdfplumber
- python-docx
- openpyxl

### LLM

- Ollama Model : llama 3.1:8B(local inference)

### Dependency Management

- pyproject.toml
- uv
- uv.lock

---


## Deployment Strategy

### Why Docker Is Used

- Streamlit is not compatible with Python 3.13 due to removal of the `imghdr` module
- Docker isolates the application using Python 3.11
- Keeps the host environment clean
- Ensures reproducible builds

### Container Architecture

- Two services using Docker Compose:
  - Backend (FastAPI) running on port 8000
  - Frontend (Streamlit) running on port 8501
- Ollama runs on the host machine

### Networking Rules

- Streamlit communicates with the backend via service name
- Backend communicates with Ollama via `host.docker.internal`

---

## Running the Application

### Prerequisites

- Docker Desktop
- Ollama installed on the host machine

### Steps

Start Ollama:

```bash
ollama serve

### Access the Services

- Streamlit UI: http://localhost:8501
- FastAPI documentation: http://localhost:8000/docs
```

---

## Safety and Design Decisions

- LLM never receives full documents
- Retrieval is deterministic
- Citations are mandatory for every answer
- Explicit refusal when no relevant context is found
- Frontend contains no business logic
- Backend is authoritative

---

## Project Status

- Fully functional end-to-end
- Stable Docker-based environment
- Clean architectural separation
- Report and PDF generation added

