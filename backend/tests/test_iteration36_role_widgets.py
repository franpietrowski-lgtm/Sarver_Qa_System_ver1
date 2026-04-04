"""
Iteration 36 - P1 Role-Specific Widgets & P2 UX Improvements Backend Tests
Tests for:
- PM Dashboard metrics
- Crew Leader Performance
- Account Manager Client Report
- Supervisor Daily Checklist
- Smart Insights
- Crew Sparklines (with division_sparklines)
- Weekly Digest
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
OWNER_EMAIL = "sadam.owner@slmco.local"
PM_MAINTENANCE_EMAIL = "atim.prom@slmco.local"
PM_INSTALL_EMAIL = "ozach.prom@slmco.local"
PASSWORD = "SLMCo2026!"


@pytest.fixture(scope="module")
def owner_token():
    """Get Owner auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": OWNER_EMAIL,
        "password": PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Owner login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def pm_maintenance_token():
    """Get PM (Maintenance) auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": PM_MAINTENANCE_EMAIL,
        "password": PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"PM Maintenance login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def pm_install_token():
    """Get PM (Install) auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": PM_INSTALL_EMAIL,
        "password": PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"PM Install login failed: {response.status_code} - {response.text}")


class TestPMDashboard:
    """PM Dashboard endpoint tests - /api/metrics/pm-dashboard"""

    def test_pm_dashboard_maintenance_division(self, owner_token):
        """GET /api/metrics/pm-dashboard?division=Maintenance returns 200 with expected fields"""
        response = requests.get(
            f"{BASE_URL}/api/metrics/pm-dashboard?division=Maintenance",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify required fields
        assert "submissions_30d" in data, "Missing submissions_30d"
        assert "avg_score_90d" in data, "Missing avg_score_90d"
        assert "pass_count" in data, "Missing pass_count"
        assert "fail_count" in data, "Missing fail_count"
        assert "crews" in data, "Missing crews"
        assert "training_total" in data, "Missing training_total"
        assert "training_completed" in data, "Missing training_completed"
        assert data.get("division") == "Maintenance", f"Expected division=Maintenance, got {data.get('division')}"
        
        # Verify data types
        assert isinstance(data["submissions_30d"], int)
        assert isinstance(data["avg_score_90d"], (int, float))
        assert isinstance(data["pass_count"], int)
        assert isinstance(data["fail_count"], int)
        assert isinstance(data["crews"], int)
        print(f"PM Dashboard Maintenance: {data}")

    def test_pm_dashboard_install_division(self, owner_token):
        """GET /api/metrics/pm-dashboard?division=Install returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/metrics/pm-dashboard?division=Install",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("division") == "Install"
        print(f"PM Dashboard Install: {data}")


class TestCrewLeaderPerformance:
    """Crew Leader Performance endpoint tests - /api/metrics/crew-leader-performance"""

    def test_crew_leader_performance_all_divisions(self, owner_token):
        """GET /api/metrics/crew-leader-performance?division=all returns 200 with leaders array"""
        response = requests.get(
            f"{BASE_URL}/api/metrics/crew-leader-performance?division=all",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify leaders array exists
        assert "leaders" in data, "Missing leaders array"
        assert isinstance(data["leaders"], list), "leaders should be a list"
        
        # Should have 4 crew leaders based on seed data
        leaders = data["leaders"]
        print(f"Crew Leaders count: {len(leaders)}")
        
        # Verify leader structure if any exist
        if len(leaders) > 0:
            leader = leaders[0]
            assert "crew_label" in leader, "Missing crew_label"
            assert "leader_name" in leader, "Missing leader_name"
            assert "division" in leader, "Missing division"
            assert "avg_score" in leader, "Missing avg_score"
            assert "submissions_90d" in leader, "Missing submissions_90d"
            assert "pass_count" in leader, "Missing pass_count"
            assert "fail_count" in leader, "Missing fail_count"
            print(f"First leader: {leader}")

    def test_crew_leader_performance_maintenance_division(self, owner_token):
        """GET /api/metrics/crew-leader-performance?division=Maintenance returns filtered results"""
        response = requests.get(
            f"{BASE_URL}/api/metrics/crew-leader-performance?division=Maintenance",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "leaders" in data
        # All returned leaders should be from Maintenance division
        for leader in data["leaders"]:
            assert leader.get("division") == "Maintenance", f"Expected Maintenance, got {leader.get('division')}"


class TestAccountManagerReport:
    """Account Manager Report endpoint tests - /api/metrics/account-manager-report"""

    def test_account_manager_report(self, owner_token):
        """GET /api/metrics/account-manager-report returns 200 with properties array"""
        response = requests.get(
            f"{BASE_URL}/api/metrics/account-manager-report",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify properties array exists
        assert "properties" in data, "Missing properties array"
        assert isinstance(data["properties"], list), "properties should be a list"
        
        # Verify property structure if any exist
        if len(data["properties"]) > 0:
            prop = data["properties"][0]
            assert "property" in prop, "Missing property name"
            assert "submissions" in prop, "Missing submissions count"
            assert "avg_score" in prop, "Missing avg_score"
            assert "pass_count" in prop, "Missing pass_count"
            assert "fail_count" in prop, "Missing fail_count"
            assert "divisions" in prop, "Missing divisions"
            print(f"First property: {prop}")
        
        print(f"Total properties: {len(data['properties'])}")


class TestSupervisorChecklist:
    """Supervisor Daily Checklist endpoint tests - /api/metrics/supervisor-checklist"""

    def test_supervisor_checklist(self, owner_token):
        """GET /api/metrics/supervisor-checklist returns 200 with expected fields"""
        response = requests.get(
            f"{BASE_URL}/api/metrics/supervisor-checklist",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify required fields
        assert "today_equipment_checks" in data, "Missing today_equipment_checks"
        assert "active_crews" in data, "Missing active_crews"
        assert "red_tags_this_week" in data, "Missing red_tags_this_week"
        
        # Verify data types
        assert isinstance(data["today_equipment_checks"], int)
        assert isinstance(data["active_crews"], int)
        assert isinstance(data["red_tags_this_week"], int)
        
        print(f"Supervisor Checklist: equipment_checks={data['today_equipment_checks']}, active_crews={data['active_crews']}, red_tags={data['red_tags_this_week']}")


class TestSmartInsights:
    """Smart Insights endpoint tests - /api/metrics/smart-insights"""

    def test_smart_insights(self, owner_token):
        """GET /api/metrics/smart-insights returns 200 with insights array"""
        response = requests.get(
            f"{BASE_URL}/api/metrics/smart-insights",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify insights array exists
        assert "insights" in data, "Missing insights array"
        assert isinstance(data["insights"], list), "insights should be a list"
        
        # Verify insight structure if any exist
        if len(data["insights"]) > 0:
            insight = data["insights"][0]
            assert "type" in insight, "Missing insight type"
            assert "message" in insight, "Missing insight message"
            print(f"First insight: {insight}")
        
        print(f"Total insights: {len(data['insights'])}")


class TestCrewSparklines:
    """Crew Sparklines endpoint tests - /api/metrics/crew-sparklines"""

    def test_crew_sparklines_all_divisions(self, owner_token):
        """GET /api/metrics/crew-sparklines?division=all returns 200 with sparklines AND division_sparklines"""
        response = requests.get(
            f"{BASE_URL}/api/metrics/crew-sparklines?division=all",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify sparklines object exists
        assert "sparklines" in data, "Missing sparklines object"
        assert isinstance(data["sparklines"], dict), "sparklines should be a dict"
        
        # Verify division_sparklines object exists (P2 UX improvement)
        assert "division_sparklines" in data, "Missing division_sparklines object"
        assert isinstance(data["division_sparklines"], dict), "division_sparklines should be a dict"
        
        # Verify sparkline structure if any exist
        if len(data["sparklines"]) > 0:
            crew_key = list(data["sparklines"].keys())[0]
            sparkline = data["sparklines"][crew_key]
            assert "months" in sparkline, "Missing months array"
            assert "scores" in sparkline, "Missing scores array"
            assert isinstance(sparkline["months"], list)
            assert isinstance(sparkline["scores"], list)
            print(f"Sparkline for {crew_key}: {sparkline}")
        
        # Verify division_sparklines structure
        if len(data["division_sparklines"]) > 0:
            div_key = list(data["division_sparklines"].keys())[0]
            div_sparkline = data["division_sparklines"][div_key]
            assert "months" in div_sparkline, "Missing months in division_sparklines"
            assert "scores" in div_sparkline, "Missing scores in division_sparklines"
            print(f"Division sparkline for {div_key}: {div_sparkline}")
        
        print(f"Total crew sparklines: {len(data['sparklines'])}, Division sparklines: {len(data['division_sparklines'])}")

    def test_crew_sparklines_maintenance_division(self, owner_token):
        """GET /api/metrics/crew-sparklines?division=Maintenance returns filtered results"""
        response = requests.get(
            f"{BASE_URL}/api/metrics/crew-sparklines?division=Maintenance",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "sparklines" in data
        assert "division_sparklines" in data


class TestWeeklyDigest:
    """Weekly Digest endpoint tests - /api/metrics/weekly-digest"""

    def test_weekly_digest(self, owner_token):
        """GET /api/metrics/weekly-digest returns 200 with top_performers and bottom_performers"""
        response = requests.get(
            f"{BASE_URL}/api/metrics/weekly-digest",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify required arrays exist
        assert "top_performers" in data, "Missing top_performers array"
        assert "bottom_performers" in data, "Missing bottom_performers array"
        assert isinstance(data["top_performers"], list), "top_performers should be a list"
        assert isinstance(data["bottom_performers"], list), "bottom_performers should be a list"
        
        # Verify performer structure if any exist
        if len(data["top_performers"]) > 0:
            performer = data["top_performers"][0]
            assert "crew" in performer, "Missing crew"
            assert "avg_score" in performer, "Missing avg_score"
            assert "submissions" in performer, "Missing submissions"
            print(f"Top performer: {performer}")
        
        if len(data["bottom_performers"]) > 0:
            performer = data["bottom_performers"][0]
            assert "crew" in performer, "Missing crew"
            print(f"Bottom performer: {performer}")
        
        print(f"Top performers: {len(data['top_performers'])}, Bottom performers: {len(data['bottom_performers'])}")


class TestPMAccessWithPMToken:
    """Test PM Dashboard access with actual PM credentials"""

    def test_pm_can_access_pm_dashboard(self, pm_maintenance_token):
        """PM user can access PM Dashboard for their division"""
        response = requests.get(
            f"{BASE_URL}/api/metrics/pm-dashboard?division=Maintenance",
            headers={"Authorization": f"Bearer {pm_maintenance_token}"}
        )
        assert response.status_code == 200, f"PM should access PM Dashboard: {response.status_code}"
        data = response.json()
        assert "submissions_30d" in data
        print(f"PM accessed dashboard: {data}")

    def test_pm_can_access_crew_leader_performance(self, pm_maintenance_token):
        """PM user can access Crew Leader Performance"""
        response = requests.get(
            f"{BASE_URL}/api/metrics/crew-leader-performance?division=Maintenance",
            headers={"Authorization": f"Bearer {pm_maintenance_token}"}
        )
        assert response.status_code == 200, f"PM should access Crew Leader Performance: {response.status_code}"


class TestUnauthorizedAccess:
    """Test that endpoints require authentication"""

    def test_pm_dashboard_requires_auth(self):
        """PM Dashboard requires authentication"""
        response = requests.get(f"{BASE_URL}/api/metrics/pm-dashboard?division=Maintenance")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"

    def test_crew_leader_performance_requires_auth(self):
        """Crew Leader Performance requires authentication"""
        response = requests.get(f"{BASE_URL}/api/metrics/crew-leader-performance?division=all")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"

    def test_account_manager_report_requires_auth(self):
        """Account Manager Report requires authentication"""
        response = requests.get(f"{BASE_URL}/api/metrics/account-manager-report")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"

    def test_supervisor_checklist_requires_auth(self):
        """Supervisor Checklist requires authentication"""
        response = requests.get(f"{BASE_URL}/api/metrics/supervisor-checklist")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"

    def test_smart_insights_requires_auth(self):
        """Smart Insights requires authentication"""
        response = requests.get(f"{BASE_URL}/api/metrics/smart-insights")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"

    def test_crew_sparklines_requires_auth(self):
        """Crew Sparklines requires authentication"""
        response = requests.get(f"{BASE_URL}/api/metrics/crew-sparklines?division=all")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"

    def test_weekly_digest_requires_auth(self):
        """Weekly Digest requires authentication"""
        response = requests.get(f"{BASE_URL}/api/metrics/weekly-digest")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
