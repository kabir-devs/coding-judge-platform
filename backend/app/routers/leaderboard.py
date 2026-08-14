from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])


@router.get("", response_model=List[schemas.LeaderboardEntry])
def leaderboard(db: Session = Depends(get_db), limit: int = 50):
    # Solved-count = distinct problems with >=1 ACCEPTED submission per user.
    solved_subq = (
        db.query(
            models.Submission.user_id,
            func.count(func.distinct(models.Submission.problem_id)).label("solved_count"),
        )
        .filter(models.Submission.status == models.SubmissionStatus.ACCEPTED)
        .group_by(models.Submission.user_id)
        .subquery()
    )

    rows = (
        db.query(models.User, solved_subq.c.solved_count)
        .outerjoin(solved_subq, models.User.id == solved_subq.c.user_id)
        .order_by(models.User.rating.desc())
        .limit(limit)
        .all()
    )

    return [
        schemas.LeaderboardEntry(
            rank=i + 1,
            username=user.username,
            rating=user.rating,
            solved_count=solved_count or 0,
        )
        for i, (user, solved_count) in enumerate(rows)
    ]

