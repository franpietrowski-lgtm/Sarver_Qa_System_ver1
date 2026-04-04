"""PDF export for Account Manager Client Report — Full detail with clickable image links."""
import io
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from starlette.responses import StreamingResponse

import shared.deps as deps
from shared.deps import require_roles

router = APIRouter()


def _safe(text):
    """Strip non-ASCII for Helvetica compatibility."""
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


@router.get("/exports/am-report-pdf")
async def export_am_report_pdf(
    user: dict = Depends(require_roles("management", "owner")),
    days: int = Query(90, ge=7, le=365),
):
    """Generate a full-detail PDF grouped by property with clickable image links."""
    from fpdf import FPDF

    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=days)).isoformat()

    # ── Gather all data ──
    subs = await deps.db.submissions.find(
        {"created_at": {"$gte": cutoff}},
        {"_id": 0}
    ).to_list(5000)
    sub_ids = [s["id"] for s in subs]

    mgmt_reviews = await deps.db.management_reviews.find(
        {"submission_id": {"$in": sub_ids or ["__none__"]}}, {"_id": 0}
    ).to_list(5000)
    mgmt_map = {r["submission_id"]: r for r in mgmt_reviews}

    rapid_reviews = await deps.db.rapid_reviews.find(
        {"submission_id": {"$in": sub_ids or ["__none__"]}}, {"_id": 0}
    ).to_list(5000)
    rapid_map = {r["submission_id"]: r for r in rapid_reviews}

    owner_reviews = await deps.db.owner_reviews.find(
        {"submission_id": {"$in": sub_ids or ["__none__"]}}, {"_id": 0}
    ).to_list(5000)
    owner_map = {r["submission_id"]: r for r in owner_reviews}

    equipment_logs = await deps.db.equipment_logs.find(
        {"created_at": {"$gte": cutoff}}, {"_id": 0}
    ).to_list(1000)
    equip_by_crew = {}
    for e in equipment_logs:
        equip_by_crew.setdefault(e.get("access_code", ""), []).append(e)

    # ── Group by property ──
    properties = {}
    for s in subs:
        prop = s.get("job_name_input") or "Unassigned"
        properties.setdefault(prop, []).append(s)

    for prop_subs in properties.values():
        prop_subs.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    # ── Build PDF ──
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # ── Cover page ──
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 24)
    pdf.ln(30)
    pdf.cell(0, 14, "Sarver Landscape", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 14)
    pdf.cell(0, 10, "Client Quality Report", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 8, _safe(f"{days}-Day Window  |  {len(properties)} Properties  |  {len(subs)} Submissions"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.cell(0, 7, _safe(f"Generated: {now.strftime('%B %d, %Y %I:%M %p UTC')}"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, _safe(f"Prepared by: {user.get('name', '')} ({user.get('email', '')})"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(12)

    # ── Summary table ──
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Executive Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    col_w = [62, 22, 25, 18, 18, 45]
    headers = ["Property", "Subs", "Avg Score", "Pass", "Fail", "Divisions"]
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(230, 230, 225)
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 6, h, border=1, fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 7)
    for prop_name, prop_subs in sorted(properties.items(), key=lambda x: len(x[1]), reverse=True):
        scores = []
        pass_ct = fail_ct = 0
        divs = set()
        for s in prop_subs:
            divs.add(s.get("division", ""))
            rev = mgmt_map.get(s["id"])
            if rev:
                sc = rev.get("total_score") or rev.get("overall_score")
                if sc:
                    scores.append(sc)
                v = rev.get("verdict") or rev.get("disposition", "")
                if "pass" in v.lower() or "exemplary" in v.lower():
                    pass_ct += 1
                elif "fail" in v.lower():
                    fail_ct += 1
        avg = round(sum(scores) / max(len(scores), 1), 2) if scores else 0
        cells = [_safe(prop_name[:30]), str(len(prop_subs)), str(avg), str(pass_ct), str(fail_ct), _safe(", ".join(sorted(divs - {""}))[:22])]
        for i, c in enumerate(cells):
            pdf.cell(col_w[i], 5, c, border=1)
        pdf.ln()

    # ── Per-property detail pages ──
    for prop_name, prop_subs in sorted(properties.items(), key=lambda x: len(x[1]), reverse=True):
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_fill_color(36, 62, 54)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 10, _safe(f"  {prop_name}"), fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, _safe(f"{len(prop_subs)} submissions in this period"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

        for idx, sub in enumerate(prop_subs):
            if pdf.get_y() > 240:
                pdf.add_page()

            # ── Submission header ──
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_fill_color(240, 241, 234)
            pdf.cell(0, 7, _safe(f"  Submission #{idx + 1}  |  {sub.get('id', '')}"), fill=True, new_x="LMARGIN", new_y="NEXT")

            pdf.set_font("Helvetica", "", 8)
            crew = sub.get("crew_label", sub.get("access_code", ""))
            division = sub.get("division", "")
            service = sub.get("service_type") or sub.get("task_type", "")
            area = sub.get("area_tag", "")
            work_date = sub.get("work_date", "")
            created = _short_date(sub.get("created_at"))
            truck = sub.get("truck_number", "")

            # Row 1: Crew, Division, Service, Truck
            pdf.cell(95, 5, _safe(f"Crew: {crew}  |  Division: {division}  |  Service: {service}"), new_x="RIGHT")
            pdf.cell(95, 5, _safe(f"Truck: {truck}  |  Area: {area}"), new_x="LMARGIN", new_y="NEXT")

            # Row 2: Date, Time, GPS
            gps_lat = sub.get("gps_lat") or sub.get("gps", {}).get("lat") if isinstance(sub.get("gps"), dict) else sub.get("gps_lat")
            gps_lng = sub.get("gps_lng") or sub.get("gps", {}).get("lng") if isinstance(sub.get("gps"), dict) else sub.get("gps_lng")
            gps_acc = sub.get("gps_accuracy") or (sub.get("gps", {}).get("accuracy") if isinstance(sub.get("gps"), dict) else None)
            gps_str = f"GPS: {gps_lat}, {gps_lng}" if gps_lat and gps_lng else "GPS: N/A"
            if gps_acc:
                gps_str += f" (+/-{gps_acc}m)"
            pdf.cell(95, 5, _safe(f"Date: {work_date}  |  Captured: {created}"), new_x="RIGHT")
            pdf.cell(95, 5, _safe(gps_str), new_x="LMARGIN", new_y="NEXT")

            # Row 3: Notes
            note = sub.get("note", "")
            if note:
                pdf.set_font("Helvetica", "I", 8)
                pdf.multi_cell(0, 4, _safe(f"Notes: {note}"), new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "", 8)

            # ── Field Report (damage/incident) ──
            field_report = sub.get("field_report") or {}
            if isinstance(field_report, dict) and field_report.get("reported"):
                pdf.set_font("Helvetica", "B", 8)
                pdf.set_text_color(200, 0, 0)
                pdf.cell(0, 5, _safe(f"FIELD REPORT: {field_report.get('type', 'Incident')}"), new_x="LMARGIN", new_y="NEXT")
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Helvetica", "", 8)
                fr_notes = field_report.get("notes", "")
                if fr_notes:
                    pdf.multi_cell(0, 4, _safe(f"  {fr_notes}"), new_x="LMARGIN", new_y="NEXT")
                # Issue photo links
                fr_photos = field_report.get("photo_files", []) or []
                issue_urls = sub.get("issue_photo_urls", []) or []
                all_issue_photos = [p.get("media_url") for p in fr_photos if p.get("media_url")] + issue_urls
                if all_issue_photos:
                    pdf.set_font("Helvetica", "", 7)
                    pdf.set_text_color(0, 0, 180)
                    for pu in all_issue_photos:
                        pdf.cell(0, 4, _safe(f"  Issue Photo: {pu[:90]}"), link=str(pu), new_x="LMARGIN", new_y="NEXT")
                    pdf.set_text_color(0, 0, 0)

            # ── Submission Photo Links ──
            photo_files = sub.get("photo_files", []) or []
            photo_urls = sub.get("photo_urls", []) or []
            all_photos = [p.get("media_url") for p in photo_files if p.get("media_url")] + photo_urls
            if all_photos:
                pdf.set_font("Helvetica", "B", 7)
                pdf.cell(0, 4, _safe(f"  Photos ({len(all_photos)}):"), new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "", 7)
                pdf.set_text_color(0, 0, 180)
                for pi, pu in enumerate(all_photos):
                    label = f"  Photo {pi + 1}: {pu[:90]}"
                    pdf.cell(0, 4, _safe(label), link=str(pu), new_x="LMARGIN", new_y="NEXT")
                pdf.set_text_color(0, 0, 0)

            # ── Review Scores ──
            mgmt = mgmt_map.get(sub["id"])
            if mgmt:
                pdf.set_font("Helvetica", "B", 8)
                score = mgmt.get("total_score") or mgmt.get("overall_score") or "-"
                verdict = mgmt.get("verdict") or mgmt.get("disposition", "-")
                reviewer = mgmt.get("reviewer_name", "")
                pdf.cell(0, 5, _safe(f"Management Review: Score {score}  |  Verdict: {verdict}  |  Reviewer: {reviewer}"), new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "", 7)
                # Category scores
                cat_scores = mgmt.get("category_scores") or mgmt.get("scores") or {}
                if cat_scores:
                    parts = [f"{k}: {v}" for k, v in cat_scores.items()]
                    pdf.cell(0, 4, _safe(f"  Scores: {', '.join(parts)}"), new_x="LMARGIN", new_y="NEXT")
                remark = mgmt.get("comments") or mgmt.get("remark", "")
                if remark:
                    pdf.set_font("Helvetica", "I", 7)
                    pdf.multi_cell(0, 4, _safe(f"  Comment: {remark}"), new_x="LMARGIN", new_y="NEXT")
                flagged = mgmt.get("flagged_issues", [])
                if flagged:
                    pdf.set_font("Helvetica", "", 7)
                    pdf.set_text_color(200, 0, 0)
                    pdf.cell(0, 4, _safe(f"  Flagged Issues: {', '.join(flagged)}"), new_x="LMARGIN", new_y="NEXT")
                    pdf.set_text_color(0, 0, 0)

            # Rapid review
            rr = rapid_map.get(sub["id"])
            if rr:
                pdf.set_font("Helvetica", "", 7)
                rr_verdict = rr.get("verdict") or rr.get("overall_rating", "-")
                rr_tag = rr.get("issue_tag", "")
                rr_remark = rr.get("remarks") or rr.get("remark", "")
                pdf.cell(0, 4, _safe(f"  Rapid Review: {rr_verdict}  |  Tag: {rr_tag}  |  {rr_remark[:60]}"), new_x="LMARGIN", new_y="NEXT")

            # Owner review
            own = owner_map.get(sub["id"])
            if own:
                pdf.set_font("Helvetica", "", 7)
                own_score = own.get("total_score") or own.get("overall_score", "-")
                own_disp = own.get("final_disposition", "-")
                own_incl = own.get("training_inclusion", "-")
                pdf.cell(0, 4, _safe(f"  Owner Review: Score {own_score}  |  Disposition: {own_disp}  |  Training: {own_incl}"), new_x="LMARGIN", new_y="NEXT")

            pdf.ln(3)
            # Separator line
            pdf.set_draw_color(200, 200, 200)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(3)

        # ── Equipment logs for crews on this property ──
        crew_codes = set(s.get("access_code", "") for s in prop_subs)
        prop_equip = []
        for cc in crew_codes:
            prop_equip.extend(equip_by_crew.get(cc, []))
        if prop_equip:
            if pdf.get_y() > 240:
                pdf.add_page()
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(0, 6, _safe(f"Equipment Reports ({len(prop_equip)} logs)"), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 7)
            for eq in prop_equip[:10]:
                eq_num = eq.get("equipment_number", "")
                red = "RED TAG" if eq.get("red_tag") else ""
                eq_notes = eq.get("notes", "")
                eq_date = _short_date(eq.get("created_at"))
                pdf.cell(0, 4, _safe(f"  {eq_num} | {eq_date} | {red} {eq_notes[:60]}"), new_x="LMARGIN", new_y="NEXT")
                # Equipment photo links
                for photo_key in ["pre_photo", "post_photo", "pre_photo_url", "post_photo_url"]:
                    url = eq.get(photo_key, "")
                    if url and isinstance(url, str) and url.startswith("http"):
                        pdf.set_text_color(0, 0, 180)
                        pdf.cell(0, 4, _safe(f"    {photo_key}: {url[:85]}"), link=str(url), new_x="LMARGIN", new_y="NEXT")
                        pdf.set_text_color(0, 0, 0)

    # ── Final footer ──
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.ln(20)
    pdf.cell(0, 8, "End of Report", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 6, _safe(f"{len(properties)} properties  |  {len(subs)} submissions  |  {len(mgmt_reviews)} reviews"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.cell(0, 5, "Confidential - Sarver Landscape Management Co.", align="C")

    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)

    filename = f"SarverLandscape_ClientReport_{now.strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
