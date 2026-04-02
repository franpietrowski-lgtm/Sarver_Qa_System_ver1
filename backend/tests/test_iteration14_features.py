"""
Iteration 14 Backend Tests
Tests for:
1. Backend modularization - shared/deps.py extraction from server.py
2. Auth login works correctly after refactoring
3. GET /api/standards?page=1&limit=5 returns 5 items with correct pagination
4. GET /api/standards?page=2&limit=5 returns next page of items
5. GET /api/equipment-logs returns paginated results
6. GET /api/dashboard/overview returns correct overview data
7. GET /api/rubric-matrices returns rubric data
8. GET /api/repeat-offenders returns crew summaries and heatmap
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials from /app/memory/test_credentials.md
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
    pytest.skip("GM authentication failed - skipping authenticated tests")


@pytest.fixture(scope="module")
def owner_token(api_client):
    """Get Owner authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": OWNER_EMAIL,
        "password": PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Owner authentication failed - skipping authenticated tests")


@pytest.fixture(scope="module")
def supervisor_token(api_client):
    """Get Supervisor authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": SUPERVISOR_EMAIL,
        "password": PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Supervisor authentication failed - skipping authenticated tests")


class TestAuthAfterRefactoring:
    """Test auth login works correctly after backend modularization"""
    
    def test_gm_login_success(self, api_client):
        """GM login should work after refactoring"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": GM_EMAIL,
            "password": PASSWORD
        })
        assert response.status_code == 200, f"GM login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == GM_EMAIL.lower()
        assert data["user"]["role"] == "management"
        assert data["user"]["title"] == "GM"
        print(f"PASS: GM login successful - {data['user']['name']}")
    
    def test_owner_login_success(self, api_client):
        """Owner login should work after refactoring"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL,
            "password": PASSWORD
        })
        assert response.status_code == 200, f"Owner login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == OWNER_EMAIL.lower()
        assert data["user"]["role"] == "owner"
        print(f"PASS: Owner login successful - {data['user']['name']}")
    
    def test_supervisor_login_success(self, api_client):
        """Supervisor login should work after refactoring"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPERVISOR_EMAIL,
            "password": PASSWORD
        })
        assert response.status_code == 200, f"Supervisor login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == SUPERVISOR_EMAIL.lower()
        assert data["user"]["role"] == "management"
        assert data["user"]["title"] == "Supervisor"
        print(f"PASS: Supervisor login successful - {data['user']['name']}")
    
    def test_auth_me_endpoint(self, api_client, gm_token):
        """GET /api/auth/me should return current user"""
        response = api_client.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 200, f"Auth me failed: {response.text}"
        data = response.json()
        assert data["email"] == GM_EMAIL.lower()
        print(f"PASS: Auth me endpoint works - {data['name']}")


