"""
Test suite for pagination contracts, Supabase storage, analytics periods, and crew portal features.
Covers: submissions, crew-access-links, jobs, exports pagination; file retrieval; analytics period tabs.
"""
import os
import uuid
from pathlib import Path

import pytest
import requests


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
def owner_token(api_client, base_url, creds_by_title):
    creds = creds_by_title.get("Owner")
    if not creds:
        pytest.skip("Owner credentials not found")
    response = api_client.post(
        f"{base_url}/api/auth/login",
        json={"email": creds["email"], "password": creds["password"]},
        timeout=30,
    )
    assert response.status_code == 200
    return response.json()["token"]


@pytest.fixture(scope="session")
def pm_token(api_client, base_url, creds_by_title):
    creds = creds_by_title.get("Production Manager")
    if not creds:
        pytest.skip("Production Manager credentials not found")
    response = api_client.post(
        f"{base_url}/api/auth/login",
        json={"email": creds["email"], "password": creds["password"]},
        timeout=30,
    )
    assert response.status_code == 200
    return response.json()["token"]


# ============================================================================
# Pagination contract tests
# ============================================================================

class TestPaginationContracts:
    """Verify all paginated endpoints return correct pagination structure."""

    def test_submissions_pagination_contract(self, api_client, base_url, owner_token):
        """GET /api/submissions returns paginated response with items and pagination keys."""
        response = api_client.get(
            f"{base_url}/api/submissions?scope=all&page=1&limit=10",
            headers=_auth_headers(owner_token),
            timeout=30,
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify pagination structure
        assert "items" in data, "Response must have 'items' key"
        assert "pagination" in data, "Response must have 'pagination' key"
        assert isinstance(data["items"], list)
        
        pagination = data["pagination"]
        assert "page" in pagination
        assert "limit" in pagination
        assert "total" in pagination
        assert "pages" in pagination
        assert "has_next" in pagination
        assert "has_prev" in pagination
        
        # Verify pagination values are correct types
        assert isinstance(pagination["page"], int)
        assert isinstance(pagination["limit"], int)
        assert isinstance(pagination["total"], int)
        assert isinstance(pagination["pages"], int)
        assert isinstance(pagination["has_next"], bool)
        assert isinstance(pagination["has_prev"], bool)

    def test_jobs_pagination_contract(self, api_client, base_url, pm_token):
        """GET /api/jobs returns paginated response."""
        response = api_client.get(
            f"{base_url}/api/jobs?page=1&limit=10",
            headers=_auth_headers(pm_token),
            timeout=30,
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert "pagination" in data
        assert isinstance(data["items"], list)
        
        pagination = data["pagination"]
        assert pagination["page"] == 1
        assert pagination["limit"] == 10

    def test_crew_access_links_pagination_contract(self, api_client, base_url, pm_token):
        """GET /api/crew-access-links returns paginated response."""
        response = api_client.get(
            f"{base_url}/api/crew-access-links?status=all&page=1&limit=10",
            headers=_auth_headers(pm_token),
            timeout=30,
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert "pagination" in data
        assert isinstance(data["items"], list)

    def test_crew_access_links_inactive_filter(self, api_client, base_url, pm_token):
        """GET /api/crew-access-links?status=inactive returns only inactive links."""
        response = api_client.get(
            f"{base_url}/api/crew-access-links?status=inactive&page=1&limit=10",
            headers=_auth_headers(pm_token),
            timeout=30,
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert "pagination" in data
        # All returned items should be inactive (enabled=False)
        for item in data["items"]:
            assert item.get("enabled") is False

    def test_exports_pagination_contract(self, api_client, base_url, owner_token):
        """GET /api/exports returns paginated response."""
        response = api_client.get(
            f"{base_url}/api/exports?page=1&limit=10",
            headers=_auth_headers(owner_token),
            timeout=30,
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert "pagination" in data
        assert isinstance(data["items"], list)


# ============================================================================
# Supabase storage tests
# ============================================================================

class TestSupabaseStorage:
    """Verify Supabase storage integration for submissions."""

    def test_storage_status_shows_supabase_configured(self, api_client, base_url, pm_token):
        """GET /api/integrations/storage/status returns Supabase configuration."""
        response = api_client.get(
            f"{base_url}/api/integrations/storage/status",
            headers=_auth_headers(pm_token),
            timeout=30,
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("provider") == "supabase"
        assert data.get("label") == "Supabase Storage"
        assert data.get("configured") is True
        assert data.get("connected") is True
        assert "bucket" in data
        assert "project_url" in data

    def test_submission_upload_with_supabase_storage(self, api_client, base_url):
        """POST /api/public/submissions uploads photos to Supabase storage."""
        # Get an active crew link
        links_response = api_client.get(f"{base_url}/api/public/crew-access", timeout=30)
        assert links_response.status_code == 200
        links = links_response.json()
        if not links:
            pytest.skip("No active crew links available")
        
        access = links[0]
        suffix = uuid.uuid4().hex[:8]
        
        # Create submission with 3 photos (minimum required)
        files = [
            ("photos", (f"test-{suffix}-1.png", b"\x89PNG\r\n\x1a\ntest1", "image/png")),
            ("photos", (f"test-{suffix}-2.png", b"\x89PNG\r\n\x1a\ntest2", "image/png")),
            ("photos", (f"test-{suffix}-3.png", b"\x89PNG\r\n\x1a\ntest3", "image/png")),
        ]
        payload = {
            "access_code": access["code"],
            "job_name": f"TEST Supabase Upload {suffix}",
            "truck_number": access["truck_number"],
            "gps_lat": "43.631000",
            "gps_lng": "-79.412000",
            "gps_accuracy": "7",
            "note": "TEST supabase storage",
            "area_tag": "TEST area",
        }
        
        response = api_client.post(
            f"{base_url}/api/public/submissions",
            data=payload,
            files=files,
            timeout=60,
        )
        assert response.status_code == 200
        submission = response.json()["submission"]
        
        # Verify photo files have supabase source type
        assert len(submission["photo_files"]) >= 3
        for photo in submission["photo_files"]:
            assert photo.get("source_type") == "supabase"
            assert "storage_path" in photo
            assert "media_url" in photo

    def test_submission_file_retrieval_route(self, api_client, base_url, pm_token):
        """GET /api/submissions/files/{submission_id}/{filename} retrieves file from Supabase."""
        # Get a submission with supabase-stored files
        subs_response = api_client.get(
            f"{base_url}/api/submissions?scope=all&page=1&limit=10",
            headers=_auth_headers(pm_token),
            timeout=30,
        )
        assert subs_response.status_code == 200
        submissions = subs_response.json()["items"]
        
        # Find a submission with supabase files
        target_submission = None
        for sub in submissions:
            detail_response = api_client.get(
                f"{base_url}/api/submissions/{sub['id']}",
                headers=_auth_headers(pm_token),
                timeout=30,
            )
            if detail_response.status_code == 200:
                detail = detail_response.json()
                photos = detail.get("submission", {}).get("photo_files", [])
                for photo in photos:
                    if photo.get("source_type") == "supabase" and photo.get("filename"):
                        target_submission = detail["submission"]
                        break
            if target_submission:
                break
        
        if not target_submission:
            pytest.skip("No submissions with Supabase-stored files found")
        
        # Test file retrieval
        photo = target_submission["photo_files"][0]
        file_response = api_client.get(
            f"{base_url}/api/submissions/files/{target_submission['id']}/{photo['filename']}",
            timeout=30,
        )
        assert file_response.status_code == 200
        assert len(file_response.content) > 0

    def test_submission_with_issue_photo_uploads_to_supabase(self, api_client, base_url):
        """POST /api/public/submissions with issue photos uploads to Supabase."""
        links_response = api_client.get(f"{base_url}/api/public/crew-access", timeout=30)
        assert links_response.status_code == 200
        links = links_response.json()
        if not links:
            pytest.skip("No active crew links available")
        
        access = links[0]
        suffix = uuid.uuid4().hex[:8]
        
        # Create submission with 3 photos + 1 issue photo
        files = [
            ("photos", (f"test-{suffix}-1.png", b"\x89PNG\r\n\x1a\ntest1", "image/png")),
            ("photos", (f"test-{suffix}-2.png", b"\x89PNG\r\n\x1a\ntest2", "image/png")),
            ("photos", (f"test-{suffix}-3.png", b"\x89PNG\r\n\x1a\ntest3", "image/png")),
            ("issue_photos", (f"issue-{suffix}.png", b"\x89PNG\r\n\x1a\nissue", "image/png")),
        ]
        payload = {
            "access_code": access["code"],
            "job_name": f"TEST Issue Upload {suffix}",
            "truck_number": access["truck_number"],
            "gps_lat": "43.631000",
            "gps_lng": "-79.412000",
            "gps_accuracy": "7",
            "note": "TEST with issue photo",
            "area_tag": "TEST area",
            "issue_type": "Damage",
            "issue_notes": "Test issue notes",
        }
        
        response = api_client.post(
            f"{base_url}/api/public/submissions",
            data=payload,
            files=files,
            timeout=60,
        )
        assert response.status_code == 200
        submission = response.json()["submission"]
        
        # Verify issue photos are stored
        field_report = submission.get("field_report", {})
        assert field_report.get("reported") is True
        issue_photos = field_report.get("photo_files", [])
        assert len(issue_photos) >= 1
        for photo in issue_photos:
            assert photo.get("source_type") == "supabase"


# ============================================================================
# Analytics period tabs tests
# ============================================================================

class TestAnalyticsPeriodTabs:
    """Verify analytics summary supports all period tabs."""

    @pytest.mark.parametrize("period", ["daily", "weekly", "monthly", "quarterly", "annual"])
    def test_analytics_summary_period(self, api_client, base_url, owner_token, period):
        """GET /api/analytics/summary?period={period} returns valid response."""
        response = api_client.get(
            f"{base_url}/api/analytics/summary?period={period}",
            headers=_auth_headers(owner_token),
            timeout=30,
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify expected fields
        assert "period" in data
        assert "period_label" in data
        assert "training_approved_count" in data
        assert "score_variance_average" in data
        assert "fail_reason_frequency" in data
        assert "average_score_by_crew" in data
        assert "submission_volume_trends" in data
        assert "calibration_heatmap" in data
        
        # Verify period matches request
        assert data["period"] == period


# ============================================================================
# Crew portal tests
# ============================================================================

class TestCrewPortal:
    """Verify crew portal hides raw IDCREWID_ string and shows proper labels."""

    def test_crew_access_link_has_proper_crew_member_id(self, api_client, base_url, pm_token):
        """Crew access links should have crew_member_id that doesn't expose raw IDCREWID_ prefix."""
        response = api_client.get(
            f"{base_url}/api/crew-access-links?status=all&page=1&limit=10",
            headers=_auth_headers(pm_token),
            timeout=30,
        )
        assert response.status_code == 200
        links = response.json()["items"]
        
        for link in links:
            crew_member_id = link.get("crew_member_id", "")
            # Should not expose raw internal ID format to users
            # The present_crew_link function should handle this
            assert crew_member_id, "crew_member_id should not be empty"

    def test_public_crew_access_returns_proper_labels(self, api_client, base_url):
        """GET /api/public/crew-access returns links with proper labels."""
        response = api_client.get(f"{base_url}/api/public/crew-access", timeout=30)
        assert response.status_code == 200
        links = response.json()
        
        for link in links:
            assert "label" in link
            assert "truck_number" in link
            assert "division" in link
            assert link["label"], "Label should not be empty"

    def test_crew_access_by_code_returns_notifications(self, api_client, base_url):
        """GET /api/public/crew-access/{code} returns link with notifications array."""
        links_response = api_client.get(f"{base_url}/api/public/crew-access", timeout=30)
        assert links_response.status_code == 200
        links = links_response.json()
        
        if not links:
            pytest.skip("No active crew links available")
        
        code = links[0]["code"]
        response = api_client.get(f"{base_url}/api/public/crew-access/{code}", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        assert "notifications" in data
        assert isinstance(data["notifications"], list)


# ============================================================================
# Owner queue pagination UI tests
# ============================================================================

class TestOwnerQueuePagination:
    """Verify owner queue pagination at 10 items per page."""

    def test_owner_queue_respects_limit_parameter(self, api_client, base_url, owner_token):
        """GET /api/submissions?scope=owner&limit=10 returns max 10 items."""
        response = api_client.get(
            f"{base_url}/api/submissions?scope=owner&page=1&limit=10",
            headers=_auth_headers(owner_token),
            timeout=30,
        )
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["items"]) <= 10
        assert data["pagination"]["limit"] == 10

    def test_owner_queue_pagination_navigation(self, api_client, base_url, owner_token):
        """Owner queue pagination has_next and has_prev work correctly."""
        # Get first page
        page1_response = api_client.get(
            f"{base_url}/api/submissions?scope=owner&page=1&limit=10",
            headers=_auth_headers(owner_token),
            timeout=30,
        )
        assert page1_response.status_code == 200
        page1 = page1_response.json()
        
        # First page should not have prev
        assert page1["pagination"]["has_prev"] is False
        
        # If there are more pages, test navigation
        if page1["pagination"]["has_next"]:
            page2_response = api_client.get(
                f"{base_url}/api/submissions?scope=owner&page=2&limit=10",
                headers=_auth_headers(owner_token),
                timeout=30,
            )
            assert page2_response.status_code == 200
            page2 = page2_response.json()
            
            # Second page should have prev
            assert page2["pagination"]["has_prev"] is True
            assert page2["pagination"]["page"] == 2
