from sqlalchemy.orm import Session

from db.models import Course
from api.routers.courses.schemas import CourseCreate


def get_all(db: Session) -> list[Course]:
    return db.query(Course).all()


def get_by_id(db: Session, course_id: int) -> Course | None:
    return db.get(Course, course_id)


def create(db: Session, payload: CourseCreate) -> Course:
    course = Course(**payload.model_dump())
    db.add(course)
    db.commit()
    db.refresh(course)
    return course
