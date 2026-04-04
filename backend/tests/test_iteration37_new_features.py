"""
Iteration 37 Tests - PDF Export, Onboarding Progress, Coaching Loop
Tests for:
1. Server refactor health check
2. Auth still works after refactor
3. PDF export for AM Client Report
4. Onboarding progress tracker
5. Coaching loop report and actions
6. Regression tests for weekly-digest and crew-leader-performance
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
OWNER_EMAIL = "sadam.owner@slmco.local"
OWNER_PASSWORD = "SLMCo2026!"
PM_EMAIL = "atim.prom@slmco.local"
PM_PASSWORD = "SLMCo2026!"


@pytest.fixture(scope="module")
def owner_token():
    """Get owner authentication token."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}
    )
    assert response.status_code == 200, f"Owner login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def pm_token():
    """Get PM authentication token."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": PM_EMAIL, "password": PM_PASSWORD}
    )
    assert response.status_code == 200, f"PM login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def crew_code(owner_token):
    """Get a valid crew code for testing."""
    response = requests.get(
        f"{BASE_URL}/api/crew-access-links",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 200
    items = response.json().get("items", [])
    assert len(items) > 0, "No crew access links found"
    return items[0]["code"]


class TestServerRefactor:
    """Tests to verify server refactor didn't break startup."""

    def test_health_endpoint(self):
        """GET /api/health returns 200 (server refactor didn't break startup)."""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data

    def test_auth_login_after_refactor(self):
        """POST /api/auth/login with owner credentials returns token."""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == OWNER_EMAIL
        assert data["user"]["role"] == "owner"


