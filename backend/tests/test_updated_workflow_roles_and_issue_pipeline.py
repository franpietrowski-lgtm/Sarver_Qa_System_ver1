import csv
import io
import os
import uuid
from pathlib import Path

import pytest
import requests


# Updated workflow regression: role logins, owner-only calibration access, free-text crew issue pipeline, and exports


def _base_url() -> str:
    base = os.environ.get("REACT_APP_BACKEND_URL", "").strip().rstrip("/")
    if base:
        return base

    env_file = Path("/app/frontend/.env")
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("REACT_APP_BACKEND_URL="):
                value = line.split("=", 1)[1].strip().strip('"').strip("'")
                if value:
                    return value.rstrip("/")

    pytest.fail("REACT_APP_BACKEND_URL is not set")


def _parse_credentials() -> dict:
    creds_path = Path("/app/memory/test_credentials.md")
    if not creds_path.exists():
        pytest.fail("/app/memory/test_credentials.md is missing")

    title_map = {}
    current_title = None
    current_email = None
    current_password = None

    for raw_line in creds_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("- ") and "email:" not in line and "password:" not in line:
            if current_title and current_email and current_password:
                title_map[current_title] = {"email": current_email, "password": current_password}
            current_title = line[2:].strip()
            current_email = None
            current_password = None
        elif line.startswith("- email:"):
            current_email = line.split(":", 1)[1].strip()
        elif line.startswith("- password:"):
            current_password = line.split(":", 1)[1].strip()

    if current_title and current_email and current_password:
        title_map[current_title] = {"email": current_email, "password": current_password}

    required = ["GM", "Account Manager", "Production Manager", "Supervisor", "Owner"]
    missing = [title for title in required if title not in title_map]
    if missing:
        pytest.fail(f"Missing credentials in /app/memory/test_credentials.md: {', '.join(missing)}")
    return title_map


@pytest.fixture(scope="session")
def base_url() -> str:
    return _base_url()


@pytest.fixture(scope="session")
def api_client():
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    return session


@pytest.fixture(scope="session")
def creds_by_title() -> dict:
    return _parse_credentials()


