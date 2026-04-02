"""
Iteration 25: Password Reset/Change and PWA Features Tests
Tests:
1. POST /api/auth/change-password - change password with correct current password
2. POST /api/auth/change-password - wrong current password returns 400
3. POST /api/auth/change-password - too short new password returns 400
4. POST /api/users/{user_id}/reset-password - admin resets user password
5. Verify temp password works for login
6. PWA manifest.json validation
7. PWA icon.svg validation
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
OWNER_EMAIL = "sadam.owner@slmco.local"
OWNER_PASSWORD = "SLMCo2026!"
MANAGEMENT_EMAIL = "hjohnny.super@slmco.local"
MANAGEMENT_PASSWORD = "SLMCo2026!"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def owner_token(api_client):
    """Get owner authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": OWNER_EMAIL,
        "password": OWNER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Owner authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def authenticated_client(api_client, owner_token):
    """Session with owner auth header"""
    api_client.headers.update({"Authorization": f"Bearer {owner_token}"})
    return api_client


class TestChangePassword:
    """Tests for POST /api/auth/change-password endpoint"""
    
    def test_change_password_success(self, authenticated_client):
        """Test changing password with correct current password"""
        # Change to a temporary password
        temp_password = "TempPass123!"
        response = authenticated_client.post(f"{BASE_URL}/api/auth/change-password", json={
            "current_password": OWNER_PASSWORD,
            "new_password": temp_password
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "message" in data
        assert "Password updated successfully" in data["message"]
        
        # Verify new password works by logging in
        login_response = authenticated_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL,
            "password": temp_password
        })
        assert login_response.status_code == 200, f"Login with new password failed: {login_response.text}"
        
        # Change password back to original
        new_token = login_response.json().get("token")
        authenticated_client.headers.update({"Authorization": f"Bearer {new_token}"})
        
        restore_response = authenticated_client.post(f"{BASE_URL}/api/auth/change-password", json={
            "current_password": temp_password,
            "new_password": OWNER_PASSWORD
        })
        assert restore_response.status_code == 200, f"Failed to restore password: {restore_response.text}"
        
        # Verify original password works again
        final_login = authenticated_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL,
            "password": OWNER_PASSWORD
        })
        assert final_login.status_code == 200, "Failed to login with restored password"
        
        # Update token for subsequent tests
        final_token = final_login.json().get("token")
        authenticated_client.headers.update({"Authorization": f"Bearer {final_token}"})
    
    def test_change_password_wrong_current(self, authenticated_client):
        """Test changing password with wrong current password returns 400"""
        response = authenticated_client.post(f"{BASE_URL}/api/auth/change-password", json={
            "current_password": "WrongPassword123!",
            "new_password": "NewPassword123!"
        })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        assert "Current password is incorrect" in data["detail"]
    
    def test_change_password_too_short(self, authenticated_client):
        """Test changing password with too short new password returns 400"""
        response = authenticated_client.post(f"{BASE_URL}/api/auth/change-password", json={
            "current_password": OWNER_PASSWORD,
            "new_password": "abc"  # Less than 6 characters
        })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        assert "at least 6 characters" in data["detail"]


class TestResetPassword:
    """Tests for POST /api/users/{user_id}/reset-password endpoint"""
    
    def test_reset_user_password(self, authenticated_client):
        """Test admin resetting another user's password"""
        # First get list of users to find a non-owner user
        users_response = authenticated_client.get(f"{BASE_URL}/api/users")
        assert users_response.status_code == 200, f"Failed to get users: {users_response.text}"
        
        users = users_response.json()
        assert len(users) > 0, "No users found"
        
        # Find a non-owner user (management role)
        target_user = None
        for user in users:
            if user.get("role") == "management" and user.get("is_active", True):
                target_user = user
                break
        
        if not target_user:
            pytest.skip("No active management user found for password reset test")
        
        user_id = target_user["id"]
        user_email = target_user["email"]
        user_name = target_user["name"]
        
        # Reset the user's password
        reset_response = authenticated_client.post(f"{BASE_URL}/api/users/{user_id}/reset-password")
        
        assert reset_response.status_code == 200, f"Expected 200, got {reset_response.status_code}: {reset_response.text}"
        data = reset_response.json()
        
        # Verify response structure
        assert "temp_password" in data, "Response should contain temp_password"
        assert "user_email" in data, "Response should contain user_email"
        assert "message" in data, "Response should contain message"
        
        assert data["user_email"] == user_email
        assert len(data["temp_password"]) >= 10, "Temp password should be at least 10 characters"
        
        temp_password = data["temp_password"]
        
        # Verify temp password works for login
        login_response = authenticated_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": user_email,
            "password": temp_password
        })
        assert login_response.status_code == 200, f"Login with temp password failed: {login_response.text}"
        
        login_data = login_response.json()
        assert "token" in login_data
        assert "user" in login_data
        assert login_data["user"]["email"] == user_email
        
        # Restore original password for the user
        user_token = login_data["token"]
        restore_headers = {"Authorization": f"Bearer {user_token}", "Content-Type": "application/json"}
        restore_response = requests.post(
            f"{BASE_URL}/api/auth/change-password",
            json={"current_password": temp_password, "new_password": MANAGEMENT_PASSWORD},
            headers=restore_headers
        )
        assert restore_response.status_code == 200, f"Failed to restore user password: {restore_response.text}"
    
    def test_reset_password_nonexistent_user(self, authenticated_client):
        """Test resetting password for non-existent user returns 404"""
        response = authenticated_client.post(f"{BASE_URL}/api/users/nonexistent_user_id/reset-password")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()


