"""
Iteration 27: Crew Member Role Testing
Tests for crew member registration, profile, standards, training, and submissions endpoints.
All endpoints are public (no auth required).
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test data - existing crew access link code
PARENT_ACCESS_CODE = "000a07ca"  # North Crew, Install division
TEST_MEMBER_CODE_1 = "ef04449f"  # John Smith
TEST_MEMBER_CODE_2 = "c694a71f"  # Mike Rivera


@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestCrewMemberRegistration:
    """POST /api/public/crew-members/register endpoint tests"""

    def test_register_crew_member_success(self, api_client):
        """Test successful crew member registration"""
        import uuid
        unique_name = f"TEST_Member_{uuid.uuid4().hex[:6]}"
        
        response = api_client.post(
            f"{BASE_URL}/api/public/crew-members/register",
            json={
                "name": unique_name,
                "division": "Install",
                "parent_access_code": PARENT_ACCESS_CODE
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "code" in data, "Response should contain 'code'"
        assert "name" in data, "Response should contain 'name'"
        assert "division" in data, "Response should contain 'division'"
        assert "parent_crew_label" in data, "Response should contain 'parent_crew_label'"
        
        # Verify values
        assert data["name"] == unique_name
        assert data["division"] == "Install"
        assert len(data["code"]) == 8, "Member code should be 8 characters"
        
        print(f"✓ Registered crew member: {data['name']} with code {data['code']}")

    def test_register_crew_member_empty_name_fails(self, api_client):
        """Test registration with empty name fails validation"""
        response = api_client.post(
            f"{BASE_URL}/api/public/crew-members/register",
            json={
                "name": "   ",  # Whitespace only
                "division": "Install",
                "parent_access_code": PARENT_ACCESS_CODE
            }
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        assert "name" in data["detail"].lower() or "required" in data["detail"].lower()
        print("✓ Empty name validation works correctly")

    def test_register_crew_member_invalid_parent_code(self, api_client):
        """Test registration with invalid parent access code fails"""
        response = api_client.post(
            f"{BASE_URL}/api/public/crew-members/register",
            json={
                "name": "Test Member",
                "division": "Install",
                "parent_access_code": "invalid_code_12345"
            }
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        print("✓ Invalid parent code returns 404")


class TestCrewMemberProfile:
    """GET /api/public/crew-member/{code} endpoint tests"""

    def test_get_crew_member_profile_success(self, api_client):
        """Test getting existing crew member profile"""
        response = api_client.get(f"{BASE_URL}/api/public/crew-member/{TEST_MEMBER_CODE_1}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "code" in data
        assert "name" in data
        assert "division" in data
        assert "parent_crew_label" in data
        assert "parent_truck_number" in data
        assert "parent_access_code" in data
        assert "created_at" in data
        
        # Verify values
        assert data["code"] == TEST_MEMBER_CODE_1
        print(f"✓ Got member profile: {data['name']} ({data['division']})")

    def test_get_crew_member_invalid_code_returns_404(self, api_client):
        """Test invalid member code returns 404"""
        response = api_client.get(f"{BASE_URL}/api/public/crew-member/invalid_code_xyz")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        print("✓ Invalid member code returns 404")


class TestCrewMemberStandards:
    """GET /api/public/crew-member/{code}/standards endpoint tests"""

    def test_get_crew_member_standards_success(self, api_client):
        """Test getting standards for crew member's division"""
        response = api_client.get(f"{BASE_URL}/api/public/crew-member/{TEST_MEMBER_CODE_1}/standards")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "standards" in data
        assert "division" in data
        assert isinstance(data["standards"], list)
        
        # If standards exist, verify structure
        if data["standards"]:
            standard = data["standards"][0]
            assert "id" in standard
            assert "title" in standard
            assert "category" in standard
            print(f"✓ Got {len(data['standards'])} standards for division: {data['division']}")
        else:
            print(f"✓ No standards found for division: {data['division']} (empty list is valid)")

    def test_get_standards_invalid_member_code_returns_404(self, api_client):
        """Test invalid member code returns 404 for standards"""
        response = api_client.get(f"{BASE_URL}/api/public/crew-member/invalid_xyz/standards")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✓ Invalid member code returns 404 for standards")


class TestCrewMemberTraining:
    """GET /api/public/crew-member/{code}/training endpoint tests"""

    def test_get_crew_member_training_success(self, api_client):
        """Test getting training sessions for crew member's parent crew"""
        response = api_client.get(f"{BASE_URL}/api/public/crew-member/{TEST_MEMBER_CODE_1}/training")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "training_sessions" in data
        assert isinstance(data["training_sessions"], list)
        
        # If sessions exist, verify structure
        if data["training_sessions"]:
            session = data["training_sessions"][0]
            assert "code" in session
            assert "crew_label" in session
            assert "division" in session
            assert "item_count" in session
            assert "status" in session
            print(f"✓ Got {len(data['training_sessions'])} training sessions")
        else:
            print("✓ No training sessions found (empty list is valid)")

    def test_get_training_invalid_member_code_returns_404(self, api_client):
        """Test invalid member code returns 404 for training"""
        response = api_client.get(f"{BASE_URL}/api/public/crew-member/invalid_xyz/training")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✓ Invalid member code returns 404 for training")


