from typing import Any
from langgraph.graph import StateGraph, END

from agent.state import AgentState
from agent.nodes import (
    generate_sql,
    validate_sql,
    execute_sql,
    format_answer,
    handle_error,
    increment_retry,
    route_after_validate,
    route_after_execute,
)


def build_graph() -> StateGraph:
    """
    Construct and compile the LangGraph question-answering graph.

    Flow:
        generate_sql
            → validate_sql
                → [valid]   execute_sql
                    → [success] format_answer → END
                    → [error]   increment_retry → generate_sql (retry)
                → [invalid] increment_retry → generate_sql (retry)
                → [retries exhausted] handle_error → END
    """
    graph = StateGraph(AgentState)

    graph.add_node("generate_sql", generate_sql)
    graph.add_node("validate_sql", validate_sql)
    graph.add_node("execute_sql", execute_sql)
    graph.add_node("format_answer", format_answer)
    graph.add_node("handle_error", handle_error)
    graph.add_node("increment_retry", increment_retry)

    graph.set_entry_point("generate_sql")

    graph.add_edge("generate_sql", "validate_sql")
    graph.add_edge("increment_retry", "generate_sql")
    graph.add_edge("format_answer", END)
    graph.add_edge("handle_error", END)

    graph.add_conditional_edges(
        "validate_sql",
        route_after_validate,
        {
            "execute": "execute_sql",
            "retry": "increment_retry",
            "give_up": "handle_error",
        },
    )

    graph.add_conditional_edges(
        "execute_sql",
        route_after_execute,
        {
            "format": "format_answer",
            "retry": "increment_retry",
            "give_up": "handle_error",
        },
    )

    return graph.compile()


qa_graph = build_graph()


def ask(question: str) -> dict[str, Any]:
    """
    Convenience wrapper. Returns the final AgentState after graph execution.
    Callers can inspect .answer, .sql_query, .sql_results, .error.
    """
    initial_state: AgentState = {
        "question": question,
        "sql_query": None,
        "sql_results": None,
        "error": None,
        "retry_count": 0,
        "answer": None,
    }
    return qa_graph.invoke(initial_state)
