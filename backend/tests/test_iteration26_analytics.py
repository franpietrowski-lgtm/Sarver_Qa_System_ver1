"""
Iteration 26: Analytics Random Sampling and Variance Drilldown Tests
Tests for:
- GET /api/analytics/random-sample (owner-only, filters, sample size)
- GET /api/analytics/variance-drilldown (owner-only, crew+service_type required)
- Role-based access control (403 for management role)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
OWNER_EMAIL = "sadam.owner@slmco.local"
OWNER_PASSWORD = "SLMCo2026!"
MANAGEMENT_EMAIL = "hjohnny.super@slmco.local"
MANAGEMENT_PASSWORD = "SLMCo2026!"


@pytest.fixture(scope="module")
def owner_token():
    """Get owner authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}
    )
    if response.status_code != 200:
        pytest.skip(f"Owner login failed: {response.status_code} - {response.text}")
    return response.json().get("token")


@pytest.fixture(scope="module")
def management_token():
    """Get management authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": MANAGEMENT_EMAIL, "password": MANAGEMENT_PASSWORD}
    )
    if response.status_code != 200:
        pytest.skip(f"Management login failed: {response.status_code} - {response.text}")
    return response.json().get("token")


class TestRandomSampleEndpoint:
    """Tests for GET /api/analytics/random-sample"""

    def test_random_sample_basic(self, owner_token):
        """Test basic random sample with default parameters"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/random-sample?size=5&period=annual",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "pool_size" in data, "Missing pool_size in response"
        assert "sample_size" in data, "Missing sample_size in response"
        assert "samples" in data, "Missing samples array in response"
        assert "filter_options" in data, "Missing filter_options in response"
        
        # Verify filter_options structure
        filter_options = data["filter_options"]
        assert "crews" in filter_options, "Missing crews in filter_options"
        assert "divisions" in filter_options, "Missing divisions in filter_options"
        assert "service_types" in filter_options, "Missing service_types in filter_options"
        
        # Verify sample_size <= requested size
        assert data["sample_size"] <= 5, f"Sample size {data['sample_size']} exceeds requested 5"
        assert len(data["samples"]) == data["sample_size"], "samples array length doesn't match sample_size"
        
        print(f"✓ Random sample returned pool_size={data['pool_size']}, sample_size={data['sample_size']}")
        print(f"✓ Filter options: {len(filter_options['crews'])} crews, {len(filter_options['divisions'])} divisions, {len(filter_options['service_types'])} service types")

    def test_random_sample_with_crew_filter(self, owner_token):
        """Test random sample filtered by crew"""
        # First get available crews
        response = requests.get(
            f"{BASE_URL}/api/analytics/random-sample?size=5&period=annual",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        crews = data["filter_options"]["crews"]
        if not crews:
            pytest.skip("No crews available for filtering")
        
        test_crew = crews[0]
        
        # Now filter by that crew
        response = requests.get(
            f"{BASE_URL}/api/analytics/random-sample?size=10&period=annual&crew={test_crew}",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        filtered_data = response.json()
        
        # Verify all samples are from the filtered crew
        for sample in filtered_data["samples"]:
            assert sample["crew"] == test_crew, f"Sample crew '{sample['crew']}' doesn't match filter '{test_crew}'"
        
        print(f"✓ Crew filter working: all {len(filtered_data['samples'])} samples from '{test_crew}'")

    def test_random_sample_sample_structure(self, owner_token):
        """Test that sample items have correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/random-sample?size=5&period=annual",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        if not data["samples"]:
            pytest.skip("No samples returned")
        
        sample = data["samples"][0]
        expected_fields = [
            "submission_id", "crew", "division", "service_type", "status",
            "created_at", "image_count", "management_score", "management_rating",
            "management_issues", "owner_score", "owner_training", "variance"
        ]
        
        for field in expected_fields:
            assert field in sample, f"Missing field '{field}' in sample"
        
        print(f"✓ Sample structure verified with all {len(expected_fields)} expected fields")

    def test_random_sample_requires_owner_role(self, management_token):
        """Test that management role gets 403 Forbidden"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/random-sample?size=5&period=annual",
            headers={"Authorization": f"Bearer {management_token}"}
        )
        assert response.status_code == 403, f"Expected 403 for management role, got {response.status_code}"
        print("✓ Management role correctly denied access (403)")

    def test_random_sample_unauthenticated(self):
        """Test that unauthenticated request gets 401"""
        response = requests.get(f"{BASE_URL}/api/analytics/random-sample?size=5&period=annual")
        assert response.status_code == 401, f"Expected 401 for unauthenticated, got {response.status_code}"
        print("✓ Unauthenticated request correctly denied (401)")


class TestVarianceDrilldownEndpoint:
    """Tests for GET /api/analytics/variance-drilldown"""

    def test_variance_drilldown_basic(self, owner_token):
        """Test variance drilldown with valid crew and service_type"""
        # First get available crews and service types from heatmap
        summary_response = requests.get(
            f"{BASE_URL}/api/analytics/summary?period=annual",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert summary_response.status_code == 200
        summary = summary_response.json()
        
        heatmap = summary.get("calibration_heatmap", [])
        if not heatmap:
            pytest.skip("No heatmap data available")
        
        # Use first heatmap entry
        test_crew = heatmap[0]["crew"]
        test_service = heatmap[0]["service_type"]
        
        response = requests.get(
            f"{BASE_URL}/api/analytics/variance-drilldown?crew={test_crew}&service_type={test_service}&period=annual",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert data["crew"] == test_crew, f"Response crew '{data['crew']}' doesn't match request '{test_crew}'"
        assert data["service_type"] == test_service, f"Response service_type doesn't match"
        assert "period" in data, "Missing period in response"
        assert "total_reviewed" in data, "Missing total_reviewed in response"
        assert "rows" in data, "Missing rows array in response"
        
        print(f"✓ Variance drilldown returned {data['total_reviewed']} reviewed submissions for {test_crew}/{test_service}")

    def test_variance_drilldown_row_structure(self, owner_token):
        """Test that drilldown rows have correct structure"""
        # Get heatmap data first
        summary_response = requests.get(
            f"{BASE_URL}/api/analytics/summary?period=annual",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert summary_response.status_code == 200
        heatmap = summary_response.json().get("calibration_heatmap", [])
        
        if not heatmap:
            pytest.skip("No heatmap data available")
        
        test_crew = heatmap[0]["crew"]
        test_service = heatmap[0]["service_type"]
        
        response = requests.get(
            f"{BASE_URL}/api/analytics/variance-drilldown?crew={test_crew}&service_type={test_service}&period=annual",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        if not data["rows"]:
            pytest.skip("No rows returned in drilldown")
        
        row = data["rows"][0]
        expected_fields = [
            "submission_id", "created_at", "status", "management_score",
            "management_rating", "management_issues", "owner_score",
            "owner_training", "variance", "exclusion_reason"
        ]
        
        for field in expected_fields:
            assert field in row, f"Missing field '{field}' in drilldown row"
        
        print(f"✓ Drilldown row structure verified with all {len(expected_fields)} expected fields")

    def test_variance_drilldown_sorted_by_variance(self, owner_token):
        """Test that drilldown rows are sorted by absolute variance (descending)"""
        summary_response = requests.get(
            f"{BASE_URL}/api/analytics/summary?period=annual",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert summary_response.status_code == 200
        heatmap = summary_response.json().get("calibration_heatmap", [])
        
        if not heatmap:
            pytest.skip("No heatmap data available")
        
        test_crew = heatmap[0]["crew"]
        test_service = heatmap[0]["service_type"]
        
        response = requests.get(
            f"{BASE_URL}/api/analytics/variance-drilldown?crew={test_crew}&service_type={test_service}&period=annual",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        rows = data["rows"]
        if len(rows) < 2:
            pytest.skip("Not enough rows to verify sorting")
        
        # Check that rows are sorted by absolute variance descending
        variances = [abs(r["variance"] or 0) for r in rows]
        assert variances == sorted(variances, reverse=True), "Rows not sorted by absolute variance descending"
        
        print(f"✓ Drilldown rows correctly sorted by absolute variance (descending)")

    def test_variance_drilldown_requires_owner_role(self, management_token):
        """Test that management role gets 403 Forbidden"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/variance-drilldown?crew=Test&service_type=Test&period=annual",
            headers={"Authorization": f"Bearer {management_token}"}
        )
        assert response.status_code == 403, f"Expected 403 for management role, got {response.status_code}"
        print("✓ Management role correctly denied access (403)")

    def test_variance_drilldown_requires_crew_param(self, owner_token):
        """Test that missing crew parameter returns 422"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/variance-drilldown?service_type=Test&period=annual",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 422, f"Expected 422 for missing crew, got {response.status_code}"
        print("✓ Missing crew parameter correctly returns 422")

    def test_variance_drilldown_requires_service_type_param(self, owner_token):
        """Test that missing service_type parameter returns 422"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/variance-drilldown?crew=Test&period=annual",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 422, f"Expected 422 for missing service_type, got {response.status_code}"
        print("✓ Missing service_type parameter correctly returns 422")


class TestAnalyticsSummaryEndpoint:
    """Tests for existing analytics summary endpoint (regression)"""

    def test_analytics_summary_has_heatmap(self, owner_token):
        """Test that analytics summary includes calibration_heatmap"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/summary?period=annual",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "calibration_heatmap" in data, "Missing calibration_heatmap in summary"
        assert isinstance(data["calibration_heatmap"], list), "calibration_heatmap should be a list"
        
        if data["calibration_heatmap"]:
            cell = data["calibration_heatmap"][0]
            expected_fields = ["crew", "service_type", "management_average", "owner_average", "variance_average", "sample_count"]
            for field in expected_fields:
                assert field in cell, f"Missing field '{field}' in heatmap cell"
        
        print(f"✓ Analytics summary has calibration_heatmap with {len(data['calibration_heatmap'])} cells")

    def test_analytics_summary_period_options(self, owner_token):
        """Test that different period options work"""
        periods = ["daily", "weekly", "monthly", "quarterly", "annual"]
        
        for period in periods:
            response = requests.get(
                f"{BASE_URL}/api/analytics/summary?period={period}",
                headers={"Authorization": f"Bearer {owner_token}"}
            )
            assert response.status_code == 200, f"Period '{period}' failed: {response.status_code}"
            data = response.json()
            assert data["period"] == period, f"Response period '{data['period']}' doesn't match request '{period}'"
        
        print(f"✓ All {len(periods)} period options work correctly")
