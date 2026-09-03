from pathlib import Path
from sqlalchemy import select
from backend.app.db import SessionLocal
from backend.app.models import Certificate

ROOT = Path(__file__).resolve().parents[2]
FILES = [("AWS Credential", "AWS.png"), ("LabLab AI", "LabLabAI.png"), ("Unstacked Labs", "UnstackedLabs.png"), ("Zindi", "Zindi.png"), ("Redis Associate Developer", "rediscredential.png")]

def main():
    db = SessionLocal()
    try:
        for order, (title, filename) in enumerate(FILES):
            path = str(ROOT / "frontend" / "src" / "data" / "certificates" / filename)
            item = db.scalar(select(Certificate).where(Certificate.title == title))
            if item:
                item.image_url, item.custom_order = path, order
            else:
                db.add(Certificate(title=title, image_url=path, custom_order=order))
        db.commit()
        print(f"Seeded {len(FILES)} certificates")
    finally:
        db.close()

if __name__ == "__main__":
    main()
