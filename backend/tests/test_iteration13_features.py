"""
Iteration 13 Backend Tests
- Role-filtered dashboard (Owner/GM vs Supervisor)
- Jobs/Alignment page toggle sections and crew link update
- Repeat Offenders page with heatmap, action tiers, carousel
- Crew Capture page with separate damage/incident reporting
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials from /app/memory/test_credentials.md
SUPERVISOR_CREDS = {"email": "hjohnny.super@slmco.local", "password": "SLMCo2026!"}
GM_CREDS = {"email": "ctyler.gm@slmco.local", "password": "SLMCo2026!"}
OWNER_CREDS = {"email": "sadam.owner@slmco.local", "password": "SLMCo2026!"}


@pytest.fixture(scope="module")
def supervisor_token():
    """Get auth token for Supervisor role"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=SUPERVISOR_CREDS)
    if response.status_code != 200:
        pytest.skip(f"Supervisor login failed: {response.status_code}")
    return response.json().get("token")


@pytest.fixture(scope="module")
def gm_token():
    """Get auth token for GM role"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=GM_CREDS)
    if response.status_code != 200:
        pytest.skip(f"GM login failed: {response.status_code}")
    return response.json().get("token")


@pytest.fixture(scope="module")
def owner_token():
    """Get auth token for Owner role"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=OWNER_CREDS)
    if response.status_code != 200:
        pytest.skip(f"Owner login failed: {response.status_code}")
    return response.json().get("token")


class TestHealthAndAuth:
    """Basic health and authentication tests"""

    def test_health_endpoint(self):
        """Health endpoint returns OK"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_supervisor_login(self):
        """Supervisor can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SUPERVISOR_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["title"] == "Supervisor"

    def test_gm_login(self):
        """GM can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=GM_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["title"] == "GM"

    def test_owner_login(self):
        """Owner can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=OWNER_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "owner"


