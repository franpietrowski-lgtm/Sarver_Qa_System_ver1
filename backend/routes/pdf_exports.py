"""PDF export & job search for Client Quality Report."""
import io
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from starlette.responses import StreamingResponse

import shared.deps as deps
from shared.deps import require_roles

router = APIRouter()


def _safe(text):
    if not text:
        return ""
    return str(text).encode("ascii", "replace").decode("ascii")


def _short_date(iso_str):
    if not iso_str:
        return "-"
    try:
        dt = datetime.fromisoformat(str(iso_str).replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y %I:%M %p")
    except Exception:
        return str(iso_str)[:19]


# ── Job search with fuzzy match ──

@router.get("/reports/job-search")
async def job_search(
    user: dict = Depends(require_roles("management", "owner")),
    q: str = Query("", min_length=0),
):
    """Fuzzy search jobs by name, property, or job_id. Returns top 15 matches."""
    query_lower = q.strip().lower()
    if not query_lower:
        jobs = await deps.db.jobs.find(
            {}, {"_id": 0, "id": 1, "job_id": 1, "job_name": 1, "property_name": 1, "division": 1, "service_type": 1}
        ).sort("job_name", 1).to_list(15)
        return {"results": jobs}

    regex_filter = {"$or": [
        {"job_name": {"$regex": query_lower, "$options": "i"}},
        {"property_name": {"$regex": query_lower, "$options": "i"}},
        {"job_id": {"$regex": query_lower, "$options": "i"}},
        {"search_text": {"$regex": query_lower, "$options": "i"}},
    ]}
    jobs = await deps.db.jobs.find(
        regex_filter, {"_id": 0, "id": 1, "job_id": 1, "job_name": 1, "property_name": 1, "division": 1, "service_type": 1}
    ).to_list(15)
    return {"results": jobs}


# ── Report preview (JSON) ──

@router.get("/reports/client-quality")
async def client_quality_report(
    user: dict = Depends(require_roles("management", "owner")),
    job_id: str = Query("all"),
    period: str = Query("monthly"),
    days: int = Query(0),
):
    """Client quality report data. period: daily/weekly/monthly/quarterly/custom."""
    now = datetime.now(timezone.utc)
    if period == "daily":
        cutoff = now - timedelta(days=1)
    elif period == "weekly":
        cutoff = now - timedelta(days=7)
    elif period == "monthly":
        cutoff = now - timedelta(days=30)
    elif period == "quarterly":
        cutoff = now - timedelta(days=90)
    elif period == "custom" and days > 0:
        cutoff = now - timedelta(days=days)
    else:
        cutoff = now - timedelta(days=30)

    sub_query = {"created_at": {"$gte": cutoff.isoformat()}}
    if job_id != "all":
        sub_query["$or"] = [{"matched_job_id": job_id}, {"job_id": job_id}]

    subs = await deps.db.submissions.find(sub_query, {"_id": 0}).to_list(5000)
    sub_ids = [s["id"] for s in subs]

    mgmt_revs = await deps.db.management_reviews.find({"submission_id": {"$in": sub_ids or ["__none__"]}}, {"_id": 0}).to_list(5000)
    mgmt_map = {r["submission_id"]: r for r in mgmt_revs}
    rapid_revs = await deps.db.rapid_reviews.find({"submission_id": {"$in": sub_ids or ["__none__"]}}, {"_id": 0}).to_list(5000)
    rapid_map = {r["submission_id"]: r for r in rapid_revs}
    owner_revs = await deps.db.owner_reviews.find({"submission_id": {"$in": sub_ids or ["__none__"]}}, {"_id": 0}).to_list(5000)
    owner_map = {r["submission_id"]: r for r in owner_revs}

    equip_codes = set(s.get("access_code", "") for s in subs)
    equip_logs = await deps.db.equipment_logs.find(
        {"access_code": {"$in": list(equip_codes) or ["__none__"]}, "created_at": {"$gte": cutoff.isoformat()}}, {"_id": 0}
    ).to_list(500)
    equip_by_crew = {}
    for eq in equip_logs:
        equip_by_crew.setdefault(eq.get("access_code", ""), []).append(eq)

    properties = {}
    for s in subs:
        prop = s.get("job_name_input") or "Unassigned"
        properties.setdefault(prop, []).append(s)

    rows = []
    for prop_name, prop_subs in sorted(properties.items(), key=lambda x: len(x[1]), reverse=True):
        submissions_detail = []
        scores = []
        pass_ct = fail_ct = 0
        divs = set()

        for s in sorted(prop_subs, key=lambda x: x.get("created_at", ""), reverse=True):
            divs.add(s.get("division", ""))
            mgmt = mgmt_map.get(s["id"])
            rr = rapid_map.get(s["id"])
            own = owner_map.get(s["id"])
            sc = None
            verdict = None
            if mgmt:
                sc = mgmt.get("total_score") or mgmt.get("overall_score")
                verdict = mgmt.get("verdict") or mgmt.get("disposition")
                if sc:
                    scores.append(sc)
                if verdict and ("pass" in verdict.lower() or "exemplary" in verdict.lower()):
                    pass_ct += 1
                elif verdict and "fail" in verdict.lower():
                    fail_ct += 1

            gps = s.get("gps") or {}
            gps_data = {"lat": gps.get("lat"), "lng": gps.get("lng"), "accuracy": gps.get("accuracy")} if isinstance(gps, dict) else {}

            photo_files = s.get("photo_files", []) or []
            photo_urls = s.get("photo_urls", []) or []
            all_photos = [p.get("media_url") for p in photo_files if p.get("media_url")] + photo_urls

            field_report = s.get("field_report") or {}
            fr_photos = []
            if isinstance(field_report, dict) and field_report.get("reported"):
                fr_pf = field_report.get("photo_files", []) or []
                fr_photos = [p.get("media_url") for p in fr_pf if p.get("media_url")] + (s.get("issue_photo_urls", []) or [])

            detail = {
                "id": s.get("id"), "crew_label": s.get("crew_label", ""),
                "division": s.get("division", ""), "service_type": s.get("service_type") or s.get("task_type", ""),
                "truck_number": s.get("truck_number", ""), "area_tag": s.get("area_tag", ""),
                "note": s.get("note", ""), "work_date": s.get("work_date", ""),
                "created_at": s.get("created_at", ""), "gps": gps_data, "photos": all_photos,
                "field_report": {
                    "reported": field_report.get("reported", False) if isinstance(field_report, dict) else False,
                    "type": field_report.get("type", "") if isinstance(field_report, dict) else "",
                    "notes": field_report.get("notes", "") if isinstance(field_report, dict) else "",
                    "photos": fr_photos,
                },
                "management_review": {"score": sc, "verdict": verdict, "comments": mgmt.get("comments", "") if mgmt else "",
                    "flagged_issues": mgmt.get("flagged_issues", []) if mgmt else [],
                    "category_scores": mgmt.get("category_scores") or (mgmt.get("scores", {}) if mgmt else {}),
                    "reviewer_name": mgmt.get("reviewer_name", "") if mgmt else "",
                } if mgmt else None,
                "rapid_review": {"rating": rr.get("overall_rating", ""), "issue_tag": rr.get("issue_tag", ""),
                    "remark": rr.get("remark") or rr.get("remarks", ""),
                } if rr else None,
                "owner_review": {"score": own.get("total_score") or own.get("overall_score"),
                    "disposition": own.get("final_disposition", ""), "training_inclusion": own.get("training_inclusion", ""),
                } if own else None,
            }
            submissions_detail.append(detail)

        crew_codes = set(s.get("access_code", "") for s in prop_subs)
        prop_equip = []
        for cc in crew_codes:
            prop_equip.extend(equip_by_crew.get(cc, []))

        rows.append({
            "property": prop_name, "submissions_count": len(prop_subs),
            "avg_score": round(sum(scores) / max(len(scores), 1), 2) if scores else 0,
            "pass_count": pass_ct, "fail_count": fail_ct, "divisions": sorted(divs - {""}),
            "submissions": submissions_detail,
            "equipment_logs": [{"equipment_number": e.get("equipment_number", ""), "red_tag": e.get("red_tag", False),
                "notes": e.get("notes", ""), "created_at": e.get("created_at", ""),
                "pre_photo_url": e.get("pre_photo_url", ""), "post_photo_url": e.get("post_photo_url", ""),
            } for e in prop_equip],
        })

    return {
        "properties": rows, "total_properties": len(rows), "total_submissions": len(subs),
        "period": period, "job_filter": job_id, "cutoff_date": cutoff.isoformat(),
    }


# ── PDF export ──

@router.get("/exports/am-report-pdf")
async def export_am_report_pdf(
    user: dict = Depends(require_roles("management", "owner")),
    job_id: str = Query("all"),
    period: str = Query("monthly"),
    days: int = Query(0),
):
    from fpdf import FPDF
    report = await client_quality_report(user=user, job_id=job_id, period=period, days=days)
    now = datetime.now(timezone.utc)
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Cover
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 24)
    pdf.ln(30)
    pdf.cell(0, 14, "Sarver Landscape", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 14)
    pdf.cell(0, 10, "Client Quality Report", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    job_label = f"Job: {job_id}" if job_id != "all" else "All Jobs"
    pdf.cell(0, 8, _safe(f"{report['period'].title()} | {job_label} | {report['total_properties']} Properties | {report['total_submissions']} Submissions"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.cell(0, 7, _safe(f"Generated: {now.strftime('%B %d, %Y %I:%M %p UTC')}"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, _safe(f"Prepared by: {user.get('name', '')} ({user.get('email', '')})"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(12)

    # Summary
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Executive Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    col_w = [62, 22, 25, 18, 18, 45]
    headers_list = ["Property", "Subs", "Avg Score", "Pass", "Fail", "Divisions"]
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(230, 230, 225)
    for idx_h, hdr in enumerate(headers_list):
        pdf.cell(col_w[idx_h], 6, hdr, border=1, fill=True)
    pdf.ln()
    pdf.set_font("Helvetica", "", 7)
    for row in report["properties"]:
        cells = [_safe(row["property"][:30]), str(row["submissions_count"]), str(row["avg_score"]), str(row["pass_count"]), str(row["fail_count"]), _safe(", ".join(row["divisions"])[:22])]
        for ci, cv in enumerate(cells):
            pdf.cell(col_w[ci], 5, cv, border=1)
        pdf.ln()

    # Detail pages
    for row in report["properties"]:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_fill_color(36, 62, 54)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 10, _safe(f"  {row['property']}"), fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, _safe(f"{row['submissions_count']} submissions | Avg: {row['avg_score']} | P: {row['pass_count']} F: {row['fail_count']}"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

        for si, sub in enumerate(row["submissions"]):
            if pdf.get_y() > 240:
                pdf.add_page()
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_fill_color(240, 241, 234)
            pdf.cell(0, 7, _safe(f"  #{si + 1}  |  {sub['id']}"), fill=True, new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 8)
            pdf.cell(95, 5, _safe(f"Crew: {sub['crew_label']}  |  Div: {sub['division']}  |  Svc: {sub['service_type']}"), new_x="RIGHT")
            pdf.cell(95, 5, _safe(f"Truck: {sub['truck_number']}  |  Area: {sub['area_tag']}"), new_x="LMARGIN", new_y="NEXT")
            gps = sub.get("gps") or {}
            gps_str = f"GPS: {gps.get('lat')}, {gps.get('lng')}" if gps.get("lat") else "GPS: N/A"
            if gps.get("accuracy"):
                gps_str += f" (+/-{gps['accuracy']}m)"
            pdf.cell(95, 5, _safe(f"Date: {sub['work_date']}  |  Captured: {_short_date(sub['created_at'])}"), new_x="RIGHT")
            pdf.cell(95, 5, _safe(gps_str), new_x="LMARGIN", new_y="NEXT")
            if sub.get("note"):
                pdf.set_font("Helvetica", "I", 8)
                pdf.multi_cell(0, 4, _safe(f"Notes: {sub['note']}"), new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "", 8)

            fr = sub.get("field_report") or {}
            if fr.get("reported"):
                pdf.set_font("Helvetica", "B", 8)
                pdf.set_text_color(200, 0, 0)
                pdf.cell(0, 5, _safe(f"INCIDENT: {fr.get('type', 'Incident')}"), new_x="LMARGIN", new_y="NEXT")
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Helvetica", "", 8)
                if fr.get("notes"):
                    pdf.multi_cell(0, 4, _safe(f"  {fr['notes']}"), new_x="LMARGIN", new_y="NEXT")
                for pu in (fr.get("photos") or []):
                    pdf.set_text_color(0, 0, 180)
                    pdf.cell(0, 4, _safe(f"  Issue Photo: {pu[:90]}"), link=str(pu), new_x="LMARGIN", new_y="NEXT")
                    pdf.set_text_color(0, 0, 0)

            photos = sub.get("photos", [])
            if photos:
                pdf.set_font("Helvetica", "B", 7)
                pdf.cell(0, 4, _safe(f"  Photos ({len(photos)}):"), new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "", 7)
                pdf.set_text_color(0, 0, 180)
                for pi, pu in enumerate(photos):
                    pdf.cell(0, 4, _safe(f"  Photo {pi + 1}: {pu[:90]}"), link=str(pu), new_x="LMARGIN", new_y="NEXT")
                pdf.set_text_color(0, 0, 0)

            mr = sub.get("management_review")
            if mr:
                pdf.set_font("Helvetica", "B", 8)
                pdf.cell(0, 5, _safe(f"Mgmt Review: Score {mr.get('score', '-')} | {mr.get('verdict', '-')} | {mr.get('reviewer_name', '')}"), new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "", 7)
                cat = mr.get("category_scores") or {}
                if cat:
                    pdf.cell(0, 4, _safe(f"  {', '.join(f'{k}: {v}' for k, v in cat.items())}"), new_x="LMARGIN", new_y="NEXT")
                if mr.get("comments"):
                    pdf.set_font("Helvetica", "I", 7)
                    pdf.multi_cell(0, 4, _safe(f"  {mr['comments']}"), new_x="LMARGIN", new_y="NEXT")
                if mr.get("flagged_issues"):
                    pdf.set_text_color(200, 0, 0)
                    pdf.set_font("Helvetica", "", 7)
                    pdf.cell(0, 4, _safe(f"  Flagged: {', '.join(mr['flagged_issues'])}"), new_x="LMARGIN", new_y="NEXT")
                    pdf.set_text_color(0, 0, 0)
            rr = sub.get("rapid_review")
            if rr:
                pdf.set_font("Helvetica", "", 7)
                pdf.cell(0, 4, _safe(f"  Rapid: {rr.get('rating', '-')} | {rr.get('issue_tag', '')} | {rr.get('remark', '')[:60]}"), new_x="LMARGIN", new_y="NEXT")
            own = sub.get("owner_review")
            if own:
                pdf.set_font("Helvetica", "", 7)
                pdf.cell(0, 4, _safe(f"  Owner: Score {own.get('score', '-')} | {own.get('disposition', '-')} | Training: {own.get('training_inclusion', '-')}"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
            pdf.set_draw_color(200, 200, 200)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(2)

        equip = row.get("equipment_logs", [])
        if equip:
            if pdf.get_y() > 240:
                pdf.add_page()
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(0, 6, _safe(f"Equipment ({len(equip)})"), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 7)
            for eq_item in equip[:10]:
                red = "RED TAG" if eq_item.get("red_tag") else ""
                pdf.cell(0, 4, _safe(f"  {eq_item.get('equipment_number', '')} | {_short_date(eq_item.get('created_at'))} | {red} {eq_item.get('notes', '')[:60]}"), new_x="LMARGIN", new_y="NEXT")

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.ln(20)
    pdf.cell(0, 8, "End of Report", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, "Confidential - Sarver Landscape Management Co.", align="C")

    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)
    filename = f"SarverLandscape_ClientReport_{now.strftime('%Y%m%d')}.pdf"
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/exports/system-reference-pdf")
async def system_reference_pdf(token: str = Query(None)):
    """Generate a system reference PDF with architecture, storage, schema, and implementation details."""
    from fpdf import FPDF

    if token:
        try:
            deps.decode_jwt(token)
        except Exception:
            pass

    now = datetime.now(timezone.utc)

    pdf = FPDF(orientation="P", unit="mm", format="Letter")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Header
    pdf.set_fill_color(36, 62, 54)
    pdf.rect(0, 0, 220, 35, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_y(8)
    pdf.cell(0, 10, "Sarver Landscape QA System", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, f"System Reference Document  |  Generated {now.strftime('%B %d, %Y')}", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(0, 0, 0)
    pdf.set_y(42)

    def section_header(title):
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_fill_color(237, 240, 231)
        pdf.cell(0, 9, f"  {_safe(title)}", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    def body_text(text, bold=False):
        pdf.set_font("Helvetica", "B" if bold else "", 9)
        pdf.multi_cell(0, 5, _safe(text))
        pdf.ln(1)

    def bullet(text):
        pdf.set_font("Helvetica", "", 9)
        x = pdf.get_x()
        pdf.cell(5, 5, chr(149))
        pdf.multi_cell(175, 5, _safe(text))
        pdf.set_x(x)

    # Tech Stack
    section_header("Technology Stack")
    for label, value in [
        ("Frontend", "React 18 + TailwindCSS + Shadcn/UI + Framer Motion"),
        ("Backend", "Python FastAPI (modular routers in /routes/)"),
        ("Database", "MongoDB (Motor async driver)"),
        ("Storage", "Supabase Object Storage (Service Role architecture)"),
        ("Auth", "JWT with role-based routing (bcrypt hashing)"),
        ("PDF", "fpdf2 for client-facing report generation"),
    ]:
        body_text(f"{label}: {value}", bold=True)

    # Storage Architecture
    section_header("Supabase Storage Architecture")
    body_text("All photo uploads are handled exclusively by the backend using the Supabase service role key.")
    body_text("Storage path: {bucket}/sarver-landscape/submissions/{SubmissionID}/{captures|issues}/{file}")
    body_text("Frontend never touches storage directly. Images are served via backend proxy routes.")

    # Database Schema
    section_header("Database Collections")
    collections = [
        ("users", "Staff accounts with role, title, division, hashed password"),
        ("crew_access_links", "QR crew portals with code, label, division, truck, leader"),
        ("crew_members", "Individual crew member registrations linked to parent crew"),
        ("jobs", "Job records with property, address, service type, division, route"),
        ("submissions", "Photo proof sets with GPS, photos, field reports, status"),
        ("management_reviews", "Detailed rubric-scored reviews by category"),
        ("rapid_reviews", "Swipe-based reviews (one per submission, unique index)"),
        ("rubric_definitions", "33 active rubrics across 7 divisions with hard fail conditions"),
        ("standards_library", "25 industry standards organized by category"),
        ("training_sessions", "Crew training with quiz scores"),
        ("equipment_logs", "Maintenance logs with red-tag notification system"),
        ("notifications", "Role-targeted notification queue"),
        ("incidents", "Emergency/accident reports with acknowledgment flow"),
        ("crew_assignments", "Daily job-to-crew mapping (PM drag-drop board)"),
    ]
    for name, desc in collections:
        bullet(f"{name}: {desc}")

    pdf.add_page()

    # Roles & Permissions
    section_header("Roles & Permissions")
    roles = [
        ("Owner", "Full system access. Calibration heatmap, reviewer performance, exports, rubric editing."),
        ("GM (General Manager)", "Dashboard overview, rapid review, incident acknowledgment."),
        ("Production Manager", "Crew assignments, rapid review, submission review. Division-scoped."),
        ("Account Manager", "Job creation, client reports, management reviews."),
        ("Supervisor", "Rapid review, repeat offender tracking, standards oversight."),
        ("Crew Leader", "QR portal: submit photos, log equipment, file incidents, view history."),
        ("Crew Member", "Member portal: submit photos for assigned jobs."),
    ]
    for role, desc in roles:
        body_text(f"{role}", bold=True)
        body_text(f"  {desc}")

    # Workflow Summary
    section_header("Core Workflows")
    workflows = [
        "1. Account Manager creates job -> PM assigns crew via daily assignment board",
        "2. Crew leader opens QR portal, captures 3+ photos per task, submits proof set",
        "3. Submission enters Review Queue -> Rapid Review (mobile swipe) or Management Review (rubric scoring)",
        "4. Scored submissions feed analytics: calibration heatmap, crew performance, repeat offender tracking",
        "5. Repeat offenders trigger auto-coaching sessions pre-loaded with division standards",
        "6. Emergency incidents bypass photo requirements, trigger red-flash dashboard alerts",
        "7. Client quality reports aggregate scores and photos into professional PDF exports",
    ]
    for w in workflows:
        bullet(w)

    # Rubric System
    section_header("Rubric Grading System")
    body_text("33 rubric definitions across 7 divisions (Maintenance, Install, Tree, Enhancement, Irrigation, Snow/Ice, PHC).")
    body_text("Each rubric has weighted categories (e.g., Continuity 25%, Depth Consistency 20%) scored 0-5.")
    body_text("Hard fail conditions: 'no_image_captured' and 'improper_image_quality' on all rubrics.")
    body_text("Rapid Review multipliers: Fail=0%, Concern=35%, Standard=72%, Exemplary=100%.")

    # API Reference
    section_header("Key API Endpoints")
    endpoints = [
        ("POST /api/auth/login", "JWT authentication"),
        ("GET /api/rapid-reviews/queue", "Paginated unreviewed submission queue"),
        ("POST /api/rapid-reviews", "Submit rapid review with rubric scoring"),
        ("GET /api/crew-assignments/week", "Weekly crew assignment board"),
        ("POST /api/crew-assignments/bulk", "Bulk job-to-crew assignment"),
        ("GET /api/coaching/score-analysis", "Score-based coaching recommendations"),
        ("GET /api/incidents/active", "Active emergency incidents"),
        ("GET /api/reports/client-quality", "Client quality report data"),
        ("GET /api/exports/am-report-pdf", "Client report PDF export"),
    ]
    for path, desc in endpoints:
        bullet(f"{path} - {desc}")

    # Footer
    pdf.ln(10)
    pdf.set_draw_color(36, 62, 54)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, "Confidential - Sarver Landscape Management Co. - Character, Quality, and Respect.", align="C")

    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)
    filename = f"SarverQA_SystemReference_{now.strftime('%Y%m%d')}.pdf"
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
