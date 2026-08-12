"""
Populate the DB with a couple of demo problems + test cases, and a demo
admin user. Run with: `python -m app.seed`
"""
from app.database import SessionLocal, Base, engine
from app import models, auth

Base.metadata.create_all(bind=engine)
db = SessionLocal()

if not db.query(models.User).filter_by(username="admin").first():
    db.add(models.User(
        username="admin", email="admin@example.com",
        hashed_password=auth.hash_password("admin12345"), is_admin=True,
    ))

if not db.query(models.Problem).filter_by(slug="two-sum").first():
    p = models.Problem(
        slug="two-sum", title="Two Sum",
        statement=(
            "Given a list of integers on one line and a target integer on "
            "the second line, print the 0-indexed positions of the two "
            "numbers that add up to the target, space separated."
        ),
        difficulty=models.Difficulty.EASY, time_limit_sec=2, memory_limit_mb=256, points=100,
    )
    p.test_cases = [
        models.TestCase(input="2 7 11 15\n9", expected_output="0 1", is_sample=True, order=0),
        models.TestCase(input="3 2 4\n6", expected_output="1 2", is_sample=True, order=1),
        models.TestCase(input="3 3\n6", expected_output="0 1", is_sample=False, order=2),
    ]
    db.add(p)

if not db.query(models.Problem).filter_by(slug="fizzbuzz").first():
    p2 = models.Problem(
        slug="fizzbuzz", title="FizzBuzz",
        statement="Given N, print numbers 1..N, one per line. Multiples of 3 -> Fizz, of 5 -> Buzz, of both -> FizzBuzz.",
        difficulty=models.Difficulty.EASY, time_limit_sec=2, memory_limit_mb=256, points=50,
    )
    p2.test_cases = [
        models.TestCase(input="5", expected_output="1\n2\nFizz\n4\nBuzz", is_sample=True, order=0),
        models.TestCase(input="15", expected_output="1\n2\nFizz\n4\nBuzz\nFizz\n7\n8\nFizz\nBuzz\n11\nFizz\n13\n14\nFizzBuzz", is_sample=False, order=1),
    ]
    db.add(p2)

db.commit()
db.close()
print("Seed complete.")

