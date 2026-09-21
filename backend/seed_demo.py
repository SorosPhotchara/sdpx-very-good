"""Seed repeatable development data in PostgreSQL."""

import os
from datetime import UTC, datetime, timedelta
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app import models, schemas
from app.assignment_setup import create_assignment
from app.database import engine
from app.publish import publish

DEMO_CLASSROOM = "PairEval Demo"
DEMO_ASSIGNMENT = "Team project review"
PRESERVED_CLASSROOMS = ("d", "AAA", "www", "ECC777")


def seed(target_engine: Engine = engine) -> None:
    if os.environ.get("APP_ENV") != "development":
        raise RuntimeError("Demo seeding requires APP_ENV=development")
    approved = [email.strip().lower() for email in os.environ.get("INSTRUCTOR_EMAILS", "").split(",") if email.strip()]
    if not approved:
        raise RuntimeError("Set INSTRUCTOR_EMAILS before seeding")
    with Session(target_engine) as db:
        for name in PRESERVED_CLASSROOMS:
            if db.query(models.Classroom.id).filter_by(name=name).first() is None:
                db.add(models.Classroom(name=name, instructor_emails=approved[0]))
        db.flush()
        classroom = db.query(models.Classroom).filter_by(name=DEMO_CLASSROOM).first()
        if classroom is None:
            classroom = models.Classroom(name=DEMO_CLASSROOM, instructor_emails=approved[0])
            db.add(classroom)
            db.flush()
        if not db.query(models.Student.id).filter_by(classroom_id=classroom.id).first():
            student_number = 1
            for group_name in ("Aurora", "Beacon", "Cobalt"):
                group = models.Group(name=group_name, classroom_id=classroom.id)
                db.add(group)
                db.flush()
                for _ in range(3):
                    db.add(models.Student(
                        email=f"student{student_number}@example.edu",
                        display_name=f"Student {student_number}", group_name=group_name,
                        classroom_id=classroom.id, group_id=group.id,
                    ))
                    student_number += 1
        db.commit()
        assignment = db.query(models.Assignment).filter_by(
            classroom_id=classroom.id, title=DEMO_ASSIGNMENT
        ).first()
        if assignment is None:
            deadline = datetime.now(UTC) + timedelta(days=30)
            assignment = create_assignment(db, classroom.id, schemas.AssignmentSetup(
                title=DEMO_ASSIGNMENT,
                group_score=15, individual_score=5,
                group_participation_max=2, individual_participation_max=2,
                group_deadline=deadline, individual_deadline=deadline,
                group_criteria=[schemas.CriterionInput(name="Quality", weight=100)],
                individual_criteria=[schemas.CriterionInput(name="Contribution", weight=100)],
            ))
        if assignment.published_at is None:
            publish(db, assignment.id)
        print(f"Demo ready: classroom={classroom.id}, assignment={assignment.id}")


if __name__ == "__main__":
    seed()
