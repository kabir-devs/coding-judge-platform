import datetime as dt
from typing import Optional, List, Any

from pydantic import BaseModel, EmailStr, Field


# ---------- Auth / Users ----------
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    email: EmailStr
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    rating: int
    is_admin: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Problems ----------
class TestCaseIn(BaseModel):
    input: str
    expected_output: str
    is_sample: bool = False


class ProblemCreate(BaseModel):
    slug: str
    title: str
    statement: str
    difficulty: str = "EASY"
    time_limit_sec: float = 2.0
    memory_limit_mb: int = 256
    points: int = 100
    test_cases: List[TestCaseIn]


class TestCaseOut(BaseModel):
    id: int
    input: str
    expected_output: str
    is_sample: bool

    class Config:
        from_attributes = True


class ProblemSummary(BaseModel):
    id: int
    slug: str
    title: str
    difficulty: str
    points: int

    class Config:
        from_attributes = True


class ProblemDetail(BaseModel):
    id: int
    slug: str
    title: str
    statement: str
    difficulty: str
    time_limit_sec: float
    memory_limit_mb: int
    points: int
    sample_tests: List[TestCaseOut]

    class Config:
        from_attributes = True


# ---------- Submissions ----------
class SubmissionCreate(BaseModel):
    problem_id: int
    language: str  # "python" | "cpp" | "java"
    source_code: str


class SubmissionOut(BaseModel):
    id: int
    problem_id: int
    language: str
    status: str
    runtime_ms: Optional[int]
    memory_kb: Optional[int]
    passed_tests: int
    total_tests: int
    stderr: Optional[str]
    result_detail: Optional[Any]
    submitted_at: dt.datetime

    class Config:
        from_attributes = True


# ---------- Leaderboard ----------
class LeaderboardEntry(BaseModel):
    rank: int
    username: str
    rating: int
    solved_count: int

