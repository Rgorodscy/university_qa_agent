[![CI](https://github.com/Rgorodscy/university_qa_agent/actions/workflows/ci.yml/badge.svg)](https://github.com/Rgorodscy/university_qa_agent/actions/workflows/ci.yml)

# University QA Agent

A natural language question-answering system over a university database, built with LangGraph, FastAPI, and SQLAlchemy.

Users ask questions in plain English. The agent translates them to SQL, executes them, and returns human-readable answers — with full tracing via LangSmith.

---

## Architecture

```
User question
     │
     ▼
POST /agent/query          (FastAPI — transport only)
     │
     ▼
ask(question)              (agent/graph.py)
     │
     ▼
┌─────────────────────────────────────────────────┐
│                LangGraph Agent                  │
│                                                 │
│  generate_sql → validate_sql → execute_sql      │
│       ▲              │               │          │
│       │         [invalid]        [error]        │
│       └──── increment_retry ────────┘           │
│                                                 │
│                         └──→ format_answer → END│
│                         └──→ handle_error  → END│
└─────────────────────────────────────────────────┘
     │
     ▼
  Final answer
```

### Key design decisions

**Truly DB-agnostic agent** — the agent has no hardcoded schema knowledge. The schema context is generated dynamically at startup by introspecting the live database via SQLAlchemy's inspector. Adding a new table to `models.py` is automatically reflected in the agent's prompt with zero manual updates.

**LangGraph over a plain chain** — conditional edges enable the retry loop (bad SQL → regenerate with error context) and explicit state makes every step inspectable. A plain LangChain chain can't express this routing.

**SQLAlchemy over raw SQL** — the engine abstraction means SQLite locally and PostgreSQL in production with zero code changes.

**Router/CRUD/schemas structure** — each API resource is a package with three files: `router.py` handles HTTP, `crud.py` handles database operations, `schemas.py` handles validation. Each layer has exactly one responsibility.

**FastAPI as a thin transport layer** — the API has no business logic. It calls `ask()` and returns the result. The agent is completely unaware the API exists.

**Request logging middleware** — every HTTP request is logged with method, path, status code, and duration. Complements LangSmith's agent-level tracing with application-level observability.

---

## Project Structure

```
university_qa_agent/
├── agent/
│   ├── state.py        # AgentState TypedDict
│   ├── nodes.py        # Node functions + conditional routing logic
│   ├── graph.py        # LangGraph graph wiring and ask() entrypoint
│   └── prompts.py      # Prompt templates + dynamic schema context
├── api/
│   ├── app.py          # FastAPI app, middleware, router registration
│   └── routers/
│       ├── teachers/
│       │   ├── router.py    # HTTP layer
│       │   ├── crud.py      # DB layer
│       │   └── schemas.py   # Pydantic models
│       ├── students/
│       ├── courses/
│       ├── offerings/
│       ├── enrollments/
│       └── agent/
│           ├── router.py    # HTTP layer
│           └── schemas.py   # no crud — talks to LangGraph
├── db/
│   ├── models.py       # SQLAlchemy ORM models
│   ├── session.py      # Engine, session factory, schema introspection
│   └── seed.py         # Seed data (5 teachers, 10 students, 8 courses)
├── tests/
│   ├── test_db.py      # DB queries, joins, aggregations
│   ├── test_sql_gen.py # SQL generation and validation nodes
│   ├── test_agent.py   # End-to-end graph behavior (mocked LLM)
│   └── test_api.py     # All API endpoints (FastAPI TestClient)
├── conftest.py         # pytest path setup
├── main.py             # CLI entrypoint
├── demo.py             # Error loop demonstration tool
└── pytest.ini
```

---

## Database Schema

| Table              | Description                                                        |
| ------------------ | ------------------------------------------------------------------ |
| `teachers`         | name, department, email                                            |
| `students`         | name, email, major                                                 |
| `courses`          | code (CS101), name, credits                                        |
| `course_offerings` | course + teacher + semester — represents a specific class instance |
| `enrollments`      | student + offering + grade (nullable)                              |

**Why CourseOffering?** The same course can be taught by different teachers across semesters. CourseOffering is the junction between course, teacher, and semester. Enrollment links a student to a specific offering and holds their grade — not the course itself.

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
pip install -r requirements.txt
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

# Or with Docker
docker-compose up --build
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

# List all teachers
curl http://localhost:8000/teachers

# Add a teacher
curl -X POST http://localhost:8000/teachers \
  -H "Content-Type: application/json" \
  -d '{"name": "Dr. New Teacher", "department": "Physics", "email": "new@university.edu"}'

# Health check
curl http://localhost:8000/health
```

---

## Demonstrating the Error Loop

The agent has a built-in retry loop — if SQL generation fails validation or execution, the error is injected back into the next prompt so the LLM can self-correct.

Use `demo.py` to exercise this path on demand:

```bash
# Attempt 1 fails (forbidden SQL), agent recovers on attempt 2
python demo.py retry

# All attempts fail, agent gives up gracefully
python demo.py exhausted
```

Every run appears in LangSmith with the full node trace — including the `increment_retry` node between attempts.

---

## Tracing

Every agent run is traced automatically via LangSmith when `LANGCHAIN_TRACING_V2=true` is set.

The trace shows:

- Full path: user input → each LangGraph node → SQL → DB results → final answer
- Per-node latency and LLM call duration
- Retry attempts with error context
- Input/output at every step

View traces at `smith.langchain.com` under the `university-qa` project.

Application-level observability is handled by the request logging middleware in `api/app.py` — every HTTP request is logged with method, path, status code, and duration.

---

## Tests

```bash
pytest              # run all 70 tests
pytest -v           # verbose output
pytest tests/test_db.py         # DB layer only
pytest tests/test_agent.py      # agent behavior only
pytest tests/test_api.py        # API endpoints only
pytest tests/test_agent.py::TestRetryLoopDemo  # retry loop specifically
```

No API key required — LLM calls are fully mocked. Tests cover:

- Schema integrity and seed data correctness
- Multi-table joins and aggregations
- NULL grade handling
- SQL validation (blocks DROP, INSERT, DELETE, UPDATE)
- LLM output cleaning (strips markdown fences)
- Retry recovery — agent self-corrects using previous error context
- Retry exhaustion — graceful failure after max retries
- Empty result handling
- All API endpoints — status codes, validation, 404s

---

## Production Considerations

**Reliability**

- Replace SQLite with PostgreSQL for concurrent writes
- Add connection pooling via SQLAlchemy `pool_size` / `max_overflow`
- Wrap LLM calls with retry + exponential backoff for transient API errors
- Set `MAX_RETRIES` via environment variable

**Scalability**

- Deploy FastAPI behind a load balancer with multiple Uvicorn workers
- Move to async SQLAlchemy (`asyncpg`) for non-blocking DB calls under load
- Cache frequent identical questions with Redis (question hash → answer)

**Security**

- `validate_sql` blocks all non-SELECT statements — extend with table allowlist
- Add JWT authentication to the FastAPI layer
- Never expose raw SQL or stack traces in API responses (handled by `handle_error`)
- Rotate LLM API keys via secrets manager (AWS Secrets Manager / Vault)

**Monitoring**

- LangSmith provides per-run tracing, latency, and error rates for the agent
- Request logging middleware covers the HTTP layer
- Add Prometheus metrics and alert on high `retry_count` values — signals prompt or schema drift
- OpenTelemetry for distributed tracing across all layers in production

**Deployment**

- Containerise with Docker
- Run DB migrations with Alembic instead of `create_all()`
- Separate read replicas for agent queries vs write path for CRUD operations
