from contextlib import asynccontextmanager
from fastapi import FastAPI

from db.session import init_db
from db.seed import seed
from api.routers.teachers.router import router as teachers_router
from api.routers.students.router import router as students_router
from api.routers.courses.router import router as courses_router
from api.routers.offerings.router import router as offerings_router
from api.routers.enrollments.router import router as enrollments_router
from api.routers.agent.router import router as agent_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed()
    yield


app = FastAPI(
    title="University QA Agent",
    description="Manage university data and ask natural language questions via a LangGraph agent.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}


app.include_router(teachers_router)
app.include_router(students_router)
app.include_router(courses_router)
app.include_router(offerings_router)
app.include_router(enrollments_router)
app.include_router(agent_router)
