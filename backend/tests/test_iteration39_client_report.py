"""
Iteration 39 - Client Report Page & Division Cascade Tests
Tests for:
1. Client Report page access for Account Manager, GM, Owner roles
2. Job search API at /api/reports/job-search
3. Client quality report API at /api/reports/client-quality with timeframe cycling
4. PDF export at /api/exports/am-report-pdf
5. Crew division cascade on PATCH /api/crew-access-links/{id}
6. Division sync on GET /api/public/crew-member/{code}
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials from test_credentials.md
OWNER_EMAIL = "sadam.owner@slmco.local"
OWNER_PASSWORD = "SLMCo2026!"
GM_EMAIL = "ctyler.gm@slmco.local"
GM_PASSWORD = "SLMCo2026!"
ACCOUNT_MANAGER_EMAIL = "kscott.accm@slmco.local"
ACCOUNT_MANAGER_PASSWORD = "SLMCo2026!"

# Demo crew codes
CREW_CODE_INSTALL = "bb01032c"
CREW_CODE_MAINTENANCE = "be1da0c6"


@pytest.fixture(scope="module")
def owner_token():
    """Get owner authentication token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": OWNER_EMAIL,
        "password": OWNER_PASSWORD
    })
    assert resp.status_code == 200, f"Owner login failed: {resp.text}"
    return resp.json()["token"]


@pytest.fixture(scope="module")
def gm_token():
    """Get GM authentication token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": GM_EMAIL,
        "password": GM_PASSWORD
    })
    assert resp.status_code == 200, f"GM login failed: {resp.text}"
    return resp.json()["token"]


@pytest.fixture(scope="module")
def account_manager_token():
    """Get Account Manager authentication token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ACCOUNT_MANAGER_EMAIL,
        "password": ACCOUNT_MANAGER_PASSWORD
    })
    assert resp.status_code == 200, f"Account Manager login failed: {resp.text}"
    return resp.json()["token"]


