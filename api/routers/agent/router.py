from fastapi import APIRouter

from agent.graph import ask
from api.routers.agent.schemas import QueryRequest, QueryResponse

router = APIRouter(prefix="/agent", tags=["Agent"])


@router.post("/query", response_model=QueryResponse)
def agent_query(payload: QueryRequest) -> QueryResponse:
    """
    Ask a natural language question about the university database.
    The LangGraph agent translates it to SQL, executes it, and returns
    a human-readable answer. Full trace available in LangSmith.
    """
    result = ask(payload.question)
    return QueryResponse(
        question=result.get("question"),
        answer=result.get("answer") or "No answer generated.",
        sql_query=result.get("sql_query"),
        row_count=len(result.get("sql_results")) if result.get("sql_results") else None,
        error=result.get("error"),
    )
