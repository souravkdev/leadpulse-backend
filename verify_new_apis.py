import requests
import sys

BASE_URL = "http://localhost:8000/api/v1"

def test_flow():
    print("1. Logging in as Admin...")
    r = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "admin@leadpulse.com",
        "password": "Admin@123"
    })
    if r.status_code != 200:
        print(f"FAILED to login as admin: {r.text}")
        sys.exit(1)
    admin_token = r.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("Admin login successful.")

    print("\n2. Creating a shift template with custom break configurations...")
    template_name = "Verification Shift Template"
    # Delete existing if any
    r = requests.get(f"{BASE_URL}/attendance/admin/shifts/templates", headers=admin_headers)
    for t in r.json():
        if t["name"] == template_name:
            requests.delete(f"{BASE_URL}/attendance/admin/shifts/templates/{t['id']}", headers=admin_headers)

    r = requests.post(f"{BASE_URL}/attendance/admin/shifts/templates", headers=admin_headers, json={
        "name": template_name,
        "start_time": "09:00:00",
        "end_time": "18:00:00",
        "days_of_week": "0,1,2,3,4",
        "lunch_break_minutes": 45,
        "short_break_minutes": 10,
    })
    if r.status_code != 201:
        print(f"FAILED to create shift template: {r.text}")
        sys.exit(1)
    template = r.json()
    print(f"Shift template created successfully: {template}")
    assert template["lunch_break_minutes"] == 45
    assert template["short_break_minutes"] == 10

    print("\n3. Logging in as Test User...")
    r = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "Test.demo@gmail.com",
        "password": "Test@123"
    })
    if r.status_code != 200:
        print(f"FAILED to login as Test User: {r.text}")
        sys.exit(1)
    user_token = r.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}
    print("Test User login successful.")

    print("\n4. Assigning shift template to Test User for today...")
    # Get test user id
    r = requests.get(f"{BASE_URL}/auth/me", headers=user_headers)
    user_id = r.json()["id"]
    from datetime import date
    today_str = date.today().isoformat()
    
    r = requests.post(f"{BASE_URL}/attendance/admin/shifts/assignments", headers=admin_headers, json={
        "user_id": user_id,
        "shift_template_id": template["id"],
        "start_date": today_str,
        "end_date": today_str
    })
    if r.status_code != 201:
        print(f"FAILED to assign shift: {r.text}")
        sys.exit(1)
    print("Shift assigned successfully.")

    # Clean up any existing sessions for today to start fresh
    print("\nCleaning up today's sessions for test user...")
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.attendance import AttendanceSession
    engine = create_engine("postgresql://neondb_owner:npg_8KZMjpkn1WyB@ep-wandering-heart-aotw422s.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    db.query(AttendanceSession).filter(
        AttendanceSession.user_id == user_id,
        AttendanceSession.work_date == date.today()
    ).delete()
    db.commit()
    db.close()
    print("Cleaned up today's sessions.")

    print("\n5. Testing clock-in 1...")
    r = requests.post(f"{BASE_URL}/attendance/clock-in", headers=user_headers)
    if r.status_code != 200:
        print(f"FAILED clock-in 1: {r.text}")
        sys.exit(1)
    session1 = r.json()
    print(f"Clock-in 1 successful: {session1['status']}")

    print("\n6. Testing clock-out 1...")
    r = requests.post(f"{BASE_URL}/attendance/clock-out", headers=user_headers)
    if r.status_code != 200:
        print(f"FAILED clock-out 1: {r.text}")
        sys.exit(1)
    session1_out = r.json()
    print(f"Clock-out 1 successful: {session1_out['status']}")

    print("\n7. Testing clock-in 2 (should succeed now!)...")
    r = requests.post(f"{BASE_URL}/attendance/clock-in", headers=user_headers)
    if r.status_code != 200:
        print(f"FAILED clock-in 2: {r.text}")
        sys.exit(1)
    session2 = r.json()
    print(f"Clock-in 2 successful: {session2['status']}")

    print("\n8. Starting a short break...")
    r = requests.post(f"{BASE_URL}/attendance/break/start", headers=user_headers, json={"break_type": "short"})
    if r.status_code != 200:
        print(f"FAILED to start short break: {r.text}")
        sys.exit(1)
    print("Short break started successfully.")

    print("\n9. Ending the break...")
    r = requests.post(f"{BASE_URL}/attendance/break/end", headers=user_headers)
    if r.status_code != 200:
        print(f"FAILED to end break: {r.text}")
        sys.exit(1)
    print("Break ended successfully.")

    print("\n10. Fetching today's attendance details...")
    r = requests.get(f"{BASE_URL}/attendance/today", headers=user_headers)
    if r.status_code != 200:
        print(f"FAILED to get today's attendance: {r.text}")
        sys.exit(1)
    today_details = r.json()
    print(f"Today details: {today_details}")

    assert today_details["lunch_breaks_taken"] == 0
    assert today_details["lunch_break_minutes"] == 45
    assert today_details["short_break_minutes"] == 10
    assert today_details["shift_warning"] is False
    assert today_details["shift_name"] == template_name

    # Clean up shift template at the end
    print("\nCleaning up shift template...")
    requests.delete(f"{BASE_URL}/attendance/admin/shifts/templates/{template['id']}", headers=admin_headers)
    print("ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_flow()
