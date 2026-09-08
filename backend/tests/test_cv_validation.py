import pytest
from fastapi import HTTPException

from app.main import _apply_cv_patch, _validate_cv_patch


def base_cv():
    return {
        "name": "Test User",
        "title": "Engineer",
        "contact": {},
        "summary": "Original summary",
        "skills": [{"category": "Languages", "items": ["Python", "Kotlin"]}],
        "projects": [{"name": "Vela", "date": "2025", "stack": ["Python"], "bullets": ["Built it"]}],
        "certifications": [],
        "education": [{"institution": "School", "degree": "Degree"}],
    }


def valid_patch():
    return {
        "summary": {"old": "Original summary", "new": "Tailored summary"},
        "selected_projects": ["vela"],
        "selected_skills": {"Languages": ["Python"]},
    }


def test_cv_patch_applies_only_verified_project_and_skills():
    result = _apply_cv_patch(base_cv(), valid_patch())
    assert result["summary"] == "Tailored summary"
    assert result["projects"] == [{"name": "Vela", "date": "2025", "stack": ["Python"], "bullets": ["Built it"]}]
    assert result["skills"] == [{"category": "Languages", "items": ["Python"]}]


def test_cv_patch_rejects_unknown_project():
    patch = valid_patch() | {"selected_projects": ["unknown-project"]}
    with pytest.raises(HTTPException, match="Unknown project IDs"):
        _apply_cv_patch(base_cv(), patch)


def test_cv_patch_rejects_unknown_skill():
    patch = valid_patch() | {"selected_skills": {"Languages": ["Rust"]}}
    with pytest.raises(HTTPException, match="Unknown skills"):
        _apply_cv_patch(base_cv(), patch)


def test_cv_patch_requires_exact_shape():
    with pytest.raises(HTTPException, match="exactly summary"):
        _validate_cv_patch({"summary": {}})
