"""
End-to-end tests for the LangGraph agent.
LLM is fully mocked — tests verify graph routing, retry logic, and error handling.
No API key required.
"""

import pytest
from unittest.mock import patch, MagicMock, call

from agent.graph import ask, build_graph
from agent.state import AgentState


def _llm_response(content: str) -> MagicMock:
    mock = MagicMock()
    mock.content = content
    return mock


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestHappyPath:
    def test_simple_question_returns_answer(self):
        sql = "select t.name from teachers t join course_offerings co on t.id = co.teacher_id join courses c on co.course_id = c.id where c.name like '%Algorithms%'"
        answer = "Prof. David Kim teaches Algorithms."

        with patch("agent.nodes.get_llm") as mock_llm:
            mock_llm.return_value.invoke.side_effect = [
                _llm_response(sql),  # generate_sql call
                _llm_response(answer),  # format_answer call
            ]
            result = (
                ask("Who teaches Algorithms?", trace=False)
                if _ask_supports_trace()
                else ask("Who teaches Algorithms?")
            )

        assert result.get("answer") == answer
        assert result.get("sql_query") == sql
        assert result.get("error") is None
        assert result.get("retry_count") == 0

    def test_aggregation_question(self):
        sql = "select avg(e.grade) as avg_grade from enrollments e join course_offerings co on e.offering_id = co.id join courses c on co.course_id = c.id where c.name like '%Machine Learning%' and e.grade is not null"
        answer = "The average grade in Machine Learning is 95.3."

        with patch("agent.nodes.get_llm") as mock_llm:
            mock_llm.return_value.invoke.side_effect = [
                _llm_response(sql),
                _llm_response(answer),
            ]
            result = _invoke("What is the average grade in Machine Learning?")

        assert result.get("answer") == answer
        assert result.get("sql_results") is not None

    def test_result_has_expected_state_keys(self):
        sql = "select name from students limit 1"
        with patch("agent.nodes.get_llm") as mock_llm:
            mock_llm.return_value.invoke.side_effect = [
                _llm_response(sql),
                _llm_response("There is one student."),
            ]
            result = _invoke("List students")

        for key in [
            "question",
            "sql_query",
            "sql_results",
            "answer",
            "error",
            "retry_count",
        ]:
            assert key in result


# ---------------------------------------------------------------------------
# Validation failure + retry
# ---------------------------------------------------------------------------


class TestRetryLogic:
    def test_retries_on_forbidden_sql(self):
        """First LLM call returns a DROP TABLE — agent should retry with a SELECT."""
        bad_sql = "DROP TABLE students"
        good_sql = "select name from students"
        answer = "There are students in the database."

        with patch("agent.nodes.get_llm") as mock_llm:
            mock_llm.return_value.invoke.side_effect = [
                _llm_response(bad_sql),  # first attempt — blocked by validate_sql
                _llm_response(good_sql),  # retry
                _llm_response(answer),  # format_answer
            ]
            result = _invoke("List all students")

        assert result.get("answer") == answer
        assert result.get("retry_count") == 1

    def test_retries_on_execution_error(self):
        """First SQL references a non-existent table — agent should retry."""
        bad_sql = "select * from nonexistent_table"
        good_sql = "select name from students"
        answer = "Here are the students."

        with patch("agent.nodes.get_llm") as mock_llm:
            mock_llm.return_value.invoke.side_effect = [
                _llm_response(bad_sql),
                _llm_response(good_sql),
                _llm_response(answer),
            ]
            result = _invoke("List students")

        assert result.get("answer") == answer
        assert result.get("retry_count") == 1

    def test_gives_up_after_max_retries(self):
        """If the LLM keeps returning bad SQL, agent should give up gracefully."""
        bad_sql = "DROP TABLE students"
        give_up_msg = "I couldn't answer that question. Please try rephrasing."

        with patch("agent.nodes.get_llm") as mock_llm:
            mock_llm.return_value.invoke.side_effect = [
                _llm_response(bad_sql),  # attempt 1
                _llm_response(bad_sql),  # attempt 2
                _llm_response(bad_sql),  # attempt 3
                _llm_response(give_up_msg),  # handle_error
            ]
            result = _invoke("Do something bad")

        assert result.get("answer") == give_up_msg
        assert result.get("retry_count") == 2


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_graceful_failure_message_is_human_readable(self):
        """handle_error should return a friendly message, not a stack trace."""
        bad_sql = "DELETE FROM students"
        error_msg = "Sorry, I couldn't answer your question. Try rephrasing it."

        with patch("agent.nodes.get_llm") as mock_llm:
            mock_llm.return_value.invoke.side_effect = [
                _llm_response(bad_sql),
                _llm_response(bad_sql),
                _llm_response(bad_sql),
                _llm_response(error_msg),
            ]
            result = _invoke("Delete all students")

        assert result.get("answer") is not None
        assert len(result.get("answer")) > 0
        # Should not expose internal error details to the user
        assert "Traceback" not in result.get("answer")
        assert "Exception" not in result.get("answer")

    def test_empty_results_still_returns_answer(self):
        """A valid query that returns no rows should produce a helpful answer."""
        sql = "select * from students where major = 'Quantum Physics'"
        answer = "No students are enrolled in that major."

        with patch("agent.nodes.get_llm") as mock_llm:
            mock_llm.return_value.invoke.side_effect = [
                _llm_response(sql),
                _llm_response(answer),
            ]
            result = _invoke("List students majoring in Quantum Physics")

        assert result.get("answer") == answer
        assert result.get("sql_results") == []


