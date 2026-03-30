import os
from pathlib import Path

import pytest
import requests


# Notification + analytics + workflow regression coverage for phase features
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


def _base_url() -> str:
    if not BASE_URL:
        pytest.fail("REACT_APP_BACKEND_URL is not set")
    return BASE_URL


@pytest.fixture(scope="session")
def credentials():
    creds_file = Path("/app/memory/test_credentials.md")
    if not creds_file.exists():
        pytest.fail("/app/memory/test_credentials.md is missing")
    text = creds_file.read_text(encoding="utf-8")
    if "management@fieldquality.local" not in text or "owner@fieldquality.local" not in text:
        pytest.fail("Required management/owner credentials missing in /app/memory/test_credentials.md")
    return {
        "management": {"email": "management@fieldquality.local", "password": "FieldQA123!"},
        "owner": {"email": "owner@fieldquality.local", "password": "FieldQA123!"},
    }


@pytest.fixture(scope="session")
def api_client():
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    return session


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def management_auth(api_client, credentials):
    response = api_client.post(f"{_base_url()}/api/auth/login", json=credentials["management"], timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["role"] == "management"
    return data


@pytest.fixture(scope="session")
def owner_auth(api_client, credentials):
    response = api_client.post(f"{_base_url()}/api/auth/login", json=credentials["owner"], timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["role"] == "owner"
    return data


@pytest.fixture(scope="session")
def created_submission(api_client):
    base = _base_url()
    links_response = api_client.get(f"{base}/api/public/crew-access", timeout=30)
    assert links_response.status_code == 200
    links = links_response.json()
    assert isinstance(links, list) and links
    access = links[0]

    jobs_response = api_client.get(f"{base}/api/public/jobs?access_code={access['code']}", timeout=30)
    assert jobs_response.status_code == 200
    jobs_payload = jobs_response.json()
    jobs = jobs_payload["jobs"]
    assert isinstance(jobs, list) and jobs
    job = jobs[0]

    files = [
        ("photos", ("qa-note-1.jpg", b"\xff\xd8\xff\xdbnotif1", "image/jpeg")),
        ("photos", ("qa-note-2.jpg", b"\xff\xd8\xff\xdbnotif2", "image/jpeg")),
        ("photos", ("qa-note-3.jpg", b"\xff\xd8\xff\xdbnotif3", "image/jpeg")),
    ]
    payload = {
        "access_code": access["code"],
        "job_id": job["id"],
        "truck_number": access["truck_number"],
        "gps_lat": "43.631000",
        "gps_lng": "-79.412000",
        "gps_accuracy": "7",
        "note": "TEST_notification_submission",
        "area_tag": "TEST_followup_area",
    }
    submission_response = api_client.post(f"{base}/api/public/submissions", data=payload, files=files, timeout=60)
    assert submission_response.status_code == 200
    submission = submission_response.json()["submission"]
    assert submission["photo_count"] == 3
    assert submission["status"] in {"Ready for Review", "Pending Match"}
    submission["_test_access_code"] = access["code"]
    return submission


def test_management_notification_after_crew_submission(api_client, management_auth, created_submission):
    response = api_client.get(
        f"{_base_url()}/api/notifications?status=unread",
        headers=_auth_headers(management_auth["token"]),
        timeout=30,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["items"], list)
    matched = [
        item
        for item in data["items"]
        if item.get("related_submission_id") == created_submission["id"] and item.get("notification_type") == "new_submission"
    ]
    assert matched, "Expected management new_submission notification not found"
    assert data["unread_count"] >= 1


def test_management_review_creates_owner_and_crew_notifications(api_client, management_auth, created_submission):
    detail_response = api_client.get(
        f"{_base_url()}/api/submissions/{created_submission['id']}",
        headers=_auth_headers(management_auth["token"]),
        timeout=30,
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    rubric_categories = detail["rubric"]["categories"]
    category_scores = {item["key"]: max(item["max_score"] - 1, 1) for item in rubric_categories}

    review_response = api_client.post(
        f"{_base_url()}/api/reviews/management",
        headers={**_auth_headers(management_auth["token"]), "Content-Type": "application/json"},
        json={
            "submission_id": created_submission["id"],
            "job_id": created_submission["matched_job_id"],
            "service_type": created_submission["service_type"],
            "category_scores": category_scores,
            "comments": "TEST_management_followup_needed",
            "disposition": "correction required",
            "flagged_issues": ["TEST_missing_angle"],
        },
        timeout=30,
    )
    assert review_response.status_code == 200
    review_payload = review_response.json()
    assert review_payload["submission"]["status"] == "Management Reviewed"
    assert review_payload["review"]["disposition"] == "correction required"

    crew_portal = api_client.get(
        f"{_base_url()}/api/public/crew-access/{created_submission['_test_access_code']}",
        timeout=30,
    )
    assert crew_portal.status_code == 200
    crew_data = crew_portal.json()
    crew_notes = [
        item
        for item in (crew_data.get("notifications") or [])
        if item.get("related_submission_id") == created_submission["id"] and item.get("notification_type") == "crew_followup"
    ]
    assert crew_notes, "Expected crew follow-up notification not found"


def test_owner_notification_after_management_review(api_client, owner_auth, created_submission):
    response = api_client.get(
        f"{_base_url()}/api/notifications?status=unread",
        headers=_auth_headers(owner_auth["token"]),
        timeout=30,
    )
    assert response.status_code == 200
    data = response.json()
    owner_notes = [
        item
        for item in data["items"]
        if item.get("related_submission_id") == created_submission["id"] and item.get("notification_type") == "owner_review"
    ]
    assert owner_notes, "Expected owner owner_review notification not found"


def test_notifications_mark_read(api_client, management_auth):
    list_response = api_client.get(
        f"{_base_url()}/api/notifications?status=unread",
        headers=_auth_headers(management_auth["token"]),
        timeout=30,
    )
    assert list_response.status_code == 200
    unread_payload = list_response.json()
    if not unread_payload["items"]:
        pytest.skip("No unread notifications to mark as read")

    target = unread_payload["items"][0]
    mark_response = api_client.post(
        f"{_base_url()}/api/notifications/{target['id']}/read",
        headers={**_auth_headers(management_auth["token"]), "Content-Type": "application/json"},
        json={},
        timeout=30,
    )
    assert mark_response.status_code == 200
    assert mark_response.json()["ok"] is True

    verify_response = api_client.get(
        f"{_base_url()}/api/notifications?status=all",
        headers=_auth_headers(management_auth["token"]),
        timeout=30,
    )
    assert verify_response.status_code == 200
    items = verify_response.json()["items"]
    match = [item for item in items if item["id"] == target["id"]]
    assert match
    assert match[0]["status"] == "read"


def test_analytics_calibration_heatmap_shape(api_client, management_auth):
    response = api_client.get(
        f"{_base_url()}/api/analytics/summary",
        headers=_auth_headers(management_auth["token"]),
        timeout=30,
    )
    assert response.status_code == 200
    payload = response.json()
    assert "calibration_heatmap" in payload
    assert isinstance(payload["calibration_heatmap"], list)
    if payload["calibration_heatmap"]:
        cell = payload["calibration_heatmap"][0]
        assert "crew" in cell and isinstance(cell["crew"], str)
        assert "service_type" in cell and isinstance(cell["service_type"], str)
        assert "variance_average" in cell


def test_settings_blueprint_and_learning_content_sources(api_client, management_auth):
    blueprint_response = api_client.get(
        f"{_base_url()}/api/system/blueprint",
        headers=_auth_headers(management_auth["token"]),
        timeout=30,
    )
    assert blueprint_response.status_code == 200
    blueprint = blueprint_response.json()
    assert isinstance(blueprint.get("architecture"), dict)
    assert isinstance(blueprint.get("implementation_plan"), list)
    assert len(blueprint.get("implementation_plan", [])) >= 3

    drive_response = api_client.get(
        f"{_base_url()}/api/integrations/drive/status",
        headers=_auth_headers(management_auth["token"]),
        timeout=30,
    )
    assert drive_response.status_code == 200
    drive_status = drive_response.json()
    assert "configured" in drive_status and isinstance(drive_status["configured"], bool)
    assert "connected" in drive_status and isinstance(drive_status["connected"], bool)


def test_owner_review_and_exports_still_work(api_client, owner_auth, created_submission):
    detail_response = api_client.get(
        f"{_base_url()}/api/submissions/{created_submission['id']}",
        headers=_auth_headers(owner_auth["token"]),
        timeout=30,
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    categories = detail["rubric"]["categories"]
    category_scores = {item["key"]: item["max_score"] for item in categories}

    owner_review_response = api_client.post(
        f"{_base_url()}/api/reviews/owner",
        headers={**_auth_headers(owner_auth["token"]), "Content-Type": "application/json"},
        json={
            "submission_id": created_submission["id"],
            "category_scores": category_scores,
            "comments": "TEST_owner_finalize_after_notifications",
            "final_disposition": "pass",
            "training_inclusion": "approved",
            "exclusion_reason": "",
        },
        timeout=30,
    )
    assert owner_review_response.status_code == 200
    owner_payload = owner_review_response.json()
    assert owner_payload["submission"]["status"] == "Export Ready"

    export_response = api_client.post(
        f"{_base_url()}/api/exports/run",
        headers={**_auth_headers(owner_auth["token"]), "Content-Type": "application/json"},
        json={"dataset_type": "owner_gold", "export_format": "jsonl"},
        timeout=60,
    )
    assert export_response.status_code == 200
    export_payload = export_response.json()
    assert export_payload["dataset_type"] == "owner_gold"
    assert export_payload["export_format"] == "jsonl"