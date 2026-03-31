import os
import uuid
from pathlib import Path

import pytest
import requests


# Regression coverage: admin staff controls, inactive crew links, and owner queue pagination readiness


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

    required = ["Production Manager", "Owner"]
    missing = [title for title in required if title not in title_map]
    if missing:
        pytest.fail(f"Missing credentials in /app/memory/test_credentials.md: {', '.join(missing)}")
    return title_map


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


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


@pytest.fixture(scope="session")
def logins(api_client, base_url, creds_by_title):
    out = {}
    for title, creds in creds_by_title.items():
        response = api_client.post(
            f"{base_url}/api/auth/login",
            json={"email": creds["email"], "password": creds["password"]},
            timeout=30,
        )
        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload.get("token"), str) and len(payload["token"]) > 20
        out[title] = payload
    return out


def _make_submission(api_client: requests.Session, base_url: str, access_code: str, truck_number: str, tag: str) -> dict:
    files = [
        ("photos", (f"{tag}-1.jpg", b"\xff\xd8\xff\xdbproof1", "image/jpeg")),
        ("photos", (f"{tag}-2.jpg", b"\xff\xd8\xff\xdbproof2", "image/jpeg")),
        ("photos", (f"{tag}-3.jpg", b"\xff\xd8\xff\xdbproof3", "image/jpeg")),
    ]
    payload = {
        "access_code": access_code,
        "job_name": f"TEST Queue Job {tag}",
        "truck_number": truck_number,
        "gps_lat": "43.631000",
        "gps_lng": "-79.412000",
        "gps_accuracy": "7",
        "note": "TEST pagination prep",
        "area_tag": "TEST area",
    }
    response = api_client.post(
        f"{base_url}/api/public/submissions",
        data=payload,
        files=files,
        timeout=60,
    )
    assert response.status_code == 200
    return response.json()["submission"]


