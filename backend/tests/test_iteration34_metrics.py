"""
Iteration 34 Tests - Metric Endpoints and Team Members Individual View
Tests:
1. GET /api/metrics/division-quality-trend - 30d/60d/90d trends
2. GET /api/metrics/standards-compliance - standards array with compliance_pct
3. GET /api/metrics/training-funnel - total_people, attempted_training, passed_training
4. GET /api/metrics/pm-dashboard?division=Maintenance - PM-scoped metrics
5. Team profiles stats endpoint for bottom panel
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

class TestIteration34Metrics:
    """Test new metric endpoints for iteration 34"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login as owner to get token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as owner
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "sadam.owner@slmco.local",
            "password": "SLMCo2026!"
        })
        assert login_resp.status_code == 200, f"Owner login failed: {login_resp.text}"
        self.owner_token = login_resp.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.owner_token}"})
        
    def test_health_check(self):
        """Test backend health"""
        resp = self.session.get(f"{BASE_URL}/api/health")
        assert resp.status_code == 200
        print("✓ Health check passed")
        
    def test_division_quality_trend(self):
        """Test GET /api/metrics/division-quality-trend returns 30d/60d/90d trends"""
        resp = self.session.get(f"{BASE_URL}/api/metrics/division-quality-trend")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        # Verify structure
        assert "trends" in data, "Response should have 'trends' key"
        trends = data["trends"]
        
        # Verify all three periods exist
        assert "30d" in trends, "Should have 30d trend"
        assert "60d" in trends, "Should have 60d trend"
        assert "90d" in trends, "Should have 90d trend"
        
        print(f"✓ Division quality trend: 30d={trends['30d']}, 60d={trends['60d']}, 90d={trends['90d']}")
        
    def test_division_quality_trend_with_filter(self):
        """Test division quality trend with division filter"""
        resp = self.session.get(f"{BASE_URL}/api/metrics/division-quality-trend?division=Maintenance")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "trends" in data
        print(f"✓ Division quality trend (Maintenance filter) returned successfully")
        
    def test_standards_compliance(self):
        """Test GET /api/metrics/standards-compliance returns standards array with compliance_pct"""
        resp = self.session.get(f"{BASE_URL}/api/metrics/standards-compliance")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        # Verify structure
        assert "standards" in data, "Response should have 'standards' key"
        standards = data["standards"]
        assert isinstance(standards, list), "Standards should be a list"
        
        # If there are standards, verify each has required fields
        if len(standards) > 0:
            for s in standards[:3]:  # Check first 3
                assert "standard" in s, "Each standard should have 'standard' field"
                assert "compliance_pct" in s, "Each standard should have 'compliance_pct' field"
                assert "total" in s, "Each standard should have 'total' field"
                assert "passed" in s, "Each standard should have 'passed' field"
            print(f"✓ Standards compliance: {len(standards)} standards returned")
            print(f"  Sample: {standards[0] if standards else 'N/A'}")
        else:
            print("✓ Standards compliance: 0 standards (no training data)")
            
    def test_training_funnel(self):
        """Test GET /api/metrics/training-funnel returns funnel data"""
        resp = self.session.get(f"{BASE_URL}/api/metrics/training-funnel")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        # Verify required fields
        assert "total_people" in data, "Should have total_people"
        assert "attempted_training" in data, "Should have attempted_training"
        assert "passed_training" in data, "Should have passed_training"
        assert "funnel_pct" in data, "Should have funnel_pct"
        
        # Verify funnel_pct structure
        funnel_pct = data["funnel_pct"]
        assert "attempted" in funnel_pct, "funnel_pct should have 'attempted'"
        assert "passed" in funnel_pct, "funnel_pct should have 'passed'"
        
        print(f"✓ Training funnel: total={data['total_people']}, attempted={data['attempted_training']}, passed={data['passed_training']}")
        print(f"  Funnel %: attempted={funnel_pct['attempted']}%, passed={funnel_pct['passed']}%")
        
    def test_pm_dashboard_metrics(self):
        """Test GET /api/metrics/pm-dashboard?division=Maintenance returns PM-scoped metrics"""
        resp = self.session.get(f"{BASE_URL}/api/metrics/pm-dashboard?division=Maintenance")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        # Verify required fields
        assert "division" in data, "Should have division"
        assert data["division"] == "Maintenance", "Division should be Maintenance"
        assert "submissions_30d" in data, "Should have submissions_30d"
        assert "submissions_90d" in data, "Should have submissions_90d"
        assert "avg_score_90d" in data, "Should have avg_score_90d"
        assert "reviews_total" in data, "Should have reviews_total"
        assert "pass_count" in data, "Should have pass_count"
        assert "fail_count" in data, "Should have fail_count"
        assert "crews" in data, "Should have crews"
        assert "training_total" in data, "Should have training_total"
        assert "training_completed" in data, "Should have training_completed"
        
        print(f"✓ PM Dashboard (Maintenance): subs_30d={data['submissions_30d']}, subs_90d={data['submissions_90d']}")
        print(f"  Avg score: {data['avg_score_90d']}, Reviews: {data['reviews_total']}, Pass: {data['pass_count']}, Fail: {data['fail_count']}")
        print(f"  Crews: {data['crews']}, Training: {data['training_completed']}/{data['training_total']}")
        
    def test_pm_dashboard_install_division(self):
        """Test PM dashboard for Install division"""
        resp = self.session.get(f"{BASE_URL}/api/metrics/pm-dashboard?division=Install")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert data["division"] == "Install"
        print(f"✓ PM Dashboard (Install): subs_30d={data['submissions_30d']}, crews={data['crews']}")
        
    def test_pm_dashboard_tree_division(self):
        """Test PM dashboard for Tree division"""
        resp = self.session.get(f"{BASE_URL}/api/metrics/pm-dashboard?division=Tree")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert data["division"] == "Tree"
        print(f"✓ PM Dashboard (Tree): subs_30d={data['submissions_30d']}, crews={data['crews']}")


