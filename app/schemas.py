from pydantic import BaseModel
from typing import Optional, List, Union, Literal

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


class ReportSection(BaseModel):
    name: str
    action: Literal[
        "extract_exact",
        "extract_tables",
        "extract_figures",
        "summarize"
    ]
    source_section: Optional[str] = None  # for summaries only


class ReportRequest(BaseModel):
    session_id: str
    sections: list[ReportSection]


class ReportResponse(BaseModel):
    report_path: str
