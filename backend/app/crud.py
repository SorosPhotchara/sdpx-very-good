from sqlalchemy.orm import Session

from . import models, schemas

# Classroom

def get_classroom(db: Session, classroom_id: int):
    return db.query(models.Classroom).filter(models.Classroom.id == classroom_id).first()


def get_classrooms(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Classroom).offset(skip).limit(limit).all()


def create_classroom(db: Session, classroom: schemas.ClassroomCreate):
    db_classroom = models.Classroom(name=classroom.name, instructor_emails=classroom.instructor_emails)
    db.add(db_classroom)
    db.commit()
    db.refresh(db_classroom)
    return db_classroom

# Student

def get_student(db: Session, student_id: int):
    return db.query(models.Student).filter(models.Student.id == student_id).first()


def get_students(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Student).offset(skip).limit(limit).all()


def create_student(db: Session, student: schemas.StudentCreate):
    db_student = models.Student(
        email=student.email,
        display_name=student.display_name,
        group_name=student.group_name,
        classroom_id=student.classroom_id,
    )
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student

# Group

def create_group(db: Session, group: schemas.GroupCreate):
    db_group = models.Group(
        name=group.name,
        classroom_id=group.classroom_id,
    )
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group


def get_groups(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Group).offset(skip).limit(limit).all()

# Assignment

def get_assignment(db: Session, assignment_id: int):
    return db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()


def get_assignments(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Assignment).offset(skip).limit(limit).all()


def create_assignment(db: Session, assignment: schemas.AssignmentCreate):
    db_assignment = models.Assignment(
        title=assignment.title,
        description=assignment.description,
        classroom_id=assignment.classroom_id,
        group_score=assignment.group_score,
        individual_score=assignment.individual_score,
        instructor_weight=assignment.instructor_weight,
        deadline=assignment.deadline,
    )
    db.add(db_assignment)
    db.commit()
    db.refresh(db_assignment)
    return db_assignment

# Criteria

def create_criteria(db: Session, criteria: schemas.CriteriaCreate):
    db_criteria = models.Criteria(
        assignment_id=criteria.assignment_id,
        name=criteria.name,
        weight=criteria.weight,
        is_group=criteria.is_group,
    )
    db.add(db_criteria)
    db.commit()
    db.refresh(db_criteria)
    return db_criteria

# Pair

def create_pair(db: Session, pair: schemas.PairCreate):
    db_pair = models.Pair(
        assignment_id=pair.assignment_id,
        criteria_id=pair.criteria_id,
        left_id=pair.left_id,
        right_id=pair.right_id,
        pair_type=pair.pair_type,
    )
    db.add(db_pair)
    db.commit()
    db.refresh(db_pair)
    return db_pair
