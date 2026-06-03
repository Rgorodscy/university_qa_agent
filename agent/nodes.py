import re
from typing import Any
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

from agent.state import AgentState
from agent.prompts import (
    get_schema_context,
    SQL_GENERATION_PROMPT,
    FORMAT_ANSWER_PROMPT,
    CANNOT_ANSWER_PROMPT,
)
from db.session import get_session

MAX_RETRIES = 2

_llm_instance: ChatGroq | None = None


def get_llm() -> ChatGroq:
    """
    Lazy LLM initialization — avoids crashing on import when no API key is set.
    Returns the same instance on every call (manual singleton).
    Tests can replace _llm_instance directly without cache issues.
    """
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    return _llm_instance


def generate_sql(state: AgentState) -> dict[str, Any]:
    """Ask the LLM to translate the user's question into a SQL query."""
    error_context = ""
    if state.get("error") and state.get("retry_count", 0) > 0:
        error_context = (
            f"Previous attempt failed with error: {state.get('error')}\n"
            f"Previous SQL was: {state.get('sql_query', 'N/A')}\n"
            "Please fix the query.\n\n"
        )

    prompt = SQL_GENERATION_PROMPT.format(
        schema=get_schema_context(),
        error_context=error_context,
        question=state.get("question"),
    )

    response = get_llm().invoke([HumanMessage(content=prompt)])
    sql = _clean_sql(response.content)

    return {
        "sql_query": sql,
        "error": None,
    }


_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|truncate|alter|create|replace)\b",
    re.IGNORECASE,
)


def validate_sql(state: AgentState) -> dict[str, Any]:
    """
    Guard against dangerous SQL. Only allows SELECT statements.
    Returns error key so the router can decide what to do.
    """
    sql = state.get("sql_query", "")

    if not sql or not sql.strip():
        return {"error": "Empty SQL query generated."}

    if _FORBIDDEN.search(sql):
        return {"error": f"Query contains forbidden statement: {sql[:120]}"}

    if not sql.strip().lower().startswith("select"):
        return {"error": f"Only SELECT queries are allowed. Got: {sql[:80]}"}

    return {"error": None}


def execute_sql(state: AgentState) -> dict[str, Any]:
    """Run the validated SQL query and return rows as a list of dicts."""
    sql = state.get("sql_query")
    session = get_session()
    try:
        result = session.execute(text(sql))
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        return {"sql_results": rows, "error": None}
    except SQLAlchemyError as exc:
        return {"sql_results": None, "error": f"SQL execution error: {exc}"}
    finally:
        session.close()


def format_answer(state: AgentState) -> dict[str, Any]:
    """Ask the LLM to turn raw DB rows into a human-readable answer."""
    results = state.get("sql_results") or []
    prompt = FORMAT_ANSWER_PROMPT.format(
        question=state.get("question"),
        sql_query=state.get("sql_query"),
        results=results if results else "No results found.",
    )
    response = get_llm().invoke([HumanMessage(content=prompt)])
    return {"answer": response.content.strip()}


def handle_error(state: AgentState) -> dict[str, Any]:
    """
    Called when retries are exhausted. Generates a graceful failure message
    instead of crashing or returning raw error text to the user.
    """
    prompt = CANNOT_ANSWER_PROMPT.format(
        question=state.get("question"),
        error=state.get("error", "Unknown error"),
    )
    response = get_llm().invoke([HumanMessage(content=prompt)])
    return {"answer": response.content.strip()}


def route_after_validate(state: AgentState) -> str:
    """Direct traffic after validation: proceed to execute or handle error."""
    if state.get("error"):
        retry_count = state.get("retry_count", 0)
        if retry_count < MAX_RETRIES:
            return "retry"
        return "give_up"
    return "execute"


def route_after_execute(state: AgentState) -> str:
    """If execution failed, retry SQL generation if budget allows."""
    if state.get("error"):
        retry_count = state.get("retry_count", 0)
        if retry_count < MAX_RETRIES:
            return "retry"
        return "give_up"
    return "format"


def increment_retry(state: AgentState) -> dict[str, Any]:
    """Bump retry counter before looping back to generate_sql."""
    return {"retry_count": state.get("retry_count", 0) + 1}


def _clean_sql(raw: str) -> str:
    """Strip markdown fences and whitespace the LLM sometimes wraps around SQL."""
    cleaned = re.sub(r"```(?:sql)?", "", raw, flags=re.IGNORECASE)
    return cleaned.replace("```", "").strip()
