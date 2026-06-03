from sqlalchemy.orm import Session

from db.models import CourseOffering
from api.routers.offerings.schemas import CourseOfferingCreate


def get_all(db: Session) -> list[CourseOffering]:
    return db.query(CourseOffering).all()


def create(db: Session, payload: CourseOfferingCreate) -> CourseOffering:
    offering = CourseOffering(**payload.model_dump())
    db.add(offering)
    db.commit()
    db.refresh(offering)
    return offering
