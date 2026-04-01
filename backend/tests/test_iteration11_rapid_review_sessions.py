"""
Iteration 11 Tests: Rapid Review Sessions, Flagged Reviews, Rescore, and Rubric Editor
Tests the new rapid review session tracking, flagged reviews endpoint, rescore functionality,
and rubric editor CRUD operations.
"""
import os
import pytest
import requests
import time

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
GM_EMAIL = "gm@fieldquality.local"
GM_PASSWORD = "FieldQA123!"
OWNER_EMAIL = "owner@fieldquality.local"
OWNER_PASSWORD = "FieldQA123!"
SUPERVISOR_EMAIL = "supervisor@fieldquality.local"
SUPERVISOR_PASSWORD = "FieldQA123!"


@pytest.fixture(scope="module")
def gm_token():
    """Get GM authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": GM_EMAIL,
        "password": GM_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("GM authentication failed")


@pytest.fixture(scope="module")
def owner_token():
    """Get Owner authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": OWNER_EMAIL,
        "password": OWNER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Owner authentication failed")


@pytest.fixture(scope="module")
def supervisor_token():
    """Get Supervisor authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": SUPERVISOR_EMAIL,
        "password": SUPERVISOR_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Supervisor authentication failed")


def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


class TestRapidReviewSessions:
    """Tests for rapid review session tracking endpoints"""
    
    session_id = None
    
    def test_create_rapid_review_session(self, gm_token):
        """POST /api/rapid-review-sessions creates session with session_id"""
        response = requests.post(
            f"{BASE_URL}/api/rapid-review-sessions",
            headers=auth_headers(gm_token),
            json={"total_queue_size": 10, "entry_mode": "mobile"}
        )
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        assert "session" in data
        assert "id" in data["session"]
        assert data["session"]["id"].startswith("rrs_")
        assert data["session"]["total_queue_size"] == 10
        assert data["session"]["entry_mode"] == "mobile"
        assert data["session"]["session_status"] == "active"
        TestRapidReviewSessions.session_id = data["session"]["id"]
        print(f"Created session: {TestRapidReviewSessions.session_id}")
    
    def test_create_session_owner_can_create(self, owner_token):
        """Owner can also create rapid review sessions"""
        response = requests.post(
            f"{BASE_URL}/api/rapid-review-sessions",
            headers=auth_headers(owner_token),
            json={"total_queue_size": 5, "entry_mode": "desktop"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["session"]["entry_mode"] == "desktop"
        print("Owner created session successfully")
    
    def test_complete_rapid_review_session(self, gm_token):
        """POST /api/rapid-review-sessions/{id}/complete ends session"""
        if not TestRapidReviewSessions.session_id:
            pytest.skip("No session_id from previous test")
        
        response = requests.post(
            f"{BASE_URL}/api/rapid-review-sessions/{TestRapidReviewSessions.session_id}/complete",
            headers=auth_headers(gm_token),
            json={"session_id": TestRapidReviewSessions.session_id, "exit_reason": "completed"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["ok"] is True
        assert data["session_id"] == TestRapidReviewSessions.session_id
        print(f"Session completed: {data}")
    
    def test_get_rapid_review_sessions_paginated(self, gm_token):
        """GET /api/rapid-review-sessions returns paginated session logs"""
        response = requests.get(
            f"{BASE_URL}/api/rapid-review-sessions?page=1&limit=10",
            headers=auth_headers(gm_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data
        assert "total" in data["pagination"]
        assert isinstance(data["items"], list)
        print(f"Retrieved {len(data['items'])} sessions, total: {data['pagination']['total']}")


class TestFlaggedReviews:
    """Tests for flagged rapid reviews endpoint"""
    
    def test_get_flagged_reviews_concern(self, gm_token):
        """GET /api/rapid-reviews/flagged?flag_type=concern returns concern-flagged reviews"""
        response = requests.get(
            f"{BASE_URL}/api/rapid-reviews/flagged?flag_type=concern&page=1&limit=10",
            headers=auth_headers(gm_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data
        print(f"Concern-flagged reviews: {data['pagination']['total']}")
    
    def test_get_flagged_reviews_fast(self, gm_token):
        """GET /api/rapid-reviews/flagged?flag_type=fast returns fast-flagged reviews"""
        response = requests.get(
            f"{BASE_URL}/api/rapid-reviews/flagged?flag_type=fast&page=1&limit=10",
            headers=auth_headers(gm_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data
        print(f"Fast-flagged reviews: {data['pagination']['total']}")
    
    def test_get_flagged_reviews_all(self, gm_token):
        """GET /api/rapid-reviews/flagged?flag_type=all returns all flagged reviews"""
        response = requests.get(
            f"{BASE_URL}/api/rapid-reviews/flagged?flag_type=all&page=1&limit=10",
            headers=auth_headers(gm_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data
        print(f"All flagged reviews: {data['pagination']['total']}")


class TestRapidReviewWithSessionTracking:
    """Tests for rapid review POST with session tracking fields"""
    
    def test_rapid_review_accepts_swipe_duration_and_session_id(self, gm_token):
        """POST /api/rapid-reviews accepts swipe_duration_ms and session_id"""
        # First get a submission from the queue
        queue_response = requests.get(
            f"{BASE_URL}/api/rapid-reviews/queue?page=1&limit=1",
            headers=auth_headers(gm_token)
        )
        if queue_response.status_code != 200 or not queue_response.json().get("items"):
            pytest.skip("No submissions in rapid review queue")
        
        submission_id = queue_response.json()["items"][0]["id"]
        
        # Create a session first
        session_response = requests.post(
            f"{BASE_URL}/api/rapid-review-sessions",
            headers=auth_headers(gm_token),
            json={"total_queue_size": 1, "entry_mode": "mobile"}
        )
        session_id = session_response.json()["session"]["id"]
        
        # Submit rapid review with session tracking
        response = requests.post(
            f"{BASE_URL}/api/rapid-reviews",
            headers=auth_headers(gm_token),
            json={
                "submission_id": submission_id,
                "overall_rating": "standard",
                "comment": "",
                "issue_tag": "",
                "annotation_count": 0,
                "entry_mode": "mobile",
                "swipe_duration_ms": 5000,
                "session_id": session_id
            }
        )
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        assert "rapid_review" in data
        print(f"Rapid review submitted with session tracking: {data['rapid_review'].get('id', 'N/A')}")


class TestRescoreFlaggedReviews:
    """Tests for rescoring concern-flagged reviews"""
    
    def test_rescore_endpoint_exists(self, gm_token):
        """PATCH /api/rapid-reviews/{id}/rescore endpoint exists"""
        # Try with a fake ID to verify endpoint exists
        response = requests.patch(
            f"{BASE_URL}/api/rapid-reviews/fake_id_12345/rescore",
            headers=auth_headers(gm_token),
            json={
                "submission_id": "test",
                "overall_rating": "standard",
                "comment": "Rescored"
            }
        )
        # Should return 404 for non-existent review, not 405 (method not allowed)
        assert response.status_code == 404, f"Expected 404 for non-existent review, got {response.status_code}"
        print("Rescore endpoint exists and returns 404 for non-existent review")


class TestRubricEditorCRUD:
    """Tests for rubric editor CRUD operations (GM/Owner only)"""
    
    test_rubric_id = None
    
    def test_get_rubrics_with_inactive(self, gm_token):
        """GET /api/rubric-matrices?include_inactive=true returns all rubrics"""
        response = requests.get(
            f"{BASE_URL}/api/rubric-matrices?division=all&include_inactive=true",
            headers=auth_headers(gm_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Retrieved {len(data)} rubrics (including inactive)")
    
    def test_create_rubric_gm(self, gm_token):
        """POST /api/rubric-matrices - GM can create rubric"""
        response = requests.post(
            f"{BASE_URL}/api/rubric-matrices",
            headers=auth_headers(gm_token),
            json={
                "service_type": "TEST_iter11_service",
                "division": "Maintenance",
                "title": "TEST Iteration 11 Rubric",
                "min_photos": 3,
                "pass_threshold": 80,
                "hard_fail_conditions": [],
                "categories": [
                    {"key": "quality", "label": "Quality", "weight": 0.5, "max_score": 5},
                    {"key": "safety", "label": "Safety", "weight": 0.5, "max_score": 5}
                ]
            }
        )
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data
        TestRubricEditorCRUD.test_rubric_id = data["id"]
        print(f"Created rubric: {TestRubricEditorCRUD.test_rubric_id}")
    
    def test_update_rubric_gm(self, gm_token):
        """PATCH /api/rubric-matrices/{id} - GM can update rubric"""
        if not TestRubricEditorCRUD.test_rubric_id:
            pytest.skip("No test rubric created")
        
        response = requests.patch(
            f"{BASE_URL}/api/rubric-matrices/{TestRubricEditorCRUD.test_rubric_id}",
            headers=auth_headers(gm_token),
            json={
                "title": "TEST Iteration 11 Rubric UPDATED",
                "pass_threshold": 85
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["title"] == "TEST Iteration 11 Rubric UPDATED"
        assert data["pass_threshold"] == 85
        print("Rubric updated successfully")
    
    def test_deactivate_rubric_gm(self, gm_token):
        """PATCH /api/rubric-matrices/{id} - GM can deactivate rubric"""
        if not TestRubricEditorCRUD.test_rubric_id:
            pytest.skip("No test rubric created")
        
        response = requests.patch(
            f"{BASE_URL}/api/rubric-matrices/{TestRubricEditorCRUD.test_rubric_id}",
            headers=auth_headers(gm_token),
            json={"is_active": False}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
        print("Rubric deactivated successfully")
    
    def test_reactivate_rubric_gm(self, gm_token):
        """PATCH /api/rubric-matrices/{id} - GM can reactivate rubric"""
        if not TestRubricEditorCRUD.test_rubric_id:
            pytest.skip("No test rubric created")
        
        response = requests.patch(
            f"{BASE_URL}/api/rubric-matrices/{TestRubricEditorCRUD.test_rubric_id}",
            headers=auth_headers(gm_token),
            json={"is_active": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True
        print("Rubric reactivated successfully")
    
    def test_supervisor_cannot_create_rubric(self, supervisor_token):
        """POST /api/rubric-matrices - Supervisor cannot create rubric (403)"""
        response = requests.post(
            f"{BASE_URL}/api/rubric-matrices",
            headers=auth_headers(supervisor_token),
            json={
                "service_type": "TEST_supervisor_blocked",
                "division": "Maintenance",
                "title": "Should Not Create",
                "min_photos": 3,
                "pass_threshold": 80,
                "hard_fail_conditions": [],
                "categories": [
                    {"key": "test", "label": "Test", "weight": 1.0, "max_score": 5}
                ]
            }
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("Supervisor correctly denied rubric creation")
    
    def test_supervisor_cannot_update_rubric(self, supervisor_token):
        """PATCH /api/rubric-matrices/{id} - Supervisor cannot update rubric (403)"""
        if not TestRubricEditorCRUD.test_rubric_id:
            pytest.skip("No test rubric created")
        
        response = requests.patch(
            f"{BASE_URL}/api/rubric-matrices/{TestRubricEditorCRUD.test_rubric_id}",
            headers=auth_headers(supervisor_token),
            json={"title": "Supervisor Should Not Update"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("Supervisor correctly denied rubric update")
    
    def test_cleanup_test_rubric(self, gm_token):
        """Cleanup: Deactivate test rubric"""
        if not TestRubricEditorCRUD.test_rubric_id:
            pytest.skip("No test rubric to cleanup")
        
        response = requests.patch(
            f"{BASE_URL}/api/rubric-matrices/{TestRubricEditorCRUD.test_rubric_id}",
            headers=auth_headers(gm_token),
            json={"is_active": False}
        )
        assert response.status_code == 200
        print(f"Cleaned up test rubric: {TestRubricEditorCRUD.test_rubric_id}")


class TestDashboardOverviewEndpoint:
    """Tests for dashboard overview endpoint"""
    
    def test_dashboard_overview_loads(self, gm_token):
        """GET /api/dashboard/overview returns overview data"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/overview",
            headers=auth_headers(gm_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert "totals" in data
        assert "queues" in data
        assert "workflow_health" in data
        print(f"Dashboard overview loaded: {data['totals']}")


class TestRubricMatricesEndpoint:
    """Tests for rubric matrices endpoint used by Quick Matrix Ref"""
    
    def test_get_rubric_matrices_all(self, gm_token):
        """GET /api/rubric-matrices?division=all returns all active rubrics"""
        response = requests.get(
            f"{BASE_URL}/api/rubric-matrices?division=all",
            headers=auth_headers(gm_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Retrieved {len(data)} active rubrics")
    
    def test_get_rubric_matrices_by_division(self, gm_token):
        """GET /api/rubric-matrices?division=Maintenance filters by division"""
        response = requests.get(
            f"{BASE_URL}/api/rubric-matrices?division=Maintenance",
            headers=auth_headers(gm_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All returned rubrics should be Maintenance division
        for rubric in data:
            assert rubric.get("division") == "Maintenance" or rubric.get("division") is None
        print(f"Retrieved {len(data)} Maintenance rubrics")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
