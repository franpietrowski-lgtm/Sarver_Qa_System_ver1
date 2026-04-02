"""
Iteration 15 Backend Tests
Tests for:
- Auth login still works
- GET /api/submissions returns items with work_date field populated
- GET /api/submissions returns 23 total seeded submissions
- GET /api/repeat-offenders?window_days=30 returns fewer crews than window_days=240
- GET /api/repeat-offenders?window_days=240 returns crew_summaries with Critical/Warning/Watch levels
- Standards Library page still loads with pagination (5 per page)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


class TestAuthLogin:
    """Test authentication still works after changes"""

    def test_gm_login_success(self):
        """GM user can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "ctyler.gm@slmco.local",
            "password": "SLMCo2026!"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == "ctyler.gm@slmco.local"
        assert data["user"]["role"] == "management"
        assert data["user"]["title"] == "GM"

    def test_owner_login_success(self):
        """Owner user can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "sadam.owner@slmco.local",
            "password": "SLMCo2026!"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == "sadam.owner@slmco.local"
        assert data["user"]["role"] == "owner"


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


class TestSubmissionsWorkDate:
    """Test submissions have work_date field populated"""

    def test_submissions_returns_23_total(self, auth_headers):
        """GET /api/submissions returns 23 total seeded submissions"""
        response = requests.get(
            f"{BASE_URL}/api/submissions?scope=all&page=1&limit=30",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "pagination" in data
        assert data["pagination"]["total"] == 23, f"Expected 23 submissions, got {data['pagination']['total']}"

    def test_submissions_have_work_date_field(self, auth_headers):
        """GET /api/submissions returns items with work_date field populated"""
        response = requests.get(
            f"{BASE_URL}/api/submissions?scope=all&page=1&limit=30",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        items = data.get("items", [])
        assert len(items) > 0, "No submissions returned"
        
        # Check that all submissions have work_date field
        for item in items:
            assert "work_date" in item, f"Submission {item.get('id')} missing work_date field"
            assert item["work_date"] is not None, f"Submission {item.get('id')} has null work_date"
            # work_date should be in YYYY-MM-DD format
            assert len(item["work_date"]) == 10, f"work_date format incorrect: {item['work_date']}"

    def test_submissions_have_captured_at_field(self, auth_headers):
        """GET /api/submissions returns items with captured_at field"""
        response = requests.get(
            f"{BASE_URL}/api/submissions?scope=all&page=1&limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        items = data.get("items", [])
        
        # Check that submissions have captured_at field (from projection)
        for item in items:
            assert "captured_at" in item or "created_at" in item, f"Submission {item.get('id')} missing timestamp field"


class TestRepeatOffendersWindowFiltering:
    """Test repeat offender endpoint responds to different window_days values"""

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
        """GET /api/repeat-offenders?window_days=240 returns crew summaries"""
        response = requests.get(
            f"{BASE_URL}/api/repeat-offenders?window_days=240",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["window_days"] == 240
        assert "crew_summaries" in data
        assert "heatmap" in data

    def test_repeat_offenders_30_fewer_crews_than_240(self, auth_headers):
        """window_days=30 returns fewer or equal crews than window_days=240"""
        response_30 = requests.get(
            f"{BASE_URL}/api/repeat-offenders?window_days=30",
            headers=auth_headers
        )
        response_240 = requests.get(
            f"{BASE_URL}/api/repeat-offenders?window_days=240",
            headers=auth_headers
        )
        
        assert response_30.status_code == 200
        assert response_240.status_code == 200
        
        crews_30 = len(response_30.json().get("crew_summaries", []))
        crews_240 = len(response_240.json().get("crew_summaries", []))
        
        assert crews_30 <= crews_240, f"30-day window ({crews_30} crews) should have <= crews than 240-day ({crews_240} crews)"

    def test_repeat_offenders_240_has_escalation_levels(self, auth_headers):
        """GET /api/repeat-offenders?window_days=240 returns crew_summaries with Critical/Warning/Watch levels"""
        response = requests.get(
            f"{BASE_URL}/api/repeat-offenders?window_days=240",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        crew_summaries = data.get("crew_summaries", [])
        assert len(crew_summaries) > 0, "No crew summaries returned"
        
        # Collect all levels
        levels_found = set()
        for crew in crew_summaries:
            assert "level" in crew, f"Crew {crew.get('crew')} missing level field"
            levels_found.add(crew["level"])
        
        # Should have at least some escalation levels (Critical, Warning, Watch, or Monitor)
        valid_levels = {"Critical", "Warning", "Watch", "Monitor"}
        assert levels_found.issubset(valid_levels), f"Invalid levels found: {levels_found - valid_levels}"
        
        # With 240 days of data, we should see at least Warning or Critical level
        high_levels = {"Critical", "Warning", "Watch"}
        assert len(levels_found & high_levels) > 0, f"Expected at least one high-level escalation, got: {levels_found}"

    def test_repeat_offenders_heatmap_has_levels(self, auth_headers):
        """Heatmap cells have level field based on crew escalation"""
        response = requests.get(
            f"{BASE_URL}/api/repeat-offenders?window_days=240",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        heatmap = data.get("heatmap", [])
        if len(heatmap) > 0:
            for cell in heatmap[:5]:  # Check first 5 cells
                assert "level" in cell, f"Heatmap cell missing level field"
                assert "crew" in cell
                assert "issue_type" in cell
                assert "count" in cell


class TestStandardsLibraryPagination:
    """Test Standards Library page still loads with pagination (5 per page)"""

    def test_standards_library_pagination_5_per_page(self, auth_headers):
        """Standards library returns 5 items per page"""
        response = requests.get(
            f"{BASE_URL}/api/standards?page=1&limit=5",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert "pagination" in data
        
        pagination = data["pagination"]
        assert pagination["limit"] == 5
        assert pagination["page"] == 1
        
        # Should have items
        items = data["items"]
        assert len(items) <= 5, f"Expected max 5 items, got {len(items)}"

    def test_standards_library_has_total_count(self, auth_headers):
        """Standards library returns total count for pagination"""
        response = requests.get(
            f"{BASE_URL}/api/standards?page=1&limit=5",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        pagination = data["pagination"]
        assert "total" in pagination
        assert pagination["total"] >= 0


class TestPublicCrewAccess:
    """Test public crew access endpoints"""

    def test_public_crew_access_list(self):
        """GET /api/public/crew-access returns active crew links"""
        response = requests.get(f"{BASE_URL}/api/public/crew-access")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0, "No crew access links found"
        
        # Check first crew link has required fields
        crew = data[0]
        assert "code" in crew
        assert "label" in crew
        assert "truck_number" in crew
        assert "division" in crew


class TestDashboardOverview:
    """Test dashboard overview endpoint"""

    def test_dashboard_overview(self, auth_headers):
        """GET /api/dashboard/overview returns expected structure"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/overview",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "totals" in data
        assert "queues" in data
        assert "storage" in data
        assert "workflow_health" in data
        
        # Check totals has submissions count
        assert data["totals"]["submissions"] >= 23, f"Expected at least 23 submissions, got {data['totals']['submissions']}"
