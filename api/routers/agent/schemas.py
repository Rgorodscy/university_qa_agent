from typing import Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=500)


class QueryResponse(BaseModel):
    question: str
    answer: str
    sql_query: Optional[str] = None
    row_count: Optional[int] = None
    error: Optional[str] = None
