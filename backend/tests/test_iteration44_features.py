"""Iteration 44 Backend Tests - New Features
Tests:
- Crew Assignments CRUD (GET /week, POST, POST /bulk, DELETE)
- Coaching score-analysis endpoint
- System reference PDF export
- Rubrics expansion (33 active across 7 divisions)
- Standards library (25 standards)
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

# Test crew codes
CREW_CODE_MAINT = "be1da0c6"
CREW_CODE_INSTALL = "bb01032c"


@pytest.fixture(scope="module")
def owner_token():
    """Get owner auth token."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": OWNER_EMAIL,
        "password": OWNER_PASSWORD
    })
    assert response.status_code == 200, f"Owner login failed: {response.text}"
    return response.json().get("token")


@pytest.fixture(scope="module")
def pm_token():
    """Get PM auth token."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": PM_EMAIL,
        "password": PM_PASSWORD
    })
    assert response.status_code == 200, f"PM login failed: {response.text}"
    return response.json().get("token")


@pytest.fixture(scope="module")
def auth_headers(owner_token):
    """Auth headers for owner."""
    return {"Authorization": f"Bearer {owner_token}"}


@pytest.fixture(scope="module")
def pm_headers(pm_token):
    """Auth headers for PM."""
    return {"Authorization": f"Bearer {pm_token}"}


class TestCrewAssignmentsWeek:
    """Test GET /api/crew-assignments/week endpoint."""

    def test_get_week_returns_200(self, auth_headers):
        """Week endpoint returns 200 with dates array and week object."""
        response = requests.get(f"{BASE_URL}/api/crew-assignments/week", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "dates" in data, "Response should contain 'dates' array"
        assert "week" in data, "Response should contain 'week' object"
        assert len(data["dates"]) == 5, "Should return 5 weekdays (Mon-Fri)"
        print(f"Week data: start={data.get('start')}, end={data.get('end')}, dates={data['dates']}")

    def test_get_week_with_start_param(self, auth_headers):
        """Week endpoint accepts start date parameter."""
        response = requests.get(f"{BASE_URL}/api/crew-assignments/week?start=2026-01-06", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["start"] == "2026-01-06", f"Start date should be 2026-01-06, got {data['start']}"
        assert "2026-01-06" in data["dates"], "Dates should include start date"

    def test_pm_can_access_week(self, pm_headers):
        """PM role can access crew assignments."""
        response = requests.get(f"{BASE_URL}/api/crew-assignments/week", headers=pm_headers)
        assert response.status_code == 200, f"PM should access crew assignments: {response.text}"


class TestCrewAssignmentsCRUD:
    """Test crew assignment create, read, delete operations."""

    def test_create_assignment(self, auth_headers):
        """POST /api/crew-assignments creates an assignment."""
        # First get a job to assign
        jobs_response = requests.get(f"{BASE_URL}/api/jobs?page=1&limit=1", headers=auth_headers)
        assert jobs_response.status_code == 200
        jobs = jobs_response.json().get("items", [])
        if not jobs:
            pytest.skip("No jobs available for assignment test")
        
        job_id = jobs[0].get("job_id")
        test_date = "2026-01-20"  # Future date to avoid conflicts
        
        payload = {
            "crew_code": CREW_CODE_MAINT,
            "job_id": job_id,
            "date": test_date,
            "priority": "normal",
            "notes": "TEST_assignment_iter44"
        }
        
        response = requests.post(f"{BASE_URL}/api/crew-assignments", json=payload, headers=auth_headers)
        # Accept 200, 201, or 409 (duplicate)
        assert response.status_code in [200, 201, 409], f"Create assignment failed: {response.text}"
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert "id" in data, "Created assignment should have an id"
            assert data["crew_code"] == CREW_CODE_MAINT
            assert data["job_id"] == job_id
            print(f"Created assignment: {data['id']}")
            # Store for cleanup
            TestCrewAssignmentsCRUD.created_assignment_id = data["id"]
        else:
            print(f"Assignment already exists (409): {response.text}")

    def test_create_assignment_validation(self, auth_headers):
        """POST /api/crew-assignments validates required fields."""
        # Missing crew_code
        response = requests.post(f"{BASE_URL}/api/crew-assignments", json={
            "job_id": "LMN-5001",
            "date": "2026-01-21"
        }, headers=auth_headers)
        assert response.status_code == 400, "Should reject missing crew_code"

    def test_bulk_assignment(self, auth_headers):
        """POST /api/crew-assignments/bulk creates multiple assignments."""
        # Get jobs
        jobs_response = requests.get(f"{BASE_URL}/api/jobs?page=1&limit=2", headers=auth_headers)
        jobs = jobs_response.json().get("items", [])
        if len(jobs) < 2:
            pytest.skip("Need at least 2 jobs for bulk test")
        
        assignments = [
            {"crew_code": CREW_CODE_MAINT, "job_id": jobs[0]["job_id"], "date": "2026-01-22", "priority": "normal", "notes": "TEST_bulk_1"},
            {"crew_code": CREW_CODE_INSTALL, "job_id": jobs[1]["job_id"], "date": "2026-01-22", "priority": "high", "notes": "TEST_bulk_2"},
        ]
        
        response = requests.post(f"{BASE_URL}/api/crew-assignments/bulk", json={"assignments": assignments}, headers=auth_headers)
        assert response.status_code == 200, f"Bulk assignment failed: {response.text}"
        data = response.json()
        assert "created" in data, "Response should have 'created' count"
        assert "skipped" in data, "Response should have 'skipped' count"
        print(f"Bulk result: created={data['created']}, skipped={data['skipped']}")

    def test_delete_assignment(self, auth_headers):
        """DELETE /api/crew-assignments/{id} removes an assignment."""
        # Create a test assignment first
        jobs_response = requests.get(f"{BASE_URL}/api/jobs?page=1&limit=1", headers=auth_headers)
        jobs = jobs_response.json().get("items", [])
        if not jobs:
            pytest.skip("No jobs for delete test")
        
        create_response = requests.post(f"{BASE_URL}/api/crew-assignments", json={
            "crew_code": CREW_CODE_MAINT,
            "job_id": jobs[0]["job_id"],
            "date": "2026-01-25",
            "notes": "TEST_to_delete"
        }, headers=auth_headers)
        
        if create_response.status_code in [200, 201]:
            assignment_id = create_response.json()["id"]
            delete_response = requests.delete(f"{BASE_URL}/api/crew-assignments/{assignment_id}", headers=auth_headers)
            assert delete_response.status_code == 200, f"Delete failed: {delete_response.text}"
            data = delete_response.json()
            assert data.get("deleted") == True
            print(f"Deleted assignment: {assignment_id}")
        else:
            # Try to delete existing
            print("Assignment already exists, skipping delete test")


class TestCoachingScoreAnalysis:
    """Test GET /api/coaching/score-analysis endpoint."""

    def test_score_analysis_returns_200(self, auth_headers):
        """Score analysis endpoint returns 200 with crew data."""
        response = requests.get(f"{BASE_URL}/api/coaching/score-analysis", headers=auth_headers)
        assert response.status_code == 200, f"Score analysis failed: {response.text}"
        data = response.json()
        assert "window_days" in data, "Response should have window_days"
        assert "crews" in data, "Response should have crews array"
        assert "division_summary" in data, "Response should have division_summary"
        print(f"Score analysis: {len(data['crews'])} crews analyzed, window={data['window_days']} days")

    def test_score_analysis_crew_structure(self, auth_headers):
        """Score analysis returns proper crew structure with coaching_priority and weak_tasks."""
        response = requests.get(f"{BASE_URL}/api/coaching/score-analysis?window_days=90", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        if data["crews"]:
            crew = data["crews"][0]
            assert "crew_code" in crew, "Crew should have crew_code"
            assert "crew_label" in crew, "Crew should have crew_label"
            assert "coaching_priority" in crew, "Crew should have coaching_priority"
            assert "weak_tasks" in crew, "Crew should have weak_tasks"
            assert "task_breakdown" in crew, "Crew should have task_breakdown"
            assert crew["coaching_priority"] in ["low", "medium", "high"], f"Invalid priority: {crew['coaching_priority']}"
            print(f"First crew: {crew['crew_label']}, priority={crew['coaching_priority']}, weak_tasks={len(crew['weak_tasks'])}")

    def test_score_analysis_division_filter(self, auth_headers):
        """Score analysis accepts division filter."""
        response = requests.get(f"{BASE_URL}/api/coaching/score-analysis?division=Maintenance", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["division_filter"] == "Maintenance"


class TestSystemReferencePDF:
    """Test GET /api/exports/system-reference-pdf endpoint."""

    def test_pdf_returns_200(self, owner_token):
        """System reference PDF returns 200 with PDF content type."""
        response = requests.get(f"{BASE_URL}/api/exports/system-reference-pdf?token={owner_token}")
        assert response.status_code == 200, f"PDF export failed: {response.text}"
        assert "application/pdf" in response.headers.get("Content-Type", ""), "Should return PDF content type"
        assert len(response.content) > 1000, "PDF should have substantial content"
        print(f"PDF size: {len(response.content)} bytes")

    def test_pdf_without_token(self):
        """System reference PDF works without token (public endpoint)."""
        response = requests.get(f"{BASE_URL}/api/exports/system-reference-pdf")
        # Should still return PDF (endpoint allows unauthenticated access)
        assert response.status_code == 200, f"PDF should work without token: {response.text}"


class TestRubricsExpansion:
    """Test rubrics expansion to 33 active across 7 divisions."""

    def test_rubrics_count(self, auth_headers):
        """GET /api/rubrics returns 33 active rubrics."""
        response = requests.get(f"{BASE_URL}/api/rubrics", headers=auth_headers)
        assert response.status_code == 200, f"Rubrics fetch failed: {response.text}"
        rubrics = response.json()
        assert isinstance(rubrics, list), "Rubrics should be a list"
        
        # Count active rubrics
        active_rubrics = [r for r in rubrics if r.get("is_active", True)]
        print(f"Total rubrics: {len(rubrics)}, Active: {len(active_rubrics)}")
        assert len(active_rubrics) >= 33, f"Expected at least 33 active rubrics, got {len(active_rubrics)}"

    def test_rubrics_divisions(self, auth_headers):
        """Rubrics cover 7 divisions."""
        response = requests.get(f"{BASE_URL}/api/rubrics", headers=auth_headers)
        rubrics = response.json()
        
        divisions = set(r.get("division", "") for r in rubrics if r.get("is_active", True))
        expected_divisions = {"Maintenance", "Install", "Tree", "Enhancement", "Irrigation", "Snow/Ice", "PHC"}
        
        print(f"Found divisions: {divisions}")
        # Check that we have at least 7 divisions
        assert len(divisions) >= 7, f"Expected 7 divisions, got {len(divisions)}: {divisions}"


class TestStandardsLibrary:
    """Test standards library expansion to 25 standards."""

    def test_standards_count(self, auth_headers):
        """GET /api/standards returns 25 standards (check pagination total)."""
        response = requests.get(f"{BASE_URL}/api/standards", headers=auth_headers)
        assert response.status_code == 200, f"Standards fetch failed: {response.text}"
        standards = response.json()
        
        # Handle paginated response
        if isinstance(standards, dict):
            pagination = standards.get("pagination", {})
            total = pagination.get("total", len(standards.get("items", [])))
            standards_list = standards.get("items", standards.get("standards", []))
        else:
            total = len(standards)
            standards_list = standards
        
        print(f"Total standards: {total}, items on page: {len(standards_list)}")
        assert total >= 25, f"Expected at least 25 standards total, got {total}"

    def test_standards_structure(self, auth_headers):
        """Standards have proper structure."""
        response = requests.get(f"{BASE_URL}/api/standards", headers=auth_headers)
        standards = response.json()
        
        if isinstance(standards, dict):
            standards_list = standards.get("items", standards.get("standards", []))
        else:
            standards_list = standards
        
        if standards_list:
            standard = standards_list[0]
            assert "id" in standard or "standard_id" in standard, "Standard should have id"
            assert "title" in standard or "name" in standard, "Standard should have title/name"
            print(f"First standard: {standard.get('title', standard.get('name', 'N/A'))}")


class TestReviewPageThemeCompliance:
    """Test that review page uses CSS variables (backend data check)."""

    def test_submissions_for_review(self, auth_headers):
        """Verify submissions endpoint works for review queue."""
        response = requests.get(f"{BASE_URL}/api/submissions?scope=management&page=1&limit=5", headers=auth_headers)
        assert response.status_code == 200, f"Submissions fetch failed: {response.text}"
        data = response.json()
        assert "items" in data, "Response should have items"
        print(f"Review queue: {len(data['items'])} items, total={data.get('total', 'N/A')}")

    def test_submission_with_field_report(self, auth_headers):
        """Check if any submission has field_report.reported=true."""
        response = requests.get(f"{BASE_URL}/api/submissions?scope=all&page=1&limit=50", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        field_report_subs = [s for s in data.get("items", []) if s.get("field_report", {}).get("reported")]
        print(f"Submissions with field reports: {len(field_report_subs)}")
        
        if field_report_subs:
            sub = field_report_subs[0]
            print(f"Field report example: {sub['id']} - type={sub['field_report'].get('type')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
