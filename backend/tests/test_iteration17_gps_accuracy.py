"""
Iteration 17: GPS Accuracy Feature Tests
Tests the gps_low_confidence flag on submissions based on gps_accuracy value.
- gps_low_confidence should be true when gps_accuracy > 2.0
- gps_low_confidence should be false when gps_accuracy <= 2.0
Also includes regression tests for auth, submissions, and dashboard.
"""
import pytest
import requests
import os
import io
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
OWNER_EMAIL = "sadam.owner@slmco.local"
GM_EMAIL = "ctyler.gm@slmco.local"
PASSWORD = "SLMCo2026!"
CREW_ACCESS_CODE = "000a07ca"

# Unique test run ID to avoid duplicate submission conflicts
TEST_RUN_ID = str(int(time.time()))


class TestGPSAccuracyFeature:
    """Tests for the GPS accuracy improvement feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_auth_token(self, email=GM_EMAIL, password=PASSWORD):
        """Get authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def create_test_photo(self, name="test_photo.jpg"):
        """Create a minimal test photo file"""
        # Minimal valid JPEG bytes
        jpeg_bytes = bytes([
            0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
            0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
            0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
            0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
            0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
            0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
            0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
            0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
            0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
            0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
            0x09, 0x0A, 0x0B, 0xFF, 0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
            0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7D,
            0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06,
            0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08,
            0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1, 0xF0, 0x24, 0x33, 0x62, 0x72,
            0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x25, 0x26, 0x27, 0x28,
            0x29, 0x2A, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45,
            0x46, 0x47, 0x48, 0x49, 0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59,
            0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75,
            0x76, 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
            0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3,
            0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6,
            0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9,
            0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xE1, 0xE2,
            0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF1, 0xF2, 0xF3, 0xF4,
            0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01,
            0x00, 0x00, 0x3F, 0x00, 0xFB, 0xD5, 0xFF, 0xD9
        ])
        return (name, io.BytesIO(jpeg_bytes), "image/jpeg")
    
    def test_submission_with_low_gps_accuracy_flagged(self):
        """Test that submissions with gps_accuracy > 2.0 have gps_low_confidence: true"""
        # Create multipart form data with gps_accuracy > 2.0
        files = [
            ("photos", self.create_test_photo("photo1.jpg")),
            ("photos", self.create_test_photo("photo2.jpg")),
            ("photos", self.create_test_photo("photo3.jpg")),
        ]
        data = {
            "access_code": CREW_ACCESS_CODE,
            "job_name": f"TEST_GPS_Low_Accuracy_{TEST_RUN_ID}",
            "task_type": "Bed edging",
            "truck_number": "T-101",
            "gps_lat": 40.7128,
            "gps_lng": -74.0060,
            "gps_accuracy": 5.5,  # > 2.0 meters - should flag as low confidence
            "note": "Test submission with low GPS accuracy",
            "area_tag": "Front yard",
            "work_date": "2026-01-15",
        }
        
        response = requests.post(
            f"{BASE_URL}/api/public/submissions",
            data=data,
            files=files
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        result = response.json()
        
        # Verify gps_low_confidence is true
        submission = result.get("submission", {})
        assert "gps_low_confidence" in submission, "gps_low_confidence field missing from response"
        assert submission["gps_low_confidence"] == True, f"Expected gps_low_confidence=True for accuracy 5.5m, got {submission['gps_low_confidence']}"
        
        # Verify GPS data is stored correctly
        gps = submission.get("gps", {})
        assert gps.get("accuracy") == 5.5, f"Expected gps.accuracy=5.5, got {gps.get('accuracy')}"
        
        print(f"✓ Submission with gps_accuracy=5.5m correctly flagged with gps_low_confidence=True")
    
    def test_submission_with_high_gps_accuracy_not_flagged(self):
        """Test that submissions with gps_accuracy <= 2.0 have gps_low_confidence: false"""
        files = [
            ("photos", self.create_test_photo("photo1.jpg")),
            ("photos", self.create_test_photo("photo2.jpg")),
            ("photos", self.create_test_photo("photo3.jpg")),
        ]
        data = {
            "access_code": CREW_ACCESS_CODE,
            "job_name": f"TEST_GPS_High_Accuracy_{TEST_RUN_ID}",
            "task_type": "Pruning",
            "truck_number": "T-102",
            "gps_lat": 40.7589,
            "gps_lng": -73.9851,
            "gps_accuracy": 1.5,  # <= 2.0 meters - should NOT flag as low confidence
            "note": "Test submission with high GPS accuracy",
            "area_tag": "Back yard",
            "work_date": "2026-01-15",
        }
        
        response = requests.post(
            f"{BASE_URL}/api/public/submissions",
            data=data,
            files=files
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        result = response.json()
        
        # Verify gps_low_confidence is false
        submission = result.get("submission", {})
        assert "gps_low_confidence" in submission, "gps_low_confidence field missing from response"
        assert submission["gps_low_confidence"] == False, f"Expected gps_low_confidence=False for accuracy 1.5m, got {submission['gps_low_confidence']}"
        
        # Verify GPS data is stored correctly
        gps = submission.get("gps", {})
        assert gps.get("accuracy") == 1.5, f"Expected gps.accuracy=1.5, got {gps.get('accuracy')}"
        
        print(f"✓ Submission with gps_accuracy=1.5m correctly has gps_low_confidence=False")
    
    def test_submission_with_exact_threshold_accuracy(self):
        """Test that submissions with gps_accuracy = 2.0 exactly have gps_low_confidence: false"""
        files = [
            ("photos", self.create_test_photo("photo1.jpg")),
            ("photos", self.create_test_photo("photo2.jpg")),
            ("photos", self.create_test_photo("photo3.jpg")),
        ]
        data = {
            "access_code": CREW_ACCESS_CODE,
            "job_name": f"TEST_GPS_Exact_Threshold_{TEST_RUN_ID}",
            "task_type": "Weeding",
            "truck_number": "T-103",
            "gps_lat": 40.7484,
            "gps_lng": -73.9857,
            "gps_accuracy": 2.0,  # Exactly 2.0 meters - should NOT flag (boundary case)
            "note": "Test submission with exact threshold GPS accuracy",
            "area_tag": "Side yard",
            "work_date": "2026-01-15",
        }
        
        response = requests.post(
            f"{BASE_URL}/api/public/submissions",
            data=data,
            files=files
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        result = response.json()
        
        # Verify gps_low_confidence is false (2.0 is NOT > 2.0)
        submission = result.get("submission", {})
        assert "gps_low_confidence" in submission, "gps_low_confidence field missing from response"
        assert submission["gps_low_confidence"] == False, f"Expected gps_low_confidence=False for accuracy 2.0m (boundary), got {submission['gps_low_confidence']}"
        
        print(f"✓ Submission with gps_accuracy=2.0m (boundary) correctly has gps_low_confidence=False")
    
    def test_submission_with_just_above_threshold_accuracy(self):
        """Test that submissions with gps_accuracy = 2.1 have gps_low_confidence: true"""
        files = [
            ("photos", self.create_test_photo("photo1.jpg")),
            ("photos", self.create_test_photo("photo2.jpg")),
            ("photos", self.create_test_photo("photo3.jpg")),
        ]
        data = {
            "access_code": CREW_ACCESS_CODE,
            "job_name": f"TEST_GPS_Above_Threshold_{TEST_RUN_ID}",
            "task_type": "Mulching",
            "truck_number": "T-104",
            "gps_lat": 40.7614,
            "gps_lng": -73.9776,
            "gps_accuracy": 2.1,  # Just above 2.0 meters - should flag
            "note": "Test submission with just above threshold GPS accuracy",
            "area_tag": "Garden bed",
            "work_date": "2026-01-15",
        }
        
        response = requests.post(
            f"{BASE_URL}/api/public/submissions",
            data=data,
            files=files
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        result = response.json()
        
        # Verify gps_low_confidence is true (2.1 > 2.0)
        submission = result.get("submission", {})
        assert "gps_low_confidence" in submission, "gps_low_confidence field missing from response"
        assert submission["gps_low_confidence"] == True, f"Expected gps_low_confidence=True for accuracy 2.1m, got {submission['gps_low_confidence']}"
        
        print(f"✓ Submission with gps_accuracy=2.1m correctly flagged with gps_low_confidence=True")


class TestRegressionEndpoints:
    """Regression tests for existing endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_auth_login_works(self):
        """Regression: POST /api/auth/login still works"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": GM_EMAIL,
            "password": PASSWORD
        })
        
        assert response.status_code == 200, f"Login failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "token" in data, "token missing from login response"
        assert "user" in data, "user missing from login response"
        print(f"✓ POST /api/auth/login works - logged in as {data['user'].get('email')}")
    
    def test_get_submissions_works(self):
        """Regression: GET /api/submissions still works"""
        # Login first
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": GM_EMAIL,
            "password": PASSWORD
        })
        token = login_response.json().get("token")
        
        # Get submissions
        response = self.session.get(
            f"{BASE_URL}/api/submissions",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"GET /api/submissions failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "items" in data or isinstance(data, list), "Expected items array or list in response"
        print(f"✓ GET /api/submissions works - returned {len(data.get('items', data))} submissions")
    
    def test_dashboard_overview_works(self):
        """Regression: GET /api/dashboard/overview still works"""
        # Login first
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": GM_EMAIL,
            "password": PASSWORD
        })
        token = login_response.json().get("token")
        
        # Get dashboard overview
        response = self.session.get(
            f"{BASE_URL}/api/dashboard/overview",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"GET /api/dashboard/overview failed: {response.status_code} - {response.text}"
        data = response.json()
        # Dashboard should have some stats
        assert isinstance(data, dict), "Expected dict response from dashboard"
        print(f"✓ GET /api/dashboard/overview works")
    
    def test_public_crew_access_works(self):
        """Regression: GET /api/public/crew-access/{code} still works"""
        response = self.session.get(f"{BASE_URL}/api/public/crew-access/{CREW_ACCESS_CODE}")
        
        assert response.status_code == 200, f"GET /api/public/crew-access/{CREW_ACCESS_CODE} failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "code" in data or "label" in data, "Expected crew access data in response"
        print(f"✓ GET /api/public/crew-access/{CREW_ACCESS_CODE} works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
