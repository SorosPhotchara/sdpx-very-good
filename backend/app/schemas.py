from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr

class ClassroomBase(BaseModel):
    name: str
    instructor_emails: Optional[str] = ""

class ClassroomCreate(ClassroomBase):
    pass

class Classroom(ClassroomBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class StudentBase(BaseModel):
    email: EmailStr
    display_name: Optional[str] = None
    group_name: Optional[str] = None

class StudentCreate(StudentBase):
    classroom_id: int
    group_name: Optional[str] = None

class Student(StudentBase):
    id: int
    classroom_id: int
    group_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

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
    group_score: Decimal = Decimal("0")
    individual_score: Decimal = Decimal("0")
    instructor_weight: Decimal = Decimal("1")
    deadline: Optional[datetime] = None

class AssignmentCreate(AssignmentBase):
    pass

class Assignment(AssignmentBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class CriteriaBase(BaseModel):
    assignment_id: int
    name: str
    weight: Decimal
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