class TestDashboardOverview:
    """Dashboard overview API tests - role-filtered stats"""

    def test_supervisor_dashboard_overview(self, supervisor_token):
        """Supervisor can access dashboard overview"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        response = requests.get(f"{BASE_URL}/api/dashboard/overview", headers=headers)
        assert response.status_code == 200
        data = response.json()
        # Verify totals exist
        assert "totals" in data
        assert "submissions" in data["totals"]
        assert "jobs" in data["totals"]
        # Verify queues exist (backend returns all, frontend filters)
        assert "queues" in data

    def test_gm_dashboard_overview(self, gm_token):
        """GM can access dashboard overview with all stats"""
        headers = {"Authorization": f"Bearer {gm_token}"}
        response = requests.get(f"{BASE_URL}/api/dashboard/overview", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "totals" in data
        assert "queues" in data
        # GM should see owner queue and export ready
        assert "owner" in data["queues"]
        assert "export_ready" in data["queues"]

    def test_owner_dashboard_overview(self, owner_token):
        """Owner can access dashboard overview with all stats"""
        headers = {"Authorization": f"Bearer {owner_token}"}
        response = requests.get(f"{BASE_URL}/api/dashboard/overview", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "totals" in data
        assert "queues" in data
        assert "owner" in data["queues"]
        assert "export_ready" in data["queues"]


class TestCrewAccessLinks:
    """Crew access links API tests - for Jobs/Alignment page"""

    def test_get_active_crew_links(self, gm_token):
        """Get active crew links with pagination"""
        headers = {"Authorization": f"Bearer {gm_token}"}
        response = requests.get(f"{BASE_URL}/api/crew-access-links?status=active&page=1&limit=10", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data

    def test_get_inactive_crew_links(self, gm_token):
        """Get inactive crew links with pagination"""
        headers = {"Authorization": f"Bearer {gm_token}"}
        response = requests.get(f"{BASE_URL}/api/crew-access-links?status=inactive&page=1&limit=10", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data

    def test_update_crew_link(self, gm_token):
        """Update a crew link (if any exist)"""
        headers = {"Authorization": f"Bearer {gm_token}"}
        # First get an active link
        response = requests.get(f"{BASE_URL}/api/crew-access-links?status=active&page=1&limit=1", headers=headers)
        assert response.status_code == 200
        data = response.json()
        if data["items"]:
            link_id = data["items"][0]["id"]
            original_label = data["items"][0].get("label", "")
            original_truck = data["items"][0].get("truck_number", "")
            original_division = data["items"][0].get("division", "Maintenance")
            original_assignment = data["items"][0].get("assignment", "")
            # Update the link with all required fields
            update_payload = {
                "label": original_label,
                "truck_number": original_truck,
                "division": original_division,
                "assignment": "TEST_UPDATED_ASSIGNMENT"
            }
            update_response = requests.patch(f"{BASE_URL}/api/crew-access-links/{link_id}", json=update_payload, headers=headers)
            assert update_response.status_code == 200
            # Revert the change
            revert_payload = {
                "label": original_label,
                "truck_number": original_truck,
                "division": original_division,
                "assignment": original_assignment
            }
            requests.patch(f"{BASE_URL}/api/crew-access-links/{link_id}", json=revert_payload, headers=headers)
        else:
            pytest.skip("No active crew links to test update")


class TestJobs:
    """Jobs API tests - for Jobs/Alignment page"""

    def test_get_jobs_paginated(self, gm_token):
        """Get jobs with pagination"""
        headers = {"Authorization": f"Bearer {gm_token}"}
        response = requests.get(f"{BASE_URL}/api/jobs?page=1&limit=10", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data

    def test_search_jobs(self, gm_token):
        """Search jobs by keyword"""
        headers = {"Authorization": f"Bearer {gm_token}"}
        response = requests.get(f"{BASE_URL}/api/jobs?search=test&page=1&limit=10", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestRepeatOffenders:
    """Repeat offenders API tests - heatmap, action tiers, carousel"""

    def test_get_repeat_offenders(self, gm_token):
        """Get repeat offenders with thresholds"""
        headers = {"Authorization": f"Bearer {gm_token}"}
        response = requests.get(f"{BASE_URL}/api/repeat-offenders?window_days=30&threshold_one=3&threshold_two=5&threshold_three=7", headers=headers)
        assert response.status_code == 200
        data = response.json()
        # Verify heatmap and crew_summaries exist
        assert "heatmap" in data
        assert "crew_summaries" in data
        assert isinstance(data["heatmap"], list)
        assert isinstance(data["crew_summaries"], list)

    def test_repeat_offenders_different_window(self, gm_token):
        """Get repeat offenders with different window"""
        headers = {"Authorization": f"Bearer {gm_token}"}
        response = requests.get(f"{BASE_URL}/api/repeat-offenders?window_days=60&threshold_one=3&threshold_two=5&threshold_three=7", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "heatmap" in data
        assert "crew_summaries" in data


class TestTrainingSessions:
    """Training sessions API tests - for Repeat Offenders create training"""

    def test_get_training_sessions(self, gm_token):
        """Get training sessions"""
        headers = {"Authorization": f"Bearer {gm_token}"}
        response = requests.get(f"{BASE_URL}/api/training-sessions", headers=headers)
        # May return 200 or 404 if no sessions exist
        assert response.status_code in [200, 404]


class TestPublicCrewAccess:
    """Public crew access API tests - for Crew Capture page"""

    def test_get_public_crew_access(self, gm_token):
        """Get a crew access code and verify public endpoint"""
        headers = {"Authorization": f"Bearer {gm_token}"}
        # First get an active link
        response = requests.get(f"{BASE_URL}/api/crew-access-links?status=active&page=1&limit=1", headers=headers)
        assert response.status_code == 200
        data = response.json()
        if data["items"]:
            code = data["items"][0]["code"]
            # Test public endpoint
            public_response = requests.get(f"{BASE_URL}/api/public/crew-access/{code}")
            assert public_response.status_code == 200
            public_data = public_response.json()
            assert "label" in public_data
            assert "division" in public_data
            assert "truck_number" in public_data
        else:
            pytest.skip("No active crew links to test public access")


class TestRubricMatrices:
    """Rubric matrices API tests - for Quick Matrix Ref"""

    def test_get_rubric_matrices(self, gm_token):
        """Get rubric matrices"""
        headers = {"Authorization": f"Bearer {gm_token}"}
        response = requests.get(f"{BASE_URL}/api/rubric-matrices?division=all", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestSubmissions:
    """Submissions API tests"""

    def test_get_submissions(self, gm_token):
        """Get submissions with pagination"""
        headers = {"Authorization": f"Bearer {gm_token}"}
        response = requests.get(f"{BASE_URL}/api/submissions?scope=all&page=1&limit=4", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data
