from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
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

class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"))

    classroom = relationship("Classroom", back_populates="groups")
    students = relationship("Student", back_populates="group")

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    display_name = Column(String, nullable=True)
    group_name = Column(String, nullable=True)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"))
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)

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
    instructor_weight = Column(Float, default=1.0)
    deadline = Column(DateTime, nullable=True)

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
    pair_type = Column(String, default="individual")
    assigned_count = Column(Integer, default=0)

    assignment = relationship("Assignment", back_populates="pairs")
    criteria = relationship("Criteria")
