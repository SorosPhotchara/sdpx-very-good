from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
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
