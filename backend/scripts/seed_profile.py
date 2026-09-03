from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.models import Profile


def main():
    db = SessionLocal()
    try:
        profile = db.scalar(select(Profile).where(Profile.id == 1))
        payload = {
            "id": 1, "name": "Michael Odhiambo", "tagline": "I build and ship apps",
            "location": "Mombasa, Kenya", "focus": "Backend · AI · Web · Mobile",
            "experience": "3+ years building software", "availability_status": "Open to opportunities",
            "availability_detail": "Let's build something great together.",
        }
        if profile:
            for key, value in payload.items():
                setattr(profile, key, value)
        else:
            db.add(Profile(**payload))
        db.commit()
        print("Seeded profile")
    finally:
        db.close()


if __name__ == "__main__":
    main()
