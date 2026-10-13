import asyncio
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

import pytest
from starlette.datastructures import Headers, UploadFile
from fastapi import HTTPException

from app.models import Entry, EntryAsset, SiteAsset
from app.routers import assets


class FakeStorage:
    def __init__(self):
        self.uploaded = []
        self.deleted = []

    def upload_fileobj(self, fileobj, bucket, key, ExtraArgs):
        self.uploaded.append((bucket, key, ExtraArgs["ContentType"]))

    def delete_object(self, Bucket, Key):
        self.deleted.append((Bucket, Key))


class FakeQuery:
    def filter(self, *args):
        return self

    def delete(self, synchronize_session=False):
        return 0


class FakeDB:
    def __init__(self, entry, fail_commit=False):
        self.entry = entry
        self.fail_commit = fail_commit
        self.added = []
        self.rolled_back = False

    def get(self, model, identity):
        return self.entry if model is Entry and identity == self.entry.id else None

    def scalar(self, query):
        return None

    def add(self, item):
        self.added.append(item)

    def query(self, model):
        return FakeQuery()

    def flush(self):
        for item in self.added:
            if isinstance(item, SiteAsset) and item.id is None:
                item.id = 23

    def commit(self):
        if self.fail_commit:
            raise RuntimeError("database unavailable")
        for item in self.added:
            if isinstance(item, EntryAsset):
                item.id = 42

    def rollback(self):
        self.rolled_back = True

    def refresh(self, item):
        return None


def setup_media_upload(monkeypatch, db):
    storage = FakeStorage()
    monkeypatch.setattr(assets, "_r2_client", lambda: storage)
    monkeypatch.setattr(assets, "_public_base", lambda: "https://cdn.example/")
    monkeypatch.setattr(assets, "settings", SimpleNamespace(r2_bucket_name="portfolio"))
    upload = UploadFile(
        filename="cover.png",
        file=BytesIO(b"image bytes"),
        headers=Headers({"content-type": "image/png"}),
    )
    return storage, upload


def test_entry_image_upload_stores_and_attaches_in_one_database_commit(monkeypatch):
    entry = Entry(id=uuid4(), slug="event", content_type="event", title="Event", blurb="desc")
    db = FakeDB(entry)
    storage, upload = setup_media_upload(monkeypatch, db)
    result = asyncio.run(assets.upload_asset(
        asset_type="event-image", label="Cover", file=upload, entry_id=entry.id,
        role="card", alt_text="Event stage", caption="Opening", custom_order=0,
        replace_role=True, db=db,
    ))
    link = next(item for item in db.added if isinstance(item, EntryAsset))
    asset = next(item for item in db.added if isinstance(item, SiteAsset))
    assert result["entry_asset_id"] == 42
    assert link.asset_id == asset.id == 23
    assert link.entry_id == entry.id and link.role == "card"
    assert link.alt_text == "Event stage" and link.caption == "Opening"
    assert storage.uploaded and not storage.deleted


def test_entry_image_upload_removes_storage_object_when_database_commit_fails(monkeypatch):
    entry = Entry(id=uuid4(), slug="project", content_type="project", title="Project", blurb="desc")
    db = FakeDB(entry, fail_commit=True)
    storage, upload = setup_media_upload(monkeypatch, db)
    with pytest.raises(RuntimeError, match="database unavailable"):
        asyncio.run(assets.upload_asset(
            asset_type="project-image", label="Card", file=upload, entry_id=entry.id,
            role="card", replace_role=True, db=db,
        ))
    assert db.rolled_back
    assert len(storage.uploaded) == len(storage.deleted) == 1


def test_entry_media_rejects_non_image_files_before_upload(monkeypatch):
    entry = Entry(id=uuid4(), slug="project", content_type="project", title="Project", blurb="desc")
    db = FakeDB(entry)
    storage, _ = setup_media_upload(monkeypatch, db)
    upload = UploadFile(filename="notes.txt", file=BytesIO(b"text"), headers=Headers({"content-type": "text/plain"}))
    with pytest.raises(HTTPException) as error:
        asyncio.run(assets.upload_asset(
            asset_type="project-image", label="Card", file=upload, entry_id=entry.id,
            role="card", db=db,
        ))
    assert error.value.status_code == 415
    assert error.value.detail == "Entry media must be an image"
    assert not storage.uploaded
