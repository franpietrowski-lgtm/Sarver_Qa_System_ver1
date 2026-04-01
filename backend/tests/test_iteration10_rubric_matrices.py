"""
Iteration 10 Tests: Rubric Matrices CRUD, Crew Icon Tabs, Rapid Review Mobile, Dark Theme
Tests the following features:
1. GET /api/rubric-matrices - returns all active rubrics with division field
2. GET /api/rubric-matrices?division=Install - filters correctly
3. POST /api/rubric-matrices - creates new rubric (GM only)
4. PATCH /api/rubric-matrices/{id} - updates rubric fields
5. DELETE /api/rubric-matrices/{id} - soft-deletes (deactivates) rubric
6. Non-GM/Owner (Supervisor) cannot create/update/delete rubric matrices
"""

import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials from /app/memory/test_credentials.md
GM_CREDENTIALS = {"email": "gm@fieldquality.local", "password": "FieldQA123!"}
OWNER_CREDENTIALS = {"email": "owner@fieldquality.local", "password": "FieldQA123!"}
SUPERVISOR_CREDENTIALS = {"email": "supervisor@fieldquality.local", "password": "FieldQA123!"}
PM_CREDENTIALS = {"email": "production.manager@fieldquality.local", "password": "FieldQA123!"}


@pytest.fixture(scope="module")
def gm_token():
    """Get GM authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=GM_CREDENTIALS)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("GM authentication failed")


@pytest.fixture(scope="module")
def owner_token():
    """Get Owner authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=OWNER_CREDENTIALS)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Owner authentication failed")


@pytest.fixture(scope="module")
def supervisor_token():
    """Get Supervisor authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=SUPERVISOR_CREDENTIALS)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Supervisor authentication failed")


@pytest.fixture(scope="module")
def pm_token():
    """Get Production Manager authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=PM_CREDENTIALS)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Production Manager authentication failed")


