from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api import router
from app.integrations.drive_ingest import ingest_from_drive_folder

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    FOLDER_ID = "1Ccz5XU9YTMHf9xxIpN7q3T8DYIqU9-ZW"
    CREDS_PATH = "app/integrations/credentials.json"

    try:
        new_files = ingest_from_drive_folder(FOLDER_ID, CREDS_PATH)
        print(f"[Startup] Drive ingestion complete. New files: {new_files}")
    except Exception as e:
        print(f"[Startup] Drive ingestion failed: {e}")

    yield
    
    # Shutdown
    pass

app = FastAPI(title="Local RAG Backend", lifespan=lifespan)
app.include_router(router)