class TestPDFExport:
    """Tests for AM Report PDF export."""

    def test_am_report_pdf_returns_200(self, owner_token):
        """GET /api/exports/am-report-pdf returns 200 with PDF content."""
        response = requests.get(
            f"{BASE_URL}/api/exports/am-report-pdf",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        # Check PDF magic bytes
        assert response.content[:4] == b"%PDF", "Response is not a valid PDF"

    def test_am_report_pdf_has_content_disposition(self, owner_token):
        """PDF export has proper Content-Disposition header for download."""
        response = requests.get(
            f"{BASE_URL}/api/exports/am-report-pdf",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        content_disp = response.headers.get("content-disposition", "")
        assert "attachment" in content_disp
        assert "SarverLandscape_ClientReport" in content_disp

    def test_am_report_pdf_requires_auth(self):
        """PDF export requires authentication."""
        response = requests.get(f"{BASE_URL}/api/exports/am-report-pdf")
        assert response.status_code in [401, 403]

    def test_am_report_pdf_pm_can_access(self, pm_token):
        """PM (management role) can access PDF export."""
        response = requests.get(
            f"{BASE_URL}/api/exports/am-report-pdf",
            headers={"Authorization": f"Bearer {pm_token}"}
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"


class TestOnboardingProgress:
    """Tests for crew onboarding progress tracker."""

    def test_onboarding_progress_all_divisions(self, owner_token):
        """GET /api/onboarding/progress?division=all returns crews with milestones."""
        response = requests.get(
            f"{BASE_URL}/api/onboarding/progress?division=all",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "crews" in data
        assert "milestone_definitions" in data
        assert isinstance(data["crews"], list)
        assert len(data["milestone_definitions"]) == 6  # 6 milestones defined
        
        # Verify milestone definitions
        milestone_keys = [m["key"] for m in data["milestone_definitions"]]
        expected_keys = ["first_submission", "first_review", "training_started", 
                        "training_completed", "equipment_check", "five_submissions"]
        assert milestone_keys == expected_keys

    def test_onboarding_progress_crew_structure(self, owner_token):
        """Each crew has proper milestone progress structure."""
        response = requests.get(
            f"{BASE_URL}/api/onboarding/progress?division=all",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        if len(data["crews"]) > 0:
            crew = data["crews"][0]
            assert "crew_label" in crew
            assert "leader_name" in crew
            assert "division" in crew
            assert "milestones" in crew
            assert "completed_count" in crew
            assert "total_milestones" in crew
            assert "progress_pct" in crew
            
            # Verify milestone structure
            milestones = crew["milestones"]
            assert "first_submission" in milestones
            assert "done" in milestones["first_submission"]
            assert "date" in milestones["first_submission"]

    def test_onboarding_progress_install_filter(self, owner_token):
        """GET /api/onboarding/progress?division=Install filters correctly."""
        response = requests.get(
            f"{BASE_URL}/api/onboarding/progress?division=Install",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # All returned crews should be Install division
        for crew in data["crews"]:
            assert crew["division"] == "Install"

    def test_onboarding_progress_requires_auth(self):
        """Onboarding progress requires authentication."""
        response = requests.get(f"{BASE_URL}/api/onboarding/progress?division=all")
        assert response.status_code in [401, 403]


class TestCoachingLoop:
    """Tests for closed-loop coaching reports and actions."""

    def test_coaching_loop_report_all(self, owner_token):
        """GET /api/coaching/loop-report?division=all returns report with summary."""
        response = requests.get(
            f"{BASE_URL}/api/coaching/loop-report?division=all",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "report" in data
        assert "summary" in data
        assert isinstance(data["report"], list)
        
        # Verify summary structure
        summary = data["summary"]
        assert "total_offenders" in summary
        assert "closed_loops" in summary
        assert "in_progress" in summary
        assert "open_loops" in summary

    def test_coaching_assign_creates_action(self, owner_token, crew_code):
        """POST /api/coaching/assign creates a coaching action."""
        response = requests.post(
            f"{BASE_URL}/api/coaching/assign",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={
                "crew_code": crew_code,
                "issue_tags": ["edge_quality", "debris_left"],
                "notes": "Test coaching assignment from pytest"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify action structure
        assert "id" in data
        assert data["crew_code"] == crew_code
        assert data["status"] == "assigned"
        assert "edge_quality" in data["issue_tags"]
        assert "debris_left" in data["issue_tags"]
        assert "assigned_by" in data
        assert "created_at" in data
        
        return data["id"]

    def test_coaching_assign_requires_crew_code(self, owner_token):
        """POST /api/coaching/assign requires crew_code."""
        response = requests.post(
            f"{BASE_URL}/api/coaching/assign",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"issue_tags": ["test"], "notes": "Missing crew code"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "error" in data

    def test_coaching_complete_marks_completed(self, owner_token, crew_code):
        """PATCH /api/coaching/{action_id}/complete marks action as completed."""
        # First create an action
        create_response = requests.post(
            f"{BASE_URL}/api/coaching/assign",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={
                "crew_code": crew_code,
                "issue_tags": ["test_complete"],
                "notes": "Action to be completed"
            }
        )
        assert create_response.status_code == 200
        action_id = create_response.json()["id"]
        
        # Complete the action
        complete_response = requests.patch(
            f"{BASE_URL}/api/coaching/{action_id}/complete",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"notes": "Completed via pytest"}
        )
        assert complete_response.status_code == 200
        data = complete_response.json()
        
        assert data["status"] == "completed"
        assert data["completed_by"] is not None
        assert data["completion_notes"] == "Completed via pytest"

    def test_coaching_complete_invalid_id(self, owner_token):
        """PATCH /api/coaching/{invalid_id}/complete returns error."""
        response = requests.patch(
            f"{BASE_URL}/api/coaching/invalid_action_id/complete",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"notes": "Should fail"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "error" in data

    def test_coaching_loop_requires_auth(self):
        """Coaching loop report requires authentication."""
        response = requests.get(f"{BASE_URL}/api/coaching/loop-report?division=all")
        assert response.status_code in [401, 403]


class TestRegressionAfterRefactor:
    """Regression tests to ensure existing endpoints still work after server refactor."""

    def test_weekly_digest_still_works(self, owner_token):
        """GET /api/metrics/weekly-digest still returns 200."""
        response = requests.get(
            f"{BASE_URL}/api/metrics/weekly-digest",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_crews_active" in data

    def test_crew_leader_performance_still_works(self, owner_token):
        """GET /api/metrics/crew-leader-performance?division=all still returns 200."""
        response = requests.get(
            f"{BASE_URL}/api/metrics/crew-leader-performance?division=all",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "leaders" in data
        assert isinstance(data["leaders"], list)

    def test_dashboard_overview_still_works(self, owner_token):
        """GET /api/dashboard/overview still returns 200."""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/overview",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "totals" in data
        assert "queues" in data

    def test_submissions_endpoint_still_works(self, owner_token):
        """GET /api/submissions still returns 200."""
        response = requests.get(
            f"{BASE_URL}/api/submissions?scope=all&page=1&limit=5",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data
        assert "total" in data["pagination"]

    def test_rubric_matrices_still_works(self, owner_token):
        """GET /api/rubric-matrices still returns 200."""
        response = requests.get(
            f"{BASE_URL}/api/rubric-matrices?division=all",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
