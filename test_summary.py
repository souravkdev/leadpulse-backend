from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services import attendance_service as svc

DATABASE_URL = "postgresql://neondb_owner:npg_8KZMjpkn1WyB@ep-wandering-heart-aotw422s.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

summaries = svc.summarize_shift_assignments(db)
print("Summaries:")
for s in summaries:
    print(s)

db.close()
