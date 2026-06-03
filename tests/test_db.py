"""
Tests for the database layer.
No LLM calls — purely verifies schema, seed data, and query correctness.
"""

import pytest
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from db.models import Base, Teacher, Student, Course, CourseOffering, Enrollment
from db.seed import seed
from db.session import session_scope


@pytest.fixture(scope="module")
def db_session():
    """In-memory SQLite database seeded once for the entire test module."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    import os

    os.environ["DATABASE_URL"] = "sqlite:///:memory:"

    # Manually seed into this engine
    session = Session()
    _seed_test_db(session)
    yield session
    session.close()


def _seed_test_db(session):
    """Insert minimal but representative data."""
    t1 = Teacher(
        name="Dr. Alice Morgan",
        department="Computer Science",
        email="a.morgan@university.edu",
    )
    t2 = Teacher(
        name="Prof. David Kim",
        department="Computer Science",
        email="d.kim@university.edu",
    )
    t3 = Teacher(
        name="Prof. James Okafor",
        department="Data Science",
        email="j.okafor@university.edu",
    )
    session.add_all([t1, t2, t3])

    s1 = Student(name="Tom Chen", email="tom@student.edu", major="Computer Science")
    s2 = Student(name="Maya Patel", email="maya@student.edu", major="Data Science")
    s3 = Student(name="Aisha Johnson", email="aisha@student.edu", major="Data Science")
    session.add_all([s1, s2, s3])

    c1 = Course(code="CS301", name="Algorithms", credits=3)
    c2 = Course(code="DS201", name="Machine Learning", credits=4)
    session.add_all([c1, c2])
    session.flush()

    o1 = CourseOffering(course_id=c1.id, teacher_id=t2.id, semester="Fall 2024")
    o2 = CourseOffering(course_id=c2.id, teacher_id=t3.id, semester="Fall 2024")
    o3 = CourseOffering(course_id=c2.id, teacher_id=t3.id, semester="Spring 2025")
    session.add_all([o1, o2, o3])
    session.flush()

    session.add_all(
        [
            Enrollment(student_id=s1.id, offering_id=o1.id, grade=79.0),
            Enrollment(student_id=s2.id, offering_id=o2.id, grade=95.0),
            Enrollment(student_id=s3.id, offering_id=o2.id, grade=98.0),
            Enrollment(student_id=s2.id, offering_id=o3.id, grade=93.0),
            Enrollment(
                student_id=s3.id, offering_id=o3.id, grade=None
            ),  # not yet graded
        ]
    )
    session.commit()


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestSchema:
    def test_teachers_created(self, db_session):
        assert db_session.query(Teacher).count() == 3

    def test_students_created(self, db_session):
        assert db_session.query(Student).count() == 3

    def test_courses_created(self, db_session):
        assert db_session.query(Course).count() == 2

    def test_offerings_created(self, db_session):
        assert db_session.query(CourseOffering).count() == 3

    def test_enrollments_created(self, db_session):
        assert db_session.query(Enrollment).count() == 5


# ---------------------------------------------------------------------------
# Query tests
# ---------------------------------------------------------------------------


class TestQueries:
    def test_find_teacher_by_name(self, db_session):
        teacher = db_session.query(Teacher).filter(Teacher.name.like("%Alice%")).first()
        assert teacher is not None
        assert teacher.department == "Computer Science"

    def test_find_course_by_code(self, db_session):
        course = db_session.query(Course).filter_by(code="CS301").first()
        assert course is not None
        assert course.name == "Algorithms"

    def test_student_major_filter(self, db_session):
        ds_students = db_session.query(Student).filter_by(major="Data Science").all()
        assert len(ds_students) == 2


# ---------------------------------------------------------------------------
# Join tests
# ---------------------------------------------------------------------------


class TestJoins:
    def test_who_teaches_algorithms(self, db_session):
        result = (
            db_session.query(Teacher.name)
            .join(CourseOffering, CourseOffering.teacher_id == Teacher.id)
            .join(Course, Course.id == CourseOffering.course_id)
            .filter(Course.name.like("%Algorithms%"))
            .distinct()
            .all()
        )
        names = [r[0] for r in result]
        assert len(names) == 1
        assert "Prof. David Kim" in names

    def test_students_enrolled_in_semester(self, db_session):
        result = (
            db_session.query(Student.name)
            .join(Enrollment, Enrollment.student_id == Student.id)
            .join(CourseOffering, CourseOffering.id == Enrollment.offering_id)
            .filter(CourseOffering.semester == "Spring 2025")
            .distinct()
            .all()
        )
        names = [r[0] for r in result]
        assert len(names) == 2
        assert "Maya Patel" in names
        assert "Aisha Johnson" in names

    def test_grades_for_course(self, db_session):
        result = (
            db_session.query(Student.name, Enrollment.grade)
            .join(Enrollment, Enrollment.student_id == Student.id)
            .join(CourseOffering, CourseOffering.id == Enrollment.offering_id)
            .join(Course, Course.id == CourseOffering.course_id)
            .filter(Course.name.like("%Machine Learning%"))
            .filter(Enrollment.grade.isnot(None))
            .all()
        )
        assert len(result) == 3
        grades = [r[1] for r in result]
        assert 95.0 in grades
        assert 98.0 in grades


# ---------------------------------------------------------------------------
# Aggregation tests
# ---------------------------------------------------------------------------


class TestAggregations:
    def test_average_grade_machine_learning(self, db_session):
        avg = (
            db_session.query(func.avg(Enrollment.grade))
            .join(CourseOffering, CourseOffering.id == Enrollment.offering_id)
            .join(Course, Course.id == CourseOffering.course_id)
            .filter(Course.name.like("%Machine Learning%"))
            .filter(Enrollment.grade.isnot(None))
            .scalar()
        )
        assert avg is not None
        assert round(avg, 1) == 95.3  # (95 + 98 + 93) / 3

    def test_highest_grade_in_course(self, db_session):
        result = (
            db_session.query(Student.name, Enrollment.grade)
            .join(Enrollment, Enrollment.student_id == Student.id)
            .join(CourseOffering, CourseOffering.id == Enrollment.offering_id)
            .join(Course, Course.id == CourseOffering.course_id)
            .filter(Course.name.like("%Machine Learning%"))
            .filter(Enrollment.grade.isnot(None))
            .order_by(Enrollment.grade.desc())
            .first()
        )
        assert result is not None
        assert result[0] == "Aisha Johnson"
        assert result[1] == 98.0

    def test_null_grades_excluded_from_average(self, db_session):
        """Enrollment with NULL grade must not affect the average."""
        total = db_session.query(Enrollment).count()
        graded = (
            db_session.query(Enrollment).filter(Enrollment.grade.isnot(None)).count()
        )
        assert graded == total - 1  # one NULL grade in our seed data

    def test_count_courses_per_teacher(self, db_session):
        result = (
            db_session.query(
                Teacher.name, func.count(func.distinct(CourseOffering.course_id))
            )
            .join(CourseOffering, CourseOffering.teacher_id == Teacher.id)
            .group_by(Teacher.name)
            .all()
        )
        counts = {name: count for name, count in result}
        assert counts["Prof. James Okafor"] == 1  # teaches ML only
        assert counts["Prof. David Kim"] == 1  # teaches Algorithms only