class TestCrewMemberSubmissions:
    """GET /api/public/crew-member/{code}/submissions endpoint tests"""

    def test_get_crew_member_submissions_success(self, api_client):
        """Test getting submissions for crew member"""
        response = api_client.get(f"{BASE_URL}/api/public/crew-member/{TEST_MEMBER_CODE_1}/submissions")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "submissions" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert isinstance(data["submissions"], list)
        
        # If submissions exist, verify structure
        if data["submissions"]:
            submission = data["submissions"][0]
            assert "id" in submission
            assert "job_name_input" in submission
            assert "task_type" in submission
            assert "status" in submission
            assert "work_date" in submission
            assert "photo_count" in submission
            assert "created_at" in submission
            print(f"✓ Got {len(data['submissions'])} submissions (total: {data['total']})")
        else:
            print("✓ No submissions found (empty list is valid)")

    def test_get_submissions_pagination(self, api_client):
        """Test submissions pagination parameters"""
        response = api_client.get(
            f"{BASE_URL}/api/public/crew-member/{TEST_MEMBER_CODE_1}/submissions",
            params={"page": 1, "limit": 5}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["page"] == 1
        assert data["limit"] == 5
        assert len(data["submissions"]) <= 5
        print(f"✓ Pagination works: page={data['page']}, limit={data['limit']}")

    def test_get_submissions_invalid_member_code_returns_404(self, api_client):
        """Test invalid member code returns 404 for submissions"""
        response = api_client.get(f"{BASE_URL}/api/public/crew-member/invalid_xyz/submissions")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✓ Invalid member code returns 404 for submissions")


class TestCrewAccessLinkForMemberInvite:
    """Test crew access link endpoint used for member invite flow"""

    def test_get_crew_access_link_for_invite(self, api_client):
        """Test getting crew access link (used by member registration page)"""
        response = api_client.get(f"{BASE_URL}/api/public/crew-access/{PARENT_ACCESS_CODE}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "code" in data
        assert "label" in data
        assert "truck_number" in data
        assert "division" in data
        
        print(f"✓ Got crew access link: {data['label']} ({data['division']})")


class TestEndToEndMemberFlow:
    """End-to-end test: Register member, get profile, check standards/training/submissions"""

    def test_full_member_registration_flow(self, api_client):
        """Test complete member registration and data access flow"""
        import uuid
        unique_name = f"TEST_E2E_{uuid.uuid4().hex[:6]}"
        
        # Step 1: Register new member
        register_response = api_client.post(
            f"{BASE_URL}/api/public/crew-members/register",
            json={
                "name": unique_name,
                "division": "Install",
                "parent_access_code": PARENT_ACCESS_CODE
            }
        )
        assert register_response.status_code == 200
        member_code = register_response.json()["code"]
        print(f"✓ Step 1: Registered member with code {member_code}")
        
        # Step 2: Get member profile
        profile_response = api_client.get(f"{BASE_URL}/api/public/crew-member/{member_code}")
        assert profile_response.status_code == 200
        profile = profile_response.json()
        assert profile["name"] == unique_name
        assert profile["code"] == member_code
        print(f"✓ Step 2: Got profile for {profile['name']}")
        
        # Step 3: Get standards
        standards_response = api_client.get(f"{BASE_URL}/api/public/crew-member/{member_code}/standards")
        assert standards_response.status_code == 200
        standards_data = standards_response.json()
        assert "standards" in standards_data
        print(f"✓ Step 3: Got {len(standards_data['standards'])} standards")
        
        # Step 4: Get training
        training_response = api_client.get(f"{BASE_URL}/api/public/crew-member/{member_code}/training")
        assert training_response.status_code == 200
        training_data = training_response.json()
        assert "training_sessions" in training_data
        print(f"✓ Step 4: Got {len(training_data['training_sessions'])} training sessions")
        
        # Step 5: Get submissions (should be empty for new member)
        submissions_response = api_client.get(f"{BASE_URL}/api/public/crew-member/{member_code}/submissions")
        assert submissions_response.status_code == 200
        submissions_data = submissions_response.json()
        assert "submissions" in submissions_data
        assert submissions_data["total"] == 0  # New member has no submissions
        print(f"✓ Step 5: Got {submissions_data['total']} submissions (expected 0 for new member)")
        
        print(f"\n✓ Full E2E flow completed successfully for member {unique_name}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
