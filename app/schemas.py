from pydantic import BaseModel
from typing import Optional, List, Union

class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class AnswerChunk(BaseModel):
    text: str
    document: str
    page: Optional[Union[int, str]] = None
    link: Optional[str] = None
class ChatResponse(BaseModel):
    answer: List[AnswerChunk]