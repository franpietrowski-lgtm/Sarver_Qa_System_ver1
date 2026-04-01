"""
Iteration 9 Backend Tests - Sarver Landscape QA System
Tests for:
- PATCH /api/crew-access-links/{id} - Crew QR metadata editing
- POST /api/public/equipment-logs - Equipment maintenance submission
- GET /api/equipment-logs - Equipment logs listing
- POST /api/equipment-logs/{id}/forward-to-owner - Red-tag notifications
- Dashboard overview endpoint
- Rapid review mobile lane
- Standards library and repeat offenders pages
"""
import os
import pytest
import requests
import io

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


class TestAuth:
    """Authentication tests"""

    def test_owner_login(self):
        """Owner can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "owner@fieldquality.local",
            "password": "FieldQA123!"
        })
        assert response.status_code == 200, f"Owner login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "owner"
        print("PASS: Owner login successful")

    def test_production_manager_login(self):
        """Production Manager can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "production.manager@fieldquality.local",
            "password": "FieldQA123!"
        })
        assert response.status_code == 200, f"PM login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "management"
        print("PASS: Production Manager login successful")


@pytest.fixture
def owner_token():
    """Get owner auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "owner@fieldquality.local",
        "password": "FieldQA123!"
    })
    if response.status_code != 200:
        pytest.skip("Owner login failed")
    return response.json()["token"]


@pytest.fixture
def pm_token():
    """Get production manager auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "production.manager@fieldquality.local",
        "password": "FieldQA123!"
    })
    if response.status_code != 200:
        pytest.skip("PM login failed")
    return response.json()["token"]


