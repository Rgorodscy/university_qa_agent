from typing import Optional
from pydantic import BaseModel, Field


class CourseCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=20)
    name: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = None
    credits: int = Field(default=3, ge=1, le=10)


class CourseRead(CourseCreate):
    id: int
    model_config = {"from_attributes": True}
