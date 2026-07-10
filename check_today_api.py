from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.models.attendance import ShiftTemplate, ShiftAssignment, AttendanceSession
from app.services import attendance_service as svc
from app.core.timezone import work_date_for_user

DATABASE_URL = "postgresql://neondb_owner:npg_8KZMjpkn1WyB@ep-wandering-heart-aotw422s.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

user = db.query(User).filter(User.email == "Test.demo@gmail.com").first()
if user:
    print(f"User found: {user.full_name} ({user.id})")
    
    # 1. Get work date
    work_date = work_date_for_user(db, user.id)
    print(f"Computed Work Date: {work_date}")
    
    # 2. Get shift assignment
    shift = svc.get_shift_for_date(db, user.id, work_date)
    if shift:
        print(f"Shift Assignment found: {shift.id}, Template: {shift.shift_template.name if shift.shift_template else 'None'}")
    else:
        print("No Shift Assignment found for this work date!")
        
    # 3. Get today session
    session = svc.get_today_session(db, user)
    if session:
        print(f"Session found: {session.id}, status: {session.status}")
    else:
        print("No Session found for today")
else:
    print("User not found!")

db.close()
