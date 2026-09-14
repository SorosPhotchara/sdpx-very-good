from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="PairEval Backend",
    description="Prototype backend for the PairEval pairwise evaluation system.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/classrooms/", response_model=schemas.Classroom)
def create_classroom(classroom: schemas.ClassroomCreate, db: Session = Depends(get_db)):
    return crud.create_classroom(db=db, classroom=classroom)

@app.get("/classrooms/")
def read_classrooms(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_classrooms(db, skip=skip, limit=limit)

@app.post("/students/", response_model=schemas.Student)
def create_student(student: schemas.StudentCreate, db: Session = Depends(get_db)):
    return crud.create_student(db=db, student=student)

@app.get("/students/")
def read_students(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_students(db, skip=skip, limit=limit)

@app.post("/groups/", response_model=schemas.Group)
def create_group(group: schemas.GroupCreate, db: Session = Depends(get_db)):
    return crud.create_group(db=db, group=group)

@app.get("/groups/")
def read_groups(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_groups(db, skip=skip, limit=limit)

@app.post("/assignments/", response_model=schemas.Assignment)
def create_assignment(assignment: schemas.AssignmentCreate, db: Session = Depends(get_db)):
    return crud.create_assignment(db=db, assignment=assignment)

@app.get("/assignments/")
def read_assignments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_assignments(db, skip=skip, limit=limit)

@app.post("/criteria/", response_model=schemas.Criteria)
def create_criteria(criteria: schemas.CriteriaCreate, db: Session = Depends(get_db)):
    return crud.create_criteria(db=db, criteria=criteria)

@app.post("/pairs/", response_model=schemas.Pair)
def create_pair(pair: schemas.PairCreate, db: Session = Depends(get_db)):
    return crud.create_pair(db=db, pair=pair)
