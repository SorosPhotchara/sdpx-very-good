"""Exercise duplicate cleanup and the database's active-pair uniqueness rule."""

import importlib.util
import os
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import make_url

from app import models


class UniquePairInvariantTests(unittest.TestCase):
    def test_model_indexes_reject_reversed_student_and_instructor_duplicates(self) -> None:
        engine = sa.create_engine("sqlite+pysqlite:///:memory:")
        models.Base.metadata.create_all(engine)
        pairs = models.Pair.__table__
        with engine.begin() as connection:
            connection.execute(pairs.insert().values(
                id=1, criteria_id=1, pair_type="group", left_group_id=10,
                right_group_id=20, assigned_to_student_id=7,
            ))
            with self.assertRaises(IntegrityError), connection.begin_nested():
                connection.execute(pairs.insert().values(
                    id=2, criteria_id=1, pair_type="group", left_group_id=20,
                    right_group_id=10, assigned_to_student_id=7,
                ))
            connection.execute(pairs.insert().values(
                id=3, criteria_id=1, pair_type="individual", left_id=11,
                right_id=12, assigned_to_instructor_email="Teacher@Example.edu",
            ))
            with self.assertRaises(IntegrityError), connection.begin_nested():
                connection.execute(pairs.insert().values(
                    id=4, criteria_id=1, pair_type="individual", left_id=12,
                    right_id=11, assigned_to_instructor_email=" teacher@example.edu ",
                ))
            connection.execute(pairs.insert().values(
                id=5, criteria_id=1, pair_type="group", left_group_id=20,
                right_group_id=10, assigned_to_student_id=7,
                superseded_at=datetime.now(UTC),
            ))
        engine.dispose()


