"""
Iteration 32: System Health Check Tests
- Backend health, auth, public standards API with division filtering
- Team hierarchy with production_managers per division
- Team profiles, team structure, timeline stats
- Submissions count verification
- Demo crews verification
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
OWNER_EMAIL = "sadam.owner@slmco.local"
GM_EMAIL = "ctyler.gm@slmco.local"  # Note: ctyler not tylerc
PM_EMAIL = "tima.pm@slmco.local"
PASSWORD = "SLMCo2026!"

# Demo crew codes
CREW_INSTALL_ALPHA = "bb01032c"
CREW_MAINTENANCE_ALPHA = "be1da0c6"
CREW_MAINTENANCE_BRAVO = "e4444b93"
CREW_TREE_ALPHA = "47701159"


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
    return response.json().get("token")  # API returns 'token' not 'access_token'


@pytest.fixture(scope="module")
def gm_token(api_client):
    """Get GM authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": GM_EMAIL,
        "password": PASSWORD
    })
    assert response.status_code == 200, f"GM login failed: {response.text}"
    return response.json().get("token")  # API returns 'token' not 'access_token'


@pytest.fixture(scope="module")
def owner_client(api_client, owner_token):
    """Session with Owner auth header"""
    api_client.headers.update({"Authorization": f"Bearer {owner_token}"})
    return api_client


