"""
This is the job function enqueued onto Redis (via rq) by the API layer.
Run one or more workers with:

    rq worker submissions --url redis://localhost:6379/0

Scaling horizontally = running more worker processes/containers pointed
at the same Redis instance. Each worker picks the next job off the
queue, so submissions are naturally load-balanced across judge hosts.
"""
import datetime as dt

from app.database import SessionLocal
from app import models
from app.judge.executor import executor


def judge_submission_job(submission_id: int):
    db = SessionLocal()
    try:
        submission = db.query(models.Submission).get(submission_id)
        if submission is None:
            return

        submission.status = models.SubmissionStatus.RUNNING
        db.commit()

        problem = submission.problem
        test_cases = [
            {"input": tc.input, "expected_output": tc.expected_output}
            for tc in sorted(problem.test_cases, key=lambda t: t.order)
        ]

        verdict = executor.judge_submission(
            language=submission.language,
            source_code=submission.source_code,
            test_cases=test_cases,
            time_limit_sec=problem.time_limit_sec,
            memory_limit_mb=problem.memory_limit_mb,
        )

        submission.status = models.SubmissionStatus(verdict.status)
        submission.passed_tests = verdict.passed_tests
        submission.total_tests = verdict.total_tests
        submission.runtime_ms = verdict.runtime_ms
        submission.memory_kb = verdict.memory_kb
        submission.stderr = verdict.stderr[:4000] if verdict.stderr else None
        submission.result_detail = verdict.detail
        submission.judged_at = dt.datetime.utcnow()

        # Bump rating on first-ever AC for this user+problem (simple ELO-lite bump)
        if verdict.status == "ACCEPTED":
            already_solved = (
                db.query(models.Submission)
                .filter(
                    models.Submission.user_id == submission.user_id,
                    models.Submission.problem_id == submission.problem_id,
                    models.Submission.status == models.SubmissionStatus.ACCEPTED,
                    models.Submission.id != submission.id,
                )
                .first()
            )
            if not already_solved:
                bump = {"EASY": 10, "MEDIUM": 25, "HARD": 50}.get(problem.difficulty.value, 10)
                submission.user.rating += bump

        db.commit()
    except Exception as e:  # noqa: BLE001 - never let a bad submission kill the worker
        db.rollback()
        submission = db.query(models.Submission).get(submission_id)
        if submission:
            submission.status = models.SubmissionStatus.INTERNAL_ERROR
            submission.stderr = str(e)[:2000]
            db.commit()
    finally:
        db.close()
