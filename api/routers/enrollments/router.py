from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from db.session import get_db
from api.routers.enrollments import crud
from api.routers.enrollments.schemas import EnrollmentCreate, EnrollmentRead

router = APIRouter(prefix="/enrollments", tags=["Enrollments"])


@router.get("", response_model=list[EnrollmentRead])
def list_enrollments(db: Session = Depends(get_db)) -> list[EnrollmentRead]:
    return crud.get_all(db)


@router.post("", response_model=EnrollmentRead, status_code=status.HTTP_201_CREATED)
def create_enrollment(
    payload: EnrollmentCreate, db: Session = Depends(get_db)
) -> EnrollmentRead:
    return crud.create(db, payload)
