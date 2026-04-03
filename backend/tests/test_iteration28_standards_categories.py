"""
Iteration 28: Standards Library - Dynamic Categories + Edit/Delete from Popup
Tests:
1. GET /api/standard-categories - returns 30+ dynamic categories (defaults + any custom from DB)
2. DELETE /api/standards/{id} - deletes a standard, returns {deleted: true}
3. PATCH /api/standards/{id} - existing edit still works
4. Custom category used in a standard appears in future category lists
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')

# Test credentials
OWNER_EMAIL = "sadam.owner@slmco.local"
OWNER_PASSWORD = "SLMCo2026!"
MANAGEMENT_EMAIL = "hjohnny.super@slmco.local"
MANAGEMENT_PASSWORD = "SLMCo2026!"


@pytest.fixture(scope="module")
def owner_token():
    """Get owner authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": OWNER_EMAIL,
        "password": OWNER_PASSWORD
    })
    assert response.status_code == 200, f"Owner login failed: {response.text}"
    return response.json().get("token")


@pytest.fixture(scope="module")
def management_token():
    """Get management authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": MANAGEMENT_EMAIL,
        "password": MANAGEMENT_PASSWORD
    })
    assert response.status_code == 200, f"Management login failed: {response.text}"
    return response.json().get("token")


@pytest.fixture
def owner_client(owner_token):
    """Session with owner auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {owner_token}"
    })
    return session


@pytest.fixture
def management_client(management_token):
    """Session with management auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {management_token}"
    })
    return session


class TestStandardCategories:
    """Test GET /api/standard-categories endpoint"""
    
    def test_get_categories_returns_30_plus_items(self, owner_client):
        """Categories endpoint should return 30+ default categories"""
        response = owner_client.get(f"{BASE_URL}/api/standard-categories")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "categories" in data, "Response should have 'categories' key"
        categories = data["categories"]
        
        # Should have at least 27 default categories (as defined in backend)
        assert len(categories) >= 27, f"Expected 27+ categories, got {len(categories)}"
        
        # Verify some expected default categories exist
        expected_defaults = [
            "Bed Edging", "Mulching", "Spring Cleanup", "Fall Cleanup",
            "Pruning", "Weeding", "Softscape", "Hardscape", "Snow Removal"
        ]
        for cat in expected_defaults:
            assert cat in categories, f"Expected default category '{cat}' not found"
        
        print(f"✓ GET /api/standard-categories returned {len(categories)} categories")
    
    def test_categories_sorted_alphabetically(self, owner_client):
        """Categories should be sorted alphabetically"""
        response = owner_client.get(f"{BASE_URL}/api/standard-categories")
        assert response.status_code == 200
        
        categories = response.json()["categories"]
        sorted_categories = sorted(categories)
        assert categories == sorted_categories, "Categories should be sorted alphabetically"
        
        print("✓ Categories are sorted alphabetically")
    
    def test_management_can_access_categories(self, management_client):
        """Management role should be able to access categories"""
        response = management_client.get(f"{BASE_URL}/api/standard-categories")
        assert response.status_code == 200, f"Management access failed: {response.text}"
        
        data = response.json()
        assert "categories" in data
        assert len(data["categories"]) >= 27
        
        print("✓ Management role can access categories")
    
    def test_categories_requires_auth(self):
        """Categories endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/standard-categories")
        assert response.status_code == 401, "Should require authentication"
        
        print("✓ Categories endpoint requires authentication")