class PostgreSQLMigrationTests(unittest.TestCase):
    def test_upgrade_deduplicates_existing_pairs_without_erasing_answers(self) -> None:
        url = os.environ.get("TEST_DATABASE_URL", "")
        if not url.startswith(("postgresql://", "postgresql+psycopg://")):
            self.skipTest("Set TEST_DATABASE_URL to a disposable PostgreSQL database")
        if make_url(url).host != "test-db":
            self.skipTest("This migration test uses the disposable compose.test.yml test-db")
        schema = "test_pair_migration_" + uuid4().hex
        admin = sa.create_engine(url)
        scoped_url = make_url(url).update_query_dict({
            # Do not fall back to public: the load-test service may already have
            # an Alembic version table at head there.
            "options": f"-csearch_path={schema}",
        }).render_as_string(hide_password=False)
        engine = sa.create_engine(scoped_url)
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        try:
            with admin.begin() as connection:
                connection.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
            with patch.dict(os.environ, {"DATABASE_URL": scoped_url, "INSTRUCTOR_EMAILS": "teacher@example.edu"}):
                command.upgrade(config, "20261016_classroom_archives")
                # Seed through tables scoped to that revision rather than the ORM
                # models: the models carry columns that later revisions add, so
                # using them here breaks every time the schema grows.
                legacy = sa.MetaData()
                classrooms = sa.Table("classrooms", legacy,
                                      sa.Column("id", sa.Integer, primary_key=True),
                                      sa.Column("name", sa.String),
                                      sa.Column("instructor_emails", sa.Text))
                groups_table = sa.Table("groups", legacy,
                                        sa.Column("id", sa.Integer, primary_key=True),
                                        sa.Column("name", sa.String),
                                        sa.Column("classroom_id", sa.Integer))
                students = sa.Table("students", legacy,
                                    sa.Column("id", sa.Integer, primary_key=True),
                                    sa.Column("email", sa.String),
                                    sa.Column("classroom_id", sa.Integer),
                                    sa.Column("group_id", sa.Integer))
                assignments = sa.Table("assignments", legacy,
                                       sa.Column("id", sa.Integer, primary_key=True),
                                       sa.Column("title", sa.String),
                                       sa.Column("classroom_id", sa.Integer))
                criteria_table = sa.Table("criteria", legacy,
                                          sa.Column("id", sa.Integer, primary_key=True),
                                          sa.Column("assignment_id", sa.Integer),
                                          sa.Column("name", sa.String),
                                          sa.Column("weight", sa.Float),
                                          sa.Column("is_group", sa.Boolean))
                pairs_table = sa.Table("pairs", legacy,
                                       sa.Column("id", sa.Integer, primary_key=True),
                                       sa.Column("assignment_id", sa.Integer),
                                       sa.Column("criteria_id", sa.Integer),
                                       sa.Column("pair_type", sa.String),
                                       sa.Column("left_group_id", sa.Integer),
                                       sa.Column("right_group_id", sa.Integer),
                                       sa.Column("assigned_to_student_id", sa.Integer),
                                       sa.Column("assigned_to_instructor_email", sa.String),
                                       sa.Column("superseded_at", sa.DateTime(timezone=True)))
                votes_table = sa.Table("instructor_votes", legacy,
                                       sa.Column("pair_id", sa.Integer, primary_key=True),
                                       sa.Column("choice", sa.Integer),
                                       sa.Column("submitted_at", sa.DateTime(timezone=True)))
                submissions_table = sa.Table("submissions", legacy,
                                             sa.Column("id", sa.Integer, primary_key=True),
                                             sa.Column("student_id", sa.Integer),
                                             sa.Column("assignment_id", sa.Integer),
                                             sa.Column("section", sa.String),
                                             sa.Column("submitted_at", sa.DateTime(timezone=True)))
                choices_table = sa.Table("submission_choices", legacy,
                                         sa.Column("id", sa.Integer, primary_key=True),
                                         sa.Column("submission_id", sa.Integer),
                                         sa.Column("pair_id", sa.Integer),
                                         sa.Column("choice", sa.Integer))
                now = datetime.now(UTC)
                with engine.begin() as connection:
                    def add(table, **values):
                        return connection.execute(
                            table.insert().returning(table.c.id), values).scalar_one()

                    room_id = add(classrooms, name="Migration invariant",
                                  instructor_emails="teacher@example.edu")
                    group_ids = [add(groups_table, name=f"Group {number}", classroom_id=room_id)
                                 for number in (1, 2, 3)]
                    student_id = add(students, email="student@example.edu",
                                     classroom_id=room_id, group_id=group_ids[2])
                    assignment_id = add(assignments, title="Review", classroom_id=room_id)
                    criterion_id = add(criteria_table, assignment_id=assignment_id,
                                       name="Quality", weight=100, is_group=True)

                    def add_pair(left, right, student=None, instructor=None):
                        return add(pairs_table, assignment_id=assignment_id,
                                   criteria_id=criterion_id, pair_type="group",
                                   left_group_id=left, right_group_id=right,
                                   assigned_to_student_id=student,
                                   assigned_to_instructor_email=instructor)

                    earlier_id = add_pair(group_ids[0], group_ids[1], student=student_id)
                    later_id = add_pair(group_ids[1], group_ids[0], student=student_id)
                    instructor_earlier_id = add_pair(group_ids[0], group_ids[1],
                                                     instructor="Teacher@Example.edu")
                    instructor_later_id = add_pair(group_ids[1], group_ids[0],
                                                   instructor="teacher@example.edu")
                    connection.execute(votes_table.insert(), [
                        {"pair_id": instructor_earlier_id, "choice": 1,
                         "submitted_at": now - timedelta(days=1)},
                        {"pair_id": instructor_later_id, "choice": 5, "submitted_at": now},
                    ])
                    first_id = add(submissions_table, student_id=student_id,
                                   assignment_id=assignment_id, section="group",
                                   submitted_at=now - timedelta(days=1))
                    latest_id = add(submissions_table, student_id=student_id,
                                    assignment_id=assignment_id, section="group",
                                    submitted_at=now)
                    connection.execute(choices_table.insert(), [
                        {"submission_id": first_id, "pair_id": earlier_id, "choice": 1},
                        {"submission_id": latest_id, "pair_id": later_id, "choice": 5},
                    ])
                left_group_id, right_group_id = group_ids[0], group_ids[1]
                # Pinned to the revision under test. A later revision retires every
                # five-point answer, which is what this test asserts survives, so
                # upgrading to "head" would conflate two separate migrations.
                command.upgrade(config, "20261017_unique_pair_votes")
            with engine.begin() as connection:
                rows = dict(connection.execute(
                    sa.select(pairs_table.c.id, pairs_table.c.superseded_at)
                    .where(pairs_table.c.id.in_((earlier_id, later_id, instructor_earlier_id,
                                                 instructor_later_id)))).all())
                self.assertIsNotNone(rows[earlier_id])
                self.assertIsNone(rows[later_id])
                self.assertIsNotNone(rows[instructor_earlier_id])
                self.assertIsNone(rows[instructor_later_id])
                self.assertEqual(connection.scalar(sa.select(sa.func.count()).select_from(choices_table)), 2)
                self.assertEqual(connection.scalar(sa.select(sa.func.count()).select_from(votes_table)), 2)
            with self.assertRaises(IntegrityError), engine.begin() as connection:
                connection.execute(pairs_table.insert().values(
                    assignment_id=assignment_id, criteria_id=criterion_id, pair_type="group",
                    left_group_id=left_group_id, right_group_id=right_group_id,
                    assigned_to_student_id=student_id,
                ))
        finally:
            engine.dispose()
            with admin.begin() as connection:
                connection.execute(sa.text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            admin.dispose()

class SQLiteMigrationTests(unittest.TestCase):
    def test_migration_keeps_latest_answer_and_supersedes_other_active_rows(self) -> None:
        engine = sa.create_engine("sqlite+pysqlite:///:memory:")
        metadata = sa.MetaData()
        pairs = sa.Table("pairs", metadata,
                         sa.Column("id", sa.Integer, primary_key=True),
                         sa.Column("criteria_id", sa.Integer),
                         sa.Column("pair_type", sa.String),
                         sa.Column("left_id", sa.Integer),
                         sa.Column("right_id", sa.Integer),
                         sa.Column("left_group_id", sa.Integer),
                         sa.Column("right_group_id", sa.Integer),
                         sa.Column("assigned_to_student_id", sa.Integer),
                         sa.Column("assigned_to_instructor_email", sa.String),
                         sa.Column("superseded_at", sa.DateTime(timezone=True)))
        submissions = sa.Table("submissions", metadata,
                               sa.Column("id", sa.Integer, primary_key=True),
                               sa.Column("student_id", sa.Integer),
                               sa.Column("assignment_id", sa.Integer),
                               sa.Column("section", sa.String),
                               sa.Column("submitted_at", sa.DateTime(timezone=True)))
        choices = sa.Table("submission_choices", metadata,
                           sa.Column("submission_id", sa.Integer),
                           sa.Column("pair_id", sa.Integer))
        votes = sa.Table("instructor_votes", metadata,
                         sa.Column("pair_id", sa.Integer),
                         sa.Column("submitted_at", sa.DateTime(timezone=True)))
        metadata.create_all(engine)
        now = datetime.now(UTC)
        with engine.begin() as connection:
            legacy_pairs = [
                {"id": 1, "criteria_id": 1, "pair_type": "group", "left_group_id": 10,
                 "right_group_id": 20, "assigned_to_student_id": 7},
                {"id": 2, "criteria_id": 1, "pair_type": "group", "left_group_id": 20,
                 "right_group_id": 10, "assigned_to_student_id": 7},
                {"id": 3, "criteria_id": 2, "pair_type": "individual", "left_id": 11,
                 "right_id": 12, "assigned_to_instructor_email": "Teacher@Example.edu"},
                {"id": 4, "criteria_id": 2, "pair_type": "individual", "left_id": 12,
                 "right_id": 11, "assigned_to_instructor_email": "teacher@example.edu"},
            ]
            for pair in legacy_pairs:
                connection.execute(pairs.insert().values(**pair))
            connection.execute(submissions.insert(), [
                # Scoring defines the latest snapshot by ID. The intentionally
                # skewed timestamps prove migration cleanup uses that rule too.
                {"id": 1, "student_id": 7, "assignment_id": 1,
                 "section": "group", "submitted_at": now},
                {"id": 2, "student_id": 7, "assignment_id": 1,
                 "section": "group", "submitted_at": now - timedelta(days=1)},
            ])
            connection.execute(choices.insert(), [
                {"submission_id": 1, "pair_id": 1},
                {"submission_id": 2, "pair_id": 2},
            ])
            connection.execute(votes.insert(), [
                {"pair_id": 3, "submitted_at": now - timedelta(days=1)},
                {"pair_id": 4, "submitted_at": now},
            ])
            path = Path(__file__).resolve().parents[1] / "migrations/versions/20261017_unique_pair_votes.py"
            spec = importlib.util.spec_from_file_location("unique_active_evaluators_migration", path)
            assert spec is not None and spec.loader is not None
            migration = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(migration)
            migration.op = Operations(MigrationContext.configure(connection))
            migration.upgrade()
            active_ids = connection.scalars(sa.select(pairs.c.id).where(
                pairs.c.superseded_at.is_(None)).order_by(pairs.c.id)).all()
            self.assertEqual(active_ids, [2, 4])
            self.assertEqual(connection.scalar(sa.select(sa.func.count()).select_from(choices)), 2)
            self.assertEqual(connection.scalar(sa.select(sa.func.count()).select_from(votes)), 2)
            with self.assertRaises(IntegrityError), connection.begin_nested():
                connection.execute(pairs.insert().values(
                    id=5, criteria_id=1, pair_type="group", left_group_id=20,
                    right_group_id=10, assigned_to_student_id=7,
                ))
        engine.dispose()


class SixPointScaleMigrationTests(unittest.TestCase):
    def test_upgrade_adds_display_order_and_retires_five_point_answers(self) -> None:
        engine = sa.create_engine("sqlite+pysqlite:///:memory:")
        metadata = sa.MetaData()
        pairs = sa.Table("pairs", metadata,
                         sa.Column("id", sa.Integer, primary_key=True),
                         sa.Column("criteria_id", sa.Integer))
        submissions = sa.Table("submissions", metadata,
                               sa.Column("id", sa.Integer, primary_key=True),
                               sa.Column("student_id", sa.Integer))
        choices = sa.Table("submission_choices", metadata,
                           sa.Column("id", sa.Integer, primary_key=True),
                           sa.Column("submission_id", sa.Integer),
                           sa.Column("pair_id", sa.Integer),
                           sa.Column("choice", sa.Integer))
        drafts = sa.Table("draft_choices", metadata,
                          sa.Column("id", sa.Integer, primary_key=True),
                          sa.Column("student_id", sa.Integer),
                          sa.Column("pair_id", sa.Integer),
                          sa.Column("choice", sa.Integer))
        votes = sa.Table("instructor_votes", metadata,
                         sa.Column("pair_id", sa.Integer, primary_key=True),
                         sa.Column("choice", sa.Integer))
        metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(pairs.insert(), [{"id": 1, "criteria_id": 1}])
            connection.execute(submissions.insert(), [{"id": 1, "student_id": 1}])
            # choice 3 was "equal" on the five-point scale and 5 was an extreme.
            connection.execute(choices.insert(),
                               [{"id": 1, "submission_id": 1, "pair_id": 1, "choice": 3}])
            connection.execute(drafts.insert(),
                               [{"id": 1, "student_id": 1, "pair_id": 1, "choice": 5}])
            connection.execute(votes.insert(), [{"pair_id": 1, "choice": 3}])

            path = Path(__file__).resolve().parents[1] / "migrations/versions/20261020_six_point_scale.py"
            spec = importlib.util.spec_from_file_location("six_point_scale_migration", path)
            assert spec is not None and spec.loader is not None
            migration = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(migration)
            migration.op = Operations(MigrationContext.configure(connection))
            migration.upgrade()

            # The display order is recorded from here on, defaulting to "as stored".
            stored = connection.scalars(
                sa.select(sa.column("display_flipped")).select_from(sa.table("pairs"))).all()
            self.assertEqual([bool(value) for value in stored], [False])
            # Every five-point answer is retired: 3 meant "equal", and the
            # six-point table has no answer that means that, so nothing can carry
            # it over faithfully. The pairs themselves stay.
            for table in (choices, drafts, votes, submissions):
                self.assertEqual(connection.scalar(sa.select(sa.func.count()).select_from(table)), 0)
            self.assertEqual(connection.scalar(sa.select(sa.func.count()).select_from(pairs)), 1)
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
