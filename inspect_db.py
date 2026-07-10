import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.models.attendance import ShiftTemplate, ShiftAssignment

DATABASE_URL = "postgresql://neondb_owner:npg_8KZMjpkn1WyB@ep-wandering-heart-aotw422s.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

print("--- USERS ---")
users = db.query(User).all()
for u in users:
    print(f"ID: {u.id}, Name: {u.full_name}, Email: {u.email}, Role: {u.role}")

print("\n--- SHIFT TEMPLATES ---")
templates = db.query(ShiftTemplate).all()
for t in templates:
    print(f"ID: {t.id}, Name: {t.name}, Time: {t.start_time}-{t.end_time}, Days: {t.days_of_week}")

print("\n--- SHIFT ASSIGNMENTS ---")
assignments = db.query(ShiftAssignment).all()
for a in assignments:
    print(f"ID: {a.id}, User ID: {a.user_id}, Template ID: {a.shift_template_id}, Date: {a.assignment_date}")

db.close()
