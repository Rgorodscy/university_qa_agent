# University QA Agent

A natural language question-answering system over a university database, built with LangGraph, FastAPI, and SQLAlchemy.

Users ask questions in plain English. The agent translates them to SQL, executes them, and returns human-readable answers — with full tracing via LangSmith.

---

## Architecture

```
User question
     │
     ▼
┌─────────────────────────────────────────────┐
│              LangGraph Agent                │
│                                             │
│  generate_sql → validate_sql → execute_sql  │
│       ▲              │               │      │
│       │         [invalid]        [error]    │
│       └──── increment_retry ────────┘       │
│                                             │
│                        └──→ format_answer   │
│                        └──→ handle_error    │
└─────────────────────────────────────────────┘
     │
     ▼
  Final answer
```

### Key design decisions

**DB-agnostic agent** — the agent has no hardcoded knowledge of the schema. Table names, columns, and relationships are injected via a schema context string in `agent/prompts.py`. To adapt the agent to a different database, only that file needs to change.

**LangGraph over a plain chain** — conditional edges enable the retry loop (bad SQL → regenerate) and explicit state makes every step inspectable. A plain LangChain chain can't express this routing cleanly.

**SQLAlchemy over raw SQL** — the engine abstraction means SQLite locally and PostgreSQL in production with zero code changes.

**FastAPI as a thin transport layer** — the API has no business logic. It calls `ask()` from `agent/graph.py` and returns the result. The agent is completely unaware the API exists.

---

## Project Structure

```
university_qa_agent/
├── agent/
│   ├── state.py        # AgentState TypedDict — shared state across all nodes
│   ├── nodes.py        # Node functions + conditional routing logic
│   ├── graph.py        # LangGraph graph wiring and ask() entrypoint
│   └── prompts.py      # Prompt templates and schema context (isolated)
├── api/
│   ├── app.py          # FastAPI routes (CRUD + /agent/query)
│   └── schemas.py      # Pydantic request/response models
├── db/
│   ├── models.py       # SQLAlchemy ORM models
│   ├── session.py      # Engine, session factory, FastAPI dependency
│   └── seed.py         # Seed data (5 teachers, 10 students, 8 courses)
├── tests/
│   ├── test_db.py      # DB queries, joins, aggregations
│   ├── test_sql_gen.py # SQL generation and validation nodes
│   └── test_agent.py   # End-to-end graph behavior (mocked LLM)
├── conftest.py         # pytest path setup
├── main.py             # CLI entrypoint
└── pytest.ini
```

---

## Database Schema

```
teachers          students
    │                 │
    │                 │
course_offerings ─────┘ (via enrollments)
    │
courses
```

| Table              | Description                           |
| ------------------ | ------------------------------------- |
| `teachers`         | name, department, email               |
| `students`         | name, email, major                    |
| `courses`          | code (CS101), name, credits           |
| `course_offerings` | course + teacher + semester           |
| `enrollments`      | student + offering + grade (nullable) |

`CourseOffering` is the join between a course, a teacher, and a semester. This allows the same course to be taught by different teachers across semesters. `Enrollment` links a student to a specific offering and holds their grade.

---

## Setup

**1. Clone and create a virtual environment**

```bash
git clone <repo-url>
cd university_qa_agent
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

**2. Install dependencies**

```bash
pip install sqlalchemy fastapi uvicorn langgraph langchain langchain-groq \
            langsmith pydantic pytest httpx python-dotenv
```

**3. Configure environment**

```bash
cp .env.example .env
```

Edit `.env`:

```dotenv
GROQ_API_KEY=gsk_...

# LangSmith tracing (optional but recommended)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=university-qa
LANGSMITH_API_KEY=ls__...

DATABASE_URL=sqlite:///./university.db
```

**4. Run**

```bash
# CLI
python main.py "Who teaches Algorithms?"

# API server
uvicorn api.app:app --reload
# → http://localhost:8000/docs
```

---

## Example Queries

```bash
python main.py "Who teaches Algorithms?"
# → Prof. David Kim teaches Algorithms.

python main.py "What is the average grade in Machine Learning?"
# → The average grade in Machine Learning is 95.3.

python main.py "Which students are enrolled in Spring 2025?"
# → Maya Patel, Lior Ben-David, Sofia Garcia, Noah Williams,
#   Aisha Johnson, Ethan Park, Lucas Silva, and Emma Wilson.

python main.py "How many courses does Dr. Alice Morgan teach?"
# → Dr. Alice Morgan teaches 2 courses.

python main.py "Who has the highest grade in Data Structures?"
# → Tom Chen has the highest grade with 92.0.
```

### API usage

```bash
# Ask the agent
curl -X POST http://localhost:8000/agent/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Who teaches Algorithms?"}'

# Add a teacher
curl -X POST http://localhost:8000/teachers \
  -H "Content-Type: application/json" \
  -d '{"name": "Dr. New Teacher", "department": "Physics", "email": "new@university.edu"}'

# List all students
curl http://localhost:8000/students
```

---

## Tracing

Every agent run is traced automatically via LangSmith when `LANGCHAIN_TRACING_V2=true` is set. The trace shows:

- Full path: user input → each LangGraph node → SQL → DB results → final answer
- Per-node latency and LLM call duration
- Retry attempts and error messages
- Input/output at every step

View traces at `smith.langchain.com` under the `university-qa` project.

---

## Tests

```bash
pytest           # run all 41 tests
pytest -v        # verbose output
pytest tests/test_db.py         # DB layer only
pytest tests/test_agent.py      # agent behavior only
```

No API key required — LLM calls are fully mocked. Tests cover:

- Schema integrity and seed data correctness
- Multi-table joins and aggregations
- SQL validation (blocks DROP, INSERT, DELETE, UPDATE)
- LLM output cleaning (strips markdown fences)
- Retry logic on invalid or failing SQL
- Graceful failure after max retries
- Empty result handling

---

## Production Considerations

**Reliability**

- Replace SQLite with PostgreSQL for concurrent writes
- Add connection pooling via SQLAlchemy's `pool_size` / `max_overflow`
- Wrap LLM calls with retry + exponential backoff for transient API errors
- Set `MAX_RETRIES` via environment variable rather than hardcoded

**Scalability**

- Deploy FastAPI behind a load balancer (e.g. Nginx + multiple Uvicorn workers)
- Move to async SQLAlchemy (`asyncpg`) for non-blocking DB calls under load
- Cache frequent identical questions with Redis (question hash → answer)

**Security**

- The `validate_sql` node blocks all non-SELECT statements — extend it with an allowlist of permitted tables
- Add authentication to the FastAPI layer (JWT or API key header)
- Never expose raw SQL or DB errors in API responses (currently handled by `handle_error`)
- Rotate LLM API keys via secrets manager (AWS Secrets Manager / Vault)

**Monitoring**

- LangSmith already provides per-run tracing, latency, and error rates
- Add `/health` and `/metrics` endpoints for infrastructure monitoring
- Alert on high `retry_count` values — signals prompt or schema drift

**Deployment**

- Containerise with Docker (`Dockerfile` + `docker-compose.yml`)
- Run DB migrations with Alembic instead of `create_all()`
- Separate read replicas for agent queries vs write path for CRUD operations
