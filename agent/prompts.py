from functools import lru_cache
from db.session import generate_schema_context

# SQL generation rules appended to the dynamic schema context
SCHEMA_RULES = """
IMPORTANT RULES:
  - To find which teacher teaches a course: JOIN course_offerings ON course_id AND teacher_id
  - To find a student's grade: JOIN enrollments ON offering_id, then JOIN course_offerings
  - Grades can be NULL — use IS NOT NULL filters when computing averages
  - Use LIKE with wildcards for name matching (e.g. WHERE name LIKE '%Algorithms%')
  - Write SQLITE-compatible SQL only
  - Write SELECT queries only — no INSERT, UPDATE, DELETE, DROP
  - Always use table aliases for clarity in JOINs
"""


@lru_cache(maxsize=1)
def get_schema_context() -> str:
    """
    Build the full schema context for the LLM prompt by combining
    the live database schema with the static query rules.

    Result is cached after the first call — the schema only changes
    when models.py is modified and the application restarts.
    """
    return generate_schema_context() + SCHEMA_RULES


SQL_GENERATION_PROMPT = """You are a SQL expert assistant for a university database.

{schema}

Given the user's question, write a single SQL SELECT query that answers it.

Rules:
- Return ONLY the SQL query, no explanation, no markdown, no backticks
- Use lowercase SQL keywords
- Use table aliases (e.g. s for students, t for teachers)
- For average grades, exclude NULL values using WHERE grade IS NOT NULL
- If the question is ambiguous, make reasonable assumptions
- Use LIKE with wildcards for name matching (e.g. WHERE c.name LIKE '%Algorithms%') to handle partial or case variations

{error_context}
Question: {question}

SQL:"""

FORMAT_ANSWER_PROMPT = """You are a helpful university assistant. 
Given a user's question and the database results, write a clear, friendly, concise answer.

Question: {question}

SQL Query used: {sql_query}

Database results: {results}

Rules:
- If results are empty, say so clearly and suggest why
- For numbers, round grades to 1 decimal place
- Be concise — 1 to 3 sentences maximum
- Do not mention SQL or databases in your answer

Answer:"""

CANNOT_ANSWER_PROMPT = """The system was unable to answer the following question after multiple attempts.

Question: {question}
Last error: {error}

Write a short, friendly message explaining that you couldn't answer this question 
and suggest the user try rephrasing it.
"""
