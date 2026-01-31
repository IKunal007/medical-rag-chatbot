from pydantic import BaseModel
from typing import Optional, List, Union

class ChatRequest(BaseModel):
    query: str

class SourceChunk(BaseModel):
    document: str
    page: Optional[Union[int,str]] = None
    url: Optional[str] = None
    chunk_id: str
    chunk_text: str
class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceChunk]
