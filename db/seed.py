from db.models import Teacher, Student, Course, CourseOffering, Enrollment
from db.session import session_scope, init_db

TEACHERS = [
    {
        "name": "Dr. Alice Morgan",
        "department": "Computer Science",
        "email": "a.morgan@university.edu",
    },
    {
        "name": "Prof. David Kim",
        "department": "Computer Science",
        "email": "d.kim@university.edu",
    },
    {
        "name": "Dr. Sara Levi",
        "department": "Mathematics",
        "email": "s.levi@university.edu",
    },
    {
        "name": "Prof. James Okafor",
        "department": "Data Science",
        "email": "j.okafor@university.edu",
    },
    {
        "name": "Dr. Elena Russo",
        "department": "Software Engineering",
        "email": "e.russo@university.edu",
    },
]

STUDENTS = [
    {"name": "Tom Chen", "email": "tom.chen@student.edu", "major": "Computer Science"},
    {"name": "Maya Patel", "email": "maya.patel@student.edu", "major": "Data Science"},
    {
        "name": "Lior Ben-David",
        "email": "lior.bd@student.edu",
        "major": "Computer Science",
    },
    {
        "name": "Sofia Garcia",
        "email": "sofia.garcia@student.edu",
        "major": "Software Engineering",
    },
    {"name": "Noah Williams", "email": "noah.w@student.edu", "major": "Mathematics"},
    {"name": "Aisha Johnson", "email": "aisha.j@student.edu", "major": "Data Science"},
    {
        "name": "Ethan Park",
        "email": "ethan.park@student.edu",
        "major": "Computer Science",
    },
    {
        "name": "Priya Sharma",
        "email": "priya.s@student.edu",
        "major": "Software Engineering",
    },
    {"name": "Lucas Silva", "email": "lucas.silva@student.edu", "major": "Mathematics"},
    {"name": "Emma Wilson", "email": "emma.w@student.edu", "major": "Computer Science"},
]

COURSES = [
    {
        "code": "CS101",
        "name": "Introduction to Programming",
        "credits": 3,
        "description": "Fundamentals of programming using Python.",
    },
    {
        "code": "CS201",
        "name": "Data Structures",
        "credits": 3,
        "description": "Arrays, linked lists, trees, graphs, and hash maps.",
    },
    {
        "code": "CS301",
        "name": "Algorithms",
        "credits": 3,
        "description": "Algorithm design, complexity analysis, and optimization.",
    },
    {
        "code": "CS401",
        "name": "Distributed Systems",
        "credits": 4,
        "description": "Design and implementation of distributed systems.",
    },
    {
        "code": "DS201",
        "name": "Machine Learning",
        "credits": 4,
        "description": "Supervised and unsupervised learning methods.",
    },
    {
        "code": "DS301",
        "name": "Data Engineering",
        "credits": 3,
        "description": "ETL pipelines, data warehouses, and streaming systems.",
    },
    {
        "code": "MATH201",
        "name": "Linear Algebra",
        "credits": 3,
        "description": "Vectors, matrices, eigenvalues, and transformations.",
    },
    {
        "code": "SE301",
        "name": "Software Architecture",
        "credits": 3,
        "description": "Design patterns, system design, and architectural styles.",
    },
]

# (course_code, teacher_email, semester)
OFFERINGS = [
    ("CS101", "a.morgan@university.edu", "Fall 2024"),
    ("CS201", "a.morgan@university.edu", "Fall 2024"),
    ("CS301", "d.kim@university.edu", "Fall 2024"),
    ("CS401", "d.kim@university.edu", "Spring 2025"),
    ("DS201", "j.okafor@university.edu", "Fall 2024"),
    ("DS201", "j.okafor@university.edu", "Spring 2025"),
    ("DS301", "j.okafor@university.edu", "Spring 2025"),
    ("MATH201", "s.levi@university.edu", "Fall 2024"),
    ("MATH201", "s.levi@university.edu", "Spring 2025"),
    ("SE301", "e.russo@university.edu", "Fall 2024"),
    ("SE301", "e.russo@university.edu", "Spring 2025"),
    ("CS101", "d.kim@university.edu", "Spring 2025"),
]

