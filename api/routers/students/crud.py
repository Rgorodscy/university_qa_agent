from sqlalchemy.orm import Session

from db.models import Student
from api.routers.students.schemas import StudentCreate


def get_all(db: Session) -> list[Student]:
    return db.query(Student).all()


def get_by_id(db: Session, student_id: int) -> Student | None:
    return db.get(Student, student_id)


def create(db: Session, payload: StudentCreate) -> Student:
    student = Student(**payload.model_dump())
    db.add(student)
    db.commit()
    db.refresh(student)
    return student
