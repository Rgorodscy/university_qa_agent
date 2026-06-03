"""
Demo script — exercises the agent's retry loop with controlled failures.
Use this to demonstrate error handling in live demos or interviews.

Usage:
    python demo.py retry      # attempt 1 fails, agent recovers on attempt 2
    python demo.py exhausted  # all attempts fail, agent gives up gracefully
"""

import sys
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv
from db.seed import seed
from agent.graph import qa_graph
from agent.nodes import MAX_RETRIES

load_dotenv()


QUESTION = "Who teaches Algorithms?"


def _state(question: str) -> dict:
    return {
        "question": question,
        "sql_query": None,
        "sql_results": None,
        "error": None,
        "retry_count": 0,
        "answer": None,
    }


def _response(content: str) -> MagicMock:
    m = MagicMock()
    m.content = content
    return m


def demo_retry():
    """First attempt returns forbidden SQL, second attempt succeeds."""
    print(f"\nQuestion: {QUESTION}")
    print("Demo:     retry recovery")
    print("-" * 60)

    real_llm = None
    call_count = 0

    def patched_invoke(messages):
        nonlocal call_count, real_llm
        call_count += 1
        if call_count == 1:
            print("  [attempt 1] LLM returns forbidden SQL → blocked by validate_sql")
            return _response("DROP TABLE students")
        print(
            f"  [attempt {call_count}] LLM retries with error context → generates valid SQL"
        )
        return real_llm.invoke(messages)

    import agent.nodes as nodes_module

    real_llm = nodes_module.get_llm()

    with patch("agent.nodes.get_llm") as mock:
        mock.return_value.invoke.side_effect = patched_invoke
        result = qa_graph.invoke(_state(QUESTION))

    _print_result(result)


def demo_exhausted():
    """All SQL attempts return forbidden SQL — agent gives up gracefully."""
    print(f"\nQuestion: {QUESTION}")
    print("Demo:     retries exhausted")
    print("-" * 60)

    real_llm = None
    call_count = 0

    def patched_invoke(messages):
        nonlocal call_count, real_llm
        call_count += 1
        if call_count <= MAX_RETRIES + 1:
            print(f"  [attempt {call_count}] LLM returns forbidden SQL → blocked")
            return _response("DROP TABLE students")
        print(f"  [attempt {call_count}] Retries exhausted → handle_error")
        return real_llm.invoke(messages)

    import agent.nodes as nodes_module

    real_llm = nodes_module.get_llm()

    with patch("agent.nodes.get_llm") as mock:
        mock.return_value.invoke.side_effect = patched_invoke
        result = qa_graph.invoke(_state(QUESTION))

    _print_result(result)


def _print_result(result: dict):
    print()
    print(f"Retries:  {result.get('retry_count', 0)}")
    print(f"SQL:      {result.get('sql_query')}")
    print(f"Answer:   {result.get('answer')}")


if __name__ == "__main__":
    seed()
    mode = sys.argv[1] if len(sys.argv) > 1 else ""

    if mode == "retry":
        demo_retry()
    elif mode == "exhausted":
        demo_exhausted()
    else:
        print("Usage:")
        print("  python demo.py retry      # agent recovers after bad SQL")
        print("  python demo.py exhausted  # agent gives up gracefully")
        sys.exit(1)
