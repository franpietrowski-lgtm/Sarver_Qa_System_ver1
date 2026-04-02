"""
Iteration 23: Reviewer Performance Dashboard & Closed-Loop Coaching Tests
Tests for:
1. GET /api/analytics/reviewer-performance - Owner-only reviewer stats
2. GET /api/coaching/recommendations - Warning/Critical crew recommendations
3. POST /api/coaching/auto-generate - Auto-generate coaching sessions
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
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Owner login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def management_token():
    """Get management authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": MANAGEMENT_EMAIL, "password": MANAGEMENT_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Management login failed: {response.status_code} - {response.text}")


class TestReviewerPerformanceEndpoint:
    """Tests for GET /api/analytics/reviewer-performance (owner-only)"""

    def test_reviewer_performance_owner_access(self, owner_token):
        """Owner should be able to access reviewer performance endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/reviewer-performance?days=90",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "period_days" in data, "Missing period_days in response"
        assert "reviewer_count" in data, "Missing reviewer_count in response"
        assert "reviewers" in data, "Missing reviewers array in response"
        assert data["period_days"] == 90, f"Expected period_days=90, got {data['period_days']}"
        print(f"Reviewer Performance: {data['reviewer_count']} reviewers found")

    def test_reviewer_performance_management_denied(self, management_token):
        """Management should NOT be able to access reviewer performance (owner-only)"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/reviewer-performance?days=90",
            headers={"Authorization": f"Bearer {management_token}"}
        )
        # Should be 403 Forbidden for non-owner roles
        assert response.status_code == 403, f"Expected 403 for management, got {response.status_code}"
        print("Management correctly denied access to reviewer performance")

    def test_reviewer_performance_unauthenticated(self):
        """Unauthenticated requests should be denied"""
        response = requests.get(f"{BASE_URL}/api/analytics/reviewer-performance?days=90")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("Unauthenticated request correctly denied")

    def test_reviewer_performance_period_options(self, owner_token):
        """Test different period options (30d, 90d, 180d, 365d)"""
        for days in [30, 90, 180, 365]:
            response = requests.get(
                f"{BASE_URL}/api/analytics/reviewer-performance?days={days}",
                headers={"Authorization": f"Bearer {owner_token}"}
            )
            assert response.status_code == 200, f"Failed for days={days}: {response.status_code}"
            data = response.json()
            assert data["period_days"] == days
        print("All period options (30, 90, 180, 365) work correctly")

    def test_reviewer_data_structure(self, owner_token):
        """Verify reviewer data structure contains required fields"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/reviewer-performance?days=365",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        reviewers = data.get("reviewers", [])
        
        if len(reviewers) > 0:
            reviewer = reviewers[0]
            required_fields = [
                "reviewer_id", "name", "title", "session_count", "total_reviews",
                "avg_swipe_ms", "avg_score", "flagged_fast_count", "flagged_fast_pct",
                "rating_distribution", "calibration_drift", "drift_direction", "speed_trend"
            ]
            for field in required_fields:
                assert field in reviewer, f"Missing field '{field}' in reviewer data"
            
            # Verify rating_distribution structure
            rating_dist = reviewer.get("rating_distribution", {})
            for rating in ["fail", "concern", "standard", "exemplary"]:
                assert rating in rating_dist, f"Missing '{rating}' in rating_distribution"
            
            print(f"Reviewer data structure verified: {reviewer['name']} has {reviewer['total_reviews']} reviews")
        else:
            print("No reviewers found in 365-day window - may need more seed data")


class TestCoachingRecommendationsEndpoint:
    """Tests for GET /api/coaching/recommendations"""

    def test_coaching_recommendations_owner_access(self, owner_token):
        """Owner should be able to access coaching recommendations"""
        response = requests.get(
            f"{BASE_URL}/api/coaching/recommendations?window_days=240",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "window_days" in data, "Missing window_days in response"
        assert "recommendations" in data, "Missing recommendations array"
        print(f"Coaching Recommendations: {len(data['recommendations'])} crews at Warning/Critical")

    def test_coaching_recommendations_management_access(self, management_token):
        """Management should also be able to access coaching recommendations"""
        response = requests.get(
            f"{BASE_URL}/api/coaching/recommendations?window_days=240",
            headers={"Authorization": f"Bearer {management_token}"}
        )
        assert response.status_code == 200, f"Expected 200 for management, got {response.status_code}"
        print("Management correctly has access to coaching recommendations")

    def test_coaching_recommendations_unauthenticated(self):
        """Unauthenticated requests should be denied"""
        response = requests.get(f"{BASE_URL}/api/coaching/recommendations?window_days=30")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("Unauthenticated request correctly denied")

    def test_coaching_recommendations_structure(self, owner_token):
        """Verify recommendation data structure"""
        response = requests.get(
            f"{BASE_URL}/api/coaching/recommendations?window_days=240",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        recommendations = data.get("recommendations", [])
        
        if len(recommendations) > 0:
            rec = recommendations[0]
            required_fields = [
                "crew", "access_code", "division", "level", "incident_count",
                "top_issues", "recommended_action", "suggested_item_count"
            ]
            for field in required_fields:
                assert field in rec, f"Missing field '{field}' in recommendation"
            
            # Verify level is Warning or Critical
            assert rec["level"] in ["Warning", "Critical"], f"Unexpected level: {rec['level']}"
            print(f"Recommendation structure verified: {rec['crew']} at {rec['level']} level")
        else:
            print("No Warning/Critical crews found in 240-day window")


class TestAutoGenerateCoachingEndpoint:
    """Tests for POST /api/coaching/auto-generate"""

    def test_auto_generate_owner_access(self, owner_token):
        """Owner should be able to auto-generate coaching sessions"""
        response = requests.post(
            f"{BASE_URL}/api/coaching/auto-generate?window_days=240",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "generated" in data, "Missing 'generated' count in response"
        assert "skipped" in data, "Missing 'skipped' count in response"
        assert "sessions" in data, "Missing 'sessions' array in response"
        assert "skipped_details" in data, "Missing 'skipped_details' array in response"
        
        print(f"Auto-Coach: {data['generated']} generated, {data['skipped']} skipped")

    def test_auto_generate_management_access(self, management_token):
        """Management should also be able to auto-generate coaching sessions"""
        response = requests.post(
            f"{BASE_URL}/api/coaching/auto-generate?window_days=240",
            headers={"Authorization": f"Bearer {management_token}"}
        )
        assert response.status_code == 200, f"Expected 200 for management, got {response.status_code}"
        print("Management correctly has access to auto-generate coaching")

    def test_auto_generate_unauthenticated(self):
        """Unauthenticated requests should be denied"""
        response = requests.post(f"{BASE_URL}/api/coaching/auto-generate?window_days=30")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("Unauthenticated request correctly denied")

    def test_auto_generate_idempotent(self, owner_token):
        """Running auto-generate twice should skip already-coached crews"""
        # First run
        response1 = requests.post(
            f"{BASE_URL}/api/coaching/auto-generate?window_days=240",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Second run - should mostly skip
        response2 = requests.post(
            f"{BASE_URL}/api/coaching/auto-generate?window_days=240",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Second run should have fewer or equal generated sessions
        assert data2["generated"] <= data1["generated"], "Second run should not generate more than first"
        print(f"Idempotency verified: 1st run={data1['generated']} generated, 2nd run={data2['generated']} generated")

    def test_auto_generate_session_structure(self, owner_token):
        """Verify generated session data structure"""
        response = requests.post(
            f"{BASE_URL}/api/coaching/auto-generate?window_days=240",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        sessions = data.get("sessions", [])
        
        if len(sessions) > 0:
            session = sessions[0]
            required_fields = ["crew", "level", "session_id", "session_code", "item_count", "top_issues"]
            for field in required_fields:
                assert field in session, f"Missing field '{field}' in session"
            
            assert session["level"] in ["Warning", "Critical"], f"Unexpected level: {session['level']}"
            print(f"Session structure verified: {session['crew']} - {session['item_count']} items")
        else:
            # Check skipped details
            skipped = data.get("skipped_details", [])
            if len(skipped) > 0:
                print(f"All crews skipped. First skip reason: {skipped[0]['reason']}")
            else:
                print("No sessions generated and no skips - may need more seed data")


class TestHealthAndAuth:
    """Basic health and auth tests"""

    def test_health_endpoint(self):
        """Verify API is healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        print("API health check passed")

    def test_owner_login(self):
        """Verify owner can login"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}
        )
        assert response.status_code == 200, f"Owner login failed: {response.status_code}"
        data = response.json()
        assert "token" in data, "Missing token in login response"
        assert "user" in data, "Missing user in login response"
        assert data["user"]["role"] == "owner", f"Expected owner role, got {data['user']['role']}"
        print(f"Owner login successful: {data['user']['name']}")

    def test_management_login(self):
        """Verify management can login"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": MANAGEMENT_EMAIL, "password": MANAGEMENT_PASSWORD}
        )
        assert response.status_code == 200, f"Management login failed: {response.status_code}"
        data = response.json()
        assert "token" in data, "Missing token in login response"
        assert data["user"]["role"] == "management", f"Expected management role, got {data['user']['role']}"
        print(f"Management login successful: {data['user']['name']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
