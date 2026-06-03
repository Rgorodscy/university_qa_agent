from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from db.session import get_db
from api.routers.offerings import crud
from api.routers.offerings.schemas import CourseOfferingCreate, CourseOfferingRead

router = APIRouter(prefix="/offerings", tags=["Offerings"])


@router.get("", response_model=list[CourseOfferingRead])
def list_offerings(db: Session = Depends(get_db)) -> list[CourseOfferingRead]:
    return crud.get_all(db)


@router.post("", response_model=CourseOfferingRead, status_code=status.HTTP_201_CREATED)
def create_offering(
    payload: CourseOfferingCreate, db: Session = Depends(get_db)
) -> CourseOfferingRead:
    return crud.create(db, payload)
