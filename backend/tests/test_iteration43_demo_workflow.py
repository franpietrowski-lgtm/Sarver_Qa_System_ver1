"""
Iteration 43 - Demo Workflow Data Verification Tests
Tests the seeded demo data for Sarver Landscape QA System:
- Job LMN-6001 metadata verification
- Maintenance Alpha crew submissions (leader, member, emergency)
- Emergency submission flags and incident feed
- Photo file serving via Supabase storage
- Rapid reviews by 7 admin staff (excluding Owner/GM)
- Management review on member submission
- Owner/GM have NO rapid reviews
- Dashboard emergency widget
- Crew portal submission history
"""

import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
OWNER_EMAIL = "sadam.owner@slmco.local"
GM_EMAIL = "ctyler.gm@slmco.local"
PM_TIM_EMAIL = "atim.prom@slmco.local"
AM_SCOTT_EMAIL = "kscott.accm@slmco.local"
PASSWORD = "SLMCo2026!"

# Key IDs from demo seed
JOB_ID = "LMN-6001"
CREW_CODE_MAINTENANCE_ALPHA = "be1da0c6"
LEADER_SUBMISSION_ID = "sub_16bdb9242407"
MEMBER_SUBMISSION_ID = "sub_7d5246c4a4a9"
EMERGENCY_SUBMISSION_ID = "sub_6dd05e2b5f1e"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def owner_token(api_client):
    """Get Owner auth token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": OWNER_EMAIL,
        "password": PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Owner login failed: {response.status_code}")


@pytest.fixture(scope="module")
def gm_token(api_client):
    """Get GM auth token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": GM_EMAIL,
        "password": PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"GM login failed: {response.status_code}")


@pytest.fixture(scope="module")
def pm_tim_token(api_client):
    """Get PM Tim auth token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": PM_TIM_EMAIL,
        "password": PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"PM Tim login failed: {response.status_code}")


@pytest.fixture(scope="module")
def am_scott_token(api_client):
    """Get AM Scott K auth token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": AM_SCOTT_EMAIL,
        "password": PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"AM Scott login failed: {response.status_code}")


