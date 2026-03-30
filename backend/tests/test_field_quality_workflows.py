import os
from pathlib import Path

import pytest
import requests


# Core auth + workflow regression tests for field quality MVP endpoints
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


def _require_base_url() -> str:
    if not BASE_URL:
        pytest.fail("REACT_APP_BACKEND_URL is not set")
    return BASE_URL


@pytest.fixture(scope="session")
def credentials():
    path = Path("/app/memory/test_credentials.md")
    text = path.read_text(encoding="utf-8")
    if "management@fieldquality.local" not in text or "owner@fieldquality.local" not in text:
        pytest.fail("Required test credentials missing in /app/memory/test_credentials.md")
    return {
        "management": {"email": "management@fieldquality.local", "password": "FieldQA123!"},
        "owner": {"email": "owner@fieldquality.local", "password": "FieldQA123!"},
    }


@pytest.fixture(scope="session")
def api_client():
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    return session


@pytest.fixture(scope="session")
def management_auth(api_client, credentials):
    base_url = _require_base_url()
    response = api_client.post(f"{base_url}/api/auth/login", json=credentials["management"], timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["role"] == "management"
    assert isinstance(data["token"], str) and len(data["token"]) > 20
    return data


@pytest.fixture(scope="session")
def owner_auth(api_client, credentials):
    base_url = _require_base_url()
    response = api_client.post(f"{base_url}/api/auth/login", json=credentials["owner"], timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["role"] == "owner"
    assert isinstance(data["token"], str) and len(data["token"]) > 20
    return data


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_management_login_and_me(api_client, management_auth):
    base_url = _require_base_url()
    response = api_client.get(f"{base_url}/api/auth/me", headers=_auth_headers(management_auth["token"]), timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "management@fieldquality.local"
    assert data["role"] == "management"


def test_owner_login_and_me(api_client, owner_auth):
    base_url = _require_base_url()
    response = api_client.get(f"{base_url}/api/auth/me", headers=_auth_headers(owner_auth["token"]), timeout=30)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "owner@fieldquality.local"
    assert data["role"] == "owner"


def test_public_crew_portal_route_and_jobs(api_client):
    base_url = _require_base_url()
    access_response = api_client.get(f"{base_url}/api/public/crew-access", timeout=30)
    assert access_response.status_code == 200
    access_links = access_response.json()
    assert isinstance(access_links, list) and len(access_links) > 0

    code = access_links[0]["code"]
    route_response = api_client.get(f"{base_url}/api/public/crew-access/{code}", timeout=30)
    assert route_response.status_code == 200
    route_data = route_response.json()
    assert route_data["code"] == code
    assert route_data["enabled"] is True

    jobs_response = api_client.get(f"{base_url}/api/public/jobs?access_code={code}", timeout=30)
    assert jobs_response.status_code == 200
    jobs_data = jobs_response.json()
    assert isinstance(jobs_data["jobs"], list)
    assert jobs_data["crew_link"]["code"] == code


@pytest.fixture(scope="session")
def created_submission(api_client):
    base_url = _require_base_url()

    access_links = api_client.get(f"{base_url}/api/public/crew-access", timeout=30).json()
    assert len(access_links) > 0
    link = access_links[0]

    jobs_payload = api_client.get(f"{base_url}/api/public/jobs?access_code={link['code']}", timeout=30).json()
    jobs = jobs_payload["jobs"]
    assert len(jobs) > 0
    job = jobs[0]

    files = [
        ("photos", ("test1.jpg", b"\xff\xd8\xff\xdbtestphoto1", "image/jpeg")),
        ("photos", ("test2.jpg", b"\xff\xd8\xff\xdbtestphoto2", "image/jpeg")),
        ("photos", ("test3.jpg", b"\xff\xd8\xff\xdbtestphoto3", "image/jpeg")),
    ]
    form_data = {
        "access_code": link["code"],
        "job_id": job["id"],
        "truck_number": link["truck_number"],
        "gps_lat": "43.631000",
        "gps_lng": "-79.412000",
        "gps_accuracy": "7",
        "note": "TEST_qa_submission",
        "area_tag": "TEST_front",
    }

    submission_response = api_client.post(
        f"{base_url}/api/public/submissions",
        data=form_data,
        files=files,
        timeout=60,
    )
    assert submission_response.status_code == 200
    payload = submission_response.json()
    submission = payload["submission"]
    assert submission["matched_job_id"] == job["id"]
    assert submission["photo_count"] == 3
    assert submission["gps"]["lat"] == 43.631
    return submission


def test_management_review_save_and_verify(api_client, management_auth, created_submission):
    base_url = _require_base_url()

    detail_before = api_client.get(
        f"{base_url}/api/submissions/{created_submission['id']}",
        headers=_auth_headers(management_auth["token"]),
        timeout=30,
    )
    assert detail_before.status_code == 200
    detail_payload = detail_before.json()
    categories = detail_payload["rubric"]["categories"]
    category_scores = {item["key"]: max(item["max_score"] - 1, 1) for item in categories}

    review_response = api_client.post(
        f"{base_url}/api/reviews/management",
        headers={**_auth_headers(management_auth["token"]), "Content-Type": "application/json"},
        json={
            "submission_id": created_submission["id"],
            "job_id": created_submission["matched_job_id"],
            "service_type": created_submission["service_type"],
            "category_scores": category_scores,
            "comments": "TEST_management_review",
            "disposition": "pass with notes",
            "flagged_issues": ["TEST_minor_issue"],
        },
        timeout=30,
    )
    assert review_response.status_code == 200
    review_payload = review_response.json()
    assert review_payload["review"]["submission_id"] == created_submission["id"]
    assert review_payload["submission"]["status"] == "Management Reviewed"

    detail_after = api_client.get(
        f"{base_url}/api/submissions/{created_submission['id']}",
        headers=_auth_headers(management_auth["token"]),
        timeout=30,
    )
    assert detail_after.status_code == 200
    detail_after_payload = detail_after.json()
    assert detail_after_payload["management_review"]["comments"] == "TEST_management_review"
    assert detail_after_payload["submission"]["status"] == "Management Reviewed"


def test_owner_review_finalize_and_verify(api_client, owner_auth, created_submission):
    base_url = _require_base_url()

    detail_before = api_client.get(
        f"{base_url}/api/submissions/{created_submission['id']}",
        headers=_auth_headers(owner_auth["token"]),
        timeout=30,
    )
    assert detail_before.status_code == 200
    detail_payload = detail_before.json()
    categories = detail_payload["rubric"]["categories"]
    category_scores = {item["key"]: item["max_score"] for item in categories}

    owner_response = api_client.post(
        f"{base_url}/api/reviews/owner",
        headers={**_auth_headers(owner_auth["token"]), "Content-Type": "application/json"},
        json={
            "submission_id": created_submission["id"],
            "category_scores": category_scores,
            "comments": "TEST_owner_review",
            "final_disposition": "pass",
            "training_inclusion": "approved",
            "exclusion_reason": "",
        },
        timeout=30,
    )
    assert owner_response.status_code == 200
    owner_payload = owner_response.json()
    assert owner_payload["review"]["submission_id"] == created_submission["id"]
    assert owner_payload["submission"]["status"] == "Export Ready"

    detail_after = api_client.get(
        f"{base_url}/api/submissions/{created_submission['id']}",
        headers=_auth_headers(owner_auth["token"]),
        timeout=30,
    )
    assert detail_after.status_code == 200
    detail_after_payload = detail_after.json()
    assert detail_after_payload["owner_review"]["training_inclusion"] == "approved"
    assert detail_after_payload["submission"]["status"] == "Export Ready"


def test_exports_run_and_download(api_client, management_auth):
    base_url = _require_base_url()
    headers = {**_auth_headers(management_auth["token"]), "Content-Type": "application/json"}

    run_response = api_client.post(
        f"{base_url}/api/exports/run",
        headers=headers,
        json={"dataset_type": "owner_gold", "export_format": "csv"},
        timeout=60,
    )
    assert run_response.status_code == 200
    export_record = run_response.json()
    assert export_record["dataset_type"] == "owner_gold"
    assert export_record["export_format"] == "csv"
    assert isinstance(export_record["row_count"], int)

    list_response = api_client.get(
        f"{base_url}/api/exports",
        headers=_auth_headers(management_auth["token"]),
        timeout=30,
    )
    assert list_response.status_code == 200
    exports_list = list_response.json()
    assert any(item["id"] == export_record["id"] for item in exports_list)

    download_response = api_client.get(
        f"{base_url}/api/exports/{export_record['id']}/download",
        headers=_auth_headers(management_auth["token"]),
        timeout=30,
    )
    assert download_response.status_code == 200
    assert len(download_response.content) > 0


def test_analytics_jobs_and_settings(api_client, management_auth):
    base_url = _require_base_url()
    headers = _auth_headers(management_auth["token"])

    analytics_response = api_client.get(f"{base_url}/api/analytics/summary", headers=headers, timeout=30)
    assert analytics_response.status_code == 200
    analytics = analytics_response.json()
    assert isinstance(analytics["average_score_by_crew"], list)
    assert "training_approved_count" in analytics

    jobs_response = api_client.get(f"{base_url}/api/jobs", headers=headers, timeout=30)
    assert jobs_response.status_code == 200
    jobs = jobs_response.json()
    assert isinstance(jobs, list) and len(jobs) > 0
    assert all("job_id" in job for job in jobs[:3])

    drive_response = api_client.get(f"{base_url}/api/integrations/drive/status", headers=headers, timeout=30)
    assert drive_response.status_code == 200
    drive_status = drive_response.json()
    assert "configured" in drive_status and "connected" in drive_status

    blueprint_response = api_client.get(f"{base_url}/api/system/blueprint", headers=headers, timeout=30)
    assert blueprint_response.status_code == 200
    blueprint = blueprint_response.json()
    assert "architecture" in blueprint and "database_schema" in blueprint