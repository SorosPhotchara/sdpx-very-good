from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr

class ClassroomBase(BaseModel):
    name: str
    instructor_emails: Optional[str] = ""

class ClassroomCreate(ClassroomBase):
    pass

class Classroom(ClassroomBase):
    id: int

    class Config:
        orm_mode = True

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

    class Config:
        orm_mode = True

class GroupBase(BaseModel):
    name: str
    classroom_id: int

class GroupCreate(GroupBase):
    pass

class Group(GroupBase):
    id: int

    class Config:
        orm_mode = True

class AssignmentBase(BaseModel):
    title: str
    description: Optional[str] = None
    classroom_id: int
    group_score: float = 0.0
    individual_score: float = 0.0
    instructor_weight: float = 1.0
    deadline: Optional[datetime] = None

class AssignmentCreate(AssignmentBase):
    pass

class Assignment(AssignmentBase):
    id: int

    class Config:
        orm_mode = True

class CriteriaBase(BaseModel):
    assignment_id: int
    name: str
    weight: float
    is_group: bool = True

class CriteriaCreate(CriteriaBase):
    pass

class Criteria(CriteriaBase):
    id: int

    class Config:
        orm_mode = True

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

    class Config:
        orm_mode = True
