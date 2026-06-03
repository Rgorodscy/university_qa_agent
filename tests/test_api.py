"""
Tests for all FastAPI endpoints.
Uses TestClient — no running server needed, no API key required.
"""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use a file-based test DB so all modules share the same connection
TEST_DB_PATH = "./test_api.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

from db.models import Base, Teacher, Student, Course, CourseOffering, Enrollment
from db.session import get_db
from api.app import app


@pytest.fixture(scope="module")
def client():
    # Build schema and seed into the test DB
    engine = create_engine(
        f"sqlite:///{TEST_DB_PATH}", connect_args={"check_same_thread": False}
    )
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    session = TestSession()
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
    s1 = Student(name="Tom Chen", email="tom@student.edu", major="Computer Science")
    s2 = Student(name="Maya Patel", email="maya@student.edu", major="Data Science")
    c1 = Course(code="CS301", name="Algorithms", credits=3)
    c2 = Course(code="DS201", name="Machine Learning", credits=4)
    session.add_all([t1, t2, s1, s2, c1, c2])
    session.flush()
    o1 = CourseOffering(course_id=c1.id, teacher_id=t2.id, semester="Fall 2024")
    o2 = CourseOffering(course_id=c2.id, teacher_id=t1.id, semester="Fall 2024")
    session.add_all([o1, o2])
    session.flush()
    session.add_all(
        [
            Enrollment(student_id=s1.id, offering_id=o1.id, grade=88.0),
            Enrollment(student_id=s2.id, offering_id=o2.id, grade=95.0),
        ]
    )
    session.commit()
    session.close()

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

    # Cleanup test DB file
    engine.dispose()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Teachers
# ---------------------------------------------------------------------------


class TestTeachersEndpoints:
    def test_list_teachers(self, client):
        response = client.get("/teachers")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) > 0

    def test_list_teachers_have_expected_fields(self, client):
        teacher = client.get("/teachers").json()[0]
        assert "id" in teacher
        assert "name" in teacher
        assert "department" in teacher
        assert "email" in teacher

    def test_get_teacher_by_id(self, client):
        teacher_id = client.get("/teachers").json()[0]["id"]
        response = client.get(f"/teachers/{teacher_id}")
        assert response.status_code == 200
        assert response.json()["id"] == teacher_id

    def test_get_teacher_not_found(self, client):
        response = client.get("/teachers/99999")
        assert response.status_code == 404

    def test_create_teacher(self, client):
        payload = {
            "name": "Dr. New Teacher",
            "department": "Physics",
            "email": "new.teacher@university.edu",
        }
        response = client.post("/teachers", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == payload["name"]
        assert data["email"] == payload["email"]
        assert "id" in data

    def test_create_teacher_missing_field(self, client):
        response = client.post("/teachers", json={"name": "Incomplete"})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------------


class TestStudentsEndpoints:
    def test_list_students(self, client):
        response = client.get("/students")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) > 0

    def test_get_student_by_id(self, client):
        student_id = client.get("/students").json()[0]["id"]
        response = client.get(f"/students/{student_id}")
        assert response.status_code == 200
        assert response.json()["id"] == student_id

    def test_get_student_not_found(self, client):
        response = client.get("/students/99999")
        assert response.status_code == 404

    def test_create_student(self, client):
        payload = {
            "name": "New Student",
            "email": "new.student@student.edu",
            "major": "Computer Science",
        }
        response = client.post("/students", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == payload["name"]
        assert data["major"] == payload["major"]
        assert "id" in data

    def test_create_student_missing_field(self, client):
        response = client.post("/students", json={"name": "Incomplete"})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Courses
# ---------------------------------------------------------------------------


class TestCoursesEndpoints:
    def test_list_courses(self, client):
        response = client.get("/courses")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) > 0

    def test_get_course_by_id(self, client):
        course_id = client.get("/courses").json()[0]["id"]
        response = client.get(f"/courses/{course_id}")
        assert response.status_code == 200
        assert response.json()["id"] == course_id

    def test_get_course_not_found(self, client):
        response = client.get("/courses/99999")
        assert response.status_code == 404

    def test_create_course(self, client):
        payload = {
            "code": "NEW101",
            "name": "New Course",
            "credits": 3,
            "description": "A brand new course",
        }
        response = client.post("/courses", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == payload["code"]
        assert data["credits"] == payload["credits"]

    def test_create_course_missing_field(self, client):
        response = client.post("/courses", json={"name": "No code"})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Offerings
# ---------------------------------------------------------------------------


class TestOfferingsEndpoints:
    def test_list_offerings(self, client):
        response = client.get("/offerings")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) > 0

    def test_list_offerings_have_expected_fields(self, client):
        offering = client.get("/offerings").json()[0]
        assert "id" in offering
        assert "course_id" in offering
        assert "teacher_id" in offering
        assert "semester" in offering

    def test_create_offering(self, client):
        teacher_id = client.get("/teachers").json()[0]["id"]
        course_id = client.get("/courses").json()[0]["id"]
        payload = {
            "course_id": course_id,
            "teacher_id": teacher_id,
            "semester": "Summer 2025",
        }
        response = client.post("/offerings", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["semester"] == "Summer 2025"
        assert data["course_id"] == course_id

    def test_create_offering_missing_field(self, client):
        response = client.post("/offerings", json={"semester": "Fall 2025"})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Enrollments
# ---------------------------------------------------------------------------


class TestEnrollmentsEndpoints:
    def test_list_enrollments(self, client):
        response = client.get("/enrollments")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) > 0

    def test_list_enrollments_have_expected_fields(self, client):
        enrollment = client.get("/enrollments").json()[0]
        assert "id" in enrollment
        assert "student_id" in enrollment
        assert "offering_id" in enrollment
        assert "grade" in enrollment

    def test_create_enrollment_with_grade(self, client):
        # Create a fresh offering to avoid unique constraint with seeded enrollments
        teacher_id = client.get("/teachers").json()[0]["id"]
        course_id = client.get("/courses").json()[0]["id"]
        offering = client.post(
            "/offerings",
            json={
                "course_id": course_id,
                "teacher_id": teacher_id,
                "semester": "Summer 2026",
            },
        ).json()
        student_id = client.get("/students").json()[0]["id"]
        payload = {
            "student_id": student_id,
            "offering_id": offering["id"],
            "grade": 88.5,
        }
        response = client.post("/enrollments", json=payload)
        assert response.status_code == 201
        assert response.json()["grade"] == 88.5

    def test_create_enrollment_without_grade(self, client):
        """Grade is nullable — student can enroll before being graded."""
        teacher_id = client.get("/teachers").json()[1]["id"]
        course_id = client.get("/courses").json()[1]["id"]
        offering = client.post(
            "/offerings",
            json={
                "course_id": course_id,
                "teacher_id": teacher_id,
                "semester": "Winter 2026",
            },
        ).json()
        student_id = client.get("/students").json()[1]["id"]
        payload = {
            "student_id": student_id,
            "offering_id": offering["id"],
        }
        response = client.post("/enrollments", json=payload)
        assert response.status_code == 201
        assert response.json()["grade"] is None

    def test_create_enrollment_invalid_grade(self, client):
        """Grade must be between 0 and 100."""
        student_id = client.get("/students").json()[0]["id"]
        offering_id = client.get("/offerings").json()[0]["id"]
        payload = {"student_id": student_id, "offering_id": offering_id, "grade": 150.0}
        response = client.post("/enrollments", json=payload)
        assert response.status_code == 422
