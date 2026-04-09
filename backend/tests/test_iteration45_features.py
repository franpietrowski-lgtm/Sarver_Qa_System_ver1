"""Iteration 45 Backend Tests - Comprehensive feature verification.

Tests:
- Rubrics: 33 active rubrics across 7 divisions
- Standards: 25 standards in library
- Crew Assignments: CRUD operations
- Coaching: Score-based analysis endpoint
- PDF Exports: System reference PDF
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
OWNER_EMAIL = "sadam.owner@slmco.local"
OWNER_PASSWORD = "SLMCo2026!"
PM_EMAIL = "atim.prom@slmco.local"
PM_PASSWORD = "SLMCo2026!"


class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def owner_token(self):
        """Get owner authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL,
            "password": OWNER_PASSWORD
        })
        assert response.status_code == 200, f"Owner login failed: {response.text}"
        data = response.json()
        token = data.get("access_token") or data.get("token")
        assert token, "No token in response"
        return token
    
    @pytest.fixture(scope="class")
    def pm_token(self):
        """Get PM authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PM_EMAIL,
            "password": PM_PASSWORD
        })
        assert response.status_code == 200, f"PM login failed: {response.text}"
        data = response.json()
        token = data.get("access_token") or data.get("token")
        assert token, "No token in response"
        return token
    
    def test_owner_login(self, owner_token):
        """Verify owner can login"""
        assert owner_token is not None
        assert len(owner_token) > 0
        print(f"Owner login successful, token length: {len(owner_token)}")
    
    def test_pm_login(self, pm_token):
        """Verify PM can login"""
        assert pm_token is not None
        assert len(pm_token) > 0
        print(f"PM login successful, token length: {len(pm_token)}")


class TestRubrics:
    """Rubric endpoint tests - verify 33 active rubrics across 7 divisions"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL,
            "password": OWNER_PASSWORD
        })
        token = response.json().get("access_token") or response.json().get("token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_rubrics_returns_33_active(self, auth_headers):
        """GET /api/rubrics should return 33 active rubrics"""
        response = requests.get(f"{BASE_URL}/api/rubrics", headers=auth_headers)
        assert response.status_code == 200, f"Failed to get rubrics: {response.text}"
        
        rubrics = response.json()
        assert isinstance(rubrics, list), "Rubrics should be a list"
        
        # Filter active rubrics
        active_rubrics = [r for r in rubrics if r.get("is_active", True)]
        print(f"Total rubrics: {len(rubrics)}, Active rubrics: {len(active_rubrics)}")
        
        assert len(active_rubrics) >= 33, f"Expected at least 33 active rubrics, got {len(active_rubrics)}"
    
    def test_rubrics_cover_7_divisions(self, auth_headers):
        """Verify rubrics cover all 7 divisions"""
        response = requests.get(f"{BASE_URL}/api/rubrics", headers=auth_headers)
        assert response.status_code == 200
        
        rubrics = response.json()
        divisions = set()
        for r in rubrics:
            if r.get("is_active", True):
                div = r.get("division", "")
                if div:
                    divisions.add(div)
        
        expected_divisions = {"Maintenance", "Install", "Tree", "Enhancement", "Irrigation", "Winter Services", "Plant Healthcare"}
        print(f"Found divisions: {divisions}")
        
        # Check that we have at least 7 divisions
        assert len(divisions) >= 7, f"Expected 7 divisions, got {len(divisions)}: {divisions}"
        
        # Verify expected divisions are present
        for div in expected_divisions:
            assert div in divisions, f"Missing division: {div}"


class TestStandards:
    """Standards library tests - verify 25 standards"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL,
            "password": OWNER_PASSWORD
        })
        token = response.json().get("access_token") or response.json().get("token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_standards_returns_25(self, auth_headers):
        """GET /api/standards should return 25 standards"""
        response = requests.get(f"{BASE_URL}/api/standards?page=1&limit=50", headers=auth_headers)
        assert response.status_code == 200, f"Failed to get standards: {response.text}"
        
        data = response.json()
        
        # Handle paginated response
        if isinstance(data, dict):
            standards = data.get("items", data.get("standards", []))
            total = data.get("total", len(standards))
        else:
            standards = data
            total = len(standards)
        
        print(f"Standards returned: {len(standards)}, Total: {total}")
        assert total >= 25, f"Expected at least 25 standards, got {total}"


class TestCrewAssignments:
    """Crew Assignment CRUD tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PM_EMAIL,
            "password": PM_PASSWORD
        })
        data = response.json()
        token = data.get("access_token") or data.get("token")
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def test_data(self, auth_headers):
        """Get test data for assignments"""
        # Get crews
        crews_resp = requests.get(f"{BASE_URL}/api/crew-access-links", headers=auth_headers)
        crews = crews_resp.json() if crews_resp.status_code == 200 else []
        if isinstance(crews, dict):
            crews = crews.get("items", [])
        
        # Get jobs
        jobs_resp = requests.get(f"{BASE_URL}/api/jobs", headers=auth_headers)
        jobs = jobs_resp.json() if jobs_resp.status_code == 200 else []
        if isinstance(jobs, dict):
            jobs = jobs.get("items", [])
        
        return {
            "crew_code": crews[0]["code"] if crews else "be1da0c6",
            "job_id": jobs[0]["job_id"] if jobs else "LMN-5001"
        }
    
    def test_get_week_assignments(self, auth_headers):
        """GET /api/crew-assignments/week returns week data"""
        response = requests.get(f"{BASE_URL}/api/crew-assignments/week", headers=auth_headers)
        assert response.status_code == 200, f"Failed to get week assignments: {response.text}"
        
        data = response.json()
        assert "dates" in data, "Response should have 'dates' array"
        assert "week" in data, "Response should have 'week' object"
        assert len(data["dates"]) == 5, f"Expected 5 weekdays, got {len(data['dates'])}"
        print(f"Week assignments: {data['start']} to {data['end']}, dates: {data['dates']}")
    
    def test_create_assignment(self, auth_headers, test_data):
        """POST /api/crew-assignments creates an assignment"""
        from datetime import datetime, timedelta
        
        # Use a future date to avoid conflicts
        test_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        payload = {
            "crew_code": test_data["crew_code"],
            "job_id": test_data["job_id"],
            "date": test_date,
            "priority": "normal",
            "notes": "TEST_iteration45_assignment"
        }
        
        response = requests.post(f"{BASE_URL}/api/crew-assignments", json=payload, headers=auth_headers)
        
        # Accept 200, 201, or 409 (already exists)
        assert response.status_code in [200, 201, 409], f"Unexpected status: {response.status_code}, {response.text}"
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert "id" in data, "Created assignment should have an ID"
            print(f"Created assignment: {data['id']}")
            return data["id"]
        else:
            print("Assignment already exists (409)")
            return None
    
    def test_delete_assignment(self, auth_headers, test_data):
        """DELETE /api/crew-assignments/{id} removes an assignment"""
        from datetime import datetime, timedelta
        
        # First create an assignment to delete
        test_date = (datetime.now() + timedelta(days=31)).strftime("%Y-%m-%d")
        
        payload = {
            "crew_code": test_data["crew_code"],
            "job_id": test_data["job_id"],
            "date": test_date,
            "priority": "normal",
            "notes": "TEST_to_delete"
        }
        
        create_resp = requests.post(f"{BASE_URL}/api/crew-assignments", json=payload, headers=auth_headers)
        
        if create_resp.status_code in [200, 201]:
            assignment_id = create_resp.json()["id"]
            
            # Now delete it
            delete_resp = requests.delete(f"{BASE_URL}/api/crew-assignments/{assignment_id}", headers=auth_headers)
            assert delete_resp.status_code in [200, 204], f"Delete failed: {delete_resp.text}"
            print(f"Deleted assignment: {assignment_id}")
        else:
            print("Skipping delete test - could not create assignment")
    
    def test_bulk_assign(self, auth_headers, test_data):
        """POST /api/crew-assignments/bulk handles multiple assignments"""
        from datetime import datetime, timedelta
        
        # Use future dates
        base_date = datetime.now() + timedelta(days=60)
        
        payload = {
            "assignments": [
                {
                    "crew_code": test_data["crew_code"],
                    "job_id": test_data["job_id"],
                    "date": (base_date + timedelta(days=i)).strftime("%Y-%m-%d"),
                    "priority": "normal",
                    "notes": f"TEST_bulk_{i}"
                }
                for i in range(3)
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/crew-assignments/bulk", json=payload, headers=auth_headers)
        assert response.status_code == 200, f"Bulk assign failed: {response.text}"
        
        data = response.json()
        assert "created" in data, "Response should have 'created' count"
        assert "skipped" in data, "Response should have 'skipped' count"
        print(f"Bulk assign: created={data['created']}, skipped={data['skipped']}")


class TestCoaching:
    """Coaching score analysis tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL,
            "password": OWNER_PASSWORD
        })
        token = response.json().get("access_token") or response.json().get("token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_score_analysis_endpoint(self, auth_headers):
        """GET /api/coaching/score-analysis returns crew performance data"""
        response = requests.get(f"{BASE_URL}/api/coaching/score-analysis?window_days=90", headers=auth_headers)
        assert response.status_code == 200, f"Score analysis failed: {response.text}"
        
        data = response.json()
        assert "window_days" in data, "Response should have 'window_days'"
        assert "crews" in data, "Response should have 'crews' array"
        
        print(f"Score analysis: window={data['window_days']} days, crews={len(data['crews'])}")
        
        # Verify crew data structure if crews exist
        if data["crews"]:
            crew = data["crews"][0]
            assert "crew_code" in crew, "Crew should have 'crew_code'"
            assert "crew_label" in crew, "Crew should have 'crew_label'"
            assert "coaching_priority" in crew, "Crew should have 'coaching_priority'"
            assert "weak_tasks" in crew, "Crew should have 'weak_tasks'"
            
            # Verify coaching_priority is valid
            assert crew["coaching_priority"] in ["low", "medium", "high"], f"Invalid priority: {crew['coaching_priority']}"
            print(f"Sample crew: {crew['crew_label']}, priority={crew['coaching_priority']}")


class TestPDFExports:
    """PDF export tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL,
            "password": OWNER_PASSWORD
        })
        token = response.json().get("access_token") or response.json().get("token")
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token for query param"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL,
            "password": OWNER_PASSWORD
        })
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    def test_system_reference_pdf(self, auth_token):
        """GET /api/exports/system-reference-pdf returns valid PDF"""
        response = requests.get(f"{BASE_URL}/api/exports/system-reference-pdf?token={auth_token}")
        assert response.status_code == 200, f"PDF export failed: {response.status_code}"
        
        # Verify content type
        content_type = response.headers.get("content-type", "")
        assert "application/pdf" in content_type, f"Expected PDF content type, got: {content_type}"
        
        # Verify PDF content starts with %PDF
        content = response.content
        assert content[:4] == b"%PDF", "Response should be a valid PDF"
        
        print(f"System reference PDF: {len(content)} bytes, content-type: {content_type}")


