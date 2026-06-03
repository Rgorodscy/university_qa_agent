from pydantic import BaseModel, Field


class CourseOfferingCreate(BaseModel):
    course_id: int
    teacher_id: int
    semester: str = Field(..., min_length=2, max_length=20)


class CourseOfferingRead(CourseOfferingCreate):
    id: int
    model_config = {"from_attributes": True}