class TestTeamProfilesStats:
    """Test team profile stats endpoint for bottom panel"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login as owner"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "sadam.owner@slmco.local",
            "password": "SLMCo2026!"
        })
        assert login_resp.status_code == 200
        self.token = login_resp.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
    def test_get_team_profiles(self):
        """Test GET /api/team/profiles returns profiles list"""
        resp = self.session.get(f"{BASE_URL}/api/team/profiles")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        assert "profiles" in data, "Should have profiles key"
        profiles = data["profiles"]
        assert len(profiles) > 0, "Should have at least one profile"
        
        # Check profile structure
        profile = profiles[0]
        assert "profile_id" in profile, "Profile should have profile_id"
        assert "name" in profile, "Profile should have name"
        assert "role" in profile, "Profile should have role"
        
        print(f"✓ Team profiles: {len(profiles)} profiles returned")
        
    def test_profile_stats_endpoint(self):
        """Test GET /api/team/profiles/{profile_id}/stats returns stats"""
        # First get profiles
        profiles_resp = self.session.get(f"{BASE_URL}/api/team/profiles")
        assert profiles_resp.status_code == 200
        profiles = profiles_resp.json()["profiles"]
        
        # Get stats for first crew profile
        crew_profile = None
        for p in profiles:
            if p["profile_id"].startswith("crew_"):
                crew_profile = p
                break
                
        if crew_profile:
            profile_id = crew_profile["profile_id"]
            stats_resp = self.session.get(f"{BASE_URL}/api/team/profiles/{profile_id}/stats?months=3")
            assert stats_resp.status_code == 200, f"Failed: {stats_resp.text}"
            stats = stats_resp.json()
            
            # Verify stats structure
            assert "review_count" in stats, "Should have review_count"
            assert "submission_count" in stats, "Should have submission_count"
            assert "avg_review_score" in stats, "Should have avg_review_score"
            assert "training_completed" in stats, "Should have training_completed"
            assert "training_total" in stats, "Should have training_total"
            
            print(f"✓ Profile stats ({profile_id}): reviews={stats['review_count']}, submissions={stats['submission_count']}")
            print(f"  Avg score: {stats['avg_review_score']}, Training: {stats['training_completed']}/{stats['training_total']}")
        else:
            pytest.skip("No crew profile found")
            
    def test_profile_stats_different_timelines(self):
        """Test profile stats with different timeline values (1, 3, 6, 12, 24 months)"""
        profiles_resp = self.session.get(f"{BASE_URL}/api/team/profiles")
        profiles = profiles_resp.json()["profiles"]
        
        crew_profile = next((p for p in profiles if p["profile_id"].startswith("crew_")), None)
        if not crew_profile:
            pytest.skip("No crew profile found")
            
        profile_id = crew_profile["profile_id"]
        
        for months in [1, 3, 6, 12, 24]:
            resp = self.session.get(f"{BASE_URL}/api/team/profiles/{profile_id}/stats?months={months}")
            assert resp.status_code == 200, f"Failed for {months} months: {resp.text}"
            print(f"✓ Profile stats ({months}mo) returned successfully")


class TestDashboardOverview:
    """Test dashboard overview endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login as owner"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "sadam.owner@slmco.local",
            "password": "SLMCo2026!"
        })
        assert login_resp.status_code == 200
        self.token = login_resp.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
    def test_dashboard_overview(self):
        """Test GET /api/dashboard/overview returns expected structure"""
        resp = self.session.get(f"{BASE_URL}/api/dashboard/overview")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        # Verify structure
        assert "totals" in data, "Should have totals"
        assert "queues" in data, "Should have queues"
        assert "workflow_health" in data, "Should have workflow_health"
        
        totals = data["totals"]
        assert "submissions" in totals
        assert "jobs" in totals
        
        print(f"✓ Dashboard overview: submissions={totals['submissions']}, jobs={totals['jobs']}")
        print(f"  Review velocity: {data['workflow_health']['review_velocity_percent']}%")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