def test_admin_can_create_staff_and_toggle_authorization(api_client, base_url, logins):
    pm_token = logins["Production Manager"]["token"]
    suffix = uuid.uuid4().hex[:8]
    email = f"test.staff.{suffix}@fieldquality.local"
    password = "FieldQA123!"

    create_response = api_client.post(
        f"{base_url}/api/users",
        headers={**_auth_headers(pm_token), "Content-Type": "application/json"},
        json={
            "name": f"TEST Staff {suffix}",
            "email": email,
            "role": "management",
            "title": "Supervisor",
            "password": password,
            "is_active": True,
        },
        timeout=30,
    )
    assert create_response.status_code == 200
    created_user = create_response.json()
    assert created_user["email"] == email
    assert created_user["is_active"] is True

    deactivate_response = api_client.patch(
        f"{base_url}/api/users/{created_user['id']}/status",
        headers={**_auth_headers(pm_token), "Content-Type": "application/json"},
        json={"is_active": False},
        timeout=30,
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False

    inactive_login = api_client.post(
        f"{base_url}/api/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    assert inactive_login.status_code == 403

    activate_response = api_client.patch(
        f"{base_url}/api/users/{created_user['id']}/status",
        headers={**_auth_headers(pm_token), "Content-Type": "application/json"},
        json={"is_active": True},
        timeout=30,
    )
    assert activate_response.status_code == 200
    assert activate_response.json()["is_active"] is True

    active_login = api_client.post(
        f"{base_url}/api/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    assert active_login.status_code == 200
    assert active_login.json()["user"]["email"] == email


def test_inactive_crew_link_removed_from_public_while_history_remains(api_client, base_url, logins):
    pm_token = logins["Production Manager"]["token"]
    suffix = uuid.uuid4().hex[:6]

    create_link = api_client.post(
        f"{base_url}/api/crew-access-links",
        headers={**_auth_headers(pm_token), "Content-Type": "application/json"},
        json={
            "label": f"TEST Crew {suffix}",
            "truck_number": f"TEST-{suffix}",
            "division": "Maintenance",
        },
        timeout=30,
    )
    assert create_link.status_code == 200
    link = create_link.json()
    assert link["enabled"] is True

    submission = _make_submission(api_client, base_url, link["code"], link["truck_number"], suffix)
    assert submission["access_code"] == link["code"]

    deactivate = api_client.patch(
        f"{base_url}/api/crew-access-links/{link['id']}/status",
        headers={**_auth_headers(pm_token), "Content-Type": "application/json"},
        json={"enabled": False},
        timeout=30,
    )
    assert deactivate.status_code == 200
    assert deactivate.json()["enabled"] is False

    public_links = api_client.get(f"{base_url}/api/public/crew-access", timeout=30)
    assert public_links.status_code == 200
    active_codes = {item["code"] for item in public_links.json()}
    assert link["code"] not in active_codes

    removed_link_response = api_client.get(f"{base_url}/api/public/crew-access/{link['code']}", timeout=30)
    assert removed_link_response.status_code == 404

    detail = api_client.get(
        f"{base_url}/api/submissions/{submission['id']}",
        headers=_auth_headers(pm_token),
        timeout=30,
    )
    assert detail.status_code == 200
    snapshot = detail.json()
    assert snapshot["submission"]["access_code"] == link["code"]
    assert snapshot["submission"]["crew_label"] == link["label"]


def test_owner_queue_dataset_supports_pagination_over_eight_entries(api_client, base_url, logins):
    pm_token = logins["Production Manager"]["token"]
    owner_token = logins["Owner"]["token"]

    owner_before = api_client.get(
        f"{base_url}/api/submissions?scope=owner&filter_by=all&page=1&limit=100",
        headers=_auth_headers(owner_token),
        timeout=30,
    )
    assert owner_before.status_code == 200
    owner_before_data = owner_before.json()
    # Handle paginated response format
    initial_owner_queue = owner_before_data.get("items", owner_before_data) if isinstance(owner_before_data, dict) else owner_before_data

    target_count = 9
    missing = max(target_count - len(initial_owner_queue), 0)
    if missing > 0:
        access_links_response = api_client.get(f"{base_url}/api/public/crew-access", timeout=30)
        assert access_links_response.status_code == 200
        links = access_links_response.json()
        assert links
        access = links[0]

        jobs_response = api_client.get(
            f"{base_url}/api/jobs",
            headers=_auth_headers(pm_token),
            timeout=30,
        )
        assert jobs_response.status_code == 200
        jobs_data = jobs_response.json()
        # Handle paginated response format
        jobs = jobs_data.get("items", jobs_data) if isinstance(jobs_data, dict) else jobs_data
        assert jobs
        job = jobs[0]

        for _ in range(missing):
            suffix = uuid.uuid4().hex[:8]
            submission = _make_submission(api_client, base_url, access["code"], access["truck_number"], suffix)

            match_response = api_client.post(
                f"{base_url}/api/submissions/{submission['id']}/match",
                headers={**_auth_headers(pm_token), "Content-Type": "application/json"},
                json={"job_id": job["id"], "service_type": job["service_type"]},
                timeout=30,
            )
            assert match_response.status_code == 200

            detail_response = api_client.get(
                f"{base_url}/api/submissions/{submission['id']}",
                headers=_auth_headers(pm_token),
                timeout=30,
            )
            assert detail_response.status_code == 200
            categories = detail_response.json()["rubric"]["categories"]
            category_scores = {item["key"]: max(item["max_score"] - 1, 1) for item in categories}

            review_response = api_client.post(
                f"{base_url}/api/reviews/management",
                headers={**_auth_headers(pm_token), "Content-Type": "application/json"},
                json={
                    "submission_id": submission["id"],
                    "job_id": job["id"],
                    "service_type": job["service_type"],
                    "category_scores": category_scores,
                    "comments": "TEST pagination owner queue setup",
                    "disposition": "pass with notes",
                    "flagged_issues": [],
                },
                timeout=30,
            )
            assert review_response.status_code == 200
            assert review_response.json()["submission"]["status"] == "Management Reviewed"

    owner_after = api_client.get(
        f"{base_url}/api/submissions?scope=owner&filter_by=all&page=1&limit=100",
        headers=_auth_headers(owner_token),
        timeout=30,
    )
    assert owner_after.status_code == 200
    owner_after_data = owner_after.json()
    # Handle paginated response format
    owner_queue = owner_after_data.get("items", owner_after_data) if isinstance(owner_after_data, dict) else owner_after_data
    assert len(owner_queue) >= 9
    assert all(item["status"] in {"Management Reviewed", "Owner Reviewed", "Export Ready"} for item in owner_queue[:9])