class TestRubricMatricesGET:
    """Tests for GET /api/rubric-matrices endpoint"""

    def test_get_rubric_matrices_returns_list(self, gm_token):
        """GET /api/rubric-matrices returns all active rubrics"""
        response = requests.get(
            f"{BASE_URL}/api/rubric-matrices",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        # Verify rubrics have division field
        if len(data) > 0:
            assert "division" in data[0], "Rubric should have division field"
            assert "service_type" in data[0], "Rubric should have service_type field"
            assert "categories" in data[0], "Rubric should have categories field"
            assert "pass_threshold" in data[0], "Rubric should have pass_threshold field"
            print(f"Found {len(data)} rubric matrices")

    def test_get_rubric_matrices_filter_by_division(self, gm_token):
        """GET /api/rubric-matrices?division=Install filters correctly"""
        response = requests.get(
            f"{BASE_URL}/api/rubric-matrices?division=Install",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        # All returned rubrics should be Install division
        for rubric in data:
            assert rubric.get("division") == "Install", f"Expected Install division, got {rubric.get('division')}"
        print(f"Found {len(data)} Install division rubrics")

    def test_get_rubric_matrices_filter_by_maintenance(self, gm_token):
        """GET /api/rubric-matrices?division=Maintenance filters correctly"""
        response = requests.get(
            f"{BASE_URL}/api/rubric-matrices?division=Maintenance",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        for rubric in data:
            assert rubric.get("division") == "Maintenance"
        print(f"Found {len(data)} Maintenance division rubrics")

    def test_get_rubric_matrices_owner_access(self, owner_token):
        """Owner can access rubric matrices"""
        response = requests.get(
            f"{BASE_URL}/api/rubric-matrices",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Owner retrieved {len(data)} rubric matrices")

    def test_get_rubric_matrices_supervisor_access(self, supervisor_token):
        """Supervisor (management role) can access rubric matrices"""
        response = requests.get(
            f"{BASE_URL}/api/rubric-matrices",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Supervisor retrieved {len(data)} rubric matrices")


class TestRubricMatricesPOST:
    """Tests for POST /api/rubric-matrices endpoint"""

    def test_gm_can_create_rubric_matrix(self, gm_token):
        """GM can create a new rubric matrix"""
        payload = {
            "service_type": "TEST_custom_service",
            "division": "Maintenance",
            "title": "TEST Custom Service v1",
            "min_photos": 3,
            "pass_threshold": 80,
            "hard_fail_conditions": ["test_fail_condition"],
            "categories": [
                {"key": "quality", "label": "Quality", "weight": 0.5, "max_score": 5},
                {"key": "completeness", "label": "Completeness", "weight": 0.5, "max_score": 5}
            ]
        }
        response = requests.post(
            f"{BASE_URL}/api/rubric-matrices",
            json=payload,
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("service_type") == "test_custom_service"  # lowercased
        assert data.get("division") == "Maintenance"
        assert data.get("title") == "TEST Custom Service v1"
        assert "id" in data
        print(f"Created rubric matrix with id: {data.get('id')}")
        # Store for cleanup
        TestRubricMatricesPOST.created_rubric_id = data.get("id")

    def test_owner_can_create_rubric_matrix(self, owner_token):
        """Owner can create a new rubric matrix"""
        payload = {
            "service_type": "TEST_owner_service",
            "division": "Install",
            "title": "TEST Owner Service v1",
            "min_photos": 4,
            "pass_threshold": 85,
            "hard_fail_conditions": [],
            "categories": [
                {"key": "accuracy", "label": "Accuracy", "weight": 1.0, "max_score": 5}
            ]
        }
        response = requests.post(
            f"{BASE_URL}/api/rubric-matrices",
            json=payload,
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("division") == "Install"
        print(f"Owner created rubric matrix with id: {data.get('id')}")
        TestRubricMatricesPOST.owner_created_rubric_id = data.get("id")

    def test_supervisor_cannot_create_rubric_matrix(self, supervisor_token):
        """Supervisor (non-GM/Owner) cannot create rubric matrices"""
        payload = {
            "service_type": "TEST_supervisor_service",
            "division": "Tree",
            "title": "TEST Supervisor Service v1",
            "min_photos": 3,
            "pass_threshold": 80,
            "hard_fail_conditions": [],
            "categories": [
                {"key": "safety", "label": "Safety", "weight": 1.0, "max_score": 5}
            ]
        }
        response = requests.post(
            f"{BASE_URL}/api/rubric-matrices",
            json=payload,
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("Supervisor correctly denied rubric creation (403)")

    def test_pm_cannot_create_rubric_matrix(self, pm_token):
        """Production Manager (non-GM/Owner) cannot create rubric matrices"""
        payload = {
            "service_type": "TEST_pm_service",
            "division": "Plant Healthcare",
            "title": "TEST PM Service v1",
            "min_photos": 2,
            "pass_threshold": 75,
            "hard_fail_conditions": [],
            "categories": [
                {"key": "coverage", "label": "Coverage", "weight": 1.0, "max_score": 5}
            ]
        }
        response = requests.post(
            f"{BASE_URL}/api/rubric-matrices",
            json=payload,
            headers={"Authorization": f"Bearer {pm_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("Production Manager correctly denied rubric creation (403)")


class TestRubricMatricesPATCH:
    """Tests for PATCH /api/rubric-matrices/{id} endpoint"""

    def test_gm_can_update_rubric_matrix(self, gm_token):
        """GM can update a rubric matrix"""
        # First get a rubric to update
        response = requests.get(
            f"{BASE_URL}/api/rubric-matrices",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        rubrics = response.json()
        test_rubric = next((r for r in rubrics if "TEST" in r.get("title", "")), rubrics[0] if rubrics else None)
        if not test_rubric:
            pytest.skip("No rubric available to update")
        
        rubric_id = test_rubric["id"]
        payload = {
            "title": f"{test_rubric['title']} - Updated",
            "pass_threshold": 82
        }
        response = requests.patch(
            f"{BASE_URL}/api/rubric-matrices/{rubric_id}",
            json=payload,
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "Updated" in data.get("title", "")
        print(f"GM updated rubric matrix: {rubric_id}")

    def test_owner_can_update_rubric_matrix(self, owner_token):
        """Owner can update a rubric matrix"""
        response = requests.get(
            f"{BASE_URL}/api/rubric-matrices",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        rubrics = response.json()
        if not rubrics:
            pytest.skip("No rubric available to update")
        
        rubric_id = rubrics[0]["id"]
        payload = {"min_photos": 4}
        response = requests.patch(
            f"{BASE_URL}/api/rubric-matrices/{rubric_id}",
            json=payload,
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"Owner updated rubric matrix: {rubric_id}")

    def test_supervisor_cannot_update_rubric_matrix(self, supervisor_token, gm_token):
        """Supervisor cannot update rubric matrices"""
        # Get a rubric ID first
        response = requests.get(
            f"{BASE_URL}/api/rubric-matrices",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        rubrics = response.json()
        if not rubrics:
            pytest.skip("No rubric available")
        
        rubric_id = rubrics[0]["id"]
        payload = {"title": "Supervisor Attempted Update"}
        response = requests.patch(
            f"{BASE_URL}/api/rubric-matrices/{rubric_id}",
            json=payload,
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("Supervisor correctly denied rubric update (403)")


class TestRubricMatricesDELETE:
    """Tests for DELETE /api/rubric-matrices/{id} endpoint (soft delete)"""

    def test_gm_can_delete_rubric_matrix(self, gm_token):
        """GM can soft-delete (deactivate) a rubric matrix"""
        # Create a test rubric to delete
        payload = {
            "service_type": "TEST_delete_service",
            "division": "Winter Services",
            "title": "TEST Delete Service v1",
            "min_photos": 2,
            "pass_threshold": 80,
            "hard_fail_conditions": [],
            "categories": [
                {"key": "coverage", "label": "Coverage", "weight": 1.0, "max_score": 5}
            ]
        }
        create_response = requests.post(
            f"{BASE_URL}/api/rubric-matrices",
            json=payload,
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        if create_response.status_code != 201:
            pytest.skip("Could not create test rubric for deletion")
        
        rubric_id = create_response.json()["id"]
        
        # Now delete it
        response = requests.delete(
            f"{BASE_URL}/api/rubric-matrices/{rubric_id}",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("ok") == True
        assert "deactivated" in data.get("detail", "").lower()
        print(f"GM soft-deleted rubric matrix: {rubric_id}")

    def test_supervisor_cannot_delete_rubric_matrix(self, supervisor_token, gm_token):
        """Supervisor cannot delete rubric matrices"""
        # Get a rubric ID
        response = requests.get(
            f"{BASE_URL}/api/rubric-matrices",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        rubrics = response.json()
        if not rubrics:
            pytest.skip("No rubric available")
        
        rubric_id = rubrics[0]["id"]
        response = requests.delete(
            f"{BASE_URL}/api/rubric-matrices/{rubric_id}",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("Supervisor correctly denied rubric deletion (403)")

    def test_pm_cannot_delete_rubric_matrix(self, pm_token, gm_token):
        """Production Manager cannot delete rubric matrices"""
        response = requests.get(
            f"{BASE_URL}/api/rubric-matrices",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        rubrics = response.json()
        if not rubrics:
            pytest.skip("No rubric available")
        
        rubric_id = rubrics[0]["id"]
        response = requests.delete(
            f"{BASE_URL}/api/rubric-matrices/{rubric_id}",
            headers={"Authorization": f"Bearer {pm_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("Production Manager correctly denied rubric deletion (403)")


class TestRubricMatricesDataIntegrity:
    """Tests for data integrity and division field presence"""

    def test_all_rubrics_have_division_field(self, gm_token):
        """All rubrics should have a division field"""
        response = requests.get(
            f"{BASE_URL}/api/rubric-matrices?division=all",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 200
        rubrics = response.json()
        for rubric in rubrics:
            assert "division" in rubric, f"Rubric {rubric.get('id')} missing division field"
            assert rubric["division"] is not None, f"Rubric {rubric.get('id')} has null division"
        print(f"All {len(rubrics)} rubrics have valid division field")

    def test_rubric_categories_structure(self, gm_token):
        """Rubric categories should have proper structure"""
        response = requests.get(
            f"{BASE_URL}/api/rubric-matrices",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        rubrics = response.json()
        for rubric in rubrics[:5]:  # Check first 5
            categories = rubric.get("categories", [])
            for cat in categories:
                assert "key" in cat, f"Category missing key in rubric {rubric.get('id')}"
                assert "label" in cat, f"Category missing label in rubric {rubric.get('id')}"
                assert "weight" in cat, f"Category missing weight in rubric {rubric.get('id')}"
        print("Rubric categories have proper structure")


class TestCleanup:
    """Cleanup test data"""

    def test_cleanup_test_rubrics(self, gm_token):
        """Clean up TEST_ prefixed rubrics"""
        response = requests.get(
            f"{BASE_URL}/api/rubric-matrices?include_inactive=true",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        rubrics = response.json()
        test_rubrics = [r for r in rubrics if "TEST" in r.get("service_type", "").upper() or "TEST" in r.get("title", "").upper()]
        for rubric in test_rubrics:
            requests.delete(
                f"{BASE_URL}/api/rubric-matrices/{rubric['id']}",
                headers={"Authorization": f"Bearer {gm_token}"}
            )
        print(f"Cleaned up {len(test_rubrics)} test rubrics")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