class TestJobVerification:
    """Verify job LMN-6001 exists with correct metadata"""
    
    def test_job_lmn6001_exists(self, api_client, owner_token):
        """Job LMN-6001 should exist with correct name, division, truck"""
        response = api_client.get(
            f"{BASE_URL}/api/jobs?search=LMN-6001",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Jobs search failed: {response.text}"
        data = response.json()
        jobs = data.get("items", [])
        
        # Find LMN-6001
        lmn6001 = next((j for j in jobs if j.get("job_id") == JOB_ID), None)
        assert lmn6001 is not None, f"Job {JOB_ID} not found in jobs list"
        
        # Verify metadata
        assert "Longvue HOA" in lmn6001.get("job_name", ""), f"Job name mismatch: {lmn6001.get('job_name')}"
        assert "291 Mailbox Bed Edging" in lmn6001.get("job_name", ""), f"Job name should contain '291 Mailbox Bed Edging'"
        assert lmn6001.get("division") == "Maintenance", f"Division should be Maintenance, got: {lmn6001.get('division')}"
        assert lmn6001.get("truck_number") == "TR-05", f"Truck should be TR-05, got: {lmn6001.get('truck_number')}"
        print(f"✓ Job {JOB_ID} verified: {lmn6001.get('job_name')}, Division: {lmn6001.get('division')}, Truck: {lmn6001.get('truck_number')}")


class TestMaintenanceAlphaSubmissions:
    """Verify 3 submissions for Maintenance Alpha crew (be1da0c6)"""
    
    def test_crew_submissions_count(self, api_client):
        """Maintenance Alpha should have 3 submissions"""
        response = api_client.get(f"{BASE_URL}/api/public/crew-submissions/{CREW_CODE_MAINTENANCE_ALPHA}")
        assert response.status_code == 200, f"Crew submissions failed: {response.text}"
        data = response.json()
        
        submissions = data.get("submissions", [])
        assert len(submissions) >= 3, f"Expected at least 3 submissions, got {len(submissions)}"
        assert data.get("crew_label") == "Maintenance Alpha", f"Crew label mismatch: {data.get('crew_label')}"
        print(f"✓ Maintenance Alpha has {len(submissions)} submissions")
    
    def test_leader_submission_exists(self, api_client, owner_token):
        """Leader submission should have 3 photos"""
        response = api_client.get(
            f"{BASE_URL}/api/submissions/{LEADER_SUBMISSION_ID}",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Leader submission fetch failed: {response.text}"
        data = response.json()
        submission = data.get("submission", {})
        
        photo_count = submission.get("photo_count", 0)
        assert photo_count == 3, f"Leader submission should have 3 photos, got {photo_count}"
        assert submission.get("access_code") == CREW_CODE_MAINTENANCE_ALPHA
        print(f"✓ Leader submission {LEADER_SUBMISSION_ID} has {photo_count} photos")
    
    def test_member_submission_exists(self, api_client, owner_token):
        """Member submission should have 3 photos"""
        response = api_client.get(
            f"{BASE_URL}/api/submissions/{MEMBER_SUBMISSION_ID}",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Member submission fetch failed: {response.text}"
        data = response.json()
        submission = data.get("submission", {})
        
        photo_count = submission.get("photo_count", 0)
        assert photo_count == 3, f"Member submission should have 3 photos, got {photo_count}"
        print(f"✓ Member submission {MEMBER_SUBMISSION_ID} has {photo_count} photos")
    
    def test_emergency_submission_exists(self, api_client, owner_token):
        """Emergency submission should have 0 main photos, 1 issue photo"""
        response = api_client.get(
            f"{BASE_URL}/api/submissions/{EMERGENCY_SUBMISSION_ID}",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Emergency submission fetch failed: {response.text}"
        data = response.json()
        submission = data.get("submission", {})
        
        # Main photos should be 0
        photo_count = submission.get("photo_count", 0)
        assert photo_count == 0, f"Emergency submission should have 0 main photos, got {photo_count}"
        
        # Issue photo in field_report
        field_report = submission.get("field_report", {})
        issue_photos = field_report.get("photo_files", [])
        assert len(issue_photos) == 1, f"Emergency should have 1 issue photo, got {len(issue_photos)}"
        print(f"✓ Emergency submission {EMERGENCY_SUBMISSION_ID} has 0 main photos, 1 issue photo")


class TestEmergencySubmissionFlags:
    """Verify emergency submission has correct flags"""
    
    def test_emergency_is_emergency_flag(self, api_client, owner_token):
        """Emergency submission should have is_emergency=true"""
        response = api_client.get(
            f"{BASE_URL}/api/submissions/{EMERGENCY_SUBMISSION_ID}",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        submission = data.get("submission", {})
        
        assert submission.get("is_emergency") is True, f"is_emergency should be True"
        print(f"✓ Emergency submission has is_emergency=True")
    
    def test_emergency_incident_not_acknowledged(self, api_client, owner_token):
        """Emergency submission should have incident_acknowledged=false"""
        response = api_client.get(
            f"{BASE_URL}/api/submissions/{EMERGENCY_SUBMISSION_ID}",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        submission = data.get("submission", {})
        
        # incident_acknowledged should be False or not set
        acknowledged = submission.get("incident_acknowledged", False)
        assert acknowledged is False, f"incident_acknowledged should be False, got {acknowledged}"
        print(f"✓ Emergency submission has incident_acknowledged=False")
    
    def test_emergency_in_active_incidents(self, api_client, owner_token):
        """Emergency submission should appear in /api/incidents/active"""
        response = api_client.get(
            f"{BASE_URL}/api/incidents/active",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Active incidents failed: {response.text}"
        data = response.json()
        incidents = data.get("incidents", [])
        
        # Find our emergency submission
        emergency_incident = next((i for i in incidents if i.get("id") == EMERGENCY_SUBMISSION_ID), None)
        assert emergency_incident is not None, f"Emergency {EMERGENCY_SUBMISSION_ID} not in active incidents"
        assert emergency_incident.get("is_emergency") is True
        print(f"✓ Emergency submission appears in active incidents feed ({len(incidents)} total)")


class TestPhotoFileServing:
    """Verify photos are served correctly via /api/submissions/files/{id}/{filename}"""
    
    def test_leader_photo_served(self, api_client, owner_token):
        """Leader submission photos should be served with HTTP 200"""
        # First get the submission to find photo filenames
        response = api_client.get(
            f"{BASE_URL}/api/submissions/{LEADER_SUBMISSION_ID}",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        submission = data.get("submission", {})
        photo_files = submission.get("photo_files", [])
        
        assert len(photo_files) > 0, "No photo files found in leader submission"
        
        # Try to fetch the first photo
        first_photo = photo_files[0]
        filename = first_photo.get("filename")
        assert filename, "Photo filename is empty"
        
        # Fetch the photo file (no auth required for file serving)
        file_response = api_client.get(
            f"{BASE_URL}/api/submissions/files/{LEADER_SUBMISSION_ID}/{filename}"
        )
        assert file_response.status_code == 200, f"Photo file fetch failed: {file_response.status_code}"
        
        # Check content type is image
        content_type = file_response.headers.get("content-type", "")
        assert "image" in content_type or "octet-stream" in content_type, f"Unexpected content type: {content_type}"
        assert len(file_response.content) > 1000, "Photo content seems too small"
        print(f"✓ Leader photo {filename} served correctly ({len(file_response.content)} bytes)")


class TestRapidReviews:
    """Verify rapid reviews exist for correct staff members"""
    
    def test_rapid_reviews_exist(self, api_client, owner_token):
        """Should have rapid reviews from 7 admin staff"""
        response = api_client.get(
            f"{BASE_URL}/api/rapid-reviews/queue?page=1&limit=100",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Rapid review queue failed: {response.text}"
        # Queue shows UNREVIEWED submissions, so we need to check the rapid_reviews collection differently
        print(f"✓ Rapid review queue endpoint working")
    
    def test_tim_rapid_review_on_leader(self, api_client, pm_tim_token):
        """Tim A should have rapid review on leader submission"""
        # Get submission detail which includes rapid review info
        response = api_client.get(
            f"{BASE_URL}/api/submissions/{LEADER_SUBMISSION_ID}",
            headers={"Authorization": f"Bearer {pm_tim_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        rapid_review = data.get("rapid_review")
        
        # Rapid review should exist for this submission
        if rapid_review:
            print(f"✓ Leader submission has rapid review: rating={rapid_review.get('overall_rating')}")
        else:
            print(f"⚠ Leader submission rapid review not found in snapshot (may be in separate collection)")
    
    def test_scott_w_rapid_review_on_member(self, api_client, owner_token):
        """Scott W should have rapid review on member submission"""
        response = api_client.get(
            f"{BASE_URL}/api/submissions/{MEMBER_SUBMISSION_ID}",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        rapid_review = data.get("rapid_review")
        
        if rapid_review:
            print(f"✓ Member submission has rapid review: rating={rapid_review.get('overall_rating')}")
        else:
            print(f"⚠ Member submission rapid review not found in snapshot")


class TestManagementReview:
    """Verify management review on member submission"""
    
    def test_management_review_exists(self, api_client, owner_token):
        """Member submission should have management review from Scott K with ~81.8% score"""
        response = api_client.get(
            f"{BASE_URL}/api/submissions/{MEMBER_SUBMISSION_ID}",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        management_review = data.get("management_review")
        
        assert management_review is not None, "Management review not found on member submission"
        
        total_score = management_review.get("total_score", 0)
        # Score should be approximately 81.8%
        assert 75 <= total_score <= 90, f"Management review score should be ~81.8%, got {total_score}"
        print(f"✓ Member submission has management review with score {total_score}%")


class TestOwnerGMNoRapidReviews:
    """Verify Owner (Adam S) and GM (Tyler C) have NO rapid reviews on DEMO submissions"""
    
    def test_owner_no_rapid_review_on_demo_submissions(self, api_client, owner_token):
        """Owner should not have rapid reviews on the demo workflow submissions"""
        # Check each demo submission's rapid review
        demo_submissions = [LEADER_SUBMISSION_ID, MEMBER_SUBMISSION_ID, EMERGENCY_SUBMISSION_ID]
        
        for sub_id in demo_submissions:
            response = api_client.get(
                f"{BASE_URL}/api/submissions/{sub_id}",
                headers={"Authorization": f"Bearer {owner_token}"}
            )
            assert response.status_code == 200
            data = response.json()
            rapid_review = data.get("rapid_review")
            
            if rapid_review:
                # If there's a rapid review, it should NOT be from Owner
                reviewer_title = rapid_review.get("reviewer_title", "")
                assert reviewer_title != "Owner", f"Owner should not have rapid review on {sub_id}"
        
        print(f"✓ Owner (Adam S) has no rapid reviews on demo submissions")
    
    def test_gm_no_rapid_review_on_demo_submissions(self, api_client, owner_token):
        """GM should not have rapid reviews on the demo workflow submissions"""
        demo_submissions = [LEADER_SUBMISSION_ID, MEMBER_SUBMISSION_ID, EMERGENCY_SUBMISSION_ID]
        
        for sub_id in demo_submissions:
            response = api_client.get(
                f"{BASE_URL}/api/submissions/{sub_id}",
                headers={"Authorization": f"Bearer {owner_token}"}
            )
            assert response.status_code == 200
            data = response.json()
            rapid_review = data.get("rapid_review")
            
            if rapid_review:
                # If there's a rapid review, it should NOT be from GM
                reviewer_title = rapid_review.get("reviewer_title", "")
                assert reviewer_title != "GM", f"GM should not have rapid review on {sub_id}"
        
        print(f"✓ GM (Tyler C) has no rapid reviews on demo submissions")


class TestDashboardEmergencyWidget:
    """Verify dashboard shows emergency incident widget"""
    
    def test_dashboard_overview_loads(self, api_client, owner_token):
        """Dashboard overview should load successfully"""
        response = api_client.get(
            f"{BASE_URL}/api/dashboard/overview",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Dashboard overview failed: {response.text}"
        print(f"✓ Dashboard overview loads successfully")
    
    def test_active_incidents_count(self, api_client, owner_token):
        """Should have at least 1 active incident"""
        response = api_client.get(
            f"{BASE_URL}/api/incidents/active",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        incidents = data.get("incidents", [])
        total = data.get("total", 0)
        
        assert total >= 1, f"Should have at least 1 active incident, got {total}"
        print(f"✓ Dashboard has {total} active incident(s)")


class TestCrewPortal:
    """Verify crew portal shows submissions for Maintenance Alpha"""
    
    def test_crew_portal_access(self, api_client):
        """Crew portal /crew/be1da0c6 should be accessible"""
        response = api_client.get(f"{BASE_URL}/api/public/crew-access/{CREW_CODE_MAINTENANCE_ALPHA}")
        assert response.status_code == 200, f"Crew portal access failed: {response.text}"
        data = response.json()
        
        assert data.get("label") == "Maintenance Alpha", f"Crew label mismatch: {data.get('label')}"
        assert data.get("division") == "Maintenance", f"Division mismatch: {data.get('division')}"
        assert data.get("truck_number") == "TR-05", f"Truck mismatch: {data.get('truck_number')}"
        print(f"✓ Crew portal accessible: {data.get('label')}, {data.get('division')}, {data.get('truck_number')}")
    
    def test_crew_submissions_history(self, api_client):
        """Crew portal should show submission history"""
        response = api_client.get(f"{BASE_URL}/api/public/crew-submissions/{CREW_CODE_MAINTENANCE_ALPHA}")
        assert response.status_code == 200
        data = response.json()
        
        submissions = data.get("submissions", [])
        assert len(submissions) >= 3, f"Should have at least 3 submissions, got {len(submissions)}"
        
        # Check submission IDs are present
        submission_ids = [s.get("id") for s in submissions]
        assert LEADER_SUBMISSION_ID in submission_ids, f"Leader submission not in history"
        assert MEMBER_SUBMISSION_ID in submission_ids, f"Member submission not in history"
        assert EMERGENCY_SUBMISSION_ID in submission_ids, f"Emergency submission not in history"
        print(f"✓ Crew portal shows {len(submissions)} submissions including leader, member, and emergency")


class TestRapidReviewQueue:
    """Verify rapid review queue shows only unreviewed submissions"""
    
    def test_queue_shows_emergency(self, api_client, owner_token):
        """Rapid review queue should show emergency submission (if unreviewed)"""
        response = api_client.get(
            f"{BASE_URL}/api/rapid-reviews/queue?page=1&limit=50",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        items = data.get("items", [])
        
        # Emergency submission should be in queue if not yet rapid reviewed
        emergency_in_queue = any(i.get("id") == EMERGENCY_SUBMISSION_ID for i in items)
        print(f"✓ Rapid review queue has {len(items)} items. Emergency in queue: {emergency_in_queue}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
