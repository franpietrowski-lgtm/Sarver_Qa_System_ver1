"""
Iteration 30: Team Members Redesign, Account Cleanup, QR Archive/Delete, Avatar Upload

Tests:
1. GET /api/team/profiles - correct profiles (no duplicates, correct names/titles)
2. GET /api/team/hierarchy - Brad S shows as Production Manager (not GM)
3. POST /api/crew-access-links/{id}/archive - archives a crew link with archived_at timestamp
4. DELETE /api/crew-access-links/{id} - permanently deletes a crew link
5. POST /api/team/profiles/{id}/avatar - uploads avatar image to Supabase
6. Login tests for valid and invalid accounts
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials from review request
OWNER_EMAIL = "sadam.owner@slmco.local"
OWNER_PASSWORD = "SLMCo2026!"
GM_EMAIL = "ctyler.gm@slmco.local"
GM_PASSWORD = "SLMCo2026!"
ACCM_MEGAN_EMAIL = "mmegan.accm@slmco.local"
ACCM_DANIEL_EMAIL = "tdaniel.accm@slmco.local"
SUPERVISOR_EMAIL = "hjohnny.super@slmco.local"
PM_EMAIL = "atim.prom@slmco.local"
COMMON_PASSWORD = "SLMCo2026!"

# Old removed accounts that should NOT work
OLD_OWNER_EMAIL = "owner@fieldquality.local"
OLD_GM_EMAIL = "gm@fieldquality.local"


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
    pytest.skip(f"Owner login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def management_token(api_client):
    """Get management authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": SUPERVISOR_EMAIL,
        "password": COMMON_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Management login failed: {response.status_code} - {response.text}")


class TestLoginCredentials:
    """Test login works for valid accounts and fails for removed accounts"""
    
    def test_login_owner_sadam(self, api_client):
        """Login works for sadam.owner@slmco.local"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL,
            "password": OWNER_PASSWORD
        })
        assert response.status_code == 200, f"Owner login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data.get("user", {}).get("email") == OWNER_EMAIL.lower()
        print(f"PASS: Owner login works for {OWNER_EMAIL}")
    
    def test_login_gm_tyler(self, api_client):
        """Login works for ctyler.gm@slmco.local"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": GM_EMAIL,
            "password": GM_PASSWORD
        })
        assert response.status_code == 200, f"GM login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data.get("user", {}).get("email") == GM_EMAIL.lower()
        print(f"PASS: GM login works for {GM_EMAIL}")
    
    def test_login_accm_megan(self, api_client):
        """Login works for mmegan.accm@slmco.local (renamed from Megan B)"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": ACCM_MEGAN_EMAIL,
            "password": COMMON_PASSWORD
        })
        assert response.status_code == 200, f"Account Manager Megan login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data.get("user", {}).get("email") == ACCM_MEGAN_EMAIL.lower()
        print(f"PASS: Account Manager login works for {ACCM_MEGAN_EMAIL}")
    
    def test_login_accm_daniel(self, api_client):
        """Login works for tdaniel.accm@slmco.local (renamed from Daniel M)"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": ACCM_DANIEL_EMAIL,
            "password": COMMON_PASSWORD
        })
        assert response.status_code == 200, f"Account Manager Daniel login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data.get("user", {}).get("email") == ACCM_DANIEL_EMAIL.lower()
        print(f"PASS: Account Manager login works for {ACCM_DANIEL_EMAIL}")
    
    def test_login_fails_old_owner(self, api_client):
        """Login fails for old removed account owner@fieldquality.local"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": OLD_OWNER_EMAIL,
            "password": COMMON_PASSWORD
        })
        assert response.status_code == 401, f"Old owner should fail login but got: {response.status_code}"
        print(f"PASS: Old owner account {OLD_OWNER_EMAIL} correctly rejected")
    
    def test_login_fails_old_gm(self, api_client):
        """Login fails for old removed account gm@fieldquality.local"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": OLD_GM_EMAIL,
            "password": COMMON_PASSWORD
        })
        assert response.status_code == 401, f"Old GM should fail login but got: {response.status_code}"
        print(f"PASS: Old GM account {OLD_GM_EMAIL} correctly rejected")