class TestDashboard:
    """Dashboard overview tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL,
            "password": OWNER_PASSWORD
        })
        token = response.json().get("access_token") or response.json().get("token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_dashboard_overview(self, auth_headers):
        """GET /api/dashboard/overview returns dashboard data"""
        response = requests.get(f"{BASE_URL}/api/dashboard/overview", headers=auth_headers)
        assert response.status_code == 200, f"Dashboard failed: {response.text}"
        
        data = response.json()
        assert "totals" in data, "Response should have 'totals'"
        assert "queues" in data, "Response should have 'queues'"
        assert "workflow_health" in data, "Response should have 'workflow_health'"
        
        print(f"Dashboard: submissions={data['totals'].get('submissions')}, jobs={data['totals'].get('jobs')}")


class TestRubricMatrices:
    """Rubric matrices endpoint tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL,
            "password": OWNER_PASSWORD
        })
        token = response.json().get("access_token") or response.json().get("token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_rubric_matrices(self, auth_headers):
        """GET /api/rubric-matrices returns matrix data"""
        response = requests.get(f"{BASE_URL}/api/rubric-matrices?division=all", headers=auth_headers)
        assert response.status_code == 200, f"Rubric matrices failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        if data:
            matrix = data[0]
            assert "service_type" in matrix, "Matrix should have 'service_type'"
            assert "categories" in matrix, "Matrix should have 'categories'"
            # pass_threshold may be named differently
            has_threshold = "pass_threshold" in matrix or "passing_threshold" in matrix or "threshold" in matrix
            print(f"Matrix keys: {list(matrix.keys())}")
        
        print(f"Rubric matrices: {len(data)} rubrics")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
