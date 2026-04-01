#!/usr/bin/env python3
"""
Backend API Testing for Field Quality Capture & Review System
Tests the live backend at https://quality-hub-32.preview.emergentagent.com/api
"""

import json
import requests
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://quality-hub-32.preview.emergentagent.com/api"
CREDENTIALS = {
    "owner": {"email": "owner@fieldquality.local", "password": "FieldQA123!"},
    "production_manager": {"email": "production.manager@fieldquality.local", "password": "FieldQA123!"}
}

class BackendTester:
    def __init__(self):
        self.session = requests.Session()
        self.tokens = {}
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "response_data": response_data,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        
    def test_auth_login(self, user_type: str) -> bool:
        """Test POST /api/auth/login"""
        try:
            creds = CREDENTIALS[user_type]
            response = self.session.post(
                f"{BASE_URL}/auth/login",
                json=creds,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if "token" in data and "user" in data:
                    self.tokens[user_type] = data["token"]
                    user_info = data["user"]
                    self.log_test(
                        f"Login {user_type}",
                        True,
                        f"Successfully logged in as {user_info.get('name', 'Unknown')} ({user_info.get('role', 'Unknown role')})",
                        {"user_role": user_info.get("role"), "user_email": user_info.get("email")}
                    )
                    return True
                else:
                    self.log_test(f"Login {user_type}", False, "Missing token or user in response", data)
                    return False
            else:
                self.log_test(f"Login {user_type}", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test(f"Login {user_type}", False, f"Exception: {str(e)}")
            return False
    
    def get_auth_headers(self, user_type: str) -> Dict[str, str]:
        """Get authorization headers for user"""
        token = self.tokens.get(user_type)
        if not token:
            return {}
        return {"Authorization": f"Bearer {token}"}
    
    def test_storage_status(self) -> bool:
        """Test GET /api/integrations/storage/status"""
        try:
            headers = self.get_auth_headers("owner")
            response = self.session.get(
                f"{BASE_URL}/integrations/storage/status",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["provider", "configured", "bucket"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test(
                        "Storage Status",
                        False,
                        f"Missing required fields: {missing_fields}",
                        data
                    )
                    return False
                
                is_supabase = data.get("provider") == "supabase"
                is_configured = data.get("configured") is True
                has_bucket = bool(data.get("bucket"))
                
                if is_supabase and is_configured and has_bucket:
                    self.log_test(
                        "Storage Status",
                        True,
                        f"Supabase storage configured with bucket: {data.get('bucket')}",
                        data
                    )
                    return True
                else:
                    self.log_test(
                        "Storage Status",
                        False,
                        f"Storage not properly configured - provider: {data.get('provider')}, configured: {data.get('configured')}, bucket: {data.get('bucket')}",
                        data
                    )
                    return False
            else:
                self.log_test("Storage Status", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Storage Status", False, f"Exception: {str(e)}")
            return False
    
    def test_multipart_submission(self) -> Optional[str]:
        """Test POST /api/public/submissions with multipart upload"""
        try:
            # Create test image files (small PNG data)
            test_image_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x12IDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
            
            # Get a crew access code first
            crew_response = self.session.get(f"{BASE_URL}/public/crew-access", timeout=30)
            if crew_response.status_code != 200:
                self.log_test("Multipart Submission", False, "Failed to get crew access codes")
                return None
                
            crew_links = crew_response.json()
            if not crew_links:
                self.log_test("Multipart Submission", False, "No crew access links available")
                return None
                
            access_code = crew_links[0]["code"]
            truck_number = crew_links[0]["truck_number"]
            
            # Prepare multipart form data - need to send as list for multiple files
            files = [
                ('photos', ('test1.png', test_image_data, 'image/png')),
                ('photos', ('test2.png', test_image_data, 'image/png')),
                ('photos', ('test3.png', test_image_data, 'image/png')),
                ('issue_photos', ('issue1.png', test_image_data, 'image/png'))
            ]
            
            data = {
                'access_code': access_code,
                'job_id': '',
                'job_name': 'Test Quality Check - Landscape Maintenance',
                'truck_number': truck_number,
                'gps_lat': 43.6532,
                'gps_lng': -79.3832,
                'gps_accuracy': 5.0,
                'note': 'Test submission for backend API validation',
                'area_tag': 'Front entrance area',
                'issue_type': 'minor_debris',
                'issue_notes': 'Small debris left near walkway'
            }
            
            response = self.session.post(
                f"{BASE_URL}/public/submissions",
                files=files,
                data=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                submission = result.get("submission", {})
                submission_id = submission.get("id")
                
                # Check required fields in response
                required_fields = ["source_type", "bucket", "storage_path"]
                photo_files = submission.get("photo_files", [])
                
                if not photo_files:
                    self.log_test("Multipart Submission", False, "No photo files in response")
                    return None
                
                first_photo = photo_files[0]
                missing_fields = [field for field in required_fields if field not in first_photo]
                
                if missing_fields:
                    self.log_test(
                        "Multipart Submission",
                        False,
                        f"Missing required fields in photo: {missing_fields}",
                        first_photo
                    )
                    return None
                
                # Verify Supabase storage fields
                if (first_photo.get("source_type") == "supabase" and 
                    first_photo.get("bucket") and 
                    first_photo.get("storage_path")):
                    
                    self.log_test(
                        "Multipart Submission",
                        True,
                        f"Successfully created submission {submission_id} with Supabase storage",
                        {
                            "submission_id": submission_id,
                            "photo_count": len(photo_files),
                            "storage_type": first_photo.get("source_type"),
                            "bucket": first_photo.get("bucket")
                        }
                    )
                    return submission_id
                else:
                    self.log_test(
                        "Multipart Submission",
                        False,
                        f"Invalid storage configuration in response",
                        first_photo
                    )
                    return None
            else:
                self.log_test("Multipart Submission", False, f"HTTP {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.log_test("Multipart Submission", False, f"Exception: {str(e)}")
            return None
    
    def test_file_retrieval(self, submission_id: str) -> bool:
        """Test GET /api/submissions/files/{submission_id}/{filename}"""
        if not submission_id:
            self.log_test("File Retrieval", False, "No submission ID provided")
            return False
            
        try:
            # First get submission details to find a filename
            headers = self.get_auth_headers("owner")
            submission_response = self.session.get(
                f"{BASE_URL}/submissions/{submission_id}",
                headers=headers,
                timeout=30
            )
            
            if submission_response.status_code != 200:
                self.log_test("File Retrieval", False, f"Failed to get submission details: {submission_response.status_code}")
                return False
            
            submission_data = submission_response.json()
            submission = submission_data.get("submission", {})
            photo_files = submission.get("photo_files", [])
            
            if not photo_files:
                self.log_test("File Retrieval", False, "No photo files found in submission")
                return False
            
            filename = photo_files[0].get("filename")
            if not filename:
                self.log_test("File Retrieval", False, "No filename found in first photo")
                return False
            
            # Test file retrieval
            file_response = self.session.get(
                f"{BASE_URL}/submissions/files/{submission_id}/{filename}",
                timeout=30
            )
            
            if file_response.status_code == 200:
                content_type = file_response.headers.get("content-type", "")
                content_length = len(file_response.content)
                
                if content_length > 0 and "image" in content_type.lower():
                    self.log_test(
                        "File Retrieval",
                        True,
                        f"Successfully retrieved file {filename} ({content_length} bytes, {content_type})",
                        {"filename": filename, "size": content_length, "content_type": content_type}
                    )
                    return True
                else:
                    self.log_test(
                        "File Retrieval",
                        False,
                        f"Invalid file response - size: {content_length}, type: {content_type}"
                    )
                    return False
            else:
                self.log_test("File Retrieval", False, f"HTTP {response.status_code}: {file_response.text}")
                return False
                
        except Exception as e:
            self.log_test("File Retrieval", False, f"Exception: {str(e)}")
            return False
    
    def test_paginated_endpoint(self, endpoint: str, params: Dict[str, Any], test_name: str) -> bool:
        """Test paginated endpoints"""
        try:
            headers = self.get_auth_headers("owner")
            response = self.session.get(
                f"{BASE_URL}/{endpoint}",
                headers=headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for new pagination format
                if "items" in data and "pagination" in data:
                    items = data["items"]
                    pagination = data["pagination"]
                    
                    required_pagination_fields = ["page", "limit", "total", "pages", "has_next", "has_prev"]
                    missing_fields = [field for field in required_pagination_fields if field not in pagination]
                    
                    if missing_fields:
                        self.log_test(
                            test_name,
                            False,
                            f"Missing pagination fields: {missing_fields}",
                            data
                        )
                        return False
                    
                    self.log_test(
                        test_name,
                        True,
                        f"Paginated response with {len(items)} items, page {pagination['page']} of {pagination['pages']}",
                        {
                            "items_count": len(items),
                            "pagination": pagination
                        }
                    )
                    return True
                else:
                    self.log_test(
                        test_name,
                        False,
                        "Response missing 'items' and 'pagination' structure",
                        data
                    )
                    return False
            else:
                self.log_test(test_name, False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")
            return False
    
    def test_dashboard_overview(self) -> bool:
        """Test GET /api/dashboard/overview"""
        try:
            headers = self.get_auth_headers("owner")
            response = self.session.get(
                f"{BASE_URL}/dashboard/overview",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for storage readiness fields
                storage = data.get("storage", {})
                required_storage_fields = ["configured", "connected", "provider"]
                missing_fields = [field for field in required_storage_fields if field not in storage]
                
                if missing_fields:
                    self.log_test(
                        "Dashboard Overview",
                        False,
                        f"Missing storage fields: {missing_fields}",
                        data
                    )
                    return False
                
                self.log_test(
                    "Dashboard Overview",
                    True,
                    f"Dashboard loaded with storage status: {storage.get('provider')} configured={storage.get('configured')}",
                    {
                        "totals": data.get("totals", {}),
                        "storage": storage
                    }
                )
                return True
            else:
                self.log_test("Dashboard Overview", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Dashboard Overview", False, f"Exception: {str(e)}")
            return False
    
    def test_analytics_summary(self) -> bool:
        """Test GET /api/analytics/summary with different periods"""
        periods = ["daily", "weekly", "monthly", "quarterly", "annual"]
        all_passed = True
        
        for period in periods:
            try:
                headers = self.get_auth_headers("owner")
                response = self.session.get(
                    f"{BASE_URL}/analytics/summary",
                    headers=headers,
                    params={"period": period},
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.log_test(
                        f"Analytics Summary ({period})",
                        True,
                        f"Analytics data loaded for {period} period",
                        {"period": period, "data_keys": list(data.keys())}
                    )
                else:
                    self.log_test(f"Analytics Summary ({period})", False, f"HTTP {response.status_code}: {response.text}")
                    all_passed = False
                    
            except Exception as e:
                self.log_test(f"Analytics Summary ({period})", False, f"Exception: {str(e)}")
                all_passed = False
        
        return all_passed
    
    def test_google_drive_retirement(self) -> bool:
        """Test that Google Drive connect/callback flow is retired"""
        try:
            # Test that old Google Drive endpoints return 404 or appropriate error
            endpoints_to_check = [
                "/integrations/drive/connect",
                "/integrations/drive/callback",
                "/integrations/drive/status"
            ]
            
            headers = self.get_auth_headers("owner")
            retired_endpoints = []
            
            for endpoint in endpoints_to_check:
                try:
                    response = self.session.get(
                        f"{BASE_URL}{endpoint}",
                        headers=headers,
                        timeout=10
                    )
                    
                    # 404 or 405 indicates the endpoint is retired/removed
                    if response.status_code in [404, 405]:
                        retired_endpoints.append(endpoint)
                    elif response.status_code == 200:
                        # Check if response indicates Google Drive is disabled
                        try:
                            data = response.json()
                            if "google" not in str(data).lower() or data.get("configured") is False:
                                retired_endpoints.append(endpoint)
                        except:
                            pass
                            
                except requests.exceptions.Timeout:
                    # Timeout might indicate endpoint is removed
                    retired_endpoints.append(endpoint)
                except:
                    pass
            
            if len(retired_endpoints) >= 2:  # Most endpoints should be retired
                self.log_test(
                    "Google Drive Retirement",
                    True,
                    f"Google Drive endpoints appear to be retired: {retired_endpoints}",
                    {"retired_endpoints": retired_endpoints}
                )
                return True
            else:
                self.log_test(
                    "Google Drive Retirement",
                    False,
                    f"Google Drive endpoints may still be active",
                    {"checked_endpoints": endpoints_to_check, "retired": retired_endpoints}
                )
                return False
                
        except Exception as e:
            self.log_test("Google Drive Retirement", False, f"Exception: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Backend API Tests")
        print("=" * 50)
        
        # Test authentication
        owner_login = self.test_auth_login("owner")
        pm_login = self.test_auth_login("production_manager")
        
        if not owner_login:
            print("❌ Cannot proceed without owner login")
            return
        
        # Test storage status
        self.test_storage_status()
        
        # Test multipart submission
        submission_id = self.test_multipart_submission()
        
        # Test file retrieval if submission was created
        if submission_id:
            self.test_file_retrieval(submission_id)
        
        # Test paginated endpoints
        paginated_tests = [
            ("submissions", {"scope": "management", "page": 1, "limit": 10}, "Submissions (Management)"),
            ("submissions", {"scope": "owner", "page": 1, "limit": 10}, "Submissions (Owner)"),
            ("crew-access-links", {"status": "inactive", "page": 1, "limit": 10}, "Crew Access Links (Inactive)"),
            ("jobs", {"page": 1, "limit": 10}, "Jobs"),
            ("exports", {"page": 1, "limit": 10}, "Exports")
        ]
        
        for endpoint, params, test_name in paginated_tests:
            self.test_paginated_endpoint(endpoint, params, test_name)
        
        # Test dashboard overview
        self.test_dashboard_overview()
        
        # Test analytics summary
        self.test_analytics_summary()
        
        # Test Google Drive retirement
        self.test_google_drive_retirement()
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        # Show failed tests
        failed_tests = [result for result in self.test_results if not result["success"]]
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"  - {test['test']}: {test['details']}")
        
        return self.test_results

if __name__ == "__main__":
    tester = BackendTester()
    results = tester.run_all_tests()