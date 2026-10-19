"""Manual local scale check: python tests/benchmark_200.py."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from sys import path
from time import perf_counter

path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session

from app import models
from app.evaluation import read_page
from app.publish import publish
from tests.support import TestDatabase


def main() -> None:
    database = TestDatabase()
    with Session(database.engine) as db:
        classroom = models.Classroom(name="Scale check", instructor_emails="teacher@example.edu")
        db.add(classroom)
        db.flush()
        for group_index in range(10):
            group = models.Group(name=f"Group {group_index}", classroom_id=classroom.id)
            db.add(group)
            db.flush()
            for student_index in range(20):
                db.add(models.Student(email=f"s{group_index}_{student_index}@example.edu",
                                      classroom_id=classroom.id, group_id=group.id))
        assignment = models.Assignment(
            title="Scale check", classroom_id=classroom.id, group_score=10,
            individual_score=10, group_deadline=datetime.now(UTC) + timedelta(days=7),
            individual_deadline=datetime.now(UTC) + timedelta(days=7),
        )
        db.add(assignment)
        db.flush()
        db.add_all([
            models.Criteria(assignment_id=assignment.id, name="Group quality", weight=100, is_group=True),
            models.Criteria(assignment_id=assignment.id, name="Individual quality", weight=100, is_group=False),
        ])
        db.commit()
        start = perf_counter()
        count = publish(db, assignment.id)
        publish_seconds = perf_counter() - start
        start = perf_counter()
        page = read_page(db, assignment.id, "individual", "s0_0@example.edu")
        page_seconds = perf_counter() - start
        print(f"students=200 groups=10 pairs={count} publish={publish_seconds:.3f}s evaluation_page={page_seconds:.3f}s assigned={len(page['pairs'])}")
    database.close()


if __name__ == "__main__":
    main()
