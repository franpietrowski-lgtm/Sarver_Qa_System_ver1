"""
Iteration 33 Regression Tests - Sarver Landscape QA System
Tests: Backend health, Auth, Team hierarchy, Profiles, Timeline stats, Standards
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://quality-hub-32.preview.emergentagent.com')

# Test credentials
OWNER_EMAIL = "sadam.owner@slmco.local"
GM_EMAIL = "ctyler.gm@slmco.local"
PM_EMAIL = "atim.prom@slmco.local"
PASSWORD = "SLMCo2026!"

# Crew codes
CREW_CODES = {
    "install_alpha": "bb01032c",
    "maintenance_alpha": "be1da0c6",
    "maintenance_bravo": "e4444b93",
    "tree_alpha": "47701159"
}


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def owner_token(api_client):
    """Get Owner authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": OWNER_EMAIL,
        "password": PASSWORD
    })
    assert response.status_code == 200, f"Owner login failed: {response.text}"
    return response.json().get("token")


@pytest.fixture(scope="module")
def gm_token(api_client):
    """Get GM authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": GM_EMAIL,
        "password": PASSWORD
    })
    assert response.status_code == 200, f"GM login failed: {response.text}"
    return response.json().get("token")


@pytest.fixture(scope="module")
def pm_token(api_client):
    """Get PM authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": PM_EMAIL,
        "password": PASSWORD
    })
    assert response.status_code == 200, f"PM login failed: {response.text}"
    return response.json().get("token")


class TestHealthAndAuth:
    """Backend health and authentication tests"""
    
    def test_health_endpoint(self, api_client):
        """GET /api/health returns ok"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        print("✓ Health endpoint returns ok")
    
    def test_owner_login(self, api_client):
        """Login as Owner returns JWT"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL,
            "password": PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "owner"
        assert data["user"]["name"] == "Adam S"
        print(f"✓ Owner login successful: {data['user']['name']}")
    
    def test_gm_login(self, api_client):
        """Login as GM returns JWT"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": GM_EMAIL,
            "password": PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "management"
        assert data["user"]["title"] == "GM"
        assert data["user"]["name"] == "Tyler C"
        print(f"✓ GM login successful: {data['user']['name']}")
    
    def test_pm_login(self, api_client):
        """Login as PM returns JWT"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": PM_EMAIL,
            "password": PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "management"
        assert data["user"]["title"] == "Production Manager"
        assert data["user"]["name"] == "Tim A"
        assert data["user"]["division"] == "Maintenance"
        print(f"✓ PM login successful: {data['user']['name']} ({data['user']['division']})")


class TestTeamHierarchy:
    """Team hierarchy API tests"""
    
    def test_hierarchy_structure(self, api_client, owner_token):
        """GET /api/team/hierarchy returns correct structure"""
        response = api_client.get(
            f"{BASE_URL}/api/team/hierarchy",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check top-level structure
        assert "owners" in data
        assert "general_managers" in data
        assert "account_managers" in data
        assert "production_managers" in data
        assert "divisions" in data
        
        # Verify counts
        assert len(data["owners"]) == 1, "Should have 1 owner"
        assert len(data["general_managers"]) == 1, "Should have 1 GM"
        assert len(data["account_managers"]) == 3, "Should have 3 AMs"
        assert len(data["production_managers"]) == 4, "Should have 4 PMs"
        
        print(f"✓ Hierarchy: {len(data['owners'])} owner, {len(data['general_managers'])} GM, {len(data['account_managers'])} AMs, {len(data['production_managers'])} PMs")
    
    def test_hierarchy_divisions_with_pms(self, api_client, owner_token):
        """Each division has production_managers field"""
        response = api_client.get(
            f"{BASE_URL}/api/team/hierarchy",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        divisions = data["divisions"]
        assert len(divisions) == 3, "Should have 3 divisions"
        
        division_names = [d["name"] for d in divisions]
        assert "Install" in division_names
        assert "Maintenance" in division_names
        assert "Tree" in division_names
        
        for div in divisions:
            assert "production_managers" in div, f"Division {div['name']} missing production_managers field"
            assert "teams" in div, f"Division {div['name']} missing teams field"
            print(f"  ✓ {div['name']}: {len(div['production_managers'])} PMs, {len(div['teams'])} teams")
    
    def test_maintenance_division_pms(self, api_client, owner_token):
        """Maintenance division has Tim A and Scott W as PMs"""
        response = api_client.get(
            f"{BASE_URL}/api/team/hierarchy",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        maintenance = next((d for d in data["divisions"] if d["name"] == "Maintenance"), None)
        assert maintenance is not None, "Maintenance division not found"
        
        pm_names = [pm["name"] for pm in maintenance["production_managers"]]
        assert len(pm_names) == 2, f"Maintenance should have 2 PMs, got {len(pm_names)}"
        assert "Tim A" in pm_names, "Tim A should be Maintenance PM"
        assert "Scott W" in pm_names, "Scott W should be Maintenance PM"
        
        # Check teams (Marcus Thompson, Derek Washington)
        team_leads = [t["lead"]["name"] for t in maintenance["teams"]]
        assert "Marcus Thompson" in team_leads, "Marcus Thompson should lead a Maintenance crew"
        assert "Derek Washington" in team_leads, "Derek Washington should lead a Maintenance crew"
        
        print(f"✓ Maintenance division: PMs={pm_names}, Crews={team_leads}")
    
    def test_tree_division_structure(self, api_client, owner_token):
        """Tree division has Brad S as PM, Nathan Cole crew, David Park with PHC"""
        response = api_client.get(
            f"{BASE_URL}/api/team/hierarchy",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        tree = next((d for d in data["divisions"] if d["name"] == "Tree"), None)
        assert tree is not None, "Tree division not found"
        
        pm_names = [pm["name"] for pm in tree["production_managers"]]
        assert "Brad S" in pm_names, "Brad S should be Tree PM"
        
        # Check Nathan Cole crew
        team_leads = [t["lead"]["name"] for t in tree["teams"]]
        assert "Nathan Cole" in team_leads, "Nathan Cole should lead Tree Alpha"
        
        # Check David Park has Plant Healthcare division
        nathan_team = next((t for t in tree["teams"] if t["lead"]["name"] == "Nathan Cole"), None)
        assert nathan_team is not None
        
        member_names = [m["name"] for m in nathan_team["members"]]
        assert "David Park" in member_names, "David Park should be in Tree Alpha"
        
        david = next((m for m in nathan_team["members"] if m["name"] == "David Park"), None)
        assert david is not None
        assert david.get("division") == "Plant Healthcare", f"David Park should have division='Plant Healthcare', got {david.get('division')}"
        
        print(f"✓ Tree division: PM=Brad S, Lead=Nathan Cole, David Park division={david.get('division')}")


class TestTeamProfiles:
    """Team profiles API tests"""
    
    def test_profiles_count(self, api_client, owner_token):
        """GET /api/team/profiles returns 22+ profiles"""
        response = api_client.get(
            f"{BASE_URL}/api/team/profiles",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "profiles" in data
        assert "total" in data
        assert data["total"] >= 22, f"Should have 22+ profiles, got {data['total']}"
        
        print(f"✓ Team profiles: {data['total']} total")
    
    def test_profiles_have_correct_names(self, api_client, owner_token):
        """Profiles include expected names"""
        response = api_client.get(
            f"{BASE_URL}/api/team/profiles",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        names = [p["name"] for p in data["profiles"]]
        
        # Check key personnel
        expected_names = ["Adam S", "Tyler C", "Tim A", "Zach O", "Scott W", "Brad S",
                         "Megan M", "Daniel T", "Scott K",
                         "Alejandro Ruiz-Domian", "Marcus Thompson", "Derek Washington", "Nathan Cole"]
        
        for name in expected_names:
            assert name in names, f"Expected {name} in profiles"
        
        print(f"✓ All expected personnel found in profiles")


class TestTimelineStats:
    """Timeline stats API tests"""
    
    def test_crew_timeline_stats(self, api_client, owner_token):
        """GET /api/team/profiles/{profile_id}/stats returns stats"""
        profile_id = f"crew_{CREW_CODES['install_alpha']}"
        response = api_client.get(
            f"{BASE_URL}/api/team/profiles/{profile_id}/stats?months=3",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "months" in data
        assert "review_count" in data
        assert "submission_count" in data
        assert "avg_review_score" in data
        assert "training_total" in data
        assert "training_completed" in data
        
        print(f"✓ Crew stats: reviews={data['review_count']}, submissions={data['submission_count']}, avg_score={data['avg_review_score']}")
    
    def test_user_timeline_stats(self, api_client, owner_token):
        """GET /api/team/profiles/user_{id}/stats returns stats for users"""
        # First get a user profile ID
        response = api_client.get(
            f"{BASE_URL}/api/team/profiles",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        profiles = response.json()["profiles"]
        
        user_profile = next((p for p in profiles if p["source_type"] == "user"), None)
        assert user_profile is not None, "No user profiles found"
        
        # Get stats for this user
        response = api_client.get(
            f"{BASE_URL}/api/team/profiles/{user_profile['profile_id']}/stats?months=6",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["months"] == 6
        print(f"✓ User stats for {user_profile['name']}: reviews={data['review_count']}")


class TestPublicStandards:
    """Public standards API tests"""
    
    def test_all_standards(self, api_client):
        """GET /api/public/standards returns 19 standards"""
        response = api_client.get(f"{BASE_URL}/api/public/standards")
        assert response.status_code == 200
        data = response.json()
        
        assert "standards" in data
        assert len(data["standards"]) == 19, f"Should have 19 standards, got {len(data['standards'])}"
        
        print(f"✓ Public standards: {len(data['standards'])} total")
    
    def test_standards_filtered_by_division(self, api_client):
        """Standards can be filtered by division"""
        # Test Maintenance filter
        response = api_client.get(f"{BASE_URL}/api/public/standards?division=Maintenance")
        assert response.status_code == 200
        data = response.json()
        
        maintenance_standards = data["standards"]
        for std in maintenance_standards:
            # Either has Maintenance in division_targets or has empty targets (applies to all)
            targets = std.get("division_targets", [])
            assert "Maintenance" in targets or len(targets) == 0, f"Standard {std['title']} should apply to Maintenance"
        
        print(f"✓ Maintenance standards: {len(maintenance_standards)}")
        
        # Test Install filter
        response = api_client.get(f"{BASE_URL}/api/public/standards?division=Install")
        assert response.status_code == 200
        install_standards = response.json()["standards"]
        print(f"✓ Install standards: {len(install_standards)}")
        
        # Test Tree filter
        response = api_client.get(f"{BASE_URL}/api/public/standards?division=Tree")
        assert response.status_code == 200
        tree_standards = response.json()["standards"]
        print(f"✓ Tree standards: {len(tree_standards)}")


class TestCrewPortal:
    """Crew portal API tests"""
    
    def test_crew_access_links_exist(self, api_client, gm_token):
        """Crew access links exist for all demo crews"""
        response = api_client.get(
            f"{BASE_URL}/api/crew-access-links",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        items = data.get("items", [])
        codes = [item["code"] for item in items]
        
        for crew_name, code in CREW_CODES.items():
            assert code in codes, f"Crew {crew_name} ({code}) not found"
            crew = next((c for c in items if c["code"] == code), None)
            assert "label" in crew
            assert "division" in crew
            print(f"✓ Crew {crew_name}: {crew['label']} ({crew['division']})")
    
    def test_crew_has_leader_name(self, api_client, gm_token):
        """Crew access links have leader_name field"""
        response = api_client.get(
            f"{BASE_URL}/api/crew-access-links",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        items = data.get("items", [])
        for crew_name, code in CREW_CODES.items():
            crew = next((c for c in items if c["code"] == code), None)
            assert crew is not None, f"Crew {crew_name} not found"
            assert "leader_name" in crew, f"Crew {crew_name} missing leader_name field"
            print(f"✓ Crew {crew_name} leader: {crew.get('leader_name', 'N/A')}")


class TestQJAPage:
    """QJA page API tests"""
    
    def test_qja_crew_links(self, api_client, gm_token):
        """GET /api/crew-access-links returns crew links with leader_name"""
        response = api_client.get(
            f"{BASE_URL}/api/crew-access-links",
            headers={"Authorization": f"Bearer {gm_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        items = data["items"]
        assert len(items) >= 4, f"Should have at least 4 crew links, got {len(items)}"
        
        # Check each link has leader_name
        for item in items:
            assert "leader_name" in item, f"Crew link {item.get('label')} missing leader_name"
        
        print(f"✓ QJA crew links: {len(items)} total, all have leader_name field")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
