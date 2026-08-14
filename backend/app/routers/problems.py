from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth

router = APIRouter(prefix="/api/problems", tags=["problems"])


@router.get("", response_model=List[schemas.ProblemSummary])
def list_problems(db: Session = Depends(get_db)):
    return db.query(models.Problem).order_by(models.Problem.id).all()


@router.get("/{slug}", response_model=schemas.ProblemDetail)
def get_problem(slug: str, db: Session = Depends(get_db)):
    problem = db.query(models.Problem).filter(models.Problem.slug == slug).first()
    if not problem:
        raise HTTPException(404, "Problem not found")
    sample_tests = [tc for tc in problem.test_cases if tc.is_sample]
    return schemas.ProblemDetail(
        id=problem.id, slug=problem.slug, title=problem.title, statement=problem.statement,
        difficulty=problem.difficulty.value, time_limit_sec=problem.time_limit_sec,
        memory_limit_mb=problem.memory_limit_mb, points=problem.points,
        sample_tests=sample_tests,
    )


@router.post("", response_model=schemas.ProblemSummary, status_code=201)
def create_problem(
    payload: schemas.ProblemCreate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(auth.require_admin),
):
    if db.query(models.Problem).filter(models.Problem.slug == payload.slug).first():
        raise HTTPException(400, "Slug already exists")

    problem = models.Problem(
        slug=payload.slug, title=payload.title, statement=payload.statement,
        difficulty=models.Difficulty(payload.difficulty),
        time_limit_sec=payload.time_limit_sec, memory_limit_mb=payload.memory_limit_mb,
        points=payload.points,
    )
    for i, tc in enumerate(payload.test_cases):
        problem.test_cases.append(models.TestCase(
            input=tc.input, expected_output=tc.expected_output,
            is_sample=tc.is_sample, order=i,
        ))
    db.add(problem)
    db.commit()
    db.refresh(problem)
    return problem

