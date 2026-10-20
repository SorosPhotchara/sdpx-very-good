from datetime import datetime
from math import isclose, isfinite
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field, field_validator, model_validator

from .scoring import DEFAULT_COMPLETION_THRESHOLD, DEFAULT_SCORE_CEILING, DEFAULT_SCORE_FLOOR
from .timezone import as_utc

class ClassroomName(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("Classroom name is required")
        return name

class ClassroomBase(ClassroomName):
    instructor_emails: Optional[str] = ""

class ClassroomRename(ClassroomName):
    pass

class ClassroomCreate(ClassroomBase):
    pass

class Classroom(ClassroomBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class InstructorApprovalCreate(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class InstructorApprovalRead(BaseModel):
    email: str
    source: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
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
    instructor_weight: float = 1.0
    score_floor: float = 0.6
    score_ceiling: float = 1.0
    completion_threshold: float = 0.9
    target_coverage: int = 5
    group_max_workload: int = 8
    individual_max_workload: int = 21
    min_comparisons: int = 3
    deadline: Optional[datetime] = None
    group_deadline: Optional[datetime] = None
    individual_deadline: Optional[datetime] = None
    published_at: Optional[datetime] = None

    @computed_field(return_type=float)
    @property
    def total_score(self) -> float:
        return self.group_score + self.individual_score

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
    total_score: float | None = None
    instructor_weight: float = 1.0
    # Omitted means "keep whatever the assignment already has" (§9.3, §9.4).
    score_floor: float | None = None
    score_ceiling: float | None = None
    completion_threshold: float | None = None
    target_coverage: int | None = None
    group_max_workload: int | None = None
    individual_max_workload: int | None = None
    min_comparisons: int | None = None
    group_deadline: datetime | None = None
    individual_deadline: datetime | None = None
    group_criteria: list[CriterionInput] = Field(default_factory=list)
    individual_criteria: list[CriterionInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def total_matches_section_maxima(self) -> "AssignmentSetup":
        maxima = (self.group_score, self.individual_score)
        if any(not isfinite(value) or value < 0 for value in maxima):
            raise ValueError("Score maxima must be finite and nonnegative")
        if not isfinite(self.instructor_weight) or self.instructor_weight <= 0:
            raise ValueError("Instructor weight must be finite and positive")
        floor = DEFAULT_SCORE_FLOOR if self.score_floor is None else self.score_floor
        ceiling = DEFAULT_SCORE_CEILING if self.score_ceiling is None else self.score_ceiling
        if not all(isfinite(value) for value in (floor, ceiling)) or not 0 <= floor < ceiling <= 1:
            raise ValueError("Score band needs 0 <= score_floor < score_ceiling <= 1")
        threshold = (DEFAULT_COMPLETION_THRESHOLD if self.completion_threshold is None
                     else self.completion_threshold)
        if not isfinite(threshold) or not 0 < threshold <= 1:
            raise ValueError("Completion threshold must be within (0, 1]")
        limits = (("target_coverage", self.target_coverage, 1, 20),
                  ("group_max_workload", self.group_max_workload, 1, 30),
                  ("individual_max_workload", self.individual_max_workload, 1, 100),
                  ("min_comparisons", self.min_comparisons, 1, 50))
        for name, value, low, high in limits:
            if value is not None and not low <= value <= high:
                raise ValueError(f"{name} must be between {low} and {high}")
        expected = sum(maxima)
        if self.total_score is not None and (
            not isfinite(self.total_score)
            or not isclose(self.total_score, expected, rel_tol=0, abs_tol=1e-6)
        ):
            raise ValueError("Total score must equal the sum of section maxima")
        self.total_score = expected
        return self


class DraftChange(BaseModel):
    pair_id: int
    choice: int | None = Field(default=None, ge=1, le=6)


class DraftChanges(BaseModel):
    changes: list[DraftChange]


class StudentRemoval(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class InstructorInvite(BaseModel):
    email: EmailStr


class InstructorPairRequest(BaseModel):
    criteria_id: int
    left_id: int
    right_id: int
    instructor_email: EmailStr


class StudentPairRequest(BaseModel):
    criteria_id: int
    left_id: int
    right_id: int
    student_id: int


class InstructorVoteRequest(BaseModel):
    choice: int = Field(ge=1, le=6)


class GroupReassignmentRequest(BaseModel):
    group_id: int
