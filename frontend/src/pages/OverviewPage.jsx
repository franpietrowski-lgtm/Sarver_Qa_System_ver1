import { Activity, Boxes, Copy, Grid3X3, ShieldCheck, Smartphone, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { QRCodeSVG } from "qrcode.react";

import StatCard from "@/components/common/StatCard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { authGet } from "@/lib/api";
import { toast } from "sonner";


const DIVISIONS = ["Maintenance", "Install", "Tree", "Plant Healthcare", "Winter Services"];


export default function OverviewPage({ user }) {
  const [overview, setOverview] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [submissionPage, setSubmissionPage] = useState(1);
  const [submissionTotal, setSubmissionTotal] = useState(0);
  const [rubricMatrices, setRubricMatrices] = useState([]);
  const [matrixDivisionFilter, setMatrixDivisionFilter] = useState("all");
  const [matrixOpen, setMatrixOpen] = useState(false);
  const matrixTimerRef = useRef(null);
  const rapidReviewUrl = useMemo(() => (typeof window !== "undefined" ? `${window.location.origin}/rapid-review/mobile` : ""), []);

  useEffect(() => {
    if (matrixOpen) {
      if (matrixTimerRef.current) clearTimeout(matrixTimerRef.current);
      matrixTimerRef.current = setTimeout(() => setMatrixOpen(false), 120000);
    }
    return () => { if (matrixTimerRef.current) clearTimeout(matrixTimerRef.current); };
  }, [matrixOpen, matrixDivisionFilter]);

  const loadSubmissions = async (page = 1) => {
    const response = await authGet(`/submissions?scope=all&page=${page}&limit=4`);
    setSubmissions(response.items || []);
    setSubmissionTotal(response.total || 0);
    setSubmissionPage(page);
  };

  useEffect(() => {
    const load = async () => {
      const [overviewResponse, matricesResponse] = await Promise.all([
        authGet("/dashboard/overview"),
        authGet("/rubric-matrices?division=all"),
      ]);
      setOverview(overviewResponse);
      setRubricMatrices(matricesResponse || []);
      await loadSubmissions(1);
    };
    load();
  }, []);

  if (!overview) {
    return <div className="rounded-[28px] border border-border bg-white p-10 text-center text-[#243e36]" data-testid="overview-loading-state">Loading overview...</div>;
  }

  const storage = overview.storage || overview.drive;
  const selectedCrew = crewLinks.find((item) => item.id === selectedCrewId);
  const copyRapidReviewLink = async () => {
    await navigator.clipboard.writeText(rapidReviewUrl);
    toast.success("Rapid review link copied.");
  };

  const stats = [
    { icon: Activity, label: "Submissions", value: overview.totals.submissions, hint: "All captured proof records", testId: "overview-stat-submissions" },
    { icon: FolderInput, label: "Imported jobs", value: overview.totals.jobs, hint: "Alignment records available for admin review", testId: "overview-stat-jobs" },
    { icon: ShieldCheck, label: "Owner queue", value: overview.queues.owner, hint: "Items needing final calibration", testId: "overview-stat-owner-queue" },
    { icon: UploadCloud, label: "Export ready", value: overview.queues.export_ready, hint: "Records ready for dataset packaging", testId: "overview-stat-export-ready" },
  ];

  return (
    <div className="space-y-4" data-testid="overview-page">
      <Card className="overflow-hidden rounded-[24px] border-border/80 bg-white/95 shadow-sm" data-testid="overview-hero-card">
        <CardContent className="grid gap-4 p-5 lg:grid-cols-[1.3fr_0.7fr] lg:p-6">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]" data-testid="overview-kicker-text">Operations pulse</p>
            <h2 className="mt-2 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815] lg:text-4xl" data-testid="overview-title">Crews fast. Labels consistent. Data clean.</h2>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[#5c6d64]" data-testid="overview-description">Capture volume, review queues, storage status, and export momentum at a glance.</p>
          </div>
          <div className="grid gap-3 rounded-[20px] border border-border bg-[#edf0e7] p-4" data-testid="overview-workflow-health-card">
            <div>
              <p className="text-sm font-semibold text-[#243e36]">Review velocity</p>
              <p className="mt-1 font-[Cabinet_Grotesk] text-4xl font-black text-[#111815]" data-testid="overview-review-velocity-value">{overview.workflow_health.review_velocity_percent}%</p>
              <p className="mt-1 text-xs text-[#5c6d64]" data-testid="overview-review-velocity-hint">Captured work moving through review and export.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge className="border-0 bg-white px-2 py-0.5 text-xs text-[#243e36]" data-testid="overview-drive-config-badge">Storage: {storage?.configured ? "OK" : "N/A"}</Badge>
              <Badge className="border-0 bg-white px-2 py-0.5 text-xs text-[#243e36]" data-testid="overview-drive-connected-badge">Ready: {storage?.connected ? "Yes" : "No"}</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {stats.map((item) => <StatCard key={item.label} {...item} />)}
      </div>

      <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="overview-rubric-matrix-card">
        <CardContent className="p-5 sm:p-6">
          <button
            type="button"
            onClick={() => setMatrixOpen(!matrixOpen)}
            className="flex w-full items-center justify-between gap-3 text-left"
            data-testid="overview-rubric-toggle"
          >
            <div className="flex items-center gap-3">
              <Grid3X3 className="h-5 w-5 text-[#243e36]" />
              <div>
                <h3 className="font-semibold text-[#111815]">Quick matrix ref</h3>
                <p className="text-xs text-[#5c6d64]">{rubricMatrices.length} active rubrics across divisions</p>
              </div>
            </div>
            <Badge className="border-0 bg-[#edf0e7] text-[#243e36]">{matrixOpen ? "Close" : "View"}</Badge>
          </button>
        </CardContent>
      </Card>

      {matrixOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4" data-testid="overview-rubric-widget-overlay" onClick={() => setMatrixOpen(false)}>
          <div className="max-h-[80vh] w-full max-w-3xl overflow-hidden rounded-[28px] border border-border/80 bg-white shadow-2xl" onClick={(e) => e.stopPropagation()} data-testid="overview-rubric-widget">
            <div className="flex items-center justify-between gap-4 border-b border-border/60 px-6 py-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Quick matrix ref</p>
                <h3 className="mt-1 font-[Outfit] text-xl font-bold text-[#111815]">Rubric grading factors</h3>
              </div>
              <div className="flex items-center gap-2">
                <Select value={matrixDivisionFilter} onValueChange={setMatrixDivisionFilter}>
                  <SelectTrigger className="h-9 w-[160px] rounded-xl border-transparent bg-[#edf0e7] text-sm" data-testid="overview-matrix-division-filter"><SelectValue placeholder="All divisions" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All divisions</SelectItem>
                    {DIVISIONS.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}
                  </SelectContent>
                </Select>
                <Button type="button" variant="ghost" onClick={() => setMatrixOpen(false)} className="h-8 w-8 rounded-full p-0" data-testid="overview-rubric-widget-close"><X className="h-4 w-4" /></Button>
              </div>
            </div>
            <div className="max-h-[60vh] overflow-y-auto px-6 py-4">
              <table className="w-full text-left text-sm" data-testid="overview-rubric-matrix-table">
                <thead>
                  <tr className="border-b border-border/60">
                    <th className="pb-2 pr-4 text-xs font-bold uppercase tracking-wider text-[#5f7464]">Task</th>
                    <th className="pb-2 pr-4 text-xs font-bold uppercase tracking-wider text-[#5f7464]">Division</th>
                    <th className="pb-2 pr-4 text-xs font-bold uppercase tracking-wider text-[#5f7464]">Factors</th>
                    <th className="pb-2 pr-4 text-xs font-bold uppercase tracking-wider text-[#5f7464]">Pass</th>
                    <th className="pb-2 text-xs font-bold uppercase tracking-wider text-[#5f7464]">Ver</th>
                  </tr>
                </thead>
                <tbody>
                  {rubricMatrices
                    .filter((item) => matrixDivisionFilter === "all" || item.division === matrixDivisionFilter)
                    .map((rubric) => (
                      <tr key={rubric.id} className="border-b border-border/30" data-testid={`overview-rubric-row-${rubric.id}`}>
                        <td className="py-2.5 pr-4 font-semibold capitalize text-[#243e36]">{rubric.service_type}</td>
                        <td className="py-2.5 pr-4"><Badge className="border-0 bg-[#edf0e7] text-xs text-[#243e36]">{rubric.division || "General"}</Badge></td>
                        <td className="py-2.5 pr-4">
                          <div className="flex flex-wrap gap-1">
                            {(rubric.categories || []).map((cat) => (
                              <span key={cat.key} className="inline-block rounded bg-[#edf0e7] px-1.5 py-0.5 text-[11px] font-medium text-[#5c6d64]">{cat.label} ({Math.round(cat.weight * 100)}%)</span>
                            ))}
                          </div>
                        </td>
                        <td className="py-2.5 pr-4 font-semibold text-[#243e36]">{rubric.pass_threshold}%</td>
                        <td className="py-2.5 text-[#5c6d64]">v{rubric.version}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
              {rubricMatrices.filter((item) => matrixDivisionFilter === "all" || item.division === matrixDivisionFilter).length === 0 && (
                <p className="mt-4 text-center text-sm text-[#5c6d64]" data-testid="overview-rubric-empty">No rubric matrices found.</p>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <Card className="rounded-[24px] border-border/80 bg-white/95 shadow-sm" data-testid="overview-recent-submissions-card">
          <CardContent className="p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Recent submissions</p>
                <h3 className="mt-1 font-[Outfit] text-lg font-bold text-[#111815]">Current field activity</h3>
              </div>
              <Boxes className="h-5 w-5 text-[#243e36]" />
            </div>
            <div className="mt-4 space-y-2">
              {submissions.map((submission) => (
                <div key={submission.id} className="rounded-[16px] border border-border bg-[#f6f6f2] px-4 py-3" data-testid={`overview-submission-card-${submission.id}`}>
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-[#243e36]" data-testid={`overview-submission-job-${submission.id}`}>{submission.job_name_input || submission.job_id || submission.submission_code}</p>
                      <p className="mt-0.5 truncate text-xs text-[#5c6d64]" data-testid={`overview-submission-meta-${submission.id}`}>{submission.crew_label} · {submission.service_type}</p>
                    </div>
                    <Badge className="shrink-0 border-0 bg-white px-2 py-0.5 text-xs text-[#243e36]" data-testid={`overview-submission-status-${submission.id}`}>{submission.status}</Badge>
                  </div>
                </div>
              ))}
            </div>
            {submissionTotal > 4 && (
              <div className="mt-3 flex items-center justify-between" data-testid="overview-submissions-pagination">
                <span className="text-xs text-[#5c6d64]">Page {submissionPage} of {Math.ceil(submissionTotal / 4)}</span>
                <div className="flex gap-1.5">
                  <Button type="button" variant="outline" size="sm" disabled={submissionPage <= 1} onClick={() => loadSubmissions(submissionPage - 1)} className="h-7 rounded-lg text-xs" data-testid="overview-submissions-prev">Prev</Button>
                  <Button type="button" variant="outline" size="sm" disabled={submissionPage >= Math.ceil(submissionTotal / 4)} onClick={() => loadSubmissions(submissionPage + 1)} className="h-7 rounded-lg text-xs" data-testid="overview-submissions-next">Next</Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="rounded-[24px] border-border/80 bg-white/95 shadow-sm" data-testid="overview-rapid-review-launch-card">
            <CardContent className="flex items-center justify-between gap-4 p-5">
              <div className="min-w-0">
                <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Rapid review</p>
                <h3 className="mt-1 font-[Outfit] text-lg font-bold text-[#111815]">Mobile swipe lane</h3>
                <p className="mt-1 text-xs text-[#5c6d64]">Scan or copy to open admin review on phone.</p>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <div className="rounded-[14px] border border-border bg-[#f6f6f2] p-2" data-testid="overview-rapid-review-qr-card">
                  <QRCodeSVG value={rapidReviewUrl} size={72} bgColor="transparent" fgColor="#243e36" />
                </div>
                <div className="space-y-1.5">
                  <Button asChild size="sm" className="h-8 w-full rounded-xl bg-[#243e36] text-xs hover:bg-[#1a2c26]" data-testid="overview-open-mobile-rapid-review-button">
                    <Link to="/rapid-review/mobile"><Smartphone className="mr-1.5 h-3 w-3" />Open</Link>
                  </Button>
                  <Button type="button" variant="outline" size="sm" onClick={copyRapidReviewLink} className="h-8 w-full rounded-xl border-[#243e36]/15 text-xs text-[#243e36]" data-testid="overview-copy-rapid-review-link-button">
                    <Copy className="mr-1.5 h-3 w-3" />Copy link
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-[24px] border-border/80 bg-[#243e36] text-white shadow-sm" data-testid="overview-lifecycle-card">
            <CardContent className="p-5">
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#d8f3dc]">Workflow lifecycle</p>
              <h3 className="mt-1 font-[Outfit] text-lg font-bold">Submission states</h3>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {(user?.role === "owner"
                  ? ["Draft", "Submitted", "Pending Match", "Ready for Review", "Mgmt Reviewed", "Owner Reviewed", "Finalized", "Export Ready", "Exported"]
                  : ["Draft", "Submitted", "Pending Match", "Ready for Review", "Mgmt Reviewed", "Owner Reviewed", "Finalized"]
                ).map((step, index) => (
                  <span key={step} className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs font-medium text-white/80" data-testid={`overview-lifecycle-step-${index + 1}`}>
                    <span className="flex h-4 w-4 items-center justify-center rounded-full bg-white/10 text-[10px] font-bold">{index + 1}</span>
                    {step}
                  </span>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}