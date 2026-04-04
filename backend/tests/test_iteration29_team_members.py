"""
Iteration 29: Team Members Page Backend Tests
Tests for:
- GET /api/team/profiles - returns unified profiles from users + crew leaders + crew members
- GET /api/team/profiles/{profile_id} - returns single profile with stats
- PATCH /api/team/profiles/{profile_id} - updates age/avatar_url
- GET /api/team/structure - returns teams grouped by crew leader with nested members
- GET /api/team/hierarchy - returns full org hierarchy
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
OWNER_EMAIL = "sadam.owner@slmco.local"
OWNER_PASSWORD = "SLMCo2026!"
MANAGEMENT_EMAIL = "mdiane.gm@slmco.local"
MANAGEMENT_PASSWORD = "SLMCo2026!"

# Test profile IDs from the problem statement
TEST_CREW_CODE = "000a07ca"  # North Crew
TEST_MEMBER_CODE_1 = "ef04449f"  # John Smith
TEST_MEMBER_CODE_2 = "c694a71f"  # Mike Rivera


@pytest.fixture(scope="module")
def owner_token():
    """Get owner authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": OWNER_EMAIL,
        "password": OWNER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Owner authentication failed: {response.status_code}")


@pytest.fixture(scope="module")
def management_token():
    """Get management authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": MANAGEMENT_EMAIL,
        "password": MANAGEMENT_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Management authentication failed: {response.status_code}")


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


@pytest.fixture
def unauthenticated_client():
    """Session without auth header"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestTeamProfilesEndpoint:
    """Tests for GET /api/team/profiles"""
    
    def test_get_all_profiles_owner_access(self, owner_client):
        """Owner can access all profiles"""
        response = owner_client.get(f"{BASE_URL}/api/team/profiles")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "profiles" in data
        assert "total" in data
        assert isinstance(data["profiles"], list)
        assert data["total"] == len(data["profiles"])
        print(f"✓ Owner retrieved {data['total']} profiles")
    
    def test_get_all_profiles_management_access(self, management_client):
        """Management can access all profiles"""
        response = management_client.get(f"{BASE_URL}/api/team/profiles")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "profiles" in data
        assert len(data["profiles"]) > 0
        print(f"✓ Management retrieved {data['total']} profiles")
    
    def test_get_all_profiles_requires_auth(self, unauthenticated_client):
        """Unauthenticated request should fail"""
        response = unauthenticated_client.get(f"{BASE_URL}/api/team/profiles")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Unauthenticated access correctly denied")
    
    def test_profiles_contain_required_fields(self, owner_client):
        """Each profile should have required fields"""
        response = owner_client.get(f"{BASE_URL}/api/team/profiles")
        assert response.status_code == 200
        
        data = response.json()
        profiles = data["profiles"]
        assert len(profiles) > 0, "No profiles returned"
        
        required_fields = ["profile_id", "source_type", "source_id", "name", "role"]
        for profile in profiles[:5]:  # Check first 5 profiles
            for field in required_fields:
                assert field in profile, f"Missing field '{field}' in profile: {profile}"
        
        print(f"✓ All required fields present in profiles")
    
    def test_profiles_include_all_source_types(self, owner_client):
        """Profiles should include users, crew leaders, and crew members"""
        response = owner_client.get(f"{BASE_URL}/api/team/profiles")
        assert response.status_code == 200
        
        data = response.json()
        profiles = data["profiles"]
        
        source_types = set(p["source_type"] for p in profiles)
        print(f"Source types found: {source_types}")
        
        # Should have at least users and crew leaders
        assert "user" in source_types, "No user profiles found"
        assert "crew" in source_types, "No crew leader profiles found"
        # Members may or may not exist depending on seed data
        print(f"✓ Found source types: {source_types}")


