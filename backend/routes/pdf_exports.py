"""PDF export for Account Manager Client Report."""
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse

import shared.deps as deps
from shared.deps import require_roles

router = APIRouter()


@router.get("/exports/am-report-pdf")
async def export_am_report_pdf(
    user: dict = Depends(require_roles("management", "owner")),
):
    """Generate a PDF of the Account Manager Client Quality Report (90 days)."""
    from fpdf import FPDF
    from datetime import timedelta

    def safe(text):
        return text.encode("ascii", "replace").decode("ascii") if text else ""

    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=90)).isoformat()

    subs = await deps.db.submissions.find(
        {"created_at": {"$gte": cutoff}},
        {"_id": 0, "id": 1, "job_name_input": 1, "division": 1}
    ).to_list(2000)
    sub_ids = [s["id"] for s in subs]
    reviews = await deps.db.management_reviews.find(
        {"submission_id": {"$in": sub_ids or ["__none__"]}},
        {"_id": 0, "submission_id": 1, "overall_score": 1, "total_score": 1, "verdict": 1}
    ).to_list(2000)
    rev_lookup = {r["submission_id"]: r for r in reviews}

    props = {}
    for s in subs:
        prop = s.get("job_name_input") or "Unassigned"
        entry = props.setdefault(prop, {"property": prop, "subs": 0, "scores": [], "pass": 0, "fail": 0, "divs": set()})
        entry["subs"] += 1
        entry["divs"].add(s.get("division", ""))
        rev = rev_lookup.get(s["id"])
        if rev:
            sc = rev.get("total_score") or rev.get("overall_score")
            if sc:
                entry["scores"].append(sc)
            if rev.get("verdict") in ("Pass", "Exemplary"):
                entry["pass"] += 1
            elif rev.get("verdict") == "Fail":
                entry["fail"] += 1

    rows = sorted(props.values(), key=lambda x: x["subs"], reverse=True)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Header
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "Sarver Landscape", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, "Client Quality Report (90-Day Window)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, safe(f"Generated: {now.strftime('%B %d, %Y %I:%M %p UTC')}  |  By: {user.get('name', user.get('email', ''))}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # Summary
    total_subs = sum(r["subs"] for r in rows)
    all_scores = [sc for r in rows for sc in r["scores"]]
    avg_all = round(sum(all_scores) / max(len(all_scores), 1), 2) if all_scores else 0
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, safe(f"Total Properties: {len(rows)}  |  Total Submissions: {total_subs}  |  Overall Avg Score: {avg_all}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Table header
    col_widths = [65, 22, 25, 18, 18, 42]
    headers = ["Property", "Subs", "Avg Score", "Pass", "Fail", "Divisions"]
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(230, 230, 225)
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 7, h, border=1, fill=True)
    pdf.ln()

    # Table rows
    pdf.set_font("Helvetica", "", 8)
    for row in rows:
        avg = round(sum(row["scores"]) / max(len(row["scores"]), 1), 2) if row["scores"] else 0
        divs = ", ".join(sorted(row["divs"] - {""}))
        prop_name = row["property"][:30] + "..." if len(row["property"]) > 30 else row["property"]
        cells = [safe(prop_name), str(row["subs"]), str(avg), str(row["pass"]), str(row["fail"]), safe(divs[:22])]
        for i, c in enumerate(cells):
            pdf.cell(col_widths[i], 6, c, border=1)
        pdf.ln()

    # Footer
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 8)
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
