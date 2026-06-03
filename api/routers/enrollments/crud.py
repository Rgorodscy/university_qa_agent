from sqlalchemy.orm import Session

from db.models import Enrollment
from api.routers.enrollments.schemas import EnrollmentCreate


def get_all(db: Session) -> list[Enrollment]:
    return db.query(Enrollment).all()


def create(db: Session, payload: EnrollmentCreate) -> Enrollment:
    enrollment = Enrollment(**payload.model_dump())
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment
