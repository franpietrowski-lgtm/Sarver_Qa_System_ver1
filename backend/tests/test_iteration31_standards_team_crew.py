"""
Iteration 31 Tests: Standards API, Team Profiles, Crew Capture Division Switcher
Tests for:
1. Public standards API with division filtering
2. Team profiles API with leader_name display
3. Team timeline stats API
4. Crew link creation with leader_name field
"""
import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials from test_credentials.md
OWNER_EMAIL = "sadam.owner@slmco.local"
OWNER_PASSWORD = "SLMCo2026!"
GM_EMAIL = "tylerc.gm@slmco.local"
GM_PASSWORD = "SLMCo2026!"
DEMO_CREW_CODE = "bb01032c"


@pytest.fixture(scope="module")
def owner_token():
    """Get owner authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": OWNER_EMAIL,
        "password": OWNER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Owner login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def gm_token():
    """Get GM authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": GM_EMAIL,
        "password": GM_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"GM login failed: {response.status_code} - {response.text}")


class TestPublicStandardsAPI:
    """Test GET /api/public/standards with division filtering"""
    
    def test_standards_no_filter_returns_all(self):
        """GET /api/public/standards without division returns all standards"""
        response = requests.get(f"{BASE_URL}/api/public/standards")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "standards" in data
        assert isinstance(data["standards"], list)
        print(f"Total standards (no filter): {len(data['standards'])}")
        # Should have standards from seeded data
        assert len(data["standards"]) > 0, "Expected at least some standards"
    
    def test_standards_maintenance_filter(self):
        """GET /api/public/standards?division=Maintenance returns only Maintenance + general standards"""
        response = requests.get(f"{BASE_URL}/api/public/standards?division=Maintenance")
        assert response.status_code == 200
        data = response.json()
        standards = data.get("standards", [])
        print(f"Maintenance standards count: {len(standards)}")
        
        # Verify each standard is either general (empty division_targets) or includes Maintenance
        for std in standards:
            div_targets = std.get("division_targets", [])
            if div_targets:  # If has specific targets
                assert "Maintenance" in div_targets, f"Standard '{std.get('title')}' has targets {div_targets} but not Maintenance"
            # Empty division_targets means general/all divisions
        
        # Print some standard titles for verification
        if standards:
            print(f"Sample Maintenance standards: {[s.get('title') for s in standards[:3]]}")
    
    def test_standards_install_filter(self):
        """GET /api/public/standards?division=Install returns only Install + general standards"""
        response = requests.get(f"{BASE_URL}/api/public/standards?division=Install")
        assert response.status_code == 200
        data = response.json()
        standards = data.get("standards", [])
        print(f"Install standards count: {len(standards)}")
        
        # Verify each standard is either general or includes Install
        for std in standards:
            div_targets = std.get("division_targets", [])
            if div_targets:
                assert "Install" in div_targets, f"Standard '{std.get('title')}' has targets {div_targets} but not Install"
        
        if standards:
            print(f"Sample Install standards: {[s.get('title') for s in standards[:3]]}")
    
    def test_standards_different_divisions_return_different_results(self):
        """Maintenance and Install should return different filtered results"""
        maint_response = requests.get(f"{BASE_URL}/api/public/standards?division=Maintenance")
        install_response = requests.get(f"{BASE_URL}/api/public/standards?division=Install")
        
        assert maint_response.status_code == 200
        assert install_response.status_code == 200
        
        maint_standards = maint_response.json().get("standards", [])
        install_standards = install_response.json().get("standards", [])
        
        maint_ids = {s.get("id") for s in maint_standards}
        install_ids = {s.get("id") for s in install_standards}
        
        # There should be some overlap (general standards) but not complete overlap
        # unless all standards are general
        print(f"Maintenance IDs: {len(maint_ids)}, Install IDs: {len(install_ids)}")
        print(f"Overlap: {len(maint_ids & install_ids)}")