class TestPWAManifest:
    """Tests for PWA manifest.json"""
    
    def test_manifest_accessible(self, api_client):
        """Test manifest.json is accessible"""
        response = api_client.get(f"{BASE_URL}/manifest.json")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    def test_manifest_valid_json(self, api_client):
        """Test manifest.json is valid JSON with required fields"""
        response = api_client.get(f"{BASE_URL}/manifest.json")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check required fields
        assert data.get("name") == "Sarver Landscape QA", f"Expected name 'Sarver Landscape QA', got {data.get('name')}"
        assert data.get("display") == "standalone", f"Expected display 'standalone', got {data.get('display')}"
        assert data.get("theme_color") == "#243e36", f"Expected theme_color '#243e36', got {data.get('theme_color')}"
        assert data.get("background_color") == "#243e36", f"Expected background_color '#243e36', got {data.get('background_color')}"
        assert data.get("start_url") == "/", f"Expected start_url '/', got {data.get('start_url')}"
        
        # Check icons array
        assert "icons" in data, "manifest should have icons array"
        assert len(data["icons"]) > 0, "icons array should not be empty"
        
        icon = data["icons"][0]
        assert icon.get("src") == "/icon.svg", f"Expected icon src '/icon.svg', got {icon.get('src')}"
        assert icon.get("type") == "image/svg+xml", f"Expected icon type 'image/svg+xml', got {icon.get('type')}"


class TestPWAIcon:
    """Tests for PWA icon.svg"""
    
    def test_icon_accessible(self, api_client):
        """Test icon.svg is accessible"""
        response = api_client.get(f"{BASE_URL}/icon.svg")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    def test_icon_is_valid_svg(self, api_client):
        """Test icon.svg is valid SVG"""
        response = api_client.get(f"{BASE_URL}/icon.svg")
        assert response.status_code == 200
        
        content = response.text
        assert "<svg" in content, "Response should contain SVG element"
        assert "xmlns" in content, "SVG should have xmlns attribute"
        assert "</svg>" in content, "SVG should have closing tag"


class TestIndexHtmlPWATags:
    """Tests for PWA meta tags in index.html"""
    
    def test_index_html_accessible(self, api_client):
        """Test index.html is accessible"""
        response = api_client.get(f"{BASE_URL}/")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    def test_manifest_link_present(self, api_client):
        """Test index.html has manifest link"""
        response = api_client.get(f"{BASE_URL}/")
        assert response.status_code == 200
        
        content = response.text
        assert 'rel="manifest"' in content, "index.html should have manifest link"
        assert 'manifest.json' in content, "manifest link should point to manifest.json"
    
    def test_apple_mobile_web_app_capable(self, api_client):
        """Test index.html has apple-mobile-web-app-capable meta tag"""
        response = api_client.get(f"{BASE_URL}/")
        assert response.status_code == 200
        
        content = response.text
        assert 'apple-mobile-web-app-capable' in content, "index.html should have apple-mobile-web-app-capable meta tag"
        assert 'content="yes"' in content, "apple-mobile-web-app-capable should be set to yes"
    
    def test_theme_color_meta(self, api_client):
        """Test index.html has theme-color meta tag"""
        response = api_client.get(f"{BASE_URL}/")
        assert response.status_code == 200
        
        content = response.text
        assert 'name="theme-color"' in content, "index.html should have theme-color meta tag"
        assert '#243e36' in content, "theme-color should be #243e36"


class Test401Interceptor:
    """Tests for 401 interceptor behavior"""
    
    def test_invalid_token_returns_401(self, api_client):
        """Test that invalid token returns 401"""
        headers = {"Authorization": "Bearer invalid_token_12345"}
        response = api_client.get(f"{BASE_URL}/api/auth/me", headers=headers)
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
    
    def test_expired_token_format(self, api_client):
        """Test that malformed token returns 401"""
        headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"}
        response = api_client.get(f"{BASE_URL}/api/auth/me", headers=headers)
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
