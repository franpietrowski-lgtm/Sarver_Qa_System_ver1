"""
Iteration 12 Backend Tests
Tests for:
- Auth login with lowercased email format
- Equipment logs API endpoint with pagination
- Dashboard overview endpoint
- Standards library endpoint
- Repeat offenders endpoint
- Crew access endpoints
"""

import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials from test_credentials.md
GM_EMAIL = "ctyler.gm@slmco.local"
OWNER_EMAIL = "sadam.owner@slmco.local"
SUPERVISOR_EMAIL = "hjohnny.super@slmco.local"
PASSWORD = "SLMCo2026!"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def gm_token(api_client):
    """Get GM authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": GM_EMAIL,
        "password": PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("GM authentication failed")


@pytest.fixture(scope="module")
def owner_token(api_client):
    """Get Owner authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": OWNER_EMAIL,
        "password": PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Owner authentication failed")


@pytest.fixture(scope="module")
def supervisor_token(api_client):
    """Get Supervisor authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": SUPERVISOR_EMAIL,
        "password": PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Supervisor authentication failed")


class TestAuthLogin:
    """Test authentication with lowercased email format"""
    
    def test_gm_login_lowercase_email(self, api_client):
        """Test GM login with lowercase email"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": GM_EMAIL,
            "password": PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == GM_EMAIL.lower()
        assert data["user"]["title"] == "GM"
        assert data["user"]["role"] == "management"
    
    def test_owner_login_lowercase_email(self, api_client):
        """Test Owner login with lowercase email"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL,
            "password": PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["email"] == OWNER_EMAIL.lower()
        assert data["user"]["role"] == "owner"
    
    def test_supervisor_login_lowercase_email(self, api_client):
        """Test Supervisor login with lowercase email"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPERVISOR_EMAIL,
            "password": PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["email"] == SUPERVISOR_EMAIL.lower()
        assert data["user"]["title"] == "Supervisor"
    
    def test_login_case_insensitive(self, api_client):
        """Test that login is case-insensitive"""
        # Try with uppercase email
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": GM_EMAIL.upper(),
            "password": PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == GM_EMAIL.lower()
    
    def test_login_invalid_credentials(self, api_client):
        """Test login with invalid credentials"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401


class TestEquipmentLogsAPI:
    """Test equipment logs API endpoint with pagination"""
    
    def test_get_equipment_logs_paginated(self, api_client, gm_token):
        """Test GET /api/equipment-logs returns paginated results"""
        response = api_client.get(
            f"{BASE_URL}/api/equipment-logs?page=1&limit=5",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data
        assert "page" in data["pagination"]
        assert "limit" in data["pagination"]
        assert "total" in data["pagination"]
        assert "pages" in data["pagination"]
        assert "has_next" in data["pagination"]
        assert "has_prev" in data["pagination"]
    
    def test_equipment_logs_pagination_page_2(self, api_client, gm_token):
        """Test equipment logs pagination - page 2"""
        response = api_client.get(
            f"{BASE_URL}/api/equipment-logs?page=2&limit=5",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["page"] == 2
    
    def test_equipment_logs_requires_auth(self, api_client):
        """Test equipment logs requires authentication"""
        response = api_client.get(f"{BASE_URL}/api/equipment-logs")
        assert response.status_code == 401


class TestDashboardOverview:
    """Test dashboard overview endpoint"""
    
    def test_get_dashboard_overview(self, api_client, gm_token):
        """Test GET /api/dashboard/overview returns overview data"""
        response = api_client.get(
            f"{BASE_URL}/api/dashboard/overview",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "totals" in data
        assert "queues" in data
        assert "workflow_health" in data
        assert "submissions" in data["totals"]
        assert "jobs" in data["totals"]


class TestStandardsLibrary:
    """Test standards library endpoint"""
    
    def test_get_standards(self, api_client, gm_token):
        """Test GET /api/standards returns standards list"""
        response = api_client.get(
            f"{BASE_URL}/api/standards?page=1&limit=10",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data
    
    def test_standards_filter_by_category(self, api_client, gm_token):
        """Test standards filtering by category"""
        response = api_client.get(
            f"{BASE_URL}/api/standards?category=Edging&page=1&limit=10",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestRepeatOffenders:
    """Test repeat offenders endpoint"""
    
    def test_get_repeat_offenders(self, api_client, gm_token):
        """Test GET /api/repeat-offenders returns summary"""
        response = api_client.get(
            f"{BASE_URL}/api/repeat-offenders?window_days=30&threshold_one=3&threshold_two=5&threshold_three=7",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "window_days" in data
        assert "thresholds" in data
        assert "crew_summaries" in data
        assert "heatmap" in data
        assert data["thresholds"]["level_1"] == 3
        assert data["thresholds"]["level_2"] == 5
        assert data["thresholds"]["level_3"] == 7


class TestCrewAccess:
    """Test crew access endpoints"""
    
    def test_get_public_crew_access(self, api_client):
        """Test GET /api/public/crew-access returns crew links"""
        response = api_client.get(f"{BASE_URL}/api/public/crew-access")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            crew = data[0]
            assert "code" in crew
            assert "label" in crew
            assert "truck_number" in crew
            assert "division" in crew
    
    def test_get_crew_access_by_code(self, api_client):
        """Test GET /api/public/crew-access/{code} returns crew details"""
        # First get a valid code
        response = api_client.get(f"{BASE_URL}/api/public/crew-access")
        assert response.status_code == 200
        crews = response.json()
        if len(crews) > 0:
            code = crews[0]["code"]
            response = api_client.get(f"{BASE_URL}/api/public/crew-access/{code}")
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == code
            assert "notifications" in data


class TestRubricMatrices:
    """Test rubric matrices endpoint"""
    
    def test_get_rubric_matrices(self, api_client, gm_token):
        """Test GET /api/rubric-matrices returns rubrics"""
        response = api_client.get(
            f"{BASE_URL}/api/rubric-matrices?division=all",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            rubric = data[0]
            assert "id" in rubric
            assert "service_type" in rubric
            assert "division" in rubric
            assert "categories" in rubric
            assert "pass_threshold" in rubric


class TestHealthEndpoint:
    """Test health endpoint"""
    
    def test_health_check(self, api_client):
        """Test GET /api/health returns ok status"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