# (student_email, course_code, semester, grade)
ENROLLMENTS = [
    ("tom.chen@student.edu", "CS101", "Fall 2024", 88.0),
    ("tom.chen@student.edu", "CS201", "Fall 2024", 92.0),
    ("tom.chen@student.edu", "CS301", "Fall 2024", 79.0),
    ("maya.patel@student.edu", "DS201", "Fall 2024", 95.0),
    ("maya.patel@student.edu", "MATH201", "Fall 2024", 91.0),
    ("maya.patel@student.edu", "DS301", "Spring 2025", 87.0),
    ("lior.bd@student.edu", "CS101", "Fall 2024", 74.0),
    ("lior.bd@student.edu", "CS201", "Fall 2024", 81.0),
    ("lior.bd@student.edu", "CS401", "Spring 2025", 69.0),
    ("sofia.garcia@student.edu", "CS101", "Fall 2024", 90.0),
    ("sofia.garcia@student.edu", "SE301", "Fall 2024", 94.0),
    (
        "sofia.garcia@student.edu",
        "SE301",
        "Spring 2025",
        None,
    ),  # enrolled, not yet graded
    ("noah.w@student.edu", "MATH201", "Fall 2024", 85.0),
    ("noah.w@student.edu", "CS101", "Fall 2024", 78.0),
    ("noah.w@student.edu", "MATH201", "Spring 2025", None),
    ("aisha.j@student.edu", "DS201", "Fall 2024", 98.0),
    ("aisha.j@student.edu", "DS201", "Spring 2025", 93.0),
    ("aisha.j@student.edu", "DS301", "Spring 2025", 90.0),
    ("ethan.park@student.edu", "CS101", "Spring 2025", 82.0),
    ("ethan.park@student.edu", "CS301", "Fall 2024", 77.0),
    ("priya.s@student.edu", "SE301", "Fall 2024", 88.0),
    ("priya.s@student.edu", "CS101", "Fall 2024", 91.0),
    ("lucas.silva@student.edu", "MATH201", "Fall 2024", 72.0),
    ("lucas.silva@student.edu", "MATH201", "Spring 2025", None),
    ("emma.w@student.edu", "CS201", "Fall 2024", 86.0),
    ("emma.w@student.edu", "CS301", "Fall 2024", 83.0),
    ("emma.w@student.edu", "CS401", "Spring 2025", None),
]


def seed(drop_first: bool = False) -> None:
    init_db()

    with session_scope() as session:
        if drop_first:
            from db.models import Base
            from db.session import engine

            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)

        # Skip if already seeded
        if session.query(Teacher).count() > 0:
            print("Database already seeded — skipping.")
            return

        # Insert teachers
        teachers = {t["email"]: Teacher(**t) for t in TEACHERS}
        session.add_all(teachers.values())
        session.flush()

        # Insert students
        students = {s["email"]: Student(**s) for s in STUDENTS}
        session.add_all(students.values())
        session.flush()

        # Insert courses
        courses = {c["code"]: Course(**c) for c in COURSES}
        session.add_all(courses.values())
        session.flush()

        # Insert offerings
        offerings: dict[tuple, CourseOffering] = {}
        for code, teacher_email, semester in OFFERINGS:
            offering = CourseOffering(
                course_id=courses[code].id,
                teacher_id=teachers[teacher_email].id,
                semester=semester,
            )
            session.add(offering)
            session.flush()
            offerings[(code, semester)] = offering

        # Insert enrollments
        for student_email, code, semester, grade in ENROLLMENTS:
            session.add(
                Enrollment(
                    student_id=students[student_email].id,
                    offering_id=offerings[(code, semester)].id,
                    grade=grade,
                )
            )

    print("Database seeded successfully.")


if __name__ == "__main__":
    seed()
