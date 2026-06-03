from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    department = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)

    offerings = relationship("CourseOffering", back_populates="teacher")

    def __repr__(self):
        return f"<Teacher(id={self.id}, name={self.name!r})>"


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    major = Column(String(100), nullable=False)

    enrollments = relationship("Enrollment", back_populates="student")

    def __repr__(self):
        return f"<Student(id={self.id}, name={self.name!r})>"


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)  # e.g. "CS101"
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    credits = Column(Integer, nullable=False, default=3)

    offerings = relationship("CourseOffering", back_populates="course")

    def __repr__(self):
        return f"<Course(id={self.id}, code={self.code!r}, name={self.name!r})>"


class CourseOffering(Base):
    """A specific instance of a course taught by a teacher in a semester."""

    __tablename__ = "course_offerings"

    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    semester = Column(String(20), nullable=False)  # e.g. "Fall 2024"

    course = relationship("Course", back_populates="offerings")
    teacher = relationship("Teacher", back_populates="offerings")
    enrollments = relationship("Enrollment", back_populates="offering")

    __table_args__ = (
        UniqueConstraint(
            "course_id",
            "teacher_id",
            "semester",
            name="uq_offering_course_teacher_semester",
        ),
    )

    def __repr__(self):
        return f"<CourseOffering(course={self.course_id}, teacher={self.teacher_id}, semester={self.semester!r})>"


class Enrollment(Base):
    """A student enrolled in a course offering, with a grade."""

    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    offering_id = Column(Integer, ForeignKey("course_offerings.id"), nullable=False)
    # Grade is nullable — student may be enrolled but not yet graded
    grade = Column(Float, nullable=True)

    student = relationship("Student", back_populates="enrollments")
    offering = relationship("CourseOffering", back_populates="enrollments")

    __table_args__ = (
        UniqueConstraint(
            "student_id", "offering_id", name="uq_enrollment_student_offering"
        ),
        CheckConstraint(
            "grade >= 0 AND grade <= 100", name="ck_enrollment_grade_range"
        ),
    )

    def __repr__(self):
        return f"<Enrollment(student={self.student_id}, offering={self.offering_id}, grade={self.grade})>"
