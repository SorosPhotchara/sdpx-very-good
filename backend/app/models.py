from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Table, Text, UniqueConstraint, and_, func, text
from sqlalchemy.orm import relationship
from .database import Base

class Classroom(Base):
    __tablename__ = "classrooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    instructor_emails = Column(Text, default="")

    students = relationship("Student", back_populates="classroom")
    groups = relationship("Group", back_populates="classroom")
    assignments = relationship("Assignment", back_populates="classroom")


# Deleted classrooms retain their evidence independently of active records.
classroom_archives = Table(
    "classroom_archives", Base.metadata,
    Column("id", Integer, primary_key=True),
    Column("classroom_id", Integer, nullable=False, index=True),
    Column("deleted_at", DateTime(timezone=True), nullable=False),
    Column("retain_until", DateTime(timezone=True), nullable=False),
    Column("deleted_by", String, nullable=False),
    Column("snapshot", JSON, nullable=False),
)


class InstructorApproval(Base):
    __tablename__ = "instructor_approvals"

    email = Column(String, primary_key=True)
    approved_by = Column(String, nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=False)

class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"))

    classroom = relationship("Classroom", back_populates="groups")
    students = relationship("Student", back_populates="group")

class Student(Base):
    __tablename__ = "students"
    __table_args__ = (UniqueConstraint("classroom_id", "email", name="uq_students_classroom_email"),)

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True)
    display_name = Column(String, nullable=True)
    group_name = Column(String, nullable=True)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"))
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    activated_at = Column(DateTime(timezone=True), nullable=True)

    classroom = relationship("Classroom", back_populates="students")
    group = relationship("Group", back_populates="students")

class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text, nullable=True)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"))
    group_score = Column(Float, default=0.0)
    individual_score = Column(Float, default=0.0)
    group_participation_max = Column(Float, default=0.0)
    individual_participation_max = Column(Float, default=0.0)
    instructor_weight = Column(Float, default=1.0)
    deadline = Column(DateTime, nullable=True)
    group_deadline = Column(DateTime(timezone=True), nullable=True)
    individual_deadline = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)

    classroom = relationship("Classroom", back_populates="assignments")
    criteria = relationship("Criteria", back_populates="assignment")
    pairs = relationship("Pair", back_populates="assignment")

class Criteria(Base):
    __tablename__ = "criteria"

    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"))
    name = Column(String, index=True)
    weight = Column(Float, default=0.0)
    is_group = Column(Boolean, default=True)

    assignment = relationship("Assignment", back_populates="criteria")

class Pair(Base):
    __tablename__ = "pairs"

    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"))
    criteria_id = Column(Integer, ForeignKey("criteria.id"))
    left_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    right_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    left_group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    right_group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    assigned_to_student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    assigned_to_instructor_email = Column(String, nullable=True)
    pair_type = Column(String, default="individual")
    assigned_count = Column(Integer, default=0)
    superseded_at = Column(DateTime(timezone=True), nullable=True)

    assignment = relationship("Assignment", back_populates="pairs")
    criteria = relationship("Criteria")


def _active_pair_index(name: str, evaluator: object, left: object, right: object,
                       pair_type: str, student: bool) -> Index:
    ordered_left = text(f"(CASE WHEN {left.key} < {right.key} THEN {left.key} ELSE {right.key} END)")
    ordered_right = text(f"(CASE WHEN {left.key} < {right.key} THEN {right.key} ELSE {left.key} END)")
    predicate = and_(Pair.superseded_at.is_(None), Pair.pair_type == pair_type,
                     Pair.assigned_to_student_id.is_not(None) if student
                     else Pair.assigned_to_instructor_email.is_not(None))
    return Index(name, Pair.criteria_id, evaluator, ordered_left, ordered_right,
                 unique=True, postgresql_where=predicate, sqlite_where=predicate)


# One active assignment/vote per evaluator and unordered subject pair.
_active_pair_index("uq_pairs_active_student_group", Pair.assigned_to_student_id,
                   Pair.left_group_id, Pair.right_group_id, "group", True)
_active_pair_index("uq_pairs_active_student_individual", Pair.assigned_to_student_id,
                   Pair.left_id, Pair.right_id, "individual", True)
_active_pair_index("uq_pairs_active_instructor_group", func.lower(func.trim(Pair.assigned_to_instructor_email)),
                   Pair.left_group_id, Pair.right_group_id, "group", False)
_active_pair_index("uq_pairs_active_instructor_individual", func.lower(func.trim(Pair.assigned_to_instructor_email)),
                   Pair.left_id, Pair.right_id, "individual", False)


class DraftChoice(Base):
    __tablename__ = "draft_choices"
    __table_args__ = (UniqueConstraint("student_id", "pair_id", name="uq_draft_student_pair"),)

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    pair_id = Column(Integer, ForeignKey("pairs.id"), nullable=False)
    choice = Column(Integer, nullable=False)


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=False)
    section = Column(String, nullable=False)
    submitted_at = Column(DateTime(timezone=True), nullable=False)
    choices = relationship("SubmissionChoice", back_populates="submission")


class SubmissionChoice(Base):
    __tablename__ = "submission_choices"
    __table_args__ = (UniqueConstraint("submission_id", "pair_id", name="uq_submission_pair"),)

    id = Column(Integer, primary_key=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)
    pair_id = Column(Integer, ForeignKey("pairs.id"), nullable=False)
    choice = Column(Integer, nullable=False)
    submission = relationship("Submission", back_populates="choices")


class InstructorVote(Base):
    __tablename__ = "instructor_votes"

    pair_id = Column(Integer, ForeignKey("pairs.id"), primary_key=True)
    choice = Column(Integer, nullable=False)
    submitted_at = Column(DateTime(timezone=True), nullable=False)


class Reassignment(Base):
    __tablename__ = "reassignments"

    id = Column(Integer, primary_key=True)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    old_group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    new_group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    instructor_email = Column(String, nullable=False)
    changed_at = Column(DateTime(timezone=True), nullable=False)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
