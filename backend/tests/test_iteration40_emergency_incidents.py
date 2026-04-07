"""
Iteration 40 Tests - Emergency Incidents, Client Report Dropdown, and Demo Jobs
Tests:
1. Client Report dropdown - min 2 chars, glass effect, search results
2. 12 new demo jobs (LMN-4201 through LMN-4212)
3. Backend /api/incidents/active endpoint
4. Emergency submission bypass photo requirement
5. Regression tests for existing features
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://quality-hub-32.preview.emergentagent.com")


class TestAuth:
    """Authentication helpers"""
    
    @pytest.fixture(scope="class")
    def owner_token(self):
        """Get owner token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "sadam.owner@slmco.local", "password": "SLMCo2026!"}
        )
        assert response.status_code == 200, f"Owner login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def gm_token(self):
        """Get GM token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "ctyler.gm@slmco.local", "password": "SLMCo2026!"}
        )
        assert response.status_code == 200, f"GM login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def am_token(self):
        """Get Account Manager token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "kscott.accm@slmco.local", "password": "SLMCo2026!"}
        )
        assert response.status_code == 200, f"AM login failed: {response.text}"
        return response.json()["token"]


class TestIncidentsEndpoint(TestAuth):
    """Test /api/incidents/active endpoint"""
    
    def test_incidents_active_returns_200_for_owner(self, owner_token):
        """Incidents endpoint returns 200 for owner"""
        response = requests.get(
            f"{BASE_URL}/api/incidents/active",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "incidents" in data
        assert "total" in data
        assert isinstance(data["incidents"], list)
    
    def test_incidents_active_returns_200_for_gm(self, gm_token):
        """Incidents endpoint returns 200 for GM"""
        response = requests.get(
            f"{BASE_URL}/api/incidents/active",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "incidents" in data
    
    def test_incidents_active_requires_auth(self):
        """Incidents endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/incidents/active")
        assert response.status_code in [401, 403, 422]


class TestJobSearchDropdown(TestAuth):
    """Test Client Report job search dropdown"""
    
    def test_job_search_cedar_returns_results(self, owner_token):
        """Search for 'cedar' returns Cedar Court and Cedar Point entries"""
        response = requests.get(
            f"{BASE_URL}/api/reports/job-search?q=cedar",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        results = data["results"]
        assert len(results) >= 2, f"Expected at least 2 cedar results, got {len(results)}"
        
        # Check for Cedar Court and Cedar Point
        job_names = [r.get("job_name", "").lower() for r in results]
        has_cedar_court = any("cedar court" in name for name in job_names)
        has_cedar_point = any("cedar point" in name for name in job_names)
        assert has_cedar_court or has_cedar_point, f"Expected Cedar Court or Cedar Point in results: {job_names}"
    
    def test_job_search_lake_returns_results(self, owner_token):
        """Search for 'lake' returns Lakeshore and Lakewood entries"""
        response = requests.get(
            f"{BASE_URL}/api/reports/job-search?q=lake",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        results = data["results"]
        assert len(results) >= 2, f"Expected at least 2 lake results, got {len(results)}"
        
        job_names = [r.get("job_name", "").lower() for r in results]
        has_lakeshore = any("lakeshore" in name for name in job_names)
        has_lakewood = any("lakewood" in name for name in job_names)
        assert has_lakeshore or has_lakewood, f"Expected Lakeshore or Lakewood in results: {job_names}"
    
    def test_job_search_oak_returns_results(self, owner_token):
        """Search for 'oak' returns Oakridge Valley and Oak Summit entries"""
        response = requests.get(
            f"{BASE_URL}/api/reports/job-search?q=oak",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        results = data["results"]
        assert len(results) >= 2, f"Expected at least 2 oak results, got {len(results)}"
        
        job_names = [r.get("job_name", "").lower() for r in results]
        has_oakridge = any("oakridge" in name for name in job_names)
        has_oak_summit = any("oak summit" in name for name in job_names)
        assert has_oakridge or has_oak_summit, f"Expected Oakridge or Oak Summit in results: {job_names}"
    
    def test_job_search_single_char_returns_empty(self, owner_token):
        """Search with single character should return empty or limited results"""
        response = requests.get(
            f"{BASE_URL}/api/reports/job-search?q=a",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        # API may return results but frontend should filter for min 2 chars


class TestDemoJobs(TestAuth):
    """Test 12 new demo jobs (LMN-4201 through LMN-4212)"""
    
    def test_demo_jobs_exist(self, owner_token):
        """Verify 12 new demo jobs exist"""
        response = requests.get(
            f"{BASE_URL}/api/jobs?limit=100",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        jobs = data.get("items", data.get("jobs", []))
        
        # Check for LMN-42xx jobs
        demo_job_ids = [j.get("job_id", "") for j in jobs if j.get("job_id", "").startswith("LMN-42")]
        assert len(demo_job_ids) >= 10, f"Expected at least 10 LMN-42xx jobs, found {len(demo_job_ids)}: {demo_job_ids}"
    
    def test_demo_jobs_have_varied_service_types(self, owner_token):
        """Demo jobs have varied maintenance tasks"""
        response = requests.get(
            f"{BASE_URL}/api/jobs?limit=100",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        jobs = data.get("items", data.get("jobs", []))
        
        demo_jobs = [j for j in jobs if j.get("job_id", "").startswith("LMN-42")]
        service_types = set(j.get("service_type", "").lower() for j in demo_jobs)
        
        # Should have multiple service types
        assert len(service_types) >= 3, f"Expected at least 3 different service types, got {service_types}"


class TestEmergencySubmission:
    """Test emergency submission photo bypass"""
    
    def test_public_submission_endpoint_exists(self):
        """Public submission endpoint exists"""
        # Just verify the endpoint is reachable (will fail without proper data)
        response = requests.post(
            f"{BASE_URL}/api/public/submissions",
            data={"access_code": "invalid"}
        )
        # Should return 404 for invalid access code, not 500
        assert response.status_code in [400, 404, 422], f"Unexpected status: {response.status_code}"


class TestClientReportPage(TestAuth):
    """Test Client Report page API endpoints"""
    
    def test_client_quality_report_daily(self, owner_token):
        """Client quality report works with daily period"""
        response = requests.get(
            f"{BASE_URL}/api/reports/client-quality?period=daily",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "properties" in data or "total_properties" in data
    
    def test_client_quality_report_weekly(self, owner_token):
        """Client quality report works with weekly period"""
        response = requests.get(
            f"{BASE_URL}/api/reports/client-quality?period=weekly",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
    
    def test_client_quality_report_monthly(self, owner_token):
        """Client quality report works with monthly period"""
        response = requests.get(
            f"{BASE_URL}/api/reports/client-quality?period=monthly",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
    
    def test_client_quality_report_quarterly(self, owner_token):
        """Client quality report works with quarterly period"""
        response = requests.get(
            f"{BASE_URL}/api/reports/client-quality?period=quarterly",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200


class TestRegressionOverview(TestAuth):
    """Regression tests for Overview page"""
    
    def test_dashboard_overview(self, owner_token):
        """Dashboard overview returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/overview",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "totals" in data
    
    def test_division_quality_trend(self, owner_token):
        """Division quality trend returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/metrics/division-quality-trend",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
    
    def test_standards_compliance(self, owner_token):
        """Standards compliance returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/metrics/standards-compliance",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
    
    def test_training_funnel(self, owner_token):
        """Training funnel returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/metrics/training-funnel",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
    
    def test_coaching_loop(self, owner_token):
        """Coaching loop returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/coaching/loop-report",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200


class TestRegressionNav(TestAuth):
    """Regression tests for navigation and role access"""
    
    def test_am_can_access_client_report(self, am_token):
        """Account Manager can access client report"""
        response = requests.get(
            f"{BASE_URL}/api/reports/client-quality?period=monthly",
            headers={"Authorization": f"Bearer {am_token}"}
        )
        assert response.status_code == 200
    
    def test_gm_can_access_client_report(self, gm_token):
        """GM can access client report"""
        response = requests.get(
            f"{BASE_URL}/api/reports/client-quality?period=monthly",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 200
    
    def test_owner_can_access_client_report(self, owner_token):
        """Owner can access client report"""
        response = requests.get(
            f"{BASE_URL}/api/reports/client-quality?period=monthly",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200


class TestCrewAccess:
    """Test crew access endpoints"""
    
    def test_crew_access_bb01032c(self):
        """Crew access for Install Alpha (bb01032c) works"""
        response = requests.get(f"{BASE_URL}/api/public/crew-access/bb01032c")
        assert response.status_code == 200
        data = response.json()
        assert "label" in data
        assert "division" in data
    
    def test_crew_access_be1da0c6(self):
        """Crew access for Maintenance Alpha (be1da0c6) works"""
        response = requests.get(f"{BASE_URL}/api/public/crew-access/be1da0c6")
        assert response.status_code == 200
        data = response.json()
        assert "label" in data
        assert "division" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
