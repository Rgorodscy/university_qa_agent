from pydantic import BaseModel, Field


class TeacherCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    department: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., max_length=150)


class TeacherRead(TeacherCreate):
    id: int
    model_config = {"from_attributes": True}