class TestTeamProfiles:
    """Test GET /api/team/profiles returns correct profiles"""
    
    def test_profiles_returns_correct_data(self, api_client, owner_token):
        """GET /api/team/profiles returns profiles with no duplicates"""
        response = api_client.get(
            f"{BASE_URL}/api/team/profiles",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "profiles" in data
        profiles = data["profiles"]
        assert len(profiles) > 0, "No profiles returned"
        
        # Check for no duplicates by profile_id
        profile_ids = [p["profile_id"] for p in profiles]
        assert len(profile_ids) == len(set(profile_ids)), "Duplicate profile_ids found"
        
        # Check structure
        for p in profiles[:5]:
            assert "profile_id" in p
            assert "name" in p
            assert "role" in p
            assert "source_type" in p
        
        print(f"PASS: GET /api/team/profiles returns {len(profiles)} unique profiles")
    
    def test_profiles_contain_correct_names(self, api_client, owner_token):
        """Verify renamed accounts appear correctly: Megan M, Daniel T"""
        response = api_client.get(
            f"{BASE_URL}/api/team/profiles",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        profiles = response.json().get("profiles", [])
        
        # Find Megan M (renamed from Megan B)
        megan_profiles = [p for p in profiles if "Megan" in p.get("name", "")]
        assert len(megan_profiles) > 0, "Megan M not found in profiles"
        megan = megan_profiles[0]
        assert "Megan M" in megan["name"], f"Expected 'Megan M' but got '{megan['name']}'"
        print(f"PASS: Found Megan M in profiles: {megan['name']}")
        
        # Find Daniel T (renamed from Daniel M)
        daniel_profiles = [p for p in profiles if "Daniel" in p.get("name", "")]
        assert len(daniel_profiles) > 0, "Daniel T not found in profiles"
        daniel = daniel_profiles[0]
        assert "Daniel T" in daniel["name"], f"Expected 'Daniel T' but got '{daniel['name']}'"
        print(f"PASS: Found Daniel T in profiles: {daniel['name']}")


class TestTeamHierarchy:
    """Test GET /api/team/hierarchy returns correct hierarchy"""
    
    def test_hierarchy_brad_s_is_production_manager(self, api_client, owner_token):
        """Brad S shows as Production Manager (not GM)"""
        response = api_client.get(
            f"{BASE_URL}/api/team/hierarchy",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Check Brad S is in production_managers, not general_managers
        production_managers = data.get("production_managers", [])
        general_managers = data.get("general_managers", [])
        
        brad_in_pm = any("Brad" in pm.get("name", "") for pm in production_managers)
        brad_in_gm = any("Brad" in gm.get("name", "") for gm in general_managers)
        
        assert brad_in_pm, f"Brad S not found in production_managers: {[pm.get('name') for pm in production_managers]}"
        assert not brad_in_gm, f"Brad S should NOT be in general_managers: {[gm.get('name') for gm in general_managers]}"
        
        # Verify Brad's title
        brad = next((pm for pm in production_managers if "Brad" in pm.get("name", "")), None)
        assert brad is not None
        assert brad.get("title") == "Production Manager", f"Brad's title should be 'Production Manager' but got '{brad.get('title')}'"
        
        print(f"PASS: Brad S is correctly listed as Production Manager: {brad}")
    
    def test_hierarchy_structure_complete(self, api_client, owner_token):
        """Hierarchy returns all expected levels"""
        response = api_client.get(
            f"{BASE_URL}/api/team/hierarchy",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check all levels exist
        assert "owners" in data
        assert "general_managers" in data
        assert "account_managers" in data
        assert "production_managers" in data
        assert "supervisors" in data
        assert "divisions" in data
        
        print(f"PASS: Hierarchy structure complete with {len(data.get('owners', []))} owners, "
              f"{len(data.get('general_managers', []))} GMs, {len(data.get('production_managers', []))} PMs")


class TestCrewAccessArchive:
    """Test POST /api/crew-access-links/{id}/archive"""
    
    def test_archive_crew_link(self, api_client, owner_token):
        """Archive a crew link sets archived=true and archived_at timestamp"""
        # First create a test crew link
        create_response = api_client.post(
            f"{BASE_URL}/api/crew-access-links",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={
                "label": "TEST_Archive_Iter30",
                "truck_number": "TR-TEST",
                "division": "Maintenance",
                "assignment": "Test assignment"
            }
        )
        assert create_response.status_code == 200, f"Failed to create test crew link: {create_response.text}"
        created_link = create_response.json()
        link_id = created_link["id"]
        
        # Archive the link
        archive_response = api_client.post(
            f"{BASE_URL}/api/crew-access-links/{link_id}/archive",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert archive_response.status_code == 200, f"Archive failed: {archive_response.text}"
        archive_data = archive_response.json()
        assert archive_data.get("archived") == True
        assert archive_data.get("id") == link_id
        print(f"PASS: Archive endpoint returns archived=true for {link_id}")
        
        # Verify the link is now in inactive list with archived_at
        inactive_response = api_client.get(
            f"{BASE_URL}/api/crew-access-links?status=inactive&page=1&limit=50",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert inactive_response.status_code == 200
        inactive_links = inactive_response.json().get("items", [])
        
        archived_link = next((l for l in inactive_links if l["id"] == link_id), None)
        assert archived_link is not None, f"Archived link not found in inactive list"
        assert archived_link.get("archived") == True
        assert archived_link.get("archived_at") is not None, "archived_at timestamp missing"
        assert archived_link.get("enabled") == False
        
        print(f"PASS: Archived link has archived_at timestamp: {archived_link.get('archived_at')}")
        
        # Cleanup - delete the test link
        api_client.delete(
            f"{BASE_URL}/api/crew-access-links/{link_id}",
            headers={"Authorization": f"Bearer {owner_token}"}
        )


class TestCrewAccessDelete:
    """Test DELETE /api/crew-access-links/{id}"""
    
    def test_delete_crew_link_permanently(self, api_client, owner_token):
        """DELETE permanently removes a crew link"""
        # First create a test crew link
        create_response = api_client.post(
            f"{BASE_URL}/api/crew-access-links",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={
                "label": "TEST_Delete_Iter30",
                "truck_number": "TR-DEL",
                "division": "Install",
                "assignment": "To be deleted"
            }
        )
        assert create_response.status_code == 200, f"Failed to create test crew link: {create_response.text}"
        created_link = create_response.json()
        link_id = created_link["id"]
        
        # Delete the link
        delete_response = api_client.delete(
            f"{BASE_URL}/api/crew-access-links/{link_id}",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert delete_response.status_code == 200, f"Delete failed: {delete_response.text}"
        delete_data = delete_response.json()
        assert delete_data.get("deleted") == True
        assert delete_data.get("id") == link_id
        print(f"PASS: Delete endpoint returns deleted=true for {link_id}")
        
        # Verify the link is gone from both active and inactive lists
        active_response = api_client.get(
            f"{BASE_URL}/api/crew-access-links?status=active&page=1&limit=100",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        active_links = active_response.json().get("items", [])
        assert not any(l["id"] == link_id for l in active_links), "Deleted link still in active list"
        
        inactive_response = api_client.get(
            f"{BASE_URL}/api/crew-access-links?status=inactive&page=1&limit=100",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        inactive_links = inactive_response.json().get("items", [])
        assert not any(l["id"] == link_id for l in inactive_links), "Deleted link still in inactive list"
        
        print(f"PASS: Crew link {link_id} permanently deleted and not found in any list")
    
    def test_delete_requires_owner_role(self, api_client, management_token):
        """DELETE requires owner role (management should fail)"""
        # Create a test link first with owner
        owner_response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL,
            "password": OWNER_PASSWORD
        })
        owner_token_temp = owner_response.json().get("token")
        
        create_response = api_client.post(
            f"{BASE_URL}/api/crew-access-links",
            headers={"Authorization": f"Bearer {owner_token_temp}"},
            json={
                "label": "TEST_Delete_Perm_Iter30",
                "truck_number": "TR-PERM",
                "division": "Tree",
                "assignment": "Permission test"
            }
        )
        link_id = create_response.json()["id"]
        
        # Try to delete with management token - should fail
        delete_response = api_client.delete(
            f"{BASE_URL}/api/crew-access-links/{link_id}",
            headers={"Authorization": f"Bearer {management_token}"}
        )
        assert delete_response.status_code == 403, f"Management should not be able to delete, got: {delete_response.status_code}"
        print(f"PASS: DELETE correctly requires owner role (management got 403)")
        
        # Cleanup with owner token
        api_client.delete(
            f"{BASE_URL}/api/crew-access-links/{link_id}",
            headers={"Authorization": f"Bearer {owner_token_temp}"}
        )


class TestAvatarUpload:
    """Test POST /api/team/profiles/{id}/avatar"""
    
    def test_avatar_upload_endpoint_exists(self, api_client, owner_token):
        """Avatar upload endpoint exists and validates input"""
        # Get a profile ID to test with
        profiles_response = api_client.get(
            f"{BASE_URL}/api/team/profiles",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        profiles = profiles_response.json().get("profiles", [])
        assert len(profiles) > 0, "No profiles to test avatar upload"
        
        test_profile_id = profiles[0]["profile_id"]
        
        # Test without file - should fail with 422 (validation error)
        response = api_client.post(
            f"{BASE_URL}/api/team/profiles/{test_profile_id}/avatar",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        # Should fail because no file provided
        assert response.status_code in [400, 422], f"Expected validation error, got: {response.status_code}"
        print(f"PASS: Avatar upload endpoint validates file requirement")
    
    def test_avatar_upload_with_file(self, api_client, owner_token):
        """Avatar upload with actual file works (if Supabase configured)"""
        # Get a profile ID to test with
        profiles_response = api_client.get(
            f"{BASE_URL}/api/team/profiles",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        profiles = profiles_response.json().get("profiles", [])
        test_profile_id = profiles[0]["profile_id"]
        
        # Create a simple test image (1x1 pixel PNG)
        import base64
        # Minimal valid PNG
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        
        files = {"file": ("test_avatar.png", png_data, "image/png")}
        response = requests.post(
            f"{BASE_URL}/api/team/profiles/{test_profile_id}/avatar",
            headers={"Authorization": f"Bearer {owner_token}"},
            files=files
        )
        
        if response.status_code == 503:
            print(f"SKIP: Storage not configured (503) - avatar upload requires Supabase")
            pytest.skip("Storage not configured")
        
        assert response.status_code == 200, f"Avatar upload failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "avatar_url" in data
        assert "profile_id" in data
        assert data["profile_id"] == test_profile_id
        print(f"PASS: Avatar uploaded successfully, URL: {data['avatar_url'][:50]}...")


class TestCrewLinkProjection:
    """Test that crew links include archived and archived_at fields"""
    
    def test_inactive_links_include_archive_fields(self, api_client, owner_token):
        """Inactive crew links include archived and archived_at fields"""
        response = api_client.get(
            f"{BASE_URL}/api/crew-access-links?status=inactive&page=1&limit=10",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check projection includes archive fields
        items = data.get("items", [])
        if len(items) > 0:
            sample = items[0]
            # These fields should be in the projection
            expected_fields = ["id", "code", "label", "truck_number", "division", "enabled"]
            for field in expected_fields:
                assert field in sample, f"Missing field: {field}"
            
            # archived and archived_at should be present for archived links
            if sample.get("archived"):
                assert "archived_at" in sample, "archived_at missing from archived link"
                print(f"PASS: Inactive link includes archived_at: {sample.get('archived_at')}")
            else:
                print(f"PASS: Inactive link projection correct (link not archived yet)")
        else:
            print("INFO: No inactive links to verify projection")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
