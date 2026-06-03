from typing import Optional
from pydantic import BaseModel, Field


class EnrollmentCreate(BaseModel):
    student_id: int
    offering_id: int
    grade: Optional[float] = Field(default=None, ge=0, le=100)


class EnrollmentRead(EnrollmentCreate):
    id: int
    model_config = {"from_attributes": True}