class TestBackendHealth:
    """Backend health check tests"""
    
    def test_health_endpoint_returns_ok(self, api_client):
        """GET /api/health returns ok"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        print("PASS: Health endpoint returns ok")


class TestAuthentication:
    """Authentication tests for Owner and GM"""
    
    def test_owner_login_returns_jwt(self, api_client):
        """Login as Owner returns JWT"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL,
            "password": PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data  # API returns 'token' not 'access_token'
        assert len(data["token"]) > 0
        print(f"PASS: Owner login returns JWT (token length: {len(data['token'])})")
    
    def test_gm_login_returns_jwt(self, api_client):
        """Login as GM returns JWT"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": GM_EMAIL,
            "password": PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data  # API returns 'token' not 'access_token'
        assert len(data["token"]) > 0
        print(f"PASS: GM login returns JWT (token length: {len(data['token'])})")


class TestPublicStandardsAPI:
    """Public standards API tests with division filtering"""
    
    def test_public_standards_returns_19_total(self, api_client):
        """GET /api/public/standards returns 19 standards total"""
        response = api_client.get(f"{BASE_URL}/api/public/standards")
        assert response.status_code == 200
        data = response.json()
        standards = data.get("standards", [])
        assert len(standards) == 19, f"Expected 19 standards, got {len(standards)}"
        print(f"PASS: Public standards returns 19 total standards")
    
    def test_public_standards_maintenance_filter(self, api_client):
        """GET /api/public/standards?division=Maintenance returns 11 standards"""
        response = api_client.get(f"{BASE_URL}/api/public/standards?division=Maintenance")
        assert response.status_code == 200
        data = response.json()
        standards = data.get("standards", [])
        assert len(standards) == 11, f"Expected 11 Maintenance standards, got {len(standards)}"
        print(f"PASS: Maintenance filter returns 11 standards")
    
    def test_public_standards_install_filter(self, api_client):
        """GET /api/public/standards?division=Install returns 9 standards"""
        response = api_client.get(f"{BASE_URL}/api/public/standards?division=Install")
        assert response.status_code == 200
        data = response.json()
        standards = data.get("standards", [])
        assert len(standards) == 9, f"Expected 9 Install standards, got {len(standards)}"
        print(f"PASS: Install filter returns 9 standards")
    
    def test_public_standards_tree_filter(self, api_client):
        """GET /api/public/standards?division=Tree returns 7 standards"""
        response = api_client.get(f"{BASE_URL}/api/public/standards?division=Tree")
        assert response.status_code == 200
        data = response.json()
        standards = data.get("standards", [])
        assert len(standards) == 7, f"Expected 7 Tree standards, got {len(standards)}"
        print(f"PASS: Tree filter returns 7 standards")


class TestTeamHierarchyAPI:
    """Team hierarchy API tests"""
    
    def test_hierarchy_returns_correct_counts(self, owner_client):
        """GET /api/team/hierarchy returns correct role counts"""
        response = owner_client.get(f"{BASE_URL}/api/team/hierarchy")
        assert response.status_code == 200
        data = response.json()
        
        # Verify counts
        assert len(data.get("owners", [])) == 1, f"Expected 1 owner, got {len(data.get('owners', []))}"
        assert len(data.get("general_managers", [])) == 1, f"Expected 1 GM, got {len(data.get('general_managers', []))}"
        assert len(data.get("production_managers", [])) == 4, f"Expected 4 PMs, got {len(data.get('production_managers', []))}"
        assert len(data.get("account_managers", [])) == 3, f"Expected 3 AMs, got {len(data.get('account_managers', []))}"
        assert len(data.get("supervisors", [])) == 3, f"Expected 3 supervisors, got {len(data.get('supervisors', []))}"
        
        print(f"PASS: Hierarchy returns 1 owner, 1 GM, 4 PMs, 3 AMs, 3 supervisors")
    
    def test_hierarchy_returns_three_divisions(self, owner_client):
        """GET /api/team/hierarchy returns 3 divisions (Install/Maintenance/Tree)"""
        response = owner_client.get(f"{BASE_URL}/api/team/hierarchy")
        assert response.status_code == 200
        data = response.json()
        
        divisions = data.get("divisions", [])
        division_names = [d["name"] for d in divisions]
        
        assert len(divisions) == 3, f"Expected 3 divisions, got {len(divisions)}"
        assert "Install" in division_names, "Install division missing"
        assert "Maintenance" in division_names, "Maintenance division missing"
        assert "Tree" in division_names, "Tree division missing"
        
        print(f"PASS: Hierarchy returns 3 divisions: {division_names}")
    
    def test_hierarchy_divisions_have_production_managers(self, owner_client):
        """Hierarchy divisions have production_managers field"""
        response = owner_client.get(f"{BASE_URL}/api/team/hierarchy")
        assert response.status_code == 200
        data = response.json()
        
        divisions = data.get("divisions", [])
        for div in divisions:
            assert "production_managers" in div, f"Division {div['name']} missing production_managers field"
            pms = div.get("production_managers", [])
            print(f"  Division {div['name']}: {len(pms)} PM(s) - {[pm['name'] for pm in pms]}")
        
        print(f"PASS: All divisions have production_managers field")


class TestTeamProfilesAPI:
    """Team profiles API tests"""
    
    def test_profiles_returns_minimum_22(self, owner_client):
        """GET /api/team/profiles returns 22+ profiles"""
        response = owner_client.get(f"{BASE_URL}/api/team/profiles")
        assert response.status_code == 200
        data = response.json()
        
        profiles = data.get("profiles", [])
        total = data.get("total", 0)
        
        assert total >= 22, f"Expected 22+ profiles, got {total}"
        print(f"PASS: Team profiles returns {total} profiles (minimum 22)")
        
        # Count by type
        users = [p for p in profiles if p.get("source_type") == "user"]
        crews = [p for p in profiles if p.get("source_type") == "crew"]
        members = [p for p in profiles if p.get("source_type") == "member"]
        print(f"  Breakdown: {len(users)} admin users, {len(crews)} crew leaders, {len(members)} crew members")


class TestTeamStructureAPI:
    """Team structure API tests"""
    
    def test_structure_returns_four_teams(self, owner_client):
        """GET /api/team/structure returns 4 teams"""
        response = owner_client.get(f"{BASE_URL}/api/team/structure")
        assert response.status_code == 200
        data = response.json()
        
        teams = data.get("teams", [])
        assert len(teams) == 4, f"Expected 4 teams, got {len(teams)}"
        print(f"PASS: Team structure returns 4 teams")
    
    def test_structure_has_correct_leaders(self, owner_client):
        """Team structure has correct leader names"""
        response = owner_client.get(f"{BASE_URL}/api/team/structure")
        assert response.status_code == 200
        data = response.json()
        
        teams = data.get("teams", [])
        leader_names = [t["lead"]["name"] for t in teams]
        
        expected_leaders = ["Alejandro Ruiz-Domian", "Marcus Thompson", "Derek Washington", "Nathan Cole"]
        for expected in expected_leaders:
            assert expected in leader_names, f"Leader {expected} not found in {leader_names}"
        
        print(f"PASS: Team structure has correct leaders: {leader_names}")


class TestTimelineStatsAPI:
    """Timeline stats API tests"""
    
    def test_timeline_stats_for_crew(self, owner_client):
        """GET /api/team/profiles/crew_bb01032c/stats?months=12 returns stats"""
        response = owner_client.get(f"{BASE_URL}/api/team/profiles/crew_{CREW_INSTALL_ALPHA}/stats?months=12")
        assert response.status_code == 200
        data = response.json()
        
        assert "review_count" in data
        assert "submission_count" in data
        assert "avg_review_score" in data
        assert "training_total" in data
        assert "training_completed" in data
        
        print(f"PASS: Timeline stats returns: reviews={data['review_count']}, submissions={data['submission_count']}, training={data['training_completed']}/{data['training_total']}")


class TestSubmissionsAPI:
    """Submissions API tests"""
    
    def test_submissions_returns_29_plus(self, owner_client):
        """GET /api/submissions returns 29+ total submissions"""
        response = owner_client.get(f"{BASE_URL}/api/submissions?limit=100")
        assert response.status_code == 200
        data = response.json()
        
        total = data.get("pagination", {}).get("total", 0)
        assert total >= 29, f"Expected 29+ submissions, got {total}"
        print(f"PASS: Submissions API returns {total} total submissions")


class TestDemoCrewsAPI:
    """Demo crews verification tests"""
    
    def test_install_alpha_crew_exists(self, api_client):
        """Demo crew bb01032c (Install Alpha) exists"""
        response = api_client.get(f"{BASE_URL}/api/public/crew-access/{CREW_INSTALL_ALPHA}")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("label") == "Install Alpha"
        assert data.get("leader_name") == "Alejandro Ruiz-Domian"
        assert data.get("division") == "Install"
        assert data.get("truck_number") == "TR-01"
        
        print(f"PASS: Install Alpha crew exists with correct data")
    
    def test_maintenance_alpha_crew_exists(self, api_client):
        """Demo crew be1da0c6 (Maintenance Alpha) exists"""
        response = api_client.get(f"{BASE_URL}/api/public/crew-access/{CREW_MAINTENANCE_ALPHA}")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("label") == "Maintenance Alpha"
        assert data.get("leader_name") == "Marcus Thompson"
        assert data.get("division") == "Maintenance"
        
        print(f"PASS: Maintenance Alpha crew exists with correct data")
    
    def test_maintenance_bravo_crew_exists(self, api_client):
        """Demo crew e4444b93 (Maintenance Bravo) exists"""
        response = api_client.get(f"{BASE_URL}/api/public/crew-access/{CREW_MAINTENANCE_BRAVO}")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("label") == "Maintenance Bravo"
        assert data.get("leader_name") == "Derek Washington"
        assert data.get("division") == "Maintenance"
        
        print(f"PASS: Maintenance Bravo crew exists with correct data")
    
    def test_tree_alpha_crew_exists(self, api_client):
        """Demo crew 47701159 (Tree Alpha) exists"""
        response = api_client.get(f"{BASE_URL}/api/public/crew-access/{CREW_TREE_ALPHA}")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("label") == "Tree Alpha"
        assert data.get("leader_name") == "Nathan Cole"
        assert data.get("division") == "Tree"
        
        print(f"PASS: Tree Alpha crew exists with correct data")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