@pytest.fixture
def gm_token():
    """Get GM auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "gm@fieldquality.local",
        "password": "FieldQA123!"
    })
    if response.status_code != 200:
        pytest.skip("GM login failed")
    return response.json()["token"]


class TestCrewAccessLinkPatch:
    """Tests for PATCH /api/crew-access-links/{id} - Crew QR metadata editing"""

    def test_patch_crew_link_owner(self, owner_token):
        """Owner can update crew QR metadata"""
        # First get a crew link
        headers = {"Authorization": f"Bearer {owner_token}"}
        response = requests.get(f"{BASE_URL}/api/crew-access-links?status=active&page=1&limit=1", headers=headers)
        assert response.status_code == 200
        items = response.json().get("items", [])
        if not items:
            pytest.skip("No active crew links to test")
        
        crew_link_id = items[0]["id"]
        original_label = items[0]["label"]
        
        # Update the crew link
        update_payload = {
            "label": f"TEST_Updated_{original_label}",
            "truck_number": items[0]["truck_number"],
            "division": items[0]["division"],
            "assignment": "Test assignment update"
        }
        patch_response = requests.patch(
            f"{BASE_URL}/api/crew-access-links/{crew_link_id}",
            json=update_payload,
            headers=headers
        )
        assert patch_response.status_code == 200, f"PATCH failed: {patch_response.text}"
        updated = patch_response.json()
        assert updated["label"] == update_payload["label"]
        assert updated["assignment"] == "Test assignment update"
        print(f"PASS: Owner updated crew link {crew_link_id}")
        
        # Restore original
        restore_payload = {
            "label": original_label,
            "truck_number": items[0]["truck_number"],
            "division": items[0]["division"],
            "assignment": items[0].get("assignment", "")
        }
        requests.patch(f"{BASE_URL}/api/crew-access-links/{crew_link_id}", json=restore_payload, headers=headers)

    def test_patch_crew_link_management(self, pm_token):
        """Management can update crew QR metadata"""
        headers = {"Authorization": f"Bearer {pm_token}"}
        response = requests.get(f"{BASE_URL}/api/crew-access-links?status=active&page=1&limit=1", headers=headers)
        assert response.status_code == 200
        items = response.json().get("items", [])
        if not items:
            pytest.skip("No active crew links to test")
        
        crew_link_id = items[0]["id"]
        original_label = items[0]["label"]
        
        update_payload = {
            "label": f"TEST_PM_Updated_{original_label}",
            "truck_number": items[0]["truck_number"],
            "division": items[0]["division"],
            "assignment": "PM test assignment"
        }
        patch_response = requests.patch(
            f"{BASE_URL}/api/crew-access-links/{crew_link_id}",
            json=update_payload,
            headers=headers
        )
        assert patch_response.status_code == 200, f"PATCH failed: {patch_response.text}"
        print(f"PASS: Management updated crew link {crew_link_id}")
        
        # Restore original
        restore_payload = {
            "label": original_label,
            "truck_number": items[0]["truck_number"],
            "division": items[0]["division"],
            "assignment": items[0].get("assignment", "")
        }
        requests.patch(f"{BASE_URL}/api/crew-access-links/{crew_link_id}", json=restore_payload, headers=headers)

    def test_patch_crew_link_returns_updated_data(self, owner_token):
        """PATCH returns the updated crew link data"""
        headers = {"Authorization": f"Bearer {owner_token}"}
        response = requests.get(f"{BASE_URL}/api/crew-access-links?status=active&page=1&limit=1", headers=headers)
        items = response.json().get("items", [])
        if not items:
            pytest.skip("No active crew links to test")
        
        crew_link_id = items[0]["id"]
        update_payload = {
            "label": items[0]["label"],
            "truck_number": "TR-TEST-99",
            "division": "Install",
            "assignment": "Test route"
        }
        patch_response = requests.patch(
            f"{BASE_URL}/api/crew-access-links/{crew_link_id}",
            json=update_payload,
            headers=headers
        )
        assert patch_response.status_code == 200
        data = patch_response.json()
        assert "id" in data
        assert "code" in data
        assert "label" in data
        assert data["truck_number"] == "TR-TEST-99"
        print("PASS: PATCH returns complete updated crew link data")
        
        # Restore
        restore_payload = {
            "label": items[0]["label"],
            "truck_number": items[0]["truck_number"],
            "division": items[0]["division"],
            "assignment": items[0].get("assignment", "")
        }
        requests.patch(f"{BASE_URL}/api/crew-access-links/{crew_link_id}", json=restore_payload, headers=headers)


class TestEquipmentLogs:
    """Tests for equipment maintenance submission and listing"""

    def test_get_equipment_logs_owner(self, owner_token):
        """Owner can list equipment logs"""
        headers = {"Authorization": f"Bearer {owner_token}"}
        response = requests.get(f"{BASE_URL}/api/equipment-logs?page=1&limit=6", headers=headers)
        assert response.status_code == 200, f"GET equipment-logs failed: {response.text}"
        data = response.json()
        assert "items" in data
        assert "pagination" in data
        print(f"PASS: Owner can list equipment logs ({len(data['items'])} items)")

    def test_get_equipment_logs_management(self, pm_token):
        """Management can list equipment logs"""
        headers = {"Authorization": f"Bearer {pm_token}"}
        response = requests.get(f"{BASE_URL}/api/equipment-logs?page=1&limit=6", headers=headers)
        assert response.status_code == 200, f"GET equipment-logs failed: {response.text}"
        data = response.json()
        assert "items" in data
        print(f"PASS: Management can list equipment logs ({len(data['items'])} items)")

    def test_equipment_log_pagination(self, owner_token):
        """Equipment logs endpoint supports pagination"""
        headers = {"Authorization": f"Bearer {owner_token}"}
        response = requests.get(f"{BASE_URL}/api/equipment-logs?page=1&limit=2", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["limit"] == 2
        assert data["pagination"]["page"] == 1
        print("PASS: Equipment logs pagination works")


class TestEquipmentLogSubmission:
    """Tests for POST /api/public/equipment-logs"""

    def test_submit_equipment_log_requires_access_code(self):
        """Equipment log submission requires valid access code"""
        # Create fake image files
        pre_photo = io.BytesIO(b"fake pre image data")
        post_photo = io.BytesIO(b"fake post image data")
        
        files = {
            "pre_service_photo": ("pre.jpg", pre_photo, "image/jpeg"),
            "post_service_photo": ("post.jpg", post_photo, "image/jpeg"),
        }
        data = {
            "access_code": "invalid_code_xyz",
            "equipment_number": "EQ-TEST-001",
            "general_note": "Test note",
            "red_tag_note": ""
        }
        response = requests.post(f"{BASE_URL}/api/public/equipment-logs", data=data, files=files)
        assert response.status_code == 404, f"Expected 404 for invalid access code: {response.text}"
        print("PASS: Equipment log submission rejects invalid access code")

    def test_submit_equipment_log_with_valid_code(self):
        """Equipment log submission works with valid access code"""
        # First get a valid access code
        response = requests.get(f"{BASE_URL}/api/public/crew-access")
        if response.status_code != 200:
            pytest.skip("Cannot get public crew access")
        
        crew_links = response.json()
        if not crew_links:
            pytest.skip("No active crew links available")
        
        access_code = crew_links[0]["code"]
        
        # Create fake image files
        pre_photo = io.BytesIO(b"fake pre image data for test")
        post_photo = io.BytesIO(b"fake post image data for test")
        
        files = {
            "pre_service_photo": ("pre_test.jpg", pre_photo, "image/jpeg"),
            "post_service_photo": ("post_test.jpg", post_photo, "image/jpeg"),
        }
        data = {
            "access_code": access_code,
            "equipment_number": "TEST-EQ-001",
            "general_note": "Test equipment maintenance note",
            "red_tag_note": ""
        }
        response = requests.post(f"{BASE_URL}/api/public/equipment-logs", data=data, files=files)
        assert response.status_code == 200, f"Equipment log submission failed: {response.text}"
        result = response.json()
        assert "equipment_log" in result
        assert result["equipment_log"]["equipment_number"] == "TEST-EQ-001"
        print(f"PASS: Equipment log submitted successfully: {result['equipment_log']['id']}")

    def test_submit_equipment_log_with_red_tag(self):
        """Equipment log with red tag note creates red_tag_review status"""
        response = requests.get(f"{BASE_URL}/api/public/crew-access")
        if response.status_code != 200:
            pytest.skip("Cannot get public crew access")
        
        crew_links = response.json()
        if not crew_links:
            pytest.skip("No active crew links available")
        
        access_code = crew_links[0]["code"]
        
        pre_photo = io.BytesIO(b"fake pre image data red tag")
        post_photo = io.BytesIO(b"fake post image data red tag")
        
        files = {
            "pre_service_photo": ("pre_redtag.jpg", pre_photo, "image/jpeg"),
            "post_service_photo": ("post_redtag.jpg", post_photo, "image/jpeg"),
        }
        data = {
            "access_code": access_code,
            "equipment_number": "TEST-REDTAG-001",
            "general_note": "Equipment needs attention",
            "red_tag_note": "Blade damaged - needs replacement"
        }
        response = requests.post(f"{BASE_URL}/api/public/equipment-logs", data=data, files=files)
        assert response.status_code == 200, f"Red tag submission failed: {response.text}"
        result = response.json()
        assert result["equipment_log"]["status"] == "red_tag_review"
        assert result["equipment_log"]["red_tag_note"] == "Blade damaged - needs replacement"
        print(f"PASS: Red tag equipment log submitted: {result['equipment_log']['id']}")


class TestEquipmentForwardToOwner:
    """Tests for POST /api/equipment-logs/{id}/forward-to-owner"""

    def test_forward_requires_gm_or_owner(self, pm_token, owner_token):
        """Forward to owner requires GM title or owner role"""
        # First create an equipment log with red tag
        response = requests.get(f"{BASE_URL}/api/public/crew-access")
        if response.status_code != 200:
            pytest.skip("Cannot get public crew access")
        
        crew_links = response.json()
        if not crew_links:
            pytest.skip("No active crew links available")
        
        access_code = crew_links[0]["code"]
        
        pre_photo = io.BytesIO(b"forward test pre")
        post_photo = io.BytesIO(b"forward test post")
        
        files = {
            "pre_service_photo": ("pre_fwd.jpg", pre_photo, "image/jpeg"),
            "post_service_photo": ("post_fwd.jpg", post_photo, "image/jpeg"),
        }
        data = {
            "access_code": access_code,
            "equipment_number": "TEST-FWD-001",
            "general_note": "Forward test",
            "red_tag_note": "Needs owner review"
        }
        create_response = requests.post(f"{BASE_URL}/api/public/equipment-logs", data=data, files=files)
        if create_response.status_code != 200:
            pytest.skip("Could not create equipment log for forward test")
        
        log_id = create_response.json()["equipment_log"]["id"]
        
        # PM (not GM) should get 403
        pm_headers = {"Authorization": f"Bearer {pm_token}"}
        pm_response = requests.post(f"{BASE_URL}/api/equipment-logs/{log_id}/forward-to-owner", headers=pm_headers, json={})
        # PM with title "Production Manager" should get 403
        assert pm_response.status_code == 403, f"Expected 403 for non-GM PM: {pm_response.text}"
        print("PASS: Non-GM management cannot forward to owner")
        
        # Owner should succeed
        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        owner_response = requests.post(f"{BASE_URL}/api/equipment-logs/{log_id}/forward-to-owner", headers=owner_headers, json={})
        assert owner_response.status_code == 200, f"Owner forward failed: {owner_response.text}"
        print("PASS: Owner can forward equipment log")

    def test_gm_can_forward_to_owner(self, gm_token):
        """GM can forward equipment logs to owner"""
        # Create equipment log
        response = requests.get(f"{BASE_URL}/api/public/crew-access")
        if response.status_code != 200:
            pytest.skip("Cannot get public crew access")
        
        crew_links = response.json()
        if not crew_links:
            pytest.skip("No active crew links available")
        
        access_code = crew_links[0]["code"]
        
        pre_photo = io.BytesIO(b"gm forward test pre")
        post_photo = io.BytesIO(b"gm forward test post")
        
        files = {
            "pre_service_photo": ("pre_gm.jpg", pre_photo, "image/jpeg"),
            "post_service_photo": ("post_gm.jpg", post_photo, "image/jpeg"),
        }
        data = {
            "access_code": access_code,
            "equipment_number": "TEST-GM-FWD-001",
            "general_note": "GM forward test",
            "red_tag_note": "GM needs to forward this"
        }
        create_response = requests.post(f"{BASE_URL}/api/public/equipment-logs", data=data, files=files)
        if create_response.status_code != 200:
            pytest.skip("Could not create equipment log for GM forward test")
        
        log_id = create_response.json()["equipment_log"]["id"]
        
        headers = {"Authorization": f"Bearer {gm_token}"}
        forward_response = requests.post(f"{BASE_URL}/api/equipment-logs/{log_id}/forward-to-owner", headers=headers, json={})
        assert forward_response.status_code == 200, f"GM forward failed: {forward_response.text}"
        result = forward_response.json()
        assert result["status"] == "forwarded"
        print("PASS: GM can forward equipment log to owner")


class TestDashboardOverview:
    """Tests for dashboard overview endpoint"""

    def test_overview_owner(self, owner_token):
        """Owner can access dashboard overview"""
        headers = {"Authorization": f"Bearer {owner_token}"}
        response = requests.get(f"{BASE_URL}/api/dashboard/overview", headers=headers)
        assert response.status_code == 200, f"Overview failed: {response.text}"
        data = response.json()
        assert "totals" in data
        assert "queues" in data
        assert "workflow_health" in data
        print("PASS: Owner can access dashboard overview")

    def test_overview_management(self, pm_token):
        """Management can access dashboard overview"""
        headers = {"Authorization": f"Bearer {pm_token}"}
        response = requests.get(f"{BASE_URL}/api/dashboard/overview", headers=headers)
        assert response.status_code == 200, f"Overview failed: {response.text}"
        data = response.json()
        assert "totals" in data
        print("PASS: Management can access dashboard overview")


class TestRapidReviewQueue:
    """Tests for rapid review queue"""

    def test_rapid_review_queue_owner(self, owner_token):
        """Owner can access rapid review queue"""
        headers = {"Authorization": f"Bearer {owner_token}"}
        response = requests.get(f"{BASE_URL}/api/rapid-reviews/queue?page=1&limit=20", headers=headers)
        assert response.status_code == 200, f"Rapid review queue failed: {response.text}"
        data = response.json()
        assert "items" in data
        assert "pagination" in data
        print(f"PASS: Owner can access rapid review queue ({len(data['items'])} items)")

    def test_rapid_review_queue_management(self, pm_token):
        """Management can access rapid review queue"""
        headers = {"Authorization": f"Bearer {pm_token}"}
        response = requests.get(f"{BASE_URL}/api/rapid-reviews/queue?page=1&limit=20", headers=headers)
        assert response.status_code == 200, f"Rapid review queue failed: {response.text}"
        print("PASS: Management can access rapid review queue")


class TestStandardsLibrary:
    """Tests for standards library endpoint"""

    def test_standards_list_owner(self, owner_token):
        """Owner can list standards"""
        headers = {"Authorization": f"Bearer {owner_token}"}
        response = requests.get(f"{BASE_URL}/api/standards?page=1&limit=10", headers=headers)
        assert response.status_code == 200, f"Standards list failed: {response.text}"
        data = response.json()
        assert "items" in data
        print(f"PASS: Owner can list standards ({len(data['items'])} items)")

    def test_standards_list_management(self, pm_token):
        """Management can list standards"""
        headers = {"Authorization": f"Bearer {pm_token}"}
        response = requests.get(f"{BASE_URL}/api/standards?page=1&limit=10", headers=headers)
        assert response.status_code == 200, f"Standards list failed: {response.text}"
        print("PASS: Management can list standards")


class TestRepeatOffenders:
    """Tests for repeat offenders endpoint"""

    def test_repeat_offenders_owner(self, owner_token):
        """Owner can access repeat offenders"""
        headers = {"Authorization": f"Bearer {owner_token}"}
        response = requests.get(f"{BASE_URL}/api/repeat-offenders?window_days=30", headers=headers)
        assert response.status_code == 200, f"Repeat offenders failed: {response.text}"
        data = response.json()
        assert "crew_summaries" in data
        assert "heatmap" in data
        print("PASS: Owner can access repeat offenders")

    def test_repeat_offenders_management(self, pm_token):
        """Management can access repeat offenders"""
        headers = {"Authorization": f"Bearer {pm_token}"}
        response = requests.get(f"{BASE_URL}/api/repeat-offenders?window_days=30", headers=headers)
        assert response.status_code == 200, f"Repeat offenders failed: {response.text}"
        print("PASS: Management can access repeat offenders")


class TestNotifications:
    """Tests for notifications endpoint"""

    def test_notifications_owner(self, owner_token):
        """Owner can access notifications"""
        headers = {"Authorization": f"Bearer {owner_token}"}
        response = requests.get(f"{BASE_URL}/api/notifications?page=1&limit=10", headers=headers)
        assert response.status_code == 200, f"Notifications failed: {response.text}"
        data = response.json()
        assert "items" in data
        print(f"PASS: Owner can access notifications ({len(data['items'])} items)")

    def test_notifications_management(self, pm_token):
        """Management can access notifications"""
        headers = {"Authorization": f"Bearer {pm_token}"}
        response = requests.get(f"{BASE_URL}/api/notifications?page=1&limit=10", headers=headers)
        assert response.status_code == 200, f"Notifications failed: {response.text}"
        print("PASS: Management can access notifications")
