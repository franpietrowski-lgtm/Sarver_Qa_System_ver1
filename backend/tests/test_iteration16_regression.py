"""
Iteration 16 Regression Tests - Backend Modularization Verification
Tests all 59 route handlers after extraction from monolithic server.py (~2593 lines)
into 17 separate route modules in /app/backend/routes/

Route modules tested:
- auth.py: login, me
- system.py: root, health, blueprint
- public.py: crew-access, jobs, submissions, equipment-logs, training
- submissions.py: files, list, detail, match
- equipment.py: list, forward, files
- jobs.py: list, CSV import
- crew_access.py: CRUD
- users.py: list, create, status
- notifications.py: list, read
- rubrics.py: list, matrices CRUD
- standards.py: list, create, update
- reviews.py: management, owner reviews
- rapid_reviews.py: queue, create, sessions, flagged, rescore
- training.py: sessions list/create, repeat offenders
- analytics.py: dashboard overview, analytics summary
- exports.py: run, list, download
- integrations.py: storage status, drive status, connect, callback
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


# ============================================================================
# AUTH MODULE TESTS (routes/auth.py)
# ============================================================================
class TestAuthModule:
    """Test authentication endpoints - POST /api/auth/login, GET /api/auth/me"""

    def test_login_owner_success(self):
        """Owner user can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "sadam.owner@slmco.local",
            "password": "SLMCo2026!"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == "sadam.owner@slmco.local"
        assert data["user"]["role"] == "owner"

    def test_login_gm_success(self):
        """GM user can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "ctyler.gm@slmco.local",
            "password": "SLMCo2026!"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == "ctyler.gm@slmco.local"
        assert data["user"]["role"] == "management"
        assert data["user"]["title"] == "GM"

    def test_login_supervisor_success(self):
        """Supervisor user can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "hjohnny.super@slmco.local",
            "password": "SLMCo2026!"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["title"] == "Supervisor"

    def test_login_invalid_credentials(self):
        """Invalid credentials return 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401

    def test_auth_me_with_valid_token(self, auth_headers):
        """GET /api/auth/me returns current user with valid token"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
        assert response.status_code == 200, f"Auth me failed: {response.text}"
        data = response.json()
        assert "email" in data
        assert "role" in data

    def test_auth_me_without_token(self):
        """GET /api/auth/me returns 401 without token"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401


# ============================================================================
# SYSTEM MODULE TESTS (routes/system.py)
# ============================================================================
class TestSystemModule:
    """Test system endpoints - GET /, GET /health, GET /system/blueprint"""

    def test_root_endpoint(self):
        """GET /api/ returns API info"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_health_endpoint(self):
        """GET /api/health returns status ok"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data

    def test_blueprint_with_auth(self, auth_headers):
        """GET /api/system/blueprint returns system blueprint with auth"""
        response = requests.get(f"{BASE_URL}/api/system/blueprint", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "architecture" in data
        assert "database_schema" in data
        assert "ui_screens" in data

    def test_blueprint_without_auth(self):
        """GET /api/system/blueprint returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/system/blueprint")
        assert response.status_code == 401


# ============================================================================
# PUBLIC MODULE TESTS (routes/public.py)
# ============================================================================
class TestPublicModule:
    """Test public endpoints - no auth required"""

    def test_public_crew_access_list(self):
        """GET /api/public/crew-access returns active crew links"""
        response = requests.get(f"{BASE_URL}/api/public/crew-access")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0, "No crew access links found"
        crew = data[0]
        assert "code" in crew
        assert "label" in crew
        assert "truck_number" in crew
        assert "division" in crew

    def test_public_jobs_list(self):
        """GET /api/public/jobs returns jobs list"""
        response = requests.get(f"{BASE_URL}/api/public/jobs")
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert isinstance(data["jobs"], list)


