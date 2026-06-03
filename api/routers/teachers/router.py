from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.session import get_db
from api.routers.teachers import crud
from api.routers.teachers.schemas import TeacherCreate, TeacherRead

router = APIRouter(prefix="/teachers", tags=["Teachers"])


@router.get("", response_model=list[TeacherRead])
def list_teachers(db: Session = Depends(get_db)) -> list[TeacherRead]:
    return crud.get_all(db)


@router.get("/{teacher_id}", response_model=TeacherRead)
def get_teacher(teacher_id: int, db: Session = Depends(get_db)) -> TeacherRead:
    teacher = crud.get_by_id(db, teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return teacher


@router.post("", response_model=TeacherRead, status_code=status.HTTP_201_CREATED)
def create_teacher(
    payload: TeacherCreate, db: Session = Depends(get_db)
) -> TeacherRead:
    return crud.create(db, payload)
