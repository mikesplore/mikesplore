import mimetypes
import re
from pathlib import Path

import boto3
from sqlalchemy import select

from backend.app.config import settings
from backend.app.db import SessionLocal
from backend.app.models import Certificate

ROOT = Path(__file__).resolve().parents[2]
FILES = [("AWS Credential", "AWS.png"), ("LabLab AI", "LabLabAI.png"), ("Unstacked Labs", "UnstackedLabs.png"), ("Zindi", "Zindi.png"), ("Redis Associate Developer", "rediscredential.png")]


def object_slug(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.lower())).strip("-")

def main():
    required = (settings.r2_endpoint_url, settings.r2_access_key_id, settings.r2_secret_access_key,
                settings.r2_bucket_name, settings.r2_public_base_url)
    if not all(required):
        raise RuntimeError("R2 is not fully configured in the repository-root .env")
    client = boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint_url,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
    )
    db = SessionLocal()
    try:
        for order, (title, filename) in enumerate(FILES):
            path = ROOT / "frontend" / "src" / "data" / "certificates" / filename
            if not path.is_file():
                raise FileNotFoundError(f"Certificate file not found: {path}")
            object_key = f"certificates/{object_slug(title)}-{filename}"
            with path.open("rb") as certificate_file:
                client.upload_fileobj(
                    certificate_file,
                    settings.r2_bucket_name,
                    object_key,
                    ExtraArgs={"ContentType": mimetypes.guess_type(filename)[0] or "application/octet-stream"},
                )
            image_url = f"{settings.r2_public_base_url.rstrip('/')}/{object_key}"
            item = db.scalar(select(Certificate).where(Certificate.title == title))
            if item:
                item.image_url, item.custom_order, item.is_visible = image_url, order, True
            else:
                db.add(Certificate(title=title, image_url=image_url, custom_order=order, is_visible=True))
        db.commit()
        print(f"Uploaded and seeded {len(FILES)} certificates to R2")
    finally:
        db.close()

if __name__ == "__main__":
    main()