def _login(api_client: requests.Session, base_url: str, email: str, password: str) -> dict:
    response = api_client.post(
        f"{base_url}/api/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data.get("token"), str) and len(data["token"]) > 20
    assert data["user"]["email"] == email
    return data


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def logins(api_client, base_url, creds_by_title):
    return {title: _login(api_client, base_url, creds["email"], creds["password"]) for title, creds in creds_by_title.items()}


@pytest.fixture(scope="session")
def created_free_text_issue_submission(api_client, base_url):
    crew_response = api_client.get(f"{base_url}/api/public/crew-access", timeout=30)
    assert crew_response.status_code == 200
    links = crew_response.json()
    assert isinstance(links, list) and len(links) > 0
    access = links[0]

    unique_job_name = f"TEST FreeText Job {uuid.uuid4().hex[:8]}"
    files = [
        ("photos", ("proof-1.jpg", b"\xff\xd8\xff\xdbproof1", "image/jpeg")),
        ("photos", ("proof-2.jpg", b"\xff\xd8\xff\xdbproof2", "image/jpeg")),
        ("photos", ("proof-3.jpg", b"\xff\xd8\xff\xdbproof3", "image/jpeg")),
        ("issue_photos", ("issue-1.jpg", b"\xff\xd8\xff\xdbissue1", "image/jpeg")),
    ]
    payload = {
        "access_code": access["code"],
        "job_name": unique_job_name,
        "truck_number": access["truck_number"],
        "gps_lat": "43.631000",
        "gps_lng": "-79.412000",
        "gps_accuracy": "7",
        "note": "TEST free-text capture",
        "area_tag": "TEST area",
        "issue_type": "Property damage",
        "issue_notes": "TEST issue notes with attachment",
    }

    submit_response = api_client.post(
        f"{base_url}/api/public/submissions",
        data=payload,
        files=files,
        timeout=60,
    )
    assert submit_response.status_code == 200
    submission = submit_response.json()["submission"]

    assert submission["job_id"] is None
    assert submission["job_name_input"] == unique_job_name
    assert submission["field_report"]["reported"] is True
    assert submission["field_report"]["type"] == "Property damage"
    assert len(submission["field_report"]["photo_files"]) == 1
    return submission


def test_all_required_role_logins_and_auth_me(api_client, base_url, logins):
    for title in ["GM", "Account Manager", "Production Manager", "Supervisor", "Owner"]:
        login_data = logins[title]
        me_response = api_client.get(
            f"{base_url}/api/auth/me",
            headers=_auth_headers(login_data["token"]),
            timeout=30,
        )
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["title"] == title


def test_owner_only_calibration_write_access(api_client, base_url, logins):
    production_manager_token = logins["Production Manager"]["token"]
    forbidden_response = api_client.post(
        f"{base_url}/api/reviews/owner",
        headers={**_auth_headers(production_manager_token), "Content-Type": "application/json"},
        json={
            "submission_id": "sub_nonexistent",
            "category_scores": {},
            "comments": "",
            "final_disposition": "pass",
            "training_inclusion": "approved",
            "exclusion_reason": "",
        },
        timeout=30,
    )
    assert forbidden_response.status_code == 403


def test_owner_can_access_calibration_and_analytics_workspace_apis(api_client, base_url, logins):
    owner_token = logins["Owner"]["token"]
    owner_scope = api_client.get(
        f"{base_url}/api/submissions?scope=owner&filter_by=all",
        headers=_auth_headers(owner_token),
        timeout=30,
    )
    assert owner_scope.status_code == 200
    assert isinstance(owner_scope.json(), list)

    analytics = api_client.get(
        f"{base_url}/api/analytics/summary",
        headers=_auth_headers(owner_token),
        timeout=30,
    )
    assert analytics.status_code == 200
    analytics_data = analytics.json()
    assert "calibration_heatmap" in analytics_data
    assert "training_approved_count" in analytics_data


def test_free_text_submission_visible_in_management_review(api_client, base_url, logins, created_free_text_issue_submission):
    token = logins["Production Manager"]["token"]
    detail = api_client.get(
        f"{base_url}/api/submissions/{created_free_text_issue_submission['id']}",
        headers=_auth_headers(token),
        timeout=30,
    )
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["submission"]["job_name_input"] == created_free_text_issue_submission["job_name_input"]
    assert payload["submission"]["field_report"]["reported"] is True


def test_field_issue_notifications_target_pm_and_account_manager(api_client, base_url, logins, created_free_text_issue_submission):
    submission_id = created_free_text_issue_submission["id"]

    pm_response = api_client.get(
        f"{base_url}/api/notifications?status=all",
        headers=_auth_headers(logins["Production Manager"]["token"]),
        timeout=30,
    )
    assert pm_response.status_code == 200
    pm_items = pm_response.json()["items"]
    assert any(
        item.get("related_submission_id") == submission_id and item.get("notification_type") == "field_issue"
        for item in pm_items
    )

    am_response = api_client.get(
        f"{base_url}/api/notifications?status=all",
        headers=_auth_headers(logins["Account Manager"]["token"]),
        timeout=30,
    )
    assert am_response.status_code == 200
    am_items = am_response.json()["items"]
    assert any(
        item.get("related_submission_id") == submission_id and item.get("notification_type") == "field_issue"
        for item in am_items
    )


def test_management_review_still_works_for_free_text_submission(api_client, base_url, logins, created_free_text_issue_submission):
    pm_token = logins["Production Manager"]["token"]
    submission_id = created_free_text_issue_submission["id"]

    jobs_response = api_client.get(
        f"{base_url}/api/jobs",
        headers=_auth_headers(pm_token),
        timeout=30,
    )
    assert jobs_response.status_code == 200
    jobs = jobs_response.json()
    assert isinstance(jobs, list) and len(jobs) > 0
    chosen_job = jobs[0]

    match_response = api_client.post(
        f"{base_url}/api/submissions/{submission_id}/match",
        headers={**_auth_headers(pm_token), "Content-Type": "application/json"},
        json={"job_id": chosen_job["id"], "service_type": chosen_job["service_type"]},
        timeout=30,
    )
    assert match_response.status_code == 200

    detail_after_match = api_client.get(
        f"{base_url}/api/submissions/{submission_id}",
        headers=_auth_headers(pm_token),
        timeout=30,
    )
    assert detail_after_match.status_code == 200
    detail_payload = detail_after_match.json()
    categories = detail_payload["rubric"]["categories"]
    category_scores = {item["key"]: max(item["max_score"] - 1, 1) for item in categories}

    review_response = api_client.post(
        f"{base_url}/api/reviews/management",
        headers={**_auth_headers(pm_token), "Content-Type": "application/json"},
        json={
            "submission_id": submission_id,
            "job_id": chosen_job["id"],
            "service_type": chosen_job["service_type"],
            "category_scores": category_scores,
            "comments": "TEST management review for free text",
            "disposition": "pass with notes",
            "flagged_issues": ["test_flag"],
        },
        timeout=30,
    )
    assert review_response.status_code == 200
    review_payload = review_response.json()
    assert review_payload["submission"]["status"] == "Management Reviewed"


def test_owner_review_shows_field_issue_and_can_finalize(api_client, base_url, logins, created_free_text_issue_submission):
    owner_token = logins["Owner"]["token"]
    submission_id = created_free_text_issue_submission["id"]

    detail_response = api_client.get(
        f"{base_url}/api/submissions/{submission_id}",
        headers=_auth_headers(owner_token),
        timeout=30,
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["submission"]["field_report"]["reported"] is True
    assert detail["submission"]["field_report"]["notes"] == "TEST issue notes with attachment"

    categories = detail["rubric"]["categories"]
    owner_scores = {item["key"]: item["max_score"] for item in categories}
    owner_review = api_client.post(
        f"{base_url}/api/reviews/owner",
        headers={**_auth_headers(owner_token), "Content-Type": "application/json"},
        json={
            "submission_id": submission_id,
            "category_scores": owner_scores,
            "comments": "TEST owner finalize",
            "final_disposition": "pass",
            "training_inclusion": "approved",
            "exclusion_reason": "",
        },
        timeout=30,
    )
    assert owner_review.status_code == 200
    assert owner_review.json()["submission"]["status"] == "Export Ready"


def test_exports_include_revised_workflow_data(api_client, base_url, logins, created_free_text_issue_submission):
    pm_token = logins["Production Manager"]["token"]

    run_export = api_client.post(
        f"{base_url}/api/exports/run",
        headers={**_auth_headers(pm_token), "Content-Type": "application/json"},
        json={"dataset_type": "full", "export_format": "csv"},
        timeout=60,
    )
    assert run_export.status_code == 200
    export_record = run_export.json()
    assert export_record["dataset_type"] == "full"

    download = api_client.get(
        f"{base_url}/api/exports/{export_record['id']}/download",
        headers=_auth_headers(pm_token),
        timeout=60,
    )
    assert download.status_code == 200
    rows = list(csv.DictReader(io.StringIO(download.text)))
    assert rows

    target_rows = [row for row in rows if row.get("submission_id") == created_free_text_issue_submission["id"]]
    assert target_rows
    row = target_rows[0]
    assert row.get("job_name_input") == created_free_text_issue_submission["job_name_input"]
    assert row.get("field_report_type") == "Property damage"
    assert "issue_" in (row.get("field_report_photo_urls") or "")