class TestStandardsPagination:
    """Test Standards Library pagination with limit=5"""
    
    def test_standards_page1_limit5(self, api_client, gm_token):
        """GET /api/standards?page=1&limit=5 should return 5 items with correct pagination"""
        response = api_client.get(
            f"{BASE_URL}/api/standards?page=1&limit=5",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 200, f"Standards page 1 failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "items" in data
        assert "pagination" in data
        
        # Verify pagination structure
        pagination = data["pagination"]
        assert "page" in pagination
        assert "limit" in pagination
        assert "total" in pagination
        assert "pages" in pagination
        assert "has_next" in pagination
        assert "has_prev" in pagination
        
        # Verify page 1 values
        assert pagination["page"] == 1
        assert pagination["limit"] == 5
        assert pagination["has_prev"] == False
        
        # Verify items count (should be 5 or less if total < 5)
        items_count = len(data["items"])
        assert items_count <= 5, f"Expected max 5 items, got {items_count}"
        
        # If total > 5, should have next page
        if pagination["total"] > 5:
            assert pagination["has_next"] == True
            assert pagination["pages"] >= 2
        
        print(f"PASS: Standards page 1 - {items_count} items, total={pagination['total']}, pages={pagination['pages']}")
        return pagination
    
    def test_standards_page2_limit5(self, api_client, gm_token):
        """GET /api/standards?page=2&limit=5 should return next page of items"""
        # First get page 1 to know total
        response1 = api_client.get(
            f"{BASE_URL}/api/standards?page=1&limit=5",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response1.status_code == 200
        page1_data = response1.json()
        total = page1_data["pagination"]["total"]
        
        if total <= 5:
            pytest.skip("Not enough standards to test page 2")
        
        # Get page 2
        response2 = api_client.get(
            f"{BASE_URL}/api/standards?page=2&limit=5",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response2.status_code == 200, f"Standards page 2 failed: {response2.text}"
        data = response2.json()
        
        pagination = data["pagination"]
        assert pagination["page"] == 2
        assert pagination["has_prev"] == True
        
        # Verify items are different from page 1
        page1_ids = {item["id"] for item in page1_data["items"]}
        page2_ids = {item["id"] for item in data["items"]}
        assert page1_ids.isdisjoint(page2_ids), "Page 2 should have different items than page 1"
        
        print(f"PASS: Standards page 2 - {len(data['items'])} items, has_prev={pagination['has_prev']}")
    
    def test_standards_total_count(self, api_client, gm_token):
        """Verify total standards count is consistent"""
        response = api_client.get(
            f"{BASE_URL}/api/standards?page=1&limit=5",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        total = data["pagination"]["total"]
        pages = data["pagination"]["pages"]
        
        # Verify pages calculation is correct
        import math
        expected_pages = max(math.ceil(total / 5), 1)
        assert pages == expected_pages, f"Expected {expected_pages} pages, got {pages}"
        
        print(f"PASS: Standards total={total}, pages={pages} (correct calculation)")


class TestEquipmentLogsPagination:
    """Test Equipment Logs pagination"""
    
    def test_equipment_logs_returns_paginated(self, api_client, gm_token):
        """GET /api/equipment-logs should return paginated results"""
        response = api_client.get(
            f"{BASE_URL}/api/equipment-logs?page=1&limit=10",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 200, f"Equipment logs failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "items" in data
        assert "pagination" in data
        
        pagination = data["pagination"]
        assert "page" in pagination
        assert "limit" in pagination
        assert "total" in pagination
        assert "pages" in pagination
        
        print(f"PASS: Equipment logs - {len(data['items'])} items, total={pagination['total']}")
    
    def test_equipment_logs_requires_auth(self, api_client):
        """GET /api/equipment-logs should require authentication"""
        response = api_client.get(f"{BASE_URL}/api/equipment-logs")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: Equipment logs requires authentication")


class TestDashboardOverview:
    """Test Dashboard Overview endpoint"""
    
    def test_dashboard_overview_returns_data(self, api_client, gm_token):
        """GET /api/dashboard/overview should return correct overview data"""
        response = api_client.get(
            f"{BASE_URL}/api/dashboard/overview",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 200, f"Dashboard overview failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "totals" in data
        assert "queues" in data
        assert "storage" in data
        assert "workflow_health" in data
        
        # Verify totals structure
        totals = data["totals"]
        assert "submissions" in totals
        assert "jobs" in totals
        assert "rubrics" in totals
        assert "exports" in totals
        
        # Verify queues structure
        queues = data["queues"]
        assert "management" in queues
        assert "owner" in queues
        assert "export_ready" in queues
        
        print(f"PASS: Dashboard overview - submissions={totals['submissions']}, jobs={totals['jobs']}")
    
    def test_dashboard_overview_requires_auth(self, api_client):
        """GET /api/dashboard/overview should require authentication"""
        response = api_client.get(f"{BASE_URL}/api/dashboard/overview")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: Dashboard overview requires authentication")


class TestRubricMatrices:
    """Test Rubric Matrices endpoint"""
    
    def test_rubric_matrices_returns_data(self, api_client, gm_token):
        """GET /api/rubric-matrices should return rubric data"""
        response = api_client.get(
            f"{BASE_URL}/api/rubric-matrices",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 200, f"Rubric matrices failed: {response.text}"
        data = response.json()
        
        # Verify response is a list of rubrics
        assert isinstance(data, list), "Expected list of rubrics"
        
        if len(data) > 0:
            rubric = data[0]
            assert "id" in rubric
            assert "service_type" in rubric
            assert "categories" in rubric
            print(f"PASS: Rubric matrices - {len(data)} rubrics found")
        else:
            print("PASS: Rubric matrices - empty list (no rubrics)")
    
    def test_rubric_matrices_requires_auth(self, api_client):
        """GET /api/rubric-matrices should require authentication"""
        response = api_client.get(f"{BASE_URL}/api/rubric-matrices")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: Rubric matrices requires authentication")


class TestRepeatOffenders:
    """Test Repeat Offenders endpoint"""
    
    def test_repeat_offenders_returns_data(self, api_client, gm_token):
        """GET /api/repeat-offenders should return crew summaries and heatmap"""
        response = api_client.get(
            f"{BASE_URL}/api/repeat-offenders",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 200, f"Repeat offenders failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "window_days" in data
        assert "thresholds" in data
        assert "crew_summaries" in data
        assert "heatmap" in data
        
        # Verify thresholds structure
        thresholds = data["thresholds"]
        assert "level_1" in thresholds
        assert "level_2" in thresholds
        assert "level_3" in thresholds
        
        print(f"PASS: Repeat offenders - {len(data['crew_summaries'])} crews, {len(data['heatmap'])} heatmap entries")
    
    def test_repeat_offenders_requires_auth(self, api_client):
        """GET /api/repeat-offenders should require authentication"""
        response = api_client.get(f"{BASE_URL}/api/repeat-offenders")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: Repeat offenders requires authentication")


class TestSharedDepsModularization:
    """Test that shared/deps.py functions are working correctly"""
    
    def test_health_endpoint(self, api_client):
        """Health endpoint should work (uses now_iso from deps)"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"
        assert "timestamp" in data
        print(f"PASS: Health endpoint works - timestamp={data['timestamp']}")
    
    def test_public_crew_access(self, api_client):
        """Public crew access should work (uses present_crew_link from deps)"""
        response = api_client.get(f"{BASE_URL}/api/public/crew-access")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            crew = data[0]
            assert "code" in crew
            assert "label" in crew
            assert "crew_member_id" in crew
            print(f"PASS: Public crew access - {len(data)} active crews")
        else:
            print("PASS: Public crew access - no active crews")
    
    def test_pagination_helper_works(self, api_client, gm_token):
        """Verify build_paginated_response works correctly"""
        response = api_client.get(
            f"{BASE_URL}/api/jobs?page=1&limit=5",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify pagination structure from build_paginated_response
        assert "items" in data
        assert "pagination" in data
        pagination = data["pagination"]
        assert pagination["page"] == 1
        assert pagination["limit"] == 5
        
        print(f"PASS: Pagination helper works - jobs page 1 with {len(data['items'])} items")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
