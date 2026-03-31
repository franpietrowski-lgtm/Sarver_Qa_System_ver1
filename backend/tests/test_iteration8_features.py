"""
Iteration 8 Backend Tests
Tests for: Standards Library, Repeat Offenders, Training Sessions, Public Training endpoints
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
OWNER_EMAIL = "owner@fieldquality.local"
OWNER_PASSWORD = "FieldQA123!"
PM_EMAIL = "production.manager@fieldquality.local"
PM_PASSWORD = "FieldQA123!"


@pytest.fixture(scope="module")
def owner_token():
    """Get owner authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": OWNER_EMAIL,
        "password": OWNER_PASSWORD
    })
    assert response.status_code == 200, f"Owner login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def pm_token():
    """Get production manager authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": PM_EMAIL,
        "password": PM_PASSWORD
    })
    assert response.status_code == 200, f"PM login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def auth_headers_owner(owner_token):
    return {"Authorization": f"Bearer {owner_token}"}


@pytest.fixture(scope="module")
def auth_headers_pm(pm_token):
    return {"Authorization": f"Bearer {pm_token}"}


# ============ Standards Library Tests ============

class TestStandardsLibrary:
    """Standards Library CRUD and filtering tests"""

    def test_get_standards_returns_200_owner(self, auth_headers_owner):
        """GET /api/standards returns 200 for owner"""
        response = requests.get(f"{BASE_URL}/api/standards", headers=auth_headers_owner)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data
        print(f"Standards count: {data['pagination']['total']}")

    def test_get_standards_returns_200_pm(self, auth_headers_pm):
        """GET /api/standards returns 200 for production manager"""
        response = requests.get(f"{BASE_URL}/api/standards", headers=auth_headers_pm)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        print(f"PM can access standards: {len(data['items'])} items")

    def test_get_standards_with_category_filter(self, auth_headers_owner):
        """GET /api/standards with category filter"""
        response = requests.get(f"{BASE_URL}/api/standards?category=Edging", headers=auth_headers_owner)
        assert response.status_code == 200
        data = response.json()
        # All returned items should have Edging category
        for item in data["items"]:
            assert item["category"] == "Edging", f"Expected Edging, got {item['category']}"
        print(f"Edging standards: {len(data['items'])}")

    def test_get_standards_with_division_filter(self, auth_headers_owner):
        """GET /api/standards with division filter"""
        response = requests.get(f"{BASE_URL}/api/standards?division=Maintenance", headers=auth_headers_owner)
        assert response.status_code == 200
        data = response.json()
        print(f"Maintenance division standards: {len(data['items'])}")

    def test_get_standards_with_search(self, auth_headers_owner):
        """GET /api/standards with search query"""
        response = requests.get(f"{BASE_URL}/api/standards?search=edge", headers=auth_headers_owner)
        assert response.status_code == 200
        data = response.json()
        print(f"Search 'edge' results: {len(data['items'])}")

    def test_create_standard_returns_201(self, auth_headers_owner):
        """POST /api/standards creates a new standard"""
        payload = {
            "title": "TEST_Standard for iteration 8",
            "category": "Cleanup",
            "audience": "crew",
            "division_targets": ["Maintenance"],
            "checklist": ["Check item 1", "Check item 2"],
            "notes": "Test notes for crew",
            "owner_notes": "Test owner notes",
            "shoutout": "@TestCrew",
            "image_url": "https://example.com/test-image.jpg",
            "training_enabled": True,
            "question_type": "multiple_choice",
            "question_prompt": "What is the correct answer?",
            "choice_options": ["Option A", "Option B", "Option C"],
            "correct_answer": "Option A",
            "is_active": True
        }
        response = requests.post(f"{BASE_URL}/api/standards", json=payload, headers=auth_headers_owner)
        assert response.status_code in [200, 201], f"Create standard failed: {response.text}"
        data = response.json()
        assert data["title"] == payload["title"]
        assert data["category"] == payload["category"]
        assert "id" in data
        print(f"Created standard: {data['id']}")
        return data["id"]

    def test_update_standard_returns_200(self, auth_headers_owner):
        """PATCH /api/standards/{id} updates a standard"""
        # First create a standard to update
        create_payload = {
            "title": "TEST_Standard to update",
            "category": "Mulch",
            "audience": "crew",
            "division_targets": [],
            "checklist": [],
            "notes": "Original notes",
            "owner_notes": "",
            "shoutout": "",
            "image_url": "https://example.com/original.jpg",
            "training_enabled": True,
            "question_type": "free_text",
            "question_prompt": "Original prompt",
            "choice_options": [],
            "correct_answer": "original",
            "is_active": True
        }
        create_response = requests.post(f"{BASE_URL}/api/standards", json=create_payload, headers=auth_headers_owner)
        assert create_response.status_code in [200, 201]
        standard_id = create_response.json()["id"]

        # Update the standard - PATCH requires all fields per the API schema
        update_payload = {
            "title": "TEST_Standard updated",
            "category": "Mulch",
            "audience": "crew",
            "division_targets": [],
            "checklist": [],
            "notes": "Updated notes",
            "owner_notes": "",
            "shoutout": "",
            "image_url": "https://example.com/original.jpg",
            "training_enabled": True,
            "question_type": "free_text",
            "question_prompt": "Original prompt",
            "choice_options": [],
            "correct_answer": "original",
            "is_active": True
        }
        update_response = requests.patch(f"{BASE_URL}/api/standards/{standard_id}", json=update_payload, headers=auth_headers_owner)
        assert update_response.status_code == 200, f"Update failed: {update_response.text}"
        data = update_response.json()
        assert data["title"] == "TEST_Standard updated"
        assert data["notes"] == "Updated notes"
        print(f"Updated standard: {standard_id}")


# ============ Repeat Offenders Tests ============

class TestRepeatOffenders:
    """Repeat Offenders tracking tests"""

    def test_get_repeat_offenders_returns_200_owner(self, auth_headers_owner):
        """GET /api/repeat-offenders returns 200 for owner"""
        response = requests.get(f"{BASE_URL}/api/repeat-offenders?window_days=30", headers=auth_headers_owner)
        assert response.status_code == 200
        data = response.json()
        assert "window_days" in data
        assert "thresholds" in data
        assert "crew_summaries" in data
        assert "heatmap" in data
        print(f"Repeat offenders: {len(data['crew_summaries'])} crews, {len(data['heatmap'])} heatmap cells")

    def test_get_repeat_offenders_returns_200_pm(self, auth_headers_pm):
        """GET /api/repeat-offenders returns 200 for production manager"""
        response = requests.get(f"{BASE_URL}/api/repeat-offenders?window_days=30", headers=auth_headers_pm)
        assert response.status_code == 200
        data = response.json()
        assert "crew_summaries" in data
        print(f"PM can access repeat offenders: {len(data['crew_summaries'])} crews")

    def test_repeat_offenders_with_custom_window(self, auth_headers_owner):
        """GET /api/repeat-offenders with custom window_days"""
        response = requests.get(f"{BASE_URL}/api/repeat-offenders?window_days=7", headers=auth_headers_owner)
        assert response.status_code == 200
        data = response.json()
        assert data["window_days"] == 7
        print(f"7-day window: {len(data['crew_summaries'])} crews")

    def test_repeat_offenders_with_custom_thresholds(self, auth_headers_owner):
        """GET /api/repeat-offenders with custom thresholds"""
        response = requests.get(
            f"{BASE_URL}/api/repeat-offenders?window_days=30&threshold_one=2&threshold_two=4&threshold_three=6",
            headers=auth_headers_owner
        )
        assert response.status_code == 200
        data = response.json()
        assert data["thresholds"]["level_1"] == 2
        assert data["thresholds"]["level_2"] == 4
        assert data["thresholds"]["level_3"] == 6
        print(f"Custom thresholds applied: {data['thresholds']}")

    def test_repeat_offenders_heatmap_structure(self, auth_headers_owner):
        """Verify heatmap structure in repeat offenders response"""
        response = requests.get(f"{BASE_URL}/api/repeat-offenders?window_days=90", headers=auth_headers_owner)
        assert response.status_code == 200
        data = response.json()
        for cell in data["heatmap"]:
            assert "crew" in cell
            assert "issue_type" in cell
            assert "count" in cell
            assert "level" in cell
        print(f"Heatmap cells validated: {len(data['heatmap'])}")


# ============ Training Sessions Tests ============

class TestTrainingSessions:
    """Training Sessions CRUD tests"""

    def test_get_training_sessions_returns_200_owner(self, auth_headers_owner):
        """GET /api/training-sessions returns 200 for owner"""
        response = requests.get(f"{BASE_URL}/api/training-sessions", headers=auth_headers_owner)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data
        print(f"Training sessions: {data['pagination']['total']}")

    def test_get_training_sessions_returns_200_pm(self, auth_headers_pm):
        """GET /api/training-sessions returns 200 for production manager"""
        response = requests.get(f"{BASE_URL}/api/training-sessions", headers=auth_headers_pm)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        print(f"PM can access training sessions: {len(data['items'])} items")

    def test_create_training_session_returns_201(self, auth_headers_owner):
        """POST /api/training-sessions creates a new session"""
        # First get a valid crew access code
        crew_response = requests.get(f"{BASE_URL}/api/crew-access-links?status=active&page=1&limit=1", headers=auth_headers_owner)
        assert crew_response.status_code == 200
        crew_links = crew_response.json()["items"]
        if not crew_links:
            pytest.skip("No active crew links available")
        
        access_code = crew_links[0]["code"]
        division = crew_links[0]["division"]
        
        payload = {
            "access_code": access_code,
            "division": division,
            "item_count": 3
        }
        response = requests.post(f"{BASE_URL}/api/training-sessions", json=payload, headers=auth_headers_owner)
        assert response.status_code in [200, 201], f"Create training session failed: {response.text}"
        data = response.json()
        # API returns session data directly, not nested under "session" key
        assert "code" in data or "session" in data
        session_code = data.get("code") or data.get("session", {}).get("code")
        session_url = data.get("session_url", "")
        print(f"Created training session: {session_code}, URL: {session_url}")


# ============ Public Training Endpoints Tests ============

class TestPublicTraining:
    """Public training endpoints (no auth required)"""

    @pytest.fixture(scope="class")
    def training_session_code(self, auth_headers_owner):
        """Create a training session and return its code"""
        # Get a valid crew access code
        crew_response = requests.get(f"{BASE_URL}/api/crew-access-links?status=active&page=1&limit=1", headers=auth_headers_owner)
        if crew_response.status_code != 200 or not crew_response.json()["items"]:
            pytest.skip("No active crew links available")
        
        access_code = crew_response.json()["items"][0]["code"]
        division = crew_response.json()["items"][0]["division"]
        
        payload = {
            "access_code": access_code,
            "division": division,
            "item_count": 3
        }
        response = requests.post(f"{BASE_URL}/api/training-sessions", json=payload, headers=auth_headers_owner)
        if response.status_code not in [200, 201]:
            pytest.skip(f"Could not create training session: {response.text}")
        data = response.json()
        # API returns session data directly, not nested under "session" key
        return data.get("code") or data.get("session", {}).get("code")

    def test_get_public_training_valid_code(self, training_session_code):
        """GET /api/public/training/{code} returns session data for valid code"""
        response = requests.get(f"{BASE_URL}/api/public/training/{training_session_code}")
        assert response.status_code == 200, f"Get public training failed: {response.text}"
        data = response.json()
        assert "session" in data
        assert "items" in data
        assert data["session"]["code"] == training_session_code
        print(f"Public training session loaded: {len(data['items'])} items")

    def test_get_public_training_invalid_code(self):
        """GET /api/public/training/{code} returns 404 for invalid code"""
        response = requests.get(f"{BASE_URL}/api/public/training/invalid_code_12345")
        assert response.status_code == 404
        print("Invalid code correctly returns 404")

    def test_submit_public_training_valid(self, training_session_code):
        """POST /api/public/training/{code}/submit submits answers"""
        # First get the session items
        session_response = requests.get(f"{BASE_URL}/api/public/training/{training_session_code}")
        if session_response.status_code != 200:
            pytest.skip("Could not load training session")
        
        items = session_response.json()["items"]
        if not items:
            pytest.skip("No items in training session")
        
        # Build answers for all items
        answers = []
        for item in items:
            if item["question_type"] == "multiple_choice" and item["choice_options"]:
                answer = item["choice_options"][0]  # Pick first option
            else:
                answer = "Test answer"
            answers.append({
                "item_id": item["id"],
                "response": answer,
                "time_seconds": 5.0
            })
        
        payload = {"answers": answers}
        response = requests.post(f"{BASE_URL}/api/public/training/{training_session_code}/submit", json=payload)
        assert response.status_code == 200, f"Submit training failed: {response.text}"
        data = response.json()
        assert "summary" in data
        assert "score_percent" in data["summary"]
        assert "completion_rate" in data["summary"]
        print(f"Training submitted: score={data['summary']['score_percent']}%, completion={data['summary']['completion_rate']}%")

    def test_submit_public_training_invalid_code(self):
        """POST /api/public/training/{code}/submit returns 404 for invalid code"""
        payload = {"answers": []}
        response = requests.post(f"{BASE_URL}/api/public/training/invalid_code_12345/submit", json=payload)
        assert response.status_code == 404
        print("Invalid code submit correctly returns 404")


# ============ Rapid Review Queue Tests (for Overview card) ============

class TestRapidReviewQueue:
    """Rapid Review queue tests for Overview card"""

    def test_rapid_review_queue_returns_200_owner(self, auth_headers_owner):
        """GET /api/rapid-reviews/queue returns 200 for owner"""
        response = requests.get(f"{BASE_URL}/api/rapid-reviews/queue", headers=auth_headers_owner)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data
        print(f"Rapid review queue: {data['pagination']['total']} items")

    def test_rapid_review_queue_returns_200_pm(self, auth_headers_pm):
        """GET /api/rapid-reviews/queue returns 200 for production manager"""
        response = requests.get(f"{BASE_URL}/api/rapid-reviews/queue", headers=auth_headers_pm)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        print(f"PM can access rapid review queue: {len(data['items'])} items")


# ============ Dashboard Overview Tests ============

class TestDashboardOverview:
    """Dashboard overview tests"""

    def test_dashboard_overview_returns_200_owner(self, auth_headers_owner):
        """GET /api/dashboard/overview returns 200 for owner"""
        response = requests.get(f"{BASE_URL}/api/dashboard/overview", headers=auth_headers_owner)
        assert response.status_code == 200
        data = response.json()
        assert "totals" in data
        assert "queues" in data
        assert "storage" in data
        print(f"Dashboard overview: {data['totals']['submissions']} submissions")

    def test_dashboard_overview_returns_200_pm(self, auth_headers_pm):
        """GET /api/dashboard/overview returns 200 for production manager"""
        response = requests.get(f"{BASE_URL}/api/dashboard/overview", headers=auth_headers_pm)
        assert response.status_code == 200
        data = response.json()
        assert "totals" in data
        print(f"PM can access dashboard: {data['totals']['submissions']} submissions")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