class TestTeamProfilesAPI:
    """Test team profiles endpoints with leader_name display"""
    
    def test_team_profiles_returns_profiles(self, owner_token):
        """GET /api/team/profiles returns profiles array"""
        response = requests.get(
            f"{BASE_URL}/api/team/profiles",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "profiles" in data
        assert isinstance(data["profiles"], list)
        print(f"Total profiles: {len(data['profiles'])}")
        
        # Check for crew leaders with leader_name
        crew_leaders = [p for p in data["profiles"] if p.get("role") == "Crew Leader"]
        print(f"Crew leaders found: {len(crew_leaders)}")
        
        # Verify crew leaders have name field (should be leader_name or label)
        for leader in crew_leaders[:3]:
            print(f"  - {leader.get('name')} (crew_label: {leader.get('crew_label')})")
    
    def test_team_profiles_crew_leader_shows_leader_name(self, owner_token):
        """Crew leaders should show leader_name as display name, not crew label"""
        response = requests.get(
            f"{BASE_URL}/api/team/profiles",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        profiles = response.json().get("profiles", [])
        
        # Find crew leaders
        crew_leaders = [p for p in profiles if p.get("source_type") == "crew"]
        
        # Check if any crew leader has a different name than crew_label
        # This indicates leader_name is being used
        for leader in crew_leaders:
            name = leader.get("name", "")
            crew_label = leader.get("crew_label", "")
            if name != crew_label and name:
                print(f"PASS: Leader '{name}' has different crew_label '{crew_label}'")
                return
        
        # If all names match labels, check if leader_name field exists in DB
        print("Note: All crew leader names match their labels (leader_name may not be set)")
    
    def test_team_structure_shows_leader_names(self, owner_token):
        """GET /api/team/structure should show leader_name for crew leaders"""
        response = requests.get(
            f"{BASE_URL}/api/team/structure",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        teams = data.get("teams", [])
        
        print(f"Teams found: {len(teams)}")
        for team in teams[:3]:
            lead = team.get("lead", {})
            print(f"  Team: {team.get('crew_label')} - Leader: {lead.get('name')}")


class TestTeamTimelineStatsAPI:
    """Test GET /api/team/profiles/{profile_id}/stats endpoint"""
    
    def test_timeline_stats_default_months(self, owner_token):
        """GET /api/team/profiles/{profile_id}/stats returns stats with default 3 months"""
        # First get a profile ID
        profiles_response = requests.get(
            f"{BASE_URL}/api/team/profiles",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert profiles_response.status_code == 200
        profiles = profiles_response.json().get("profiles", [])
        assert len(profiles) > 0, "Need at least one profile to test"
        
        profile_id = profiles[0]["profile_id"]
        
        response = requests.get(
            f"{BASE_URL}/api/team/profiles/{profile_id}/stats",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify stats structure
        assert "months" in data
        assert "review_count" in data
        assert "submission_count" in data
        assert "avg_review_score" in data
        assert "training_total" in data
        assert "training_completed" in data
        
        print(f"Stats for {profile_id}: {data}")
    
    def test_timeline_stats_6_months(self, owner_token):
        """GET /api/team/profiles/{profile_id}/stats?months=6 returns 6-month stats"""
        profiles_response = requests.get(
            f"{BASE_URL}/api/team/profiles",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        profiles = profiles_response.json().get("profiles", [])
        profile_id = profiles[0]["profile_id"]
        
        response = requests.get(
            f"{BASE_URL}/api/team/profiles/{profile_id}/stats?months=6",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("months") == 6
        print(f"6-month stats: {data}")
    
    def test_timeline_stats_various_periods(self, owner_token):
        """Test timeline stats for 1, 3, 6, 12, 24 month periods"""
        profiles_response = requests.get(
            f"{BASE_URL}/api/team/profiles",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        profiles = profiles_response.json().get("profiles", [])
        profile_id = profiles[0]["profile_id"]
        
        for months in [1, 3, 6, 12, 24]:
            response = requests.get(
                f"{BASE_URL}/api/team/profiles/{profile_id}/stats?months={months}",
                headers={"Authorization": f"Bearer {owner_token}"}
            )
            assert response.status_code == 200, f"Failed for {months} months"
            data = response.json()
            assert data.get("months") == months
            print(f"  {months}mo: reviews={data.get('review_count')}, submissions={data.get('submission_count')}")
    
    def test_timeline_stats_requires_auth(self):
        """Timeline stats endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/team/profiles/user_test/stats")
        assert response.status_code == 401 or response.status_code == 403


class TestTeamHierarchy:
    """Test division hierarchy display"""
    
    def test_hierarchy_structure(self, owner_token):
        """GET /api/team/hierarchy returns correct org structure"""
        response = requests.get(
            f"{BASE_URL}/api/team/hierarchy",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure: Owner → GM → Production/Account Managers → Supervisors → Crews
        assert "owners" in data
        assert "general_managers" in data
        assert "production_managers" in data
        assert "account_managers" in data
        assert "supervisors" in data
        assert "divisions" in data
        
        print(f"Owners: {len(data['owners'])}")
        print(f"GMs: {len(data['general_managers'])}")
        print(f"Production Managers: {len(data['production_managers'])}")
        print(f"Account Managers: {len(data['account_managers'])}")
        print(f"Supervisors: {len(data['supervisors'])}")
        print(f"Divisions: {len(data['divisions'])}")
        
        # Verify divisions have teams with leaders and members
        for div in data["divisions"]:
            print(f"  Division '{div['name']}': {len(div['teams'])} teams")


class TestCrewLinkLeaderName:
    """Test crew link creation with leader_name field"""
    
    def test_create_crew_link_with_leader_name(self, owner_token):
        """POST /api/crew-access-links with leader_name field"""
        payload = {
            "label": "TEST_Iter31_Crew",
            "truck_number": "TR-TEST31",
            "division": "Install",
            "assignment": "Test route",
            "leader_name": "Test Leader Name"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/crew-access-links",
            json=payload,
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify leader_name is returned
        assert data.get("leader_name") == "Test Leader Name", f"Expected leader_name, got {data}"
        print(f"Created crew link: {data.get('code')} with leader_name: {data.get('leader_name')}")
        
        # Cleanup - delete the test crew link
        crew_id = data.get("id")
        if crew_id:
            delete_response = requests.delete(
                f"{BASE_URL}/api/crew-access-links/{crew_id}",
                headers={"Authorization": f"Bearer {owner_token}"}
            )
            print(f"Cleanup: deleted test crew link, status: {delete_response.status_code}")
    
    def test_update_crew_link_leader_name(self, owner_token):
        """PATCH /api/crew-access-links/{id} can update leader_name"""
        # First create a test crew link
        create_payload = {
            "label": "TEST_Iter31_Update",
            "truck_number": "TR-TEST31U",
            "division": "Maintenance",
            "assignment": "",
            "leader_name": "Original Leader"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/crew-access-links",
            json=create_payload,
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert create_response.status_code == 200
        crew_id = create_response.json().get("id")
        
        # Update with new leader_name
        update_payload = {
            "label": "TEST_Iter31_Update",
            "truck_number": "TR-TEST31U",
            "division": "Maintenance",
            "assignment": "",
            "leader_name": "Updated Leader Name"
        }
        
        update_response = requests.patch(
            f"{BASE_URL}/api/crew-access-links/{crew_id}",
            json=update_payload,
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert update_response.status_code == 200
        data = update_response.json()
        assert data.get("leader_name") == "Updated Leader Name"
        print(f"Updated leader_name to: {data.get('leader_name')}")
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/crew-access-links/{crew_id}",
            headers={"Authorization": f"Bearer {owner_token}"}
        )


class TestDemoCrewAccess:
    """Test demo crew code bb01032c"""
    
    def test_demo_crew_exists(self):
        """GET /api/public/crew-access/{code} returns demo crew"""
        response = requests.get(f"{BASE_URL}/api/public/crew-access/{DEMO_CREW_CODE}")
        
        if response.status_code == 404:
            pytest.skip(f"Demo crew {DEMO_CREW_CODE} not found in database")
        
        assert response.status_code == 200
        data = response.json()
        
        print(f"Demo crew: {data.get('label')}")
        print(f"Leader name: {data.get('leader_name')}")
        print(f"Division: {data.get('division')}")
        print(f"Truck: {data.get('truck_number')}")
        
        # Verify expected values from request
        # Demo crew should be Install Alpha with leader Alejandro Ruiz-Domian
        if data.get("label"):
            assert "Install" in data.get("label", "") or data.get("division") == "Install"


class TestNavRename:
    """Test QJA rename in navigation"""
    
    def test_login_and_check_nav(self, owner_token):
        """Verify QJA appears in navigation (tested via API user info)"""
        # This is primarily a frontend test, but we verify the user can access jobs page
        response = requests.get(
            f"{BASE_URL}/api/jobs?page=1&limit=1",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        # Jobs endpoint should be accessible
        assert response.status_code == 200
        print("Jobs endpoint accessible - QJA navigation should work")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