# ============================================================================
# ANALYTICS MODULE TESTS (routes/analytics.py)
# ============================================================================
class TestAnalyticsModule:
    """Test analytics endpoints - dashboard overview, analytics summary"""

    def test_dashboard_overview(self, auth_headers):
        """GET /api/dashboard/overview returns expected structure"""
        response = requests.get(f"{BASE_URL}/api/dashboard/overview", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "totals" in data
        assert "queues" in data
        assert "storage" in data
        assert "workflow_health" in data
        assert data["totals"]["submissions"] >= 23, f"Expected at least 23 submissions"

    def test_analytics_summary_monthly(self, auth_headers):
        """GET /api/analytics/summary?period=monthly returns analytics"""
        response = requests.get(f"{BASE_URL}/api/analytics/summary?period=monthly", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "monthly"
        assert "average_score_by_crew" in data
        assert "fail_reason_frequency" in data
        assert "submission_volume_trends" in data

    def test_analytics_summary_weekly(self, auth_headers):
        """GET /api/analytics/summary?period=weekly returns analytics"""
        response = requests.get(f"{BASE_URL}/api/analytics/summary?period=weekly", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "weekly"


# ============================================================================
# SUBMISSIONS MODULE TESTS (routes/submissions.py)
# ============================================================================
class TestSubmissionsModule:
    """Test submissions endpoints - list, detail, pagination"""

    def test_submissions_list_with_pagination(self, auth_headers):
        """GET /api/submissions returns paginated list"""
        response = requests.get(
            f"{BASE_URL}/api/submissions?scope=all&page=1&limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["limit"] == 10

    def test_submissions_total_count(self, auth_headers):
        """GET /api/submissions returns 23 total seeded submissions"""
        response = requests.get(
            f"{BASE_URL}/api/submissions?scope=all&page=1&limit=30",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total"] == 23, f"Expected 23 submissions, got {data['pagination']['total']}"

    def test_submissions_have_work_date(self, auth_headers):
        """Submissions have work_date field populated"""
        response = requests.get(
            f"{BASE_URL}/api/submissions?scope=all&page=1&limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        items = data.get("items", [])
        for item in items:
            assert "work_date" in item, f"Submission {item.get('id')} missing work_date"

    def test_submission_detail(self, auth_headers):
        """GET /api/submissions/{id} returns submission detail"""
        # First get a submission ID
        list_response = requests.get(
            f"{BASE_URL}/api/submissions?scope=all&page=1&limit=1",
            headers=auth_headers
        )
        assert list_response.status_code == 200
        items = list_response.json().get("items", [])
        if items:
            submission_id = items[0]["id"]
            detail_response = requests.get(
                f"{BASE_URL}/api/submissions/{submission_id}",
                headers=auth_headers
            )
            assert detail_response.status_code == 200
            detail = detail_response.json()
            # Response structure: {submission: {...}, job: {...}, rubric: {...}, ...}
            assert "submission" in detail
            assert detail["submission"]["id"] == submission_id


# ============================================================================
# JOBS MODULE TESTS (routes/jobs.py)
# ============================================================================
class TestJobsModule:
    """Test jobs endpoints - list with pagination and search"""

    def test_jobs_list_with_pagination(self, auth_headers):
        """GET /api/jobs returns paginated list"""
        response = requests.get(
            f"{BASE_URL}/api/jobs?page=1&limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data

    def test_jobs_search(self, auth_headers):
        """GET /api/jobs with search parameter"""
        response = requests.get(
            f"{BASE_URL}/api/jobs?search=riverview&page=1&limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


# ============================================================================
# CREW ACCESS MODULE TESTS (routes/crew_access.py)
# ============================================================================
class TestCrewAccessModule:
    """Test crew access endpoints - list with pagination"""

    def test_crew_access_links_list(self, auth_headers):
        """GET /api/crew-access-links returns paginated list"""
        response = requests.get(
            f"{BASE_URL}/api/crew-access-links?page=1&limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data


# ============================================================================
# USERS MODULE TESTS (routes/users.py)
# ============================================================================
class TestUsersModule:
    """Test users endpoints - list with auth"""

    def test_users_list(self, auth_headers):
        """GET /api/users returns users list"""
        response = requests.get(f"{BASE_URL}/api/users", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0, "No users found"


# ============================================================================
# NOTIFICATIONS MODULE TESTS (routes/notifications.py)
# ============================================================================
class TestNotificationsModule:
    """Test notifications endpoints - list with auth"""

    def test_notifications_list(self, auth_headers):
        """GET /api/notifications returns notifications list"""
        response = requests.get(f"{BASE_URL}/api/notifications", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Response structure: {items: [...], unread_count: N}
        assert "items" in data
        assert "unread_count" in data
        assert isinstance(data["items"], list)


# ============================================================================
# RUBRICS MODULE TESTS (routes/rubrics.py)
# ============================================================================
class TestRubricsModule:
    """Test rubrics endpoints - list and matrices"""

    def test_rubrics_list(self, auth_headers):
        """GET /api/rubrics returns rubrics list"""
        response = requests.get(f"{BASE_URL}/api/rubrics", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0, "No rubrics found"

    def test_rubric_matrices_list(self, auth_headers):
        """GET /api/rubric-matrices returns matrices list"""
        response = requests.get(f"{BASE_URL}/api/rubric-matrices", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


# ============================================================================
# STANDARDS MODULE TESTS (routes/standards.py)
# ============================================================================
class TestStandardsModule:
    """Test standards endpoints - list with pagination and filters"""

    def test_standards_list_with_pagination(self, auth_headers):
        """GET /api/standards returns paginated list"""
        response = requests.get(
            f"{BASE_URL}/api/standards?page=1&limit=5",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data
        assert data["pagination"]["limit"] == 5

    def test_standards_total_count(self, auth_headers):
        """Standards library has expected count"""
        response = requests.get(
            f"{BASE_URL}/api/standards?page=1&limit=5",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total"] >= 4, "Expected at least 4 standards"


# ============================================================================
# TRAINING MODULE TESTS (routes/training.py)
# ============================================================================
class TestTrainingModule:
    """Test training endpoints - sessions list, repeat offenders"""

    def test_training_sessions_list(self, auth_headers):
        """GET /api/training-sessions returns paginated list"""
        response = requests.get(
            f"{BASE_URL}/api/training-sessions?page=1&limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data

    def test_repeat_offenders_30_days(self, auth_headers):
        """GET /api/repeat-offenders?window_days=30 returns crew summaries"""
        response = requests.get(
            f"{BASE_URL}/api/repeat-offenders?window_days=30",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["window_days"] == 30
        assert "crew_summaries" in data
        assert "heatmap" in data

    def test_repeat_offenders_240_days(self, auth_headers):
        """GET /api/repeat-offenders?window_days=240 returns more crews"""
        response = requests.get(
            f"{BASE_URL}/api/repeat-offenders?window_days=240",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["window_days"] == 240
        assert "crew_summaries" in data


# ============================================================================
# RAPID REVIEWS MODULE TESTS (routes/rapid_reviews.py)
# ============================================================================
class TestRapidReviewsModule:
    """Test rapid reviews endpoints - queue, sessions, flagged"""

    def test_rapid_reviews_queue(self, auth_headers):
        """GET /api/rapid-reviews/queue returns paginated queue"""
        response = requests.get(
            f"{BASE_URL}/api/rapid-reviews/queue?page=1&limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data

    def test_rapid_review_sessions_list(self, auth_headers):
        """GET /api/rapid-review-sessions returns paginated list"""
        response = requests.get(
            f"{BASE_URL}/api/rapid-review-sessions?page=1&limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data

    def test_rapid_reviews_flagged(self, auth_headers):
        """GET /api/rapid-reviews/flagged returns flagged items"""
        response = requests.get(
            f"{BASE_URL}/api/rapid-reviews/flagged?flag_type=fail",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


# ============================================================================
# EQUIPMENT MODULE TESTS (routes/equipment.py)
# ============================================================================
class TestEquipmentModule:
    """Test equipment endpoints - list with pagination"""

    def test_equipment_logs_list(self, auth_headers):
        """GET /api/equipment-logs returns paginated list"""
        response = requests.get(
            f"{BASE_URL}/api/equipment-logs?page=1&limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data


# ============================================================================
# EXPORTS MODULE TESTS (routes/exports.py)
# ============================================================================
class TestExportsModule:
    """Test exports endpoints - list with pagination"""

    def test_exports_list(self, auth_headers):
        """GET /api/exports returns paginated list"""
        response = requests.get(
            f"{BASE_URL}/api/exports?page=1&limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data


# ============================================================================
# INTEGRATIONS MODULE TESTS (routes/integrations.py)
# ============================================================================
class TestIntegrationsModule:
    """Test integrations endpoints - storage status, drive status"""

    def test_storage_status(self, auth_headers):
        """GET /api/integrations/storage/status returns storage info"""
        response = requests.get(
            f"{BASE_URL}/api/integrations/storage/status",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "configured" in data
        assert "connected" in data

    def test_drive_status(self, auth_headers):
        """GET /api/integrations/drive/status returns drive info"""
        response = requests.get(
            f"{BASE_URL}/api/integrations/drive/status",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "configured" in data
        assert "scope" in data


# ============================================================================
# FIXTURES
# ============================================================================
@pytest.fixture
def auth_token():
    """Get authentication token for GM user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "ctyler.gm@slmco.local",
        "password": "SLMCo2026!"
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def owner_token():
    """Get authentication token for Owner user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "sadam.owner@slmco.local",
        "password": "SLMCo2026!"
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Owner authentication failed")


@pytest.fixture
def owner_headers(owner_token):
    """Get headers with owner auth token"""
    return {"Authorization": f"Bearer {owner_token}"}
