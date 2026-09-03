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
            "about": "The Backstory\n\nI'm a software engineer based in Mombasa who builds backend systems, Android applications, and distributed AI-powered tools. My journey started in 2023 during my second year of computer science. I took the coursework seriously, but I quickly realized the real learning happens when you start building.\n\nWhat I Build\n\nI work primarily with Python and Kotlin, but my real focus is figuring out how systems fit together. Recently that's meant building Vela, a distributed AI assistant ecosystem connecting Linux hosts, Android clients, cloud infrastructure, and MCP-compatible AI agents.\n\nHow I Think About Engineering\n\nI care about system boundaries, reliability, and shipping software that actually works in production. I enjoy the hard questions: how do multiple clients interact with one host, how do you authenticate remote operations, and how do you keep a growing system extensible instead of tangled.\n\nWhat I'm Looking For\n\nI'm looking for a team where I can apply my systems architecture skills to scale distributed infrastructure and ship reliable AI-powered products.",
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
