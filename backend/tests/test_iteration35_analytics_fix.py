"""
Iteration 35 Tests - Analytics 500 Error Fix & Metric Widgets
Tests the fix for KeyError: 'total_score' in analytics.py
The fix uses .get() with fallback to handle both 'total_score' and 'overall_score' field names
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


@pytest.fixture(scope="module")
def owner_session():
    """Get auth token for owner user - shared across all tests in module"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    # Login as owner
    login_response = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": "sadam.owner@slmco.local",
        "password": "SLMCo2026!"
    })
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    token = login_response.json().get("token")  # API returns 'token' not 'access_token'
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session


class TestAnalyticsFix:
    """Test analytics endpoints that were returning 500 errors due to KeyError: 'total_score'"""
    
    def test_analytics_summary_returns_200(self, owner_session):
        """GET /api/analytics/summary should return 200 with calibration_heatmap, average_score_by_crew"""
        response = owner_session.get(f"{BASE_URL}/api/analytics/summary")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify expected fields exist
        assert "calibration_heatmap" in data, "Missing calibration_heatmap field"
        assert "average_score_by_crew" in data, "Missing average_score_by_crew field"
        assert "period" in data, "Missing period field"
        assert "period_label" in data, "Missing period_label field"
        assert "score_variance_average" in data, "Missing score_variance_average field"
        assert "fail_reason_frequency" in data, "Missing fail_reason_frequency field"
        assert "submission_volume_trends" in data, "Missing submission_volume_trends field"
        assert "training_approved_count" in data, "Missing training_approved_count field"
        
        # Verify calibration_heatmap structure if data exists
        if data["calibration_heatmap"]:
            heatmap_item = data["calibration_heatmap"][0]
            assert "crew" in heatmap_item
            assert "service_type" in heatmap_item
            assert "management_average" in heatmap_item
            assert "owner_average" in heatmap_item
            assert "variance_average" in heatmap_item
            assert "sample_count" in heatmap_item
    
    def test_analytics_summary_with_period_params(self, owner_session):
        """Test analytics summary with different period parameters"""
        for period in ["daily", "weekly", "monthly", "quarterly"]:
            response = owner_session.get(f"{BASE_URL}/api/analytics/summary?period={period}")
            assert response.status_code == 200, f"Failed for period={period}: {response.text}"
            data = response.json()
            assert data["period"] == period
    
    def test_analytics_random_sample_returns_200(self, owner_session):
        """GET /api/analytics/random-sample should return 200 with samples array"""
        response = owner_session.get(f"{BASE_URL}/api/analytics/random-sample")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify expected fields exist
        assert "pool_size" in data, "Missing pool_size field"
        assert "sample_size" in data, "Missing sample_size field"
        assert "samples" in data, "Missing samples array"
        assert "filter_options" in data, "Missing filter_options field"
        
        # Verify samples structure if data exists
        if data["samples"]:
            sample = data["samples"][0]
            assert "submission_id" in sample
            assert "crew" in sample
            assert "service_type" in sample
            assert "status" in sample
            # These fields should be present (may be None if no review)
            assert "management_score" in sample
            assert "owner_score" in sample
    
    def test_analytics_random_sample_with_filters(self, owner_session):
        """Test random sample with filter parameters"""
        response = owner_session.get(f"{BASE_URL}/api/analytics/random-sample?size=5")
        assert response.status_code == 200
        data = response.json()
        assert data["sample_size"] <= 5
    
    def test_analytics_variance_drilldown_returns_200(self, owner_session):
        """GET /api/analytics/variance-drilldown should return 200 when given crew and service_type params"""
        # First get a valid crew and service_type from summary
        summary_response = owner_session.get(f"{BASE_URL}/api/analytics/summary")
        assert summary_response.status_code == 200
        summary_data = summary_response.json()
        
        # Use a crew from the heatmap if available, otherwise use test values
        if summary_data["calibration_heatmap"]:
            crew = summary_data["calibration_heatmap"][0]["crew"]
            service_type = summary_data["calibration_heatmap"][0]["service_type"]
        else:
            crew = "Maintenance Alpha"
            service_type = "Mowing"
        
        response = owner_session.get(
            f"{BASE_URL}/api/analytics/variance-drilldown",
            params={"crew": crew, "service_type": service_type}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "crew" in data
        assert "service_type" in data
        assert "period" in data
        assert "total_reviewed" in data
        assert "rows" in data
        
        # Verify rows structure if data exists
        if data["rows"]:
            row = data["rows"][0]
            assert "submission_id" in row
            assert "management_score" in row
            assert "owner_score" in row
            assert "variance" in row


class TestMetricEndpoints:
    """Test the metric endpoints used by Overview page widgets"""
    
    def test_division_quality_trend_returns_200(self, owner_session):
        """GET /api/metrics/division-quality-trend returns 200"""
        response = owner_session.get(f"{BASE_URL}/api/metrics/division-quality-trend")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "trends" in data
        # Should have 30d, 60d, 90d keys
        assert "30d" in data["trends"]
        assert "60d" in data["trends"]
        assert "90d" in data["trends"]
    
    def test_standards_compliance_returns_200(self, owner_session):
        """GET /api/metrics/standards-compliance returns 200"""
        response = owner_session.get(f"{BASE_URL}/api/metrics/standards-compliance")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "standards" in data
        
        # Verify standards structure if data exists
        if data["standards"]:
            standard = data["standards"][0]
            assert "standard" in standard
            assert "total" in standard
            assert "passed" in standard
            assert "compliance_pct" in standard
    
    def test_training_funnel_returns_200(self, owner_session):
        """GET /api/metrics/training-funnel returns 200"""
        response = owner_session.get(f"{BASE_URL}/api/metrics/training-funnel")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "total_people" in data
        assert "total_crews" in data
        assert "total_members" in data
        assert "attempted_training" in data
        assert "passed_training" in data
        assert "funnel_pct" in data
        
        # Verify funnel_pct structure
        assert "attempted" in data["funnel_pct"]
        assert "passed" in data["funnel_pct"]


class TestDashboardOverview:
    """Test dashboard overview endpoint"""
    
    def test_dashboard_overview_returns_200(self, owner_session):
        """GET /api/dashboard/overview returns 200"""
        response = owner_session.get(f"{BASE_URL}/api/dashboard/overview")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "totals" in data
        assert "queues" in data
        assert "workflow_health" in data