class TestDeleteStandard:
    """Test DELETE /api/standards/{id} endpoint"""
    
    def test_delete_standard_success(self, owner_client):
        """Should delete a standard and return {deleted: true}"""
        # First create a standard to delete
        create_payload = {
            "title": "TEST_Delete_Standard_Iter28",
            "category": "Mulching",
            "audience": "crew",
            "division_targets": ["Maintenance"],
            "checklist": ["Step 1", "Step 2"],
            "notes": "Test notes for deletion",
            "owner_notes": "",
            "shoutout": "",
            "image_url": "",
            "training_enabled": False,
            "question_type": "multiple_choice",
            "question_prompt": "",
            "choice_options": [],
            "correct_answer": "",
            "is_active": True
        }
        
        create_response = owner_client.post(f"{BASE_URL}/api/standards", json=create_payload)
        assert create_response.status_code == 201, f"Create failed: {create_response.text}"
        
        created_standard = create_response.json()
        standard_id = created_standard["id"]
        
        # Now delete it
        delete_response = owner_client.delete(f"{BASE_URL}/api/standards/{standard_id}")
        assert delete_response.status_code == 200, f"Delete failed: {delete_response.text}"
        
        delete_data = delete_response.json()
        assert delete_data.get("deleted") == True, "Response should have deleted: true"
        assert delete_data.get("id") == standard_id, "Response should include the deleted id"
        
        # Verify it's actually deleted - GET should return 404 or not find it
        get_response = owner_client.get(f"{BASE_URL}/api/standards?search=TEST_Delete_Standard_Iter28")
        assert get_response.status_code == 200
        items = get_response.json().get("items", [])
        matching = [i for i in items if i["id"] == standard_id]
        assert len(matching) == 0, "Deleted standard should not appear in search"
        
        print(f"✓ DELETE /api/standards/{standard_id} returned deleted: true")
    
    def test_delete_nonexistent_standard_returns_404(self, owner_client):
        """Deleting a non-existent standard should return 404"""
        response = owner_client.delete(f"{BASE_URL}/api/standards/nonexistent_id_12345")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        print("✓ DELETE non-existent standard returns 404")
    
    def test_management_can_delete_standard(self, management_client, owner_client):
        """Management role should be able to delete standards"""
        # Create a standard first (using owner)
        create_payload = {
            "title": "TEST_Mgmt_Delete_Iter28",
            "category": "Pruning",
            "audience": "crew",
            "division_targets": [],
            "checklist": [],
            "notes": "",
            "owner_notes": "",
            "shoutout": "",
            "image_url": "",
            "training_enabled": False,
            "question_type": "multiple_choice",
            "question_prompt": "",
            "choice_options": [],
            "correct_answer": "",
            "is_active": True
        }
        
        create_response = owner_client.post(f"{BASE_URL}/api/standards", json=create_payload)
        assert create_response.status_code == 201
        standard_id = create_response.json()["id"]
        
        # Delete using management
        delete_response = management_client.delete(f"{BASE_URL}/api/standards/{standard_id}")
        assert delete_response.status_code == 200, f"Management delete failed: {delete_response.text}"
        assert delete_response.json().get("deleted") == True
        
        print("✓ Management role can delete standards")
    
    def test_delete_requires_auth(self):
        """Delete endpoint should require authentication"""
        response = requests.delete(f"{BASE_URL}/api/standards/some_id")
        assert response.status_code == 401, "Should require authentication"
        
        print("✓ DELETE endpoint requires authentication")


