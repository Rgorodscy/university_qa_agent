"""
Tests for SQL generation and validation nodes.
LLM calls are mocked — no API key required.
"""

import pytest
from unittest.mock import patch, MagicMock

from agent.nodes import validate_sql, execute_sql, _clean_sql
from agent.state import AgentState


def _make_state(**overrides) -> AgentState:
    base: AgentState = {
        "question": "test question",
        "sql_query": None,
        "sql_results": None,
        "error": None,
        "retry_count": 0,
        "answer": None,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# _clean_sql helper
# ---------------------------------------------------------------------------


class TestCleanSql:
    def test_strips_markdown_fences(self):
        raw = "```sql\nselect * from students\n```"
        assert _clean_sql(raw) == "select * from students"

    def test_strips_plain_fences(self):
        raw = "```\nselect * from teachers\n```"
        assert _clean_sql(raw) == "select * from teachers"

    def test_passthrough_clean_sql(self):
        sql = "select name from students where id = 1"
        assert _clean_sql(sql) == sql

    def test_strips_whitespace(self):
        raw = "  \n  select * from courses  \n  "
        assert _clean_sql(raw) == "select * from courses"


# ---------------------------------------------------------------------------
# validate_sql node
# ---------------------------------------------------------------------------


class TestValidateSql:
    def test_valid_select_passes(self):
        result = validate_sql(_make_state(sql_query="select * from students"))
        assert result["error"] is None

    def test_empty_sql_fails(self):
        result = validate_sql(_make_state(sql_query=""))
        assert result["error"] is not None

    def test_none_sql_fails(self):
        result = validate_sql(_make_state(sql_query=None))
        assert result["error"] is not None

    def test_drop_table_blocked(self):
        result = validate_sql(_make_state(sql_query="DROP TABLE students"))
        assert result["error"] is not None
        assert "forbidden" in result["error"].lower()

    def test_insert_blocked(self):
        result = validate_sql(
            _make_state(sql_query="INSERT INTO students VALUES (1, 'x')")
        )
        assert result["error"] is not None

    def test_delete_blocked(self):
        result = validate_sql(_make_state(sql_query="DELETE FROM enrollments"))
        assert result["error"] is not None

    def test_update_blocked(self):
        result = validate_sql(_make_state(sql_query="UPDATE teachers SET name='x'"))
        assert result["error"] is not None

    def test_complex_select_passes(self):
        sql = """
            select s.name, avg(e.grade)
            from students s
            join enrollments e on s.id = e.student_id
            where e.grade is not null
            group by s.name
        """
        result = validate_sql(_make_state(sql_query=sql))
        assert result["error"] is None


# ---------------------------------------------------------------------------
# generate_sql node (mocked LLM)
# ---------------------------------------------------------------------------


class TestGenerateSql:
    def _mock_llm_response(self, sql: str):
        mock_response = MagicMock()
        mock_response.content = sql
        return mock_response

    def test_generates_sql_for_simple_question(self):
        expected_sql = "select name from teachers where department = 'Computer Science'"
        with patch("agent.nodes.get_llm") as mock_get_llm:
            mock_get_llm.return_value.invoke.return_value = self._mock_llm_response(
                expected_sql
            )
            from agent.nodes import generate_sql

            result = generate_sql(_make_state(question="List CS teachers"))

        assert result["sql_query"] == expected_sql
        assert result["error"] is None

    def test_cleans_markdown_from_llm_output(self):
        raw_sql = "```sql\nselect * from students\n```"
        with patch("agent.nodes.get_llm") as mock_get_llm:
            mock_get_llm.return_value.invoke.return_value = self._mock_llm_response(
                raw_sql
            )
            from agent.nodes import generate_sql

            result = generate_sql(_make_state(question="List all students"))

        assert result["sql_query"] == "select * from students"

    def test_includes_error_context_on_retry(self):
        """On retry, the prompt should include the previous error."""
        captured_prompts = []

        def capture_invoke(messages):
            captured_prompts.append(messages[0].content)
            mock = MagicMock()
            mock.content = "select * from students"
            return mock

        with patch("agent.nodes.get_llm") as mock_get_llm:
            mock_get_llm.return_value.invoke.side_effect = capture_invoke
            from agent.nodes import generate_sql

            generate_sql(
                _make_state(
                    question="Who teaches CS?",
                    error="no such table: teacher",
                    retry_count=1,
                )
            )

        assert len(captured_prompts) == 1
        assert "no such table: teacher" in captured_prompts[0]
        assert "Previous attempt failed" in captured_prompts[0]


# ---------------------------------------------------------------------------
# execute_sql node (uses real in-memory DB)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_llm_cache():
    """Clear lru_cache on get_llm before each test so mocks work correctly."""
    from agent.nodes import get_llm

    get_llm.cache_clear()
    yield
    get_llm.cache_clear()


@pytest.fixture(scope="module", autouse=True)
def seed_database():
    """Ensure the database is seeded before execute_sql tests run."""
    from db.seed import seed

    seed()


class TestExecuteSql:
    def test_valid_query_returns_rows(self):
        result = execute_sql(_make_state(sql_query="select name from teachers limit 2"))
        assert result["error"] is None
        assert isinstance(result["sql_results"], list)
        assert len(result["sql_results"]) == 2
        assert "name" in result["sql_results"][0]

    def test_invalid_query_returns_error(self):
        result = execute_sql(_make_state(sql_query="select * from nonexistent_table"))
        assert result["error"] is not None
        assert result["sql_results"] is None

    def test_aggregation_query(self):
        result = execute_sql(_make_state(sql_query="""
                select avg(e.grade) as avg_grade
                from enrollments e
                where e.grade is not null
            """))
        assert result["error"] is None
        assert len(result["sql_results"]) == 1
        assert "avg_grade" in result["sql_results"][0]
