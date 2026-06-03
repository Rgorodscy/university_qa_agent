from sqlalchemy.orm import Session

from db.models import Teacher
from api.routers.teachers.schemas import TeacherCreate


def get_all(db: Session) -> list[Teacher]:
    return db.query(Teacher).all()


def get_by_id(db: Session, teacher_id: int) -> Teacher | None:
    return db.get(Teacher, teacher_id)


def create(db: Session, payload: TeacherCreate) -> Teacher:
    teacher = Teacher(**payload.model_dump())
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return teacher