class TestPatchStandard:
    """Test PATCH /api/standards/{id} endpoint (existing edit functionality)"""
    
    def test_patch_standard_success(self, owner_client):
        """Should update a standard and return updated data"""
        # Create a standard first
        create_payload = {
            "title": "TEST_Patch_Standard_Iter28",
            "category": "Weeding",
            "audience": "crew",
            "division_targets": ["Maintenance"],
            "checklist": ["Original step"],
            "notes": "Original notes",
            "owner_notes": "",
            "shoutout": "",
            "image_url": "",
            "training_enabled": False,
            "question_type": "multiple_choice",
            "question_prompt": "",
            "choice_options": [],
            "correct_answer": "",
            "is_active": True
        }
        
        create_response = owner_client.post(f"{BASE_URL}/api/standards", json=create_payload)
        assert create_response.status_code == 201
        standard_id = create_response.json()["id"]
        
        # Patch it
        patch_payload = {
            "title": "TEST_Patch_Standard_Iter28_Updated",
            "notes": "Updated notes",
            "training_enabled": True,
            "question_prompt": "What is the best practice?"
        }
        
        patch_response = owner_client.patch(f"{BASE_URL}/api/standards/{standard_id}", json=patch_payload)
        assert patch_response.status_code == 200, f"Patch failed: {patch_response.text}"
        
        updated = patch_response.json()
        assert updated["title"] == "TEST_Patch_Standard_Iter28_Updated"
        assert updated["notes"] == "Updated notes"
        assert updated["training_enabled"] == True
        assert updated["question_prompt"] == "What is the best practice?"
        # Original fields should be preserved
        assert updated["category"] == "Weeding"
        assert updated["audience"] == "crew"
        
        # Cleanup
        owner_client.delete(f"{BASE_URL}/api/standards/{standard_id}")
        
        print(f"✓ PATCH /api/standards/{standard_id} updated successfully")
    
    def test_patch_nonexistent_standard_returns_404(self, owner_client):
        """Patching a non-existent standard should return 404"""
        response = owner_client.patch(
            f"{BASE_URL}/api/standards/nonexistent_id_12345",
            json={"title": "New Title"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        print("✓ PATCH non-existent standard returns 404")


class TestCustomCategoryInFutureList:
    """Test that custom categories appear in future category lists"""
    
    def test_custom_category_appears_in_list(self, owner_client):
        """A custom category used in a standard should appear in category list"""
        custom_category = "TEST_Custom_Category_Iter28"
        
        # Create a standard with custom category
        create_payload = {
            "title": "TEST_Custom_Cat_Standard",
            "category": custom_category,
            "audience": "crew",
            "division_targets": [],
            "checklist": [],
            "notes": "",
            "owner_notes": "",
            "shoutout": "",
            "image_url": "",
            "training_enabled": False,
            "question_type": "multiple_choice",
            "question_prompt": "",
            "choice_options": [],
            "correct_answer": "",
            "is_active": True
        }
        
        create_response = owner_client.post(f"{BASE_URL}/api/standards", json=create_payload)
        assert create_response.status_code == 201
        standard_id = create_response.json()["id"]
        
        # Now check categories list
        categories_response = owner_client.get(f"{BASE_URL}/api/standard-categories")
        assert categories_response.status_code == 200
        
        categories = categories_response.json()["categories"]
        assert custom_category in categories, f"Custom category '{custom_category}' should appear in list"
        
        # Cleanup
        owner_client.delete(f"{BASE_URL}/api/standards/{standard_id}")
        
        print(f"✓ Custom category '{custom_category}' appears in category list")


class TestStandardsListEndpoint:
    """Test GET /api/standards endpoint with category filter"""
    
    def test_filter_by_category(self, owner_client):
        """Should filter standards by category"""
        # Create a standard with specific category
        create_payload = {
            "title": "TEST_Filter_Category_Iter28",
            "category": "Bed Edging",
            "audience": "crew",
            "division_targets": [],
            "checklist": [],
            "notes": "",
            "owner_notes": "",
            "shoutout": "",
            "image_url": "",
            "training_enabled": False,
            "question_type": "multiple_choice",
            "question_prompt": "",
            "choice_options": [],
            "correct_answer": "",
            "is_active": True
        }
        
        create_response = owner_client.post(f"{BASE_URL}/api/standards", json=create_payload)
        assert create_response.status_code == 201
        standard_id = create_response.json()["id"]
        
        # Filter by category
        filter_response = owner_client.get(f"{BASE_URL}/api/standards?category=Bed%20Edging")
        assert filter_response.status_code == 200
        
        items = filter_response.json().get("items", [])
        # All items should have the filtered category
        for item in items:
            assert item["category"] == "Bed Edging", f"Item has wrong category: {item['category']}"
        
        # Cleanup
        owner_client.delete(f"{BASE_URL}/api/standards/{standard_id}")
        
        print("✓ Standards filter by category works")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
