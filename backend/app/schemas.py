from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .timezone import as_utc

class ClassroomBase(BaseModel):
    name: str
    instructor_emails: Optional[str] = ""

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("Classroom name is required")
        return name

class ClassroomCreate(ClassroomBase):
    pass

class Classroom(ClassroomBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class StudentBase(BaseModel):
    email: EmailStr
    display_name: Optional[str] = None
    group_name: Optional[str] = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

class StudentCreate(StudentBase):
    classroom_id: int
    group_name: Optional[str] = None

class Student(StudentBase):
    id: int
    classroom_id: int
    group_id: Optional[int] = None
    activated_at: Optional[datetime] = None
    group_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("activated_at", mode="before")
    @classmethod
    def activated_at_is_utc(cls, value: datetime | None) -> datetime | None:
        return as_utc(value)

class GroupBase(BaseModel):
    name: str
    classroom_id: int

class GroupCreate(GroupBase):
    pass

class Group(GroupBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class AssignmentBase(BaseModel):
    title: str
    description: Optional[str] = None
    classroom_id: int
    group_score: float = 0.0
    individual_score: float = 0.0
    group_participation_max: float = 0.0
    individual_participation_max: float = 0.0
    instructor_weight: float = 1.0
    deadline: Optional[datetime] = None
    group_deadline: Optional[datetime] = None
    individual_deadline: Optional[datetime] = None
    published_at: Optional[datetime] = None

    @field_validator("deadline", "group_deadline", "individual_deadline", "published_at", mode="before")
    @classmethod
    def timestamps_are_utc(cls, value: datetime | None) -> datetime | None:
        return as_utc(value)

class AssignmentCreate(AssignmentBase):
    pass

class Assignment(AssignmentBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class CriteriaBase(BaseModel):
    assignment_id: int
    name: str
    weight: float
    is_group: bool = True

class CriteriaCreate(CriteriaBase):
    pass

class Criteria(CriteriaBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class PairBase(BaseModel):
    assignment_id: int
    criteria_id: int
    left_id: int
    right_id: int
    pair_type: str

class PairCreate(PairBase):
    pass

class Pair(PairBase):
    id: int
    assigned_count: int
    model_config = ConfigDict(from_attributes=True)


class RosterImportRequest(BaseModel):
    csv_text: str


class RosterImportResponse(BaseModel):
    imported: int
    errors: list[str]


class CriterionInput(BaseModel):
    name: str
    weight: float


class AssignmentSetup(BaseModel):
    title: str
    group_score: float = 0.0
    individual_score: float = 0.0
    group_participation_max: float = 0.0
    individual_participation_max: float = 0.0
    instructor_weight: float = 1.0
    group_deadline: datetime | None = None
    individual_deadline: datetime | None = None
    group_criteria: list[CriterionInput] = Field(default_factory=list)
    individual_criteria: list[CriterionInput] = Field(default_factory=list)


class DraftChange(BaseModel):
    pair_id: int
    choice: int | None = Field(default=None, ge=1, le=5)


class DraftChanges(BaseModel):
    changes: list[DraftChange]


class InstructorInvite(BaseModel):
    email: EmailStr


class InstructorPairRequest(BaseModel):
    criteria_id: int
    left_id: int
    right_id: int
    instructor_email: EmailStr


class InstructorVoteRequest(BaseModel):
    choice: int = Field(ge=1, le=5)


class GroupReassignmentRequest(BaseModel):
    group_id: int
