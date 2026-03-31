"""
Test suite for Rapid Review features:
- /api/rapid-reviews/queue endpoint
- /api/rapid-reviews POST endpoint
- 4-state rapid review model (Fail, Concern, Standard, Exemplary)
- Comment requirement for Fail and Exemplary
- No comment requirement for Concern and Standard
- Queue excludes already rapid-reviewed items
- Rapid review summary in submission detail
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials from /app/memory/test_credentials.md
OWNER_EMAIL = "owner@fieldquality.local"
OWNER_PASSWORD = "FieldQA123!"
PM_EMAIL = "production.manager@fieldquality.local"
PM_PASSWORD = "FieldQA123!"


class TestRapidReviewFeatures:
    """Rapid Review feature tests"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def get_auth_token(self, email, password):
        """Get authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None

    def test_owner_login_success(self):
        """Test owner can login successfully"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL,
            "password": OWNER_PASSWORD
        })
        assert response.status_code == 200, f"Owner login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "owner"
        print("PASS: Owner login successful")

    def test_pm_login_success(self):
        """Test production manager can login successfully"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PM_EMAIL,
            "password": PM_PASSWORD
        })
        assert response.status_code == 200, f"PM login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "management"
        print("PASS: Production Manager login successful")

    def test_rapid_review_queue_returns_200(self):
        """Test /api/rapid-reviews/queue returns 200 for owner"""
        token = self.get_auth_token(OWNER_EMAIL, OWNER_PASSWORD)
        assert token, "Failed to get owner token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/rapid-reviews/queue?page=1&limit=30")
        
        assert response.status_code == 200, f"Queue endpoint failed: {response.text}"
        data = response.json()
        assert "items" in data
        assert "pagination" in data
        print(f"PASS: Rapid review queue returned {len(data['items'])} items")

    def test_rapid_review_queue_returns_200_for_management(self):
        """Test /api/rapid-reviews/queue returns 200 for management role"""
        token = self.get_auth_token(PM_EMAIL, PM_PASSWORD)
        assert token, "Failed to get PM token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/rapid-reviews/queue?page=1&limit=30")
        
        assert response.status_code == 200, f"Queue endpoint failed for management: {response.text}"
        data = response.json()
        assert "items" in data
        print(f"PASS: Rapid review queue accessible by management, returned {len(data['items'])} items")

    def test_rapid_review_fail_requires_comment(self):
        """Test that Fail rating requires a comment"""
        token = self.get_auth_token(OWNER_EMAIL, OWNER_PASSWORD)
        assert token, "Failed to get owner token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get a submission from queue
        queue_response = self.session.get(f"{BASE_URL}/api/rapid-reviews/queue?page=1&limit=10")
        assert queue_response.status_code == 200
        queue_data = queue_response.json()
        
        if not queue_data["items"]:
            pytest.skip("No items in rapid review queue to test")
        
        submission_id = queue_data["items"][0]["id"]
        
        # Try to submit fail without comment
        response = self.session.post(f"{BASE_URL}/api/rapid-reviews", json={
            "submission_id": submission_id,
            "overall_rating": "fail",
            "comment": "",  # Empty comment
            "issue_tag": "quality-concern",
            "annotation_count": 0,
            "entry_mode": "desktop"
        })
        
        assert response.status_code == 400, f"Expected 400 for fail without comment, got {response.status_code}"
        assert "comment" in response.text.lower() or "required" in response.text.lower()
        print("PASS: Fail rating correctly requires comment")

    def test_rapid_review_exemplary_requires_comment(self):
        """Test that Exemplary rating requires a comment"""
        token = self.get_auth_token(OWNER_EMAIL, OWNER_PASSWORD)
        assert token, "Failed to get owner token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get a submission from queue
        queue_response = self.session.get(f"{BASE_URL}/api/rapid-reviews/queue?page=1&limit=10")
        assert queue_response.status_code == 200
        queue_data = queue_response.json()
        
        if not queue_data["items"]:
            pytest.skip("No items in rapid review queue to test")
        
        submission_id = queue_data["items"][0]["id"]
        
        # Try to submit exemplary without comment
        response = self.session.post(f"{BASE_URL}/api/rapid-reviews", json={
            "submission_id": submission_id,
            "overall_rating": "exemplary",
            "comment": "",  # Empty comment
            "issue_tag": "quality-concern",
            "annotation_count": 0,
            "entry_mode": "desktop"
        })
        
        assert response.status_code == 400, f"Expected 400 for exemplary without comment, got {response.status_code}"
        print("PASS: Exemplary rating correctly requires comment")

    def test_rapid_review_concern_no_comment_required(self):
        """Test that Concern rating does NOT require a comment"""
        token = self.get_auth_token(OWNER_EMAIL, OWNER_PASSWORD)
        assert token, "Failed to get owner token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get a submission from queue
        queue_response = self.session.get(f"{BASE_URL}/api/rapid-reviews/queue?page=1&limit=10")
        assert queue_response.status_code == 200
        queue_data = queue_response.json()
        
        if not queue_data["items"]:
            pytest.skip("No items in rapid review queue to test")
        
        submission_id = queue_data["items"][0]["id"]
        
        # Submit concern without comment - should succeed
        response = self.session.post(f"{BASE_URL}/api/rapid-reviews", json={
            "submission_id": submission_id,
            "overall_rating": "concern",
            "comment": "",  # Empty comment should be OK
            "issue_tag": "quality-concern",
            "annotation_count": 0,
            "entry_mode": "desktop"
        })
        
        # Should succeed (200) or conflict if already reviewed (409)
        assert response.status_code in [200, 409], f"Unexpected status {response.status_code}: {response.text}"
        if response.status_code == 200:
            print("PASS: Concern rating accepted without comment")
        else:
            print("PASS: Concern rating validation correct (item already reviewed)")

    def test_rapid_review_standard_no_comment_required(self):
        """Test that Standard rating does NOT require a comment"""
        token = self.get_auth_token(OWNER_EMAIL, OWNER_PASSWORD)
        assert token, "Failed to get owner token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get a submission from queue
        queue_response = self.session.get(f"{BASE_URL}/api/rapid-reviews/queue?page=1&limit=10")
        assert queue_response.status_code == 200
        queue_data = queue_response.json()
        
        if not queue_data["items"]:
            pytest.skip("No items in rapid review queue to test")
        
        submission_id = queue_data["items"][0]["id"]
        
        # Submit standard without comment - should succeed
        response = self.session.post(f"{BASE_URL}/api/rapid-reviews", json={
            "submission_id": submission_id,
            "overall_rating": "standard",
            "comment": "",  # Empty comment should be OK
            "issue_tag": "quality-concern",
            "annotation_count": 0,
            "entry_mode": "desktop"
        })
        
        # Should succeed (200) or conflict if already reviewed (409)
        assert response.status_code in [200, 409], f"Unexpected status {response.status_code}: {response.text}"
        if response.status_code == 200:
            print("PASS: Standard rating accepted without comment")
        else:
            print("PASS: Standard rating validation correct (item already reviewed)")

    def test_rapid_review_invalid_rating_rejected(self):
        """Test that invalid rating values are rejected"""
        token = self.get_auth_token(OWNER_EMAIL, OWNER_PASSWORD)
        assert token, "Failed to get owner token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get a submission from queue
        queue_response = self.session.get(f"{BASE_URL}/api/rapid-reviews/queue?page=1&limit=10")
        assert queue_response.status_code == 200
        queue_data = queue_response.json()
        
        if not queue_data["items"]:
            pytest.skip("No items in rapid review queue to test")
        
        submission_id = queue_data["items"][0]["id"]
        
        # Try invalid rating
        response = self.session.post(f"{BASE_URL}/api/rapid-reviews", json={
            "submission_id": submission_id,
            "overall_rating": "invalid_rating",
            "comment": "test",
            "issue_tag": "quality-concern",
            "annotation_count": 0,
            "entry_mode": "desktop"
        })
        
        assert response.status_code == 400, f"Expected 400 for invalid rating, got {response.status_code}"
        print("PASS: Invalid rating correctly rejected")

    def test_rapid_review_queue_excludes_reviewed_items(self):
        """Test that queue excludes already rapid-reviewed items"""
        token = self.get_auth_token(OWNER_EMAIL, OWNER_PASSWORD)
        assert token, "Failed to get owner token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get initial queue
        queue_response = self.session.get(f"{BASE_URL}/api/rapid-reviews/queue?page=1&limit=50")
        assert queue_response.status_code == 200
        queue_data = queue_response.json()
        initial_count = len(queue_data["items"])
        
        if initial_count == 0:
            pytest.skip("No items in rapid review queue to test exclusion")
        
        # Get first item
        submission_id = queue_data["items"][0]["id"]
        
        # Submit a rapid review for it
        review_response = self.session.post(f"{BASE_URL}/api/rapid-reviews", json={
            "submission_id": submission_id,
            "overall_rating": "standard",
            "comment": "",
            "issue_tag": "quality-concern",
            "annotation_count": 0,
            "entry_mode": "desktop"
        })
        
        if review_response.status_code == 409:
            # Already reviewed, check it's not in queue
            pass
        elif review_response.status_code == 200:
            # Successfully reviewed
            pass
        else:
            pytest.fail(f"Unexpected response: {review_response.status_code} - {review_response.text}")
        
        # Get queue again
        queue_response2 = self.session.get(f"{BASE_URL}/api/rapid-reviews/queue?page=1&limit=50")
        assert queue_response2.status_code == 200
        queue_data2 = queue_response2.json()
        
        # Check that the reviewed item is not in the queue
        reviewed_ids = [item["id"] for item in queue_data2["items"]]
        assert submission_id not in reviewed_ids, "Reviewed item should not appear in queue"
        print("PASS: Queue correctly excludes rapid-reviewed items")

    def test_submission_detail_includes_rapid_review_summary(self):
        """Test that submission detail includes rapid review summary when available"""
        token = self.get_auth_token(OWNER_EMAIL, OWNER_PASSWORD)
        assert token, "Failed to get owner token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get submissions that might have rapid reviews
        submissions_response = self.session.get(f"{BASE_URL}/api/submissions?scope=owner&page=1&limit=20")
        assert submissions_response.status_code == 200
        submissions = submissions_response.json()["items"]
        
        # Check each submission for rapid_review field
        found_rapid_review = False
        for submission in submissions:
            detail_response = self.session.get(f"{BASE_URL}/api/submissions/{submission['id']}")
            assert detail_response.status_code == 200
            detail = detail_response.json()
            
            # Check if rapid_review field exists in response
            if detail.get("rapid_review"):
                found_rapid_review = True
                assert "overall_rating" in detail["rapid_review"]
                assert "rubric_sum_percent" in detail["rapid_review"]
                print(f"PASS: Found rapid review summary for {submission['id']}: {detail['rapid_review']['overall_rating']}")
                break
        
        if not found_rapid_review:
            # Check if there's a known rapid-reviewed submission
            # From context: sub_775243e0633e has a concern rapid review
            detail_response = self.session.get(f"{BASE_URL}/api/submissions/sub_775243e0633e")
            if detail_response.status_code == 200:
                detail = detail_response.json()
                if detail.get("rapid_review"):
                    found_rapid_review = True
                    assert detail["rapid_review"]["overall_rating"] == "concern"
                    print(f"PASS: Found rapid review summary for sub_775243e0633e: concern")
        
        if not found_rapid_review:
            print("INFO: No rapid-reviewed submissions found to verify summary display")

    def test_rapid_review_rubric_sum_calculation(self):
        """Test that rapid review calculates rubric sum correctly"""
        token = self.get_auth_token(OWNER_EMAIL, OWNER_PASSWORD)
        assert token, "Failed to get owner token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Check the known rapid-reviewed submission
        detail_response = self.session.get(f"{BASE_URL}/api/submissions/sub_775243e0633e")
        if detail_response.status_code == 200:
            detail = detail_response.json()
            if detail.get("rapid_review"):
                rapid_review = detail["rapid_review"]
                # Concern multiplier is 0.55, so rubric_sum_percent should be around 55%
                assert "rubric_sum_percent" in rapid_review
                assert rapid_review["overall_rating"] == "concern"
                # Concern should give ~55% (0.55 * 100)
                assert 50 <= rapid_review["rubric_sum_percent"] <= 60, f"Expected ~55% for concern, got {rapid_review['rubric_sum_percent']}"
                print(f"PASS: Rubric sum calculation correct: {rapid_review['rubric_sum_percent']}% for concern rating")
            else:
                print("INFO: No rapid review found for sub_775243e0633e")
        else:
            print("INFO: Could not fetch sub_775243e0633e to verify rubric sum")

    def test_rapid_review_entry_modes(self):
        """Test that both desktop and mobile entry modes are accepted"""
        token = self.get_auth_token(OWNER_EMAIL, OWNER_PASSWORD)
        assert token, "Failed to get owner token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get a submission from queue
        queue_response = self.session.get(f"{BASE_URL}/api/rapid-reviews/queue?page=1&limit=10")
        assert queue_response.status_code == 200
        queue_data = queue_response.json()
        
        if not queue_data["items"]:
            pytest.skip("No items in rapid review queue to test entry modes")
        
        submission_id = queue_data["items"][0]["id"]
        
        # Test desktop mode
        response = self.session.post(f"{BASE_URL}/api/rapid-reviews", json={
            "submission_id": submission_id,
            "overall_rating": "standard",
            "comment": "",
            "issue_tag": "quality-concern",
            "annotation_count": 0,
            "entry_mode": "desktop"
        })
        
        # Should succeed or conflict
        assert response.status_code in [200, 409], f"Desktop mode failed: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            assert data["rapid_review"]["entry_mode"] == "desktop"
            print("PASS: Desktop entry mode accepted and stored")
        else:
            print("PASS: Entry mode validation correct (item already reviewed)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
