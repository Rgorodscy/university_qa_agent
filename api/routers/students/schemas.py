from pydantic import BaseModel, Field


class StudentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., max_length=150)
    major: str = Field(..., min_length=2, max_length=100)


class StudentRead(StudentCreate):
    id: int
    model_config = {"from_attributes": True}
