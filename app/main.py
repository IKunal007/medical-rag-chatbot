from fastapi import FastAPI
from app.api import router

app = FastAPI(title="Local RAG Backend")
app.include_router(router)
