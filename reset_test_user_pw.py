from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.core.security import hash_password

DATABASE_URL = "postgresql://neondb_owner:npg_8KZMjpkn1WyB@ep-wandering-heart-aotw422s.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

user = db.query(User).filter(User.email == "Test.demo@gmail.com").first()
if user:
    user.hashed_password = hash_password("Test@123")
    db.commit()
    print("Successfully set Test User password to 'Test@123'")
else:
    print("Test User not found!")

db.close()
