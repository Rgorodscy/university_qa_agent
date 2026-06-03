from typing import TypedDict, Optional, Any


class AgentState(TypedDict):
    """
    Shared state passed between every node in the LangGraph graph.
    Each node reads what it needs and returns only the keys it mutates.
    """

    # Input
    question: str  # Original natural language question from the user

    # Intermediate
    sql_query: Optional[str]  # Generated SQL query
    sql_results: Optional[list[dict[str, Any]]]  # Rows returned from the DB
    error: Optional[str]  # Last error message, if any
    retry_count: int  # How many times sql generation has been retried

    # Output
    answer: Optional[str]  # Final human-readable answer
