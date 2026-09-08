"""R2-backed asset and certificate upload, listing, and deletion endpoints."""

from io import BytesIO
from uuid import UUID, uuid4

try:
    import boto3
except ImportError:  # R2 support is optional for read-only and test usage.
    boto3 = None

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import require_service_key
from ..config import settings
from ..db import get_db
from ..models import Certificate, SiteAsset, SiteSetting
from ..services.sync import slugify

router = APIRouter(tags=["assets"])

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def _r2_client():
    """Return a configured S3-compatible client or raise a clear service error."""
    if boto3 is None:
        raise HTTPException(status_code=503, detail="Object storage support is not installed")
    if not all((settings.r2_endpoint_url, settings.r2_access_key_id, settings.r2_secret_access_key, settings.r2_bucket_name, settings.r2_public_base_url)):
        raise HTTPException(status_code=503, detail="R2 storage is not configured")
    return boto3.client("s3", endpoint_url=settings.r2_endpoint_url, aws_access_key_id=settings.r2_access_key_id, aws_secret_access_key=settings.r2_secret_access_key, region_name="auto")


def _public_base() -> str:
    return settings.r2_public_base_url.rstrip("/") + "/"


def _public_url(object_key: str) -> str:
    return _public_base() + object_key


@router.get("/certificates")
def list_certificates(db: Session = Depends(get_db)):
    return db.scalars(select(Certificate).where(Certificate.is_visible.is_(True)).order_by(Certificate.custom_order)).all()


@router.delete("/certificates/{certificate_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_service_key)])
def delete_certificate(certificate_id: UUID, db: Session = Depends(get_db)):
    certificate = db.get(Certificate, certificate_id)
    if not certificate:
        raise HTTPException(status_code=404, detail="Certificate not found")
    db.delete(certificate)
    db.commit()


@router.post("/certificates", response_model=dict, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_service_key)])
def upload_certificate(title: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db)):
    client = _r2_client()
    object_key = f"certificates/{slugify(title)}-{uuid4().hex}-{file.filename}"
    file_bytes = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Certificate file exceeds the 5 MB limit")
    client.upload_fileobj(BytesIO(file_bytes), settings.r2_bucket_name, object_key, ExtraArgs={"ContentType": file.content_type or "application/octet-stream"})
    item = Certificate(title=title, image_url=_public_url(object_key), custom_order=0)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": str(item.id), "title": item.title, "image_url": item.image_url}


@router.get("/assets")
def list_assets(db: Session = Depends(get_db)):
    return [{"id": asset.id, "asset_type": asset.asset_type, "url": asset.url, "label": asset.label} for asset in db.scalars(select(SiteAsset)).all()]


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_service_key)])
def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.get(SiteAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    db.delete(asset)
    db.commit()


@router.post("/assets", response_model=dict, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_service_key)])
async def upload_asset(asset_type: str = Form(...), label: str = Form(""), file: UploadFile = File(...), db: Session = Depends(get_db)):
    client = _r2_client()
    object_key = f"assets/{slugify(asset_type)}/{slugify(label or file.filename or 'upload')}-{uuid4().hex}-{file.filename}"
    file_bytes = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Upload exceeds the 5 MB limit")
    cv_text = None
    if asset_type == "cv":
        try:
            cv_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(file_bytes)).pages).strip()
        except Exception:
            raise HTTPException(status_code=400, detail="The CV must be a readable PDF file")
    client.upload_fileobj(BytesIO(file_bytes), settings.r2_bucket_name, object_key, ExtraArgs={"ContentType": file.content_type or "application/octet-stream"})
    asset_url = _public_url(object_key)
    item = None
    previous_url = None
    if asset_type in {"profile-image", "cv"}:
        item = db.scalar(select(SiteAsset).where(SiteAsset.asset_type == asset_type))
    if item:
        previous_url = item.url
        item.label, item.url = label or file.filename, asset_url
    else:
        item = SiteAsset(asset_type=asset_type, label=label or file.filename, url=asset_url)
        db.add(item)
    db.commit()
    db.refresh(item)
    if asset_type == "cv":
        cv_setting = db.get(SiteSetting, "cv_text")
        if cv_setting:
            cv_setting.value = {"text": cv_text, "asset_url": asset_url}
        else:
            db.add(SiteSetting(key="cv_text", value={"text": cv_text, "asset_url": asset_url}))
        db.commit()
    if previous_url and previous_url.startswith(_public_base()):
        previous_key = previous_url.removeprefix(_public_base())
        if previous_key != object_key:
            try:
                client.delete_object(Bucket=settings.r2_bucket_name, Key=previous_key)
            except Exception:
                pass
    return {"id": item.id, "asset_type": item.asset_type, "label": item.label, "url": item.url}