class TestTeamProfileDetailEndpoint:
    """Tests for GET /api/team/profiles/{profile_id}"""
    
    def test_get_user_profile_detail(self, owner_client):
        """Get detail for a user profile"""
        # First get all profiles to find a user profile
        response = owner_client.get(f"{BASE_URL}/api/team/profiles")
        assert response.status_code == 200
        
        profiles = response.json()["profiles"]
        user_profile = next((p for p in profiles if p["source_type"] == "user"), None)
        assert user_profile is not None, "No user profile found"
        
        # Get detail
        detail_response = owner_client.get(f"{BASE_URL}/api/team/profiles/{user_profile['profile_id']}")
        assert detail_response.status_code == 200, f"Expected 200, got {detail_response.status_code}"
        
        detail = detail_response.json()
        assert detail["profile_id"] == user_profile["profile_id"]
        assert "stats" in detail
        assert "review_count" in detail["stats"]
        print(f"✓ User profile detail retrieved: {detail['name']}")
    
    def test_get_crew_leader_profile_detail(self, owner_client):
        """Get detail for a crew leader profile"""
        profile_id = f"crew_{TEST_CREW_CODE}"
        response = owner_client.get(f"{BASE_URL}/api/team/profiles/{profile_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        detail = response.json()
        assert detail["profile_id"] == profile_id
        assert detail["source_type"] == "crew"
        assert detail["role"] == "Crew Leader"
        assert "stats" in detail
        assert "submission_count" in detail["stats"]
        print(f"✓ Crew leader profile detail retrieved: {detail['name']}")
    
    def test_get_crew_member_profile_detail(self, owner_client):
        """Get detail for a crew member profile"""
        profile_id = f"member_{TEST_MEMBER_CODE_1}"
        response = owner_client.get(f"{BASE_URL}/api/team/profiles/{profile_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        detail = response.json()
        assert detail["profile_id"] == profile_id
        assert detail["source_type"] == "member"
        assert detail["role"] == "Crew Member"
        assert "stats" in detail
        print(f"✓ Crew member profile detail retrieved: {detail['name']}")
    
    def test_profile_detail_stats_structure(self, owner_client):
        """Stats should have correct structure"""
        profile_id = f"crew_{TEST_CREW_CODE}"
        response = owner_client.get(f"{BASE_URL}/api/team/profiles/{profile_id}")
        assert response.status_code == 200
        
        stats = response.json()["stats"]
        expected_stats = ["review_count", "submission_count", "training_total", "training_completed"]
        for stat in expected_stats:
            assert stat in stats, f"Missing stat '{stat}'"
        print(f"✓ Stats structure correct: {stats}")
    
    def test_profile_detail_not_found(self, owner_client):
        """Non-existent profile should return 404"""
        response = owner_client.get(f"{BASE_URL}/api/team/profiles/user_nonexistent123")
        assert response.status_code == 404
        print("✓ Non-existent profile returns 404")
    
    def test_profile_detail_invalid_format(self, owner_client):
        """Invalid profile ID format should return 400"""
        response = owner_client.get(f"{BASE_URL}/api/team/profiles/invalidformat")
        assert response.status_code == 400
        print("✓ Invalid profile ID format returns 400")


class TestTeamProfileUpdateEndpoint:
    """Tests for PATCH /api/team/profiles/{profile_id}"""
    
    def test_update_profile_age(self, owner_client):
        """Update age for a profile"""
        profile_id = f"crew_{TEST_CREW_CODE}"
        
        # Update age
        response = owner_client.patch(
            f"{BASE_URL}/api/team/profiles/{profile_id}",
            json={"age": 35}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["updated"] == True
        assert data["profile_id"] == profile_id
        
        # Verify update persisted
        detail_response = owner_client.get(f"{BASE_URL}/api/team/profiles/{profile_id}")
        assert detail_response.status_code == 200
        assert detail_response.json()["age"] == 35
        print("✓ Profile age updated and persisted")
    
    def test_update_profile_avatar_url(self, owner_client):
        """Update avatar_url for a profile"""
        profile_id = f"member_{TEST_MEMBER_CODE_1}"
        test_avatar = "https://example.com/avatar.jpg"
        
        response = owner_client.patch(
            f"{BASE_URL}/api/team/profiles/{profile_id}",
            json={"avatar_url": test_avatar}
        )
        assert response.status_code == 200
        
        # Verify update persisted
        detail_response = owner_client.get(f"{BASE_URL}/api/team/profiles/{profile_id}")
        assert detail_response.status_code == 200
        assert detail_response.json()["avatar_url"] == test_avatar
        print("✓ Profile avatar_url updated and persisted")
    
    def test_update_profile_no_fields(self, owner_client):
        """Update with no fields should return 400"""
        profile_id = f"crew_{TEST_CREW_CODE}"
        response = owner_client.patch(
            f"{BASE_URL}/api/team/profiles/{profile_id}",
            json={}
        )
        assert response.status_code == 400
        print("✓ Empty update returns 400")
    
    def test_update_profile_management_access(self, management_client):
        """Management can update profiles"""
        profile_id = f"member_{TEST_MEMBER_CODE_2}"
        response = management_client.patch(
            f"{BASE_URL}/api/team/profiles/{profile_id}",
            json={"age": 28}
        )
        assert response.status_code == 200
        print("✓ Management can update profiles")


class TestTeamStructureEndpoint:
    """Tests for GET /api/team/structure"""
    
    def test_get_team_structure_owner(self, owner_client):
        """Owner can access team structure"""
        response = owner_client.get(f"{BASE_URL}/api/team/structure")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "teams" in data
        assert isinstance(data["teams"], list)
        print(f"✓ Owner retrieved {len(data['teams'])} teams")
    
    def test_get_team_structure_management(self, management_client):
        """Management can access team structure"""
        response = management_client.get(f"{BASE_URL}/api/team/structure")
        assert response.status_code == 200
        
        data = response.json()
        assert "teams" in data
        print(f"✓ Management retrieved {len(data['teams'])} teams")
    
    def test_team_structure_format(self, owner_client):
        """Team structure should have correct format"""
        response = owner_client.get(f"{BASE_URL}/api/team/structure")
        assert response.status_code == 200
        
        teams = response.json()["teams"]
        if len(teams) > 0:
            team = teams[0]
            assert "lead" in team, "Team missing 'lead'"
            assert "members" in team, "Team missing 'members'"
            assert "division" in team, "Team missing 'division'"
            
            # Check lead structure
            lead = team["lead"]
            assert "profile_id" in lead
            assert "name" in lead
            assert lead["role"] == "Crew Leader"
            
            # Check members structure
            assert isinstance(team["members"], list)
            print(f"✓ Team structure format correct: {lead['name']} with {len(team['members'])} members")
    
    def test_team_structure_requires_auth(self, unauthenticated_client):
        """Unauthenticated request should fail"""
        response = unauthenticated_client.get(f"{BASE_URL}/api/team/structure")
        assert response.status_code in [401, 403]
        print("✓ Unauthenticated access correctly denied")


class TestTeamHierarchyEndpoint:
    """Tests for GET /api/team/hierarchy"""
    
    def test_get_hierarchy_owner(self, owner_client):
        """Owner can access full hierarchy"""
        response = owner_client.get(f"{BASE_URL}/api/team/hierarchy")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        expected_keys = ["owners", "general_managers", "account_managers", 
                        "production_managers", "supervisors", "divisions"]
        for key in expected_keys:
            assert key in data, f"Missing key '{key}' in hierarchy"
        print(f"✓ Owner retrieved hierarchy with {len(data['divisions'])} divisions")
    
    def test_get_hierarchy_management(self, management_client):
        """Management can access full hierarchy"""
        response = management_client.get(f"{BASE_URL}/api/team/hierarchy")
        assert response.status_code == 200
        
        data = response.json()
        assert "owners" in data
        assert "divisions" in data
        print(f"✓ Management retrieved hierarchy")
    
    def test_hierarchy_owners_structure(self, owner_client):
        """Owners list should have correct structure"""
        response = owner_client.get(f"{BASE_URL}/api/team/hierarchy")
        assert response.status_code == 200
        
        owners = response.json()["owners"]
        assert isinstance(owners, list)
        if len(owners) > 0:
            owner = owners[0]
            assert "profile_id" in owner
            assert "name" in owner
            assert owner["source_type"] == "user"
            print(f"✓ Found {len(owners)} owner(s): {[o['name'] for o in owners]}")
    
    def test_hierarchy_divisions_structure(self, owner_client):
        """Divisions should have correct nested structure"""
        response = owner_client.get(f"{BASE_URL}/api/team/hierarchy")
        assert response.status_code == 200
        
        divisions = response.json()["divisions"]
        assert isinstance(divisions, list)
        
        if len(divisions) > 0:
            division = divisions[0]
            assert "name" in division
            assert "teams" in division
            assert isinstance(division["teams"], list)
            
            if len(division["teams"]) > 0:
                team = division["teams"][0]
                assert "lead" in team
                assert "members" in team
                print(f"✓ Division '{division['name']}' has {len(division['teams'])} teams")
    
    def test_hierarchy_requires_auth(self, unauthenticated_client):
        """Unauthenticated request should fail"""
        response = unauthenticated_client.get(f"{BASE_URL}/api/team/hierarchy")
        assert response.status_code in [401, 403]
        print("✓ Unauthenticated access correctly denied")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