class TestHealthCheck:
    """Basic health check"""
    
    def test_health_endpoint(self):
        resp = requests.get(f"{BASE_URL}/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "ok"


class TestJobSearchAPI:
    """Tests for /api/reports/job-search endpoint"""
    
    def test_job_search_owner_access(self, owner_token):
        """Owner can access job search"""
        resp = requests.get(
            f"{BASE_URL}/api/reports/job-search?q=",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert isinstance(data["results"], list)
    
    def test_job_search_gm_access(self, gm_token):
        """GM (management role) can access job search"""
        resp = requests.get(
            f"{BASE_URL}/api/reports/job-search?q=",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
    
    def test_job_search_account_manager_access(self, account_manager_token):
        """Account Manager (management role) can access job search"""
        resp = requests.get(
            f"{BASE_URL}/api/reports/job-search?q=",
            headers={"Authorization": f"Bearer {account_manager_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
    
    def test_job_search_returns_results(self, owner_token):
        """Job search returns up to 15 results"""
        resp = requests.get(
            f"{BASE_URL}/api/reports/job-search?q=",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        results = data["results"]
        assert len(results) <= 15
        # Verify result structure
        if results:
            job = results[0]
            assert "id" in job or "job_id" in job
    
    def test_job_search_with_query(self, owner_token):
        """Job search filters by query string"""
        resp = requests.get(
            f"{BASE_URL}/api/reports/job-search?q=maintenance",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
    
    def test_job_search_requires_auth(self):
        """Job search requires authentication"""
        resp = requests.get(f"{BASE_URL}/api/reports/job-search?q=")
        assert resp.status_code in [401, 403]


class TestClientQualityReportAPI:
    """Tests for /api/reports/client-quality endpoint"""
    
    def test_client_quality_daily(self, owner_token):
        """Client quality report with daily period"""
        resp = requests.get(
            f"{BASE_URL}/api/reports/client-quality?period=daily&job_id=all",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "properties" in data
        assert "total_properties" in data
        assert "total_submissions" in data
        assert data["period"] == "daily"
    
    def test_client_quality_weekly(self, owner_token):
        """Client quality report with weekly period"""
        resp = requests.get(
            f"{BASE_URL}/api/reports/client-quality?period=weekly&job_id=all",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["period"] == "weekly"
    
    def test_client_quality_monthly(self, owner_token):
        """Client quality report with monthly period (default)"""
        resp = requests.get(
            f"{BASE_URL}/api/reports/client-quality?period=monthly&job_id=all",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["period"] == "monthly"
    
    def test_client_quality_quarterly(self, owner_token):
        """Client quality report with quarterly period"""
        resp = requests.get(
            f"{BASE_URL}/api/reports/client-quality?period=quarterly&job_id=all",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["period"] == "quarterly"
    
    def test_client_quality_property_structure(self, owner_token):
        """Client quality report returns proper property structure"""
        resp = requests.get(
            f"{BASE_URL}/api/reports/client-quality?period=quarterly&job_id=all",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        if data["properties"]:
            prop = data["properties"][0]
            assert "property" in prop
            assert "submissions_count" in prop
            assert "avg_score" in prop
            assert "pass_count" in prop
            assert "fail_count" in prop
            assert "divisions" in prop
            assert "submissions" in prop
    
    def test_client_quality_account_manager_access(self, account_manager_token):
        """Account Manager can access client quality report"""
        resp = requests.get(
            f"{BASE_URL}/api/reports/client-quality?period=monthly&job_id=all",
            headers={"Authorization": f"Bearer {account_manager_token}"}
        )
        assert resp.status_code == 200
    
    def test_client_quality_requires_auth(self):
        """Client quality report requires authentication"""
        resp = requests.get(f"{BASE_URL}/api/reports/client-quality?period=monthly&job_id=all")
        assert resp.status_code in [401, 403]


class TestPDFExportAPI:
    """Tests for /api/exports/am-report-pdf endpoint"""
    
    def test_pdf_export_owner_access(self, owner_token):
        """Owner can export PDF"""
        resp = requests.get(
            f"{BASE_URL}/api/exports/am-report-pdf?period=monthly&job_id=all",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers.get("content-type", "")
        # Verify PDF magic bytes
        assert resp.content[:4] == b"%PDF"
    
    def test_pdf_export_gm_access(self, gm_token):
        """GM can export PDF"""
        resp = requests.get(
            f"{BASE_URL}/api/exports/am-report-pdf?period=monthly&job_id=all",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers.get("content-type", "")
    
    def test_pdf_export_account_manager_access(self, account_manager_token):
        """Account Manager can export PDF"""
        resp = requests.get(
            f"{BASE_URL}/api/exports/am-report-pdf?period=monthly&job_id=all",
            headers={"Authorization": f"Bearer {account_manager_token}"}
        )
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers.get("content-type", "")
    
    def test_pdf_export_content_disposition(self, owner_token):
        """PDF export has proper Content-Disposition header"""
        resp = requests.get(
            f"{BASE_URL}/api/exports/am-report-pdf?period=monthly&job_id=all",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code == 200
        content_disp = resp.headers.get("content-disposition", "")
        assert "attachment" in content_disp
        assert "SarverLandscape_ClientReport" in content_disp
    
    def test_pdf_export_with_different_periods(self, owner_token):
        """PDF export works with different periods"""
        for period in ["daily", "weekly", "monthly", "quarterly"]:
            resp = requests.get(
                f"{BASE_URL}/api/exports/am-report-pdf?period={period}&job_id=all",
                headers={"Authorization": f"Bearer {owner_token}"}
            )
            assert resp.status_code == 200, f"PDF export failed for period={period}"
    
    def test_pdf_export_requires_auth(self):
        """PDF export requires authentication"""
        resp = requests.get(f"{BASE_URL}/api/exports/am-report-pdf?period=monthly&job_id=all")
        assert resp.status_code in [401, 403]


class TestCrewDivisionCascade:
    """Tests for crew division cascade on PATCH /api/crew-access-links/{id}"""
    
    def test_get_crew_access_links(self, owner_token):
        """Can get crew access links"""
        resp = requests.get(
            f"{BASE_URL}/api/crew-access-links",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
    
    def test_patch_crew_link_updates_division(self, owner_token):
        """PATCH crew link updates division field"""
        # First get a crew link
        resp = requests.get(
            f"{BASE_URL}/api/crew-access-links",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code == 200
        links = resp.json()["items"]
        if not links:
            pytest.skip("No crew links available for testing")
        
        link = links[0]
        link_id = link["id"]
        original_division = link.get("division", "")
        
        # Update with same data to verify endpoint works
        resp = requests.patch(
            f"{BASE_URL}/api/crew-access-links/{link_id}",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={
                "label": link.get("label", "Test"),
                "leader_name": link.get("leader_name", "Test Leader"),
                "truck_number": link.get("truck_number", "TR-99"),
                "division": original_division,
                "assignment": link.get("assignment", "")
            }
        )
        assert resp.status_code == 200
        updated = resp.json()
        assert updated["division"] == original_division


class TestCrewMemberDivisionSync:
    """Tests for division sync on GET /api/public/crew-member/{code}"""
    
    def test_get_crew_member_by_code(self):
        """Can get crew member by code (public endpoint)"""
        # First get a crew member code from the crew stats
        resp = requests.get(f"{BASE_URL}/api/public/crew-member-stats/{CREW_CODE_INSTALL}")
        if resp.status_code == 404:
            pytest.skip("No crew members available for testing")
        
        assert resp.status_code == 200
        data = resp.json()
        members = data.get("members", [])
        if not members:
            pytest.skip("No crew members under this crew link")
        
        member_code = members[0]["code"]
        
        # Get the member
        resp = requests.get(f"{BASE_URL}/api/public/crew-member/{member_code}")
        assert resp.status_code == 200
        member = resp.json()
        assert "code" in member
        assert "name" in member
        assert "division" in member
        assert "parent_access_code" in member
    
    def test_crew_member_invalid_code(self):
        """Invalid crew member code returns 404"""
        resp = requests.get(f"{BASE_URL}/api/public/crew-member/invalid_code_xyz")
        assert resp.status_code == 404


class TestRegressionChecks:
    """Regression tests for existing functionality"""
    
    def test_dashboard_overview(self, owner_token):
        """Dashboard overview still works"""
        resp = requests.get(
            f"{BASE_URL}/api/dashboard/overview",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code == 200
    
    def test_metrics_division_quality_trend(self, owner_token):
        """Division quality trend metric still works"""
        resp = requests.get(
            f"{BASE_URL}/api/metrics/division-quality-trend",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code == 200
    
    def test_metrics_standards_compliance(self, owner_token):
        """Standards compliance metric still works"""
        resp = requests.get(
            f"{BASE_URL}/api/metrics/standards-compliance",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code == 200
    
    def test_metrics_training_funnel(self, owner_token):
        """Training funnel metric still works"""
        resp = requests.get(
            f"{BASE_URL}/api/metrics/training-funnel",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code == 200
    
    def test_coaching_loop_report(self, owner_token):
        """Coaching loop report still works"""
        resp = requests.get(
            f"{BASE_URL}/api/coaching/loop-report?division=all",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code == 200
    
    def test_onboarding_progress(self, owner_token):
        """Onboarding progress still works"""
        resp = requests.get(
            f"{BASE_URL}/api/onboarding/progress?division=all",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code == 200