# ---------------------------------------------------------------------------
# Retry loop — explicit demonstration tests
# These mirror exactly what --demo-retry and --demo-exhausted do in main.py
# ---------------------------------------------------------------------------


class TestRetryLoopDemo:
    def test_demo_retry_recovers(self):
        """
        Simulates the --demo-retry scenario:
        - Attempt 1: LLM returns forbidden SQL -> validate_sql blocks it
        - Attempt 2: LLM returns valid SQL -> executes successfully
        Verifies the agent recovers and produces a real answer.
        """
        bad_sql = "DROP TABLE students"
        good_sql = "select distinct t.name from teachers t join course_offerings co on t.id = co.teacher_id join courses c on co.course_id = c.id where c.name like '%Algorithms%'"
        answer = "Prof. David Kim teaches Algorithms."

        with patch("agent.nodes.get_llm") as mock_llm:
            mock_llm.return_value.invoke.side_effect = [
                _llm_response(bad_sql),
                _llm_response(good_sql),
                _llm_response(answer),
            ]
            result = _invoke("Who teaches Algorithms?")

        assert result.get("retry_count") == 1
        assert result.get("answer") == answer
        assert result.get("error") is None
        assert result.get("sql_query") == good_sql

    def test_demo_exhausted_gives_graceful_message(self):
        """
        Simulates the --demo-exhausted scenario:
        - All SQL generation attempts return forbidden SQL
        - Retries exhausted -> handle_error produces a graceful message
        Verifies the agent never crashes and always returns something user-friendly.
        """
        from agent.nodes import MAX_RETRIES

        bad_sql = "DROP TABLE students"
        graceful_msg = (
            "I wasn't able to answer your question. Please try rephrasing it."
        )

        responses = [_llm_response(bad_sql)] * (MAX_RETRIES + 1)
        responses.append(_llm_response(graceful_msg))

        with patch("agent.nodes.get_llm") as mock_llm:
            mock_llm.return_value.invoke.side_effect = responses
            result = _invoke("Who teaches Algorithms?")

        assert result.get("retry_count") == MAX_RETRIES
        assert result.get("answer") == graceful_msg
        assert "Traceback" not in result.get("answer")
        assert "Exception" not in result.get("answer")

    def test_retry_prompt_includes_previous_error(self):
        """
        When retrying, the prompt sent to the LLM must include
        the previous error so it can self-correct.
        """
        captured = []

        def capture(messages):
            captured.append(messages[0].content)
            if len(captured) == 1:
                return _llm_response("DROP TABLE students")
            if len(captured) == 2:
                return _llm_response("select * from students")
            return _llm_response("Here are the students.")

        with patch("agent.nodes.get_llm") as mock_llm:
            mock_llm.return_value.invoke.side_effect = capture
            _invoke("List all students")

        assert len(captured) >= 2
        assert "Previous attempt failed" in captured[1]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _invoke(question: str) -> dict:
    """Invoke the graph directly with a clean initial state."""
    from agent.graph import qa_graph

    return qa_graph.invoke(
        {
            "question": question,
            "sql_query": None,
            "sql_results": None,
            "error": None,
            "retry_count": 0,
            "answer": None,
        }
    )


def _ask_supports_trace() -> bool:
    import inspect

    return "trace" in inspect.signature(ask).parameters
