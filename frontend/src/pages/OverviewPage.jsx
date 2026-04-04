import { Activity, AlertTriangle, ArrowDown, ArrowUp, Boxes, CheckCircle2, CircleDot, ClipboardCheck, Copy, Download, FolderInput, Grid3X3, ShieldCheck, Smartphone, Target, TrendingUp, UploadCloud, Users, X, Zap } from "lucide-react";
import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { Link } from "react-router-dom";

import { QRCodeSVG } from "qrcode.react";

import StatCard from "@/components/common/StatCard";
import GettingStartedPanel from "@/components/common/GettingStartedPanel";
import { HelpPopover } from "@/components/common/HelpPopover";
import WelcomeModal from "@/components/common/WelcomeModal";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { authGet } from "@/lib/api";
import { copyToClipboard } from "@/lib/clipboard";
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
  const [divQuality, setDivQuality] = useState(null);
  const [compliance, setCompliance] = useState(null);
  const [funnel, setFunnel] = useState(null);
  const [hoveredMetric, setHoveredMetric] = useState(null);
  const hoverTimerRef = useRef(null);

  // Role-specific widget states
  const [pmDash, setPmDash] = useState(null);
  const [crewLeaders, setCrewLeaders] = useState(null);
  const [amReport, setAmReport] = useState(null);
  const [supervisorCheck, setSupervisorCheck] = useState(null);
  const [insights, setInsights] = useState(null);
  const [digest, setDigest] = useState(null);
  const [onboarding, setOnboarding] = useState(null);
  const [coachingLoop, setCoachingLoop] = useState(null);

  const isOwnerOrGM = user?.role === "owner" || user?.title === "GM";

  const handleMetricEnter = useCallback((key) => {
    if (hoverTimerRef.current) clearTimeout(hoverTimerRef.current);
    setHoveredMetric(key);
  }, []);
  const handleMetricLeave = useCallback(() => {
    hoverTimerRef.current = setTimeout(() => setHoveredMetric(null), 150);
  }, []);

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
      // Load metrics
      authGet("/metrics/division-quality-trend").then(setDivQuality).catch(() => {});
      authGet("/metrics/standards-compliance").then(setCompliance).catch(() => {});
      authGet("/metrics/training-funnel").then(setFunnel).catch(() => {});
      authGet("/metrics/smart-insights").then(setInsights).catch(() => {});
      authGet("/metrics/weekly-digest").then(setDigest).catch(() => {});
      authGet("/onboarding/progress?division=all").then(setOnboarding).catch(() => {});
      authGet("/coaching/loop-report?division=all").then(setCoachingLoop).catch(() => {});
    };
    load();
  }, []);

  // Role-specific data loading
  useEffect(() => {
    if (!user) return;
    const title = user.title || "";
    const div = user.division || "all";
    if (title === "Production Manager") {
      authGet(`/metrics/pm-dashboard?division=${encodeURIComponent(div)}`).then(setPmDash).catch(() => {});
      authGet(`/metrics/crew-leader-performance?division=${encodeURIComponent(div)}`).then(setCrewLeaders).catch(() => {});
    }
    if (title === "Account Manager" || isOwnerOrGM) {
      authGet("/metrics/account-manager-report").then(setAmReport).catch(() => {});
    }
    if (title === "Supervisor" || isOwnerOrGM) {
      authGet("/metrics/supervisor-checklist").then(setSupervisorCheck).catch(() => {});
    }
    if (isOwnerOrGM) {
      authGet("/metrics/crew-leader-performance?division=all").then(setCrewLeaders).catch(() => {});
    }
  }, [user, isOwnerOrGM]);

  if (!overview) {
    return <div className="rounded-[28px] border border-border bg-[var(--card)] p-10 text-center text-[var(--foreground)]" data-testid="overview-loading-state">Loading overview...</div>;
  }

  const storage = overview.storage || overview.drive;
  const copyRapidReviewLink = async () => {
    try {
      await copyToClipboard(rapidReviewUrl);
      toast.success("Rapid review link copied.");
    } catch {
      toast.info(rapidReviewUrl);
    }
  };

  const baseStats = [
    { icon: Activity, label: "Submissions", value: overview.totals.submissions, hint: "All captured proof records", testId: "overview-stat-submissions" },
    { icon: FolderInput, label: "Imported jobs", value: overview.totals.jobs, hint: "Alignment records available for admin review", testId: "overview-stat-jobs" },
  ];
  const ownerStats = [
    { icon: ShieldCheck, label: "Owner queue", value: overview.queues.owner, hint: "Items needing final calibration", testId: "overview-stat-owner-queue" },
    { icon: UploadCloud, label: "Export ready", value: overview.queues.export_ready, hint: "Records ready for dataset packaging", testId: "overview-stat-export-ready" },
  ];
  const stats = isOwnerOrGM ? [...baseStats, ...ownerStats] : baseStats;

  return (
    <div className="space-y-4" data-testid="overview-page">
      <WelcomeModal user={user} />
      <GettingStartedPanel user={user} />

      <Card className="overflow-hidden rounded-[24px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="overview-hero-card">
        <CardContent className="grid gap-4 p-5 lg:grid-cols-[1.3fr_0.7fr] lg:p-6">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]" data-testid="overview-kicker-text">Operations pulse</p>
            <h2 className="mt-2 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[var(--foreground)] lg:text-4xl" data-testid="overview-title">Crews fast. Labels consistent. Data clean.</h2>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[var(--muted-foreground)]" data-testid="overview-description">Capture volume, review queues, storage status, and export momentum at a glance.</p>
          </div>
          <div className="grid gap-3 rounded-[20px] border border-border bg-[var(--accent)] p-4" data-testid="overview-workflow-health-card">
            <div>
              <p className="text-sm font-semibold text-[var(--foreground)]">Review velocity</p>
              <p className="mt-1 font-[Cabinet_Grotesk] text-4xl font-black text-[var(--foreground)]" data-testid="overview-review-velocity-value">{overview.workflow_health.review_velocity_percent}%</p>
              <p className="mt-1 text-xs text-[var(--muted-foreground)]" data-testid="overview-review-velocity-hint">Captured work moving through review and export.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge className="border-0 bg-[var(--accent)] px-2 py-0.5 text-xs text-[var(--foreground)]" data-testid="overview-drive-config-badge">Storage: {storage?.configured ? "OK" : "N/A"}</Badge>
              <Badge className="border-0 bg-[var(--accent)] px-2 py-0.5 text-xs text-[var(--foreground)]" data-testid="overview-drive-connected-badge">Ready: {storage?.connected ? "Yes" : "No"}</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className={`grid gap-3 md:grid-cols-2 ${isOwnerOrGM ? "xl:grid-cols-4" : "xl:grid-cols-2"}`}>
        {stats.map((item) => <StatCard key={item.label} {...item} />)}
      </div>

      <Card className="rounded-[32px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="overview-rubric-matrix-card">
        <CardContent className="p-5 sm:p-6">
          <button
            type="button"
            onClick={() => setMatrixOpen(!matrixOpen)}
            className="flex w-full items-center justify-between gap-3 text-left"
            data-testid="overview-rubric-toggle"
          >
            <div className="flex items-center gap-3">
              <Grid3X3 className="h-5 w-5 text-[var(--foreground)]" />
              <div>
                <h3 className="font-semibold text-[var(--foreground)]">Quick matrix ref</h3>
                <p className="text-xs text-[var(--muted-foreground)]">{rubricMatrices.length} active rubrics across divisions</p>
              </div>
              <HelpPopover title="Rubric matrices">
                <p className="mb-2">Each service type has a rubric with <strong>weighted grading categories</strong> that must sum to 1.0.</p>
                <p className="mb-2"><strong>Pass threshold</strong> — the minimum score % to pass review.</p>
                <p className="mb-2"><strong>Hard-fail conditions</strong> — if triggered, the submission fails regardless of score.</p>
                <p>GM and Owner can create, edit, and deactivate rubrics from the <strong>Rubric Editor</strong> page.</p>
              </HelpPopover>
            </div>
            <Badge className="border-0 bg-[var(--accent)] text-[var(--foreground)]">{matrixOpen ? "Close" : "View"}</Badge>
          </button>
        </CardContent>
      </Card>

      {matrixOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4" data-testid="overview-rubric-widget-overlay" onClick={() => setMatrixOpen(false)}>
          <div className="max-h-[80vh] w-full max-w-3xl overflow-hidden rounded-[28px] border border-border/80 shadow-2xl" style={{ backgroundColor: 'var(--modal-bg)' }} onClick={(e) => e.stopPropagation()} data-testid="overview-rubric-widget">
            <div className="flex items-center justify-between gap-4 border-b border-border/60 px-6 py-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Quick matrix ref</p>
                <h3 className="mt-1 font-[Outfit] text-xl font-bold text-[var(--foreground)]">Rubric grading factors</h3>
              </div>
              <div className="flex items-center gap-2">
                <Select value={matrixDivisionFilter} onValueChange={setMatrixDivisionFilter}>
                  <SelectTrigger className="h-9 w-[160px] rounded-xl border-transparent bg-[var(--accent)] text-sm" data-testid="overview-matrix-division-filter"><SelectValue placeholder="All divisions" /></SelectTrigger>
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
                    <th className="pb-2 pr-4 text-xs font-bold uppercase tracking-wider text-[var(--muted-foreground)]">Task</th>
                    <th className="pb-2 pr-4 text-xs font-bold uppercase tracking-wider text-[var(--muted-foreground)]">Division</th>
                    <th className="pb-2 pr-4 text-xs font-bold uppercase tracking-wider text-[var(--muted-foreground)]">Factors</th>
                    <th className="pb-2 pr-4 text-xs font-bold uppercase tracking-wider text-[var(--muted-foreground)]">Pass</th>
                    <th className="pb-2 text-xs font-bold uppercase tracking-wider text-[var(--muted-foreground)]">Ver</th>
                  </tr>
                </thead>
                <tbody>
                  {rubricMatrices
                    .filter((item) => matrixDivisionFilter === "all" || item.division === matrixDivisionFilter)
                    .map((rubric) => (
                      <tr key={rubric.id} className="border-b border-border/30" data-testid={`overview-rubric-row-${rubric.id}`}>
                        <td className="py-2.5 pr-4 font-semibold capitalize text-[var(--foreground)]">{rubric.service_type}</td>
                        <td className="py-2.5 pr-4"><Badge className="border-0 bg-[var(--accent)] text-xs text-[var(--foreground)]">{rubric.division || "General"}</Badge></td>
                        <td className="py-2.5 pr-4">
                          <div className="flex flex-wrap gap-1">
                            {(rubric.categories || []).map((cat) => (
                              <span key={cat.key} className="inline-block rounded px-1.5 py-0.5 text-[11px] font-medium" style={{ backgroundColor: 'var(--chip-bg)', color: 'var(--tier-desc-text)' }}>{cat.label} ({Math.round(cat.weight * 100)}%)</span>
                            ))}
                          </div>
                        </td>
                        <td className="py-2.5 pr-4 font-semibold text-[var(--foreground)]">{rubric.pass_threshold}%</td>
                        <td className="py-2.5 text-[var(--muted-foreground)]">v{rubric.version}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
              {rubricMatrices.filter((item) => matrixDivisionFilter === "all" || item.division === matrixDivisionFilter).length === 0 && (
                <p className="mt-4 text-center text-sm text-[var(--muted-foreground)]" data-testid="overview-rubric-empty">No rubric matrices found.</p>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <Card className="rounded-[24px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="overview-recent-submissions-card">
          <CardContent className="p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Recent submissions</p>
                <h3 className="mt-1 font-[Outfit] text-lg font-bold text-[var(--foreground)]">Current field activity</h3>
              </div>
              <Boxes className="h-5 w-5 text-[var(--foreground)]" />
            </div>
            <div className="mt-4 space-y-2">
              {submissions.map((submission) => (
                <div key={submission.id} className="rounded-[16px] border border-border bg-[var(--accent)] px-4 py-3" data-testid={`overview-submission-card-${submission.id}`}>
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-[var(--foreground)]" data-testid={`overview-submission-job-${submission.id}`}>{submission.job_name_input || submission.job_id || submission.submission_code}</p>
                      <p className="mt-0.5 truncate text-xs text-[var(--muted-foreground)]" data-testid={`overview-submission-meta-${submission.id}`}>{submission.crew_label} · {submission.service_type}{submission.work_date ? ` · ${submission.work_date}` : ""}</p>
                    </div>
                    <Badge className="shrink-0 border-0 bg-[var(--accent)] px-2 py-0.5 text-xs text-[var(--foreground)]" data-testid={`overview-submission-status-${submission.id}`}>{submission.status}</Badge>
                  </div>
                </div>
              ))}
            </div>
            {submissionTotal > 4 && (
              <div className="mt-3 flex items-center justify-between" data-testid="overview-submissions-pagination">
                <span className="text-xs text-[var(--muted-foreground)]">Page {submissionPage} of {Math.ceil(submissionTotal / 4)}</span>
                <div className="flex gap-1.5">
                  <Button type="button" variant="outline" size="sm" disabled={submissionPage <= 1} onClick={() => loadSubmissions(submissionPage - 1)} className="h-7 rounded-lg text-xs" data-testid="overview-submissions-prev">Prev</Button>
                  <Button type="button" variant="outline" size="sm" disabled={submissionPage >= Math.ceil(submissionTotal / 4)} onClick={() => loadSubmissions(submissionPage + 1)} className="h-7 rounded-lg text-xs" data-testid="overview-submissions-next">Next</Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="rounded-[24px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="overview-rapid-review-launch-card">
            <CardContent className="flex items-center justify-between gap-4 p-5">
              <div className="min-w-0">
                <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Rapid review</p>
                <h3 className="mt-1 font-[Outfit] text-lg font-bold text-[var(--foreground)]">Mobile swipe lane</h3>
                <p className="mt-1 flex items-center gap-1.5 text-xs text-[var(--muted-foreground)]">
                  Scan or copy to open admin review on phone.
                  <HelpPopover title="Rapid review swipe controls" side="left">
                    <p className="mb-2"><strong>Swipe right</strong> — Standard pass</p>
                    <p className="mb-2"><strong>Swipe left</strong> — Fail (comment required)</p>
                    <p className="mb-2"><strong>Swipe up</strong> — Exemplary (comment required)</p>
                    <p className="mb-2"><strong>Speed alerts</strong> — Reviews under 4 seconds are flagged. 3+ fast reviews in a session triggers an Owner notification.</p>
                    <p><strong>Concern</strong> — Marks the submission for manual rescore by a senior reviewer.</p>
                  </HelpPopover>
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <div className="rounded-[14px] border border-border bg-[var(--accent)] p-2" data-testid="overview-rapid-review-qr-card">
                  <QRCodeSVG value={rapidReviewUrl} size={72} bgColor="transparent" fgColor="#243e36" />
                </div>
                <div className="space-y-1.5">
                  <Button asChild size="sm" className="h-8 w-full rounded-xl bg-[#243e36] text-xs hover:bg-[#1a2c26]" data-testid="overview-open-mobile-rapid-review-button">
                    <Link to="/rapid-review/mobile"><Smartphone className="mr-1.5 h-3 w-3" />Open</Link>
                  </Button>
                  <Button type="button" variant="outline" size="sm" onClick={copyRapidReviewLink} className="h-8 w-full rounded-xl border-[#243e36]/15 text-xs text-[var(--foreground)]" data-testid="overview-copy-rapid-review-link-button">
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
                {(isOwnerOrGM
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

        {/* ─── METRICS WIDGETS ROW — hover to expand ─── */}
        <div
          className="grid gap-4 transition-all duration-500 ease-in-out"
          style={{
            gridTemplateColumns:
              hoveredMetric === "quality"  ? "2.2fr 0.9fr 0.9fr" :
              hoveredMetric === "compliance" ? "0.9fr 2.2fr 0.9fr" :
              hoveredMetric === "funnel"   ? "0.9fr 0.9fr 2.2fr" :
              "1fr 1fr 1fr",
          }}
          data-testid="metrics-widgets-row"
        >

          {/* Division Quality Trend */}
          {divQuality && (
            <Card
              className="rounded-[24px] border-border/80 bg-[var(--card)] shadow-sm cursor-default transition-shadow duration-300 hover:shadow-lg overflow-hidden"
              data-testid="metric-division-quality"
              onMouseEnter={() => handleMetricEnter("quality")}
              onMouseLeave={handleMetricLeave}
            >
              <CardContent className="p-5">
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-[#38a89d]" />
                  <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Division Quality Trend</p>
                </div>
                <div className="mt-3 space-y-2">
                  {["30d", "60d", "90d"].map(period => (
                    <div key={period}>
                      <p className="text-[10px] font-bold uppercase text-[var(--muted-foreground)]">{period}</p>
                      <div className="mt-1 flex flex-wrap gap-1.5">
                        {divQuality.trends[period] && Object.entries(divQuality.trends[period]).map(([div, score]) => (
                          <span key={div} className="inline-flex items-center gap-1 rounded-full bg-[var(--accent)] px-2 py-0.5 text-[10px] font-semibold text-[var(--foreground)]">
                            {div}: <strong>{score}</strong>
                          </span>
                        ))}
                        {(!divQuality.trends[period] || Object.keys(divQuality.trends[period]).length === 0) && (
                          <span className="text-[10px] text-[var(--muted-foreground)]">No data</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
                {/* Expanded detail */}
                <div className={`overflow-hidden transition-all duration-400 ease-in-out ${hoveredMetric === "quality" ? "mt-4 max-h-[300px] opacity-100" : "mt-0 max-h-0 opacity-0"}`}>
                  <div className="border-t border-border/60 pt-3 space-y-2">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted-foreground)]">Score Breakdown</p>
                    {["30d", "60d", "90d"].map(period => (
                      divQuality.trends[period] && Object.entries(divQuality.trends[period]).map(([div, score]) => (
                        <div key={`${period}-${div}`} className="flex items-center gap-2">
                          <span className="w-14 text-[10px] font-semibold text-[var(--muted-foreground)]">{period}</span>
                          <span className="w-24 truncate text-[11px] font-medium text-[var(--foreground)]">{div}</span>
                          <div className="h-1.5 flex-1 rounded-full bg-[var(--border)] overflow-hidden">
                            <div className="h-full rounded-full bg-[#38a89d] transition-all duration-500" style={{ width: `${Math.min((score / 5) * 100, 100)}%` }} />
                          </div>
                          <span className="w-8 text-right text-[11px] font-black text-[var(--foreground)]">{score}</span>
                        </div>
                      ))
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Standards Compliance */}
          {compliance && compliance.standards?.length > 0 && (
            <Card
              className="rounded-[24px] border-border/80 bg-[var(--card)] shadow-sm cursor-default transition-shadow duration-300 hover:shadow-lg overflow-hidden"
              data-testid="metric-standards-compliance"
              onMouseEnter={() => handleMetricEnter("compliance")}
              onMouseLeave={handleMetricLeave}
            >
              <CardContent className="p-5">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-[#34d399]" />
                  <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Standards Compliance</p>
                </div>
                <div className={`mt-3 space-y-1.5 overflow-y-auto transition-all duration-400 ${hoveredMetric === "compliance" ? "max-h-[360px]" : "max-h-[180px]"}`}>
                  {compliance.standards.map(s => (
                    <div key={s.standard} className="flex items-center justify-between gap-2 rounded-[10px] bg-[var(--accent)] px-2.5 py-1.5">
                      <p className={`font-medium text-[var(--foreground)] truncate flex-1 transition-all duration-300 ${hoveredMetric === "compliance" ? "text-[11px]" : "text-[10px]"}`} title={s.standard}>{s.standard}</p>
                      <div className="flex items-center gap-2 shrink-0">
                        <div className={`rounded-full bg-[var(--border)] overflow-hidden transition-all duration-400 ${hoveredMetric === "compliance" ? "h-2 w-24" : "h-1.5 w-16"}`}>
                          <div className="h-full rounded-full transition-all duration-500" style={{ width: `${s.compliance_pct}%`, backgroundColor: s.compliance_pct >= 70 ? "#34d399" : s.compliance_pct >= 40 ? "#f59e0b" : "#ef4444" }} />
                        </div>
                        <span className="text-[10px] font-bold text-[var(--foreground)] w-9 text-right">{s.compliance_pct}%</span>
                      </div>
                    </div>
                  ))}
                </div>
                {/* Expanded detail */}
                <div className={`overflow-hidden transition-all duration-400 ease-in-out ${hoveredMetric === "compliance" ? "mt-4 max-h-[200px] opacity-100" : "mt-0 max-h-0 opacity-0"}`}>
                  <div className="border-t border-border/60 pt-3 space-y-1">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted-foreground)]">Summary</p>
                    <div className="flex gap-3">
                      <div className="flex-1 rounded-[10px] bg-[var(--accent)] p-2 text-center">
                        <p className="text-lg font-black text-[#34d399]">{compliance.standards.filter(s => s.compliance_pct >= 70).length}</p>
                        <p className="text-[9px] font-semibold text-[var(--muted-foreground)]">Passing</p>
                      </div>
                      <div className="flex-1 rounded-[10px] bg-[var(--accent)] p-2 text-center">
                        <p className="text-lg font-black text-[#f59e0b]">{compliance.standards.filter(s => s.compliance_pct >= 40 && s.compliance_pct < 70).length}</p>
                        <p className="text-[9px] font-semibold text-[var(--muted-foreground)]">At Risk</p>
                      </div>
                      <div className="flex-1 rounded-[10px] bg-[var(--accent)] p-2 text-center">
                        <p className="text-lg font-black text-[#ef4444]">{compliance.standards.filter(s => s.compliance_pct < 40).length}</p>
                        <p className="text-[9px] font-semibold text-[var(--muted-foreground)]">Failing</p>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Training Funnel */}
          {funnel && (
            <Card
              className="rounded-[24px] border-border/80 bg-[var(--card)] shadow-sm cursor-default transition-shadow duration-300 hover:shadow-lg overflow-hidden"
              data-testid="metric-training-funnel"
              onMouseEnter={() => handleMetricEnter("funnel")}
              onMouseLeave={handleMetricLeave}
            >
              <CardContent className="p-5">
                <div className="flex items-center gap-2">
                  <Activity className="h-4 w-4 text-[#9b7cd8]" />
                  <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Training Funnel</p>
                </div>
                <div className="mt-4 space-y-3">
                  {[
                    { label: "Total People", value: funnel.total_people, pct: 100, color: "#243e36" },
                    { label: "Attempted Training", value: funnel.attempted_training, pct: funnel.funnel_pct?.attempted || 0, color: "#38a89d" },
                    { label: "Passed Training", value: funnel.passed_training, pct: funnel.funnel_pct?.passed || 0, color: "#34d399" },
                  ].map(step => (
                    <div key={step.label}>
                      <div className="flex items-center justify-between mb-1">
                        <p className="text-[10px] font-semibold text-[var(--foreground)]">{step.label}</p>
                        <p className="text-xs font-black text-[var(--foreground)]">{step.value} <span className="font-normal text-[var(--muted-foreground)]">({step.pct}%)</span></p>
                      </div>
                      <div className="h-2 w-full rounded-full bg-[var(--border)] overflow-hidden">
                        <div className="h-full rounded-full transition-all" style={{ width: `${step.pct}%`, backgroundColor: step.color }} />
                      </div>
                    </div>
                  ))}
                </div>
                {/* Expanded detail */}
                <div className={`overflow-hidden transition-all duration-400 ease-in-out ${hoveredMetric === "funnel" ? "mt-4 max-h-[300px] opacity-100" : "mt-0 max-h-0 opacity-0"}`}>
                  <div className="border-t border-border/60 pt-3 space-y-2">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted-foreground)]">Breakdown</p>
                    <div className="grid grid-cols-2 gap-2">
                      <div className="rounded-[10px] bg-[var(--accent)] p-2.5">
                        <p className="text-[9px] font-bold uppercase text-[var(--muted-foreground)]">Crews</p>
                        <p className="text-lg font-black text-[var(--foreground)]">{funnel.total_crews}</p>
                      </div>
                      <div className="rounded-[10px] bg-[var(--accent)] p-2.5">
                        <p className="text-[9px] font-bold uppercase text-[var(--muted-foreground)]">Members</p>
                        <p className="text-lg font-black text-[var(--foreground)]">{funnel.total_members}</p>
                      </div>
                      <div className="rounded-[10px] bg-[var(--accent)] p-2.5">
                        <p className="text-[9px] font-bold uppercase text-[var(--muted-foreground)]">Drop-off Rate</p>
                        <p className="text-lg font-black text-[#f59e0b]">{(100 - (funnel.funnel_pct?.passed || 0)).toFixed(1)}%</p>
                      </div>
                      <div className="rounded-[10px] bg-[var(--accent)] p-2.5">
                        <p className="text-[9px] font-bold uppercase text-[var(--muted-foreground)]">Completion</p>
                        <p className="text-lg font-black text-[#34d399]">{funnel.funnel_pct?.passed || 0}%</p>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* ─── SMART INSIGHTS BAR ─── */}
        {insights && insights.insights?.length > 0 && (
          <div className="flex flex-wrap gap-2" data-testid="smart-insights-bar">
            {insights.insights.map((ins, i) => (
              <div
                key={i}
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[11px] font-semibold transition-transform hover:scale-105 ${
                  ins.type === "drop" ? "bg-red-500/15 text-red-400" :
                  ins.type === "rise" ? "bg-emerald-500/15 text-emerald-400" :
                  ins.type === "red_tag" ? "bg-orange-500/15 text-orange-400" :
                  "bg-[var(--accent)] text-[var(--muted-foreground)]"
                }`}
                data-testid={`smart-insight-${i}`}
                title={ins.message}
              >
                {ins.type === "drop" && <ArrowDown className="h-3 w-3" />}
                {ins.type === "rise" && <ArrowUp className="h-3 w-3" />}
                {ins.type === "red_tag" && <AlertTriangle className="h-3 w-3" />}
                {ins.type === "training_gap" && <Users className="h-3 w-3" />}
                <span className="truncate max-w-[260px]">{ins.message}</span>
              </div>
            ))}
          </div>
        )}

        {/* ─── ROLE-SPECIFIC WIDGETS ─── */}

        {/* PM Dashboard Widget */}
        {pmDash && user?.title === "Production Manager" && (
          <Card className="rounded-[24px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="widget-pm-dashboard">
            <CardContent className="p-5">
              <div className="flex items-center gap-2 mb-4">
                <ClipboardCheck className="h-4 w-4 text-[#38a89d]" />
                <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">
                  {user?.title === "Production Manager" ? `${pmDash.division} Division` : "PM Dashboard"} — 90 Day Snapshot
                </p>
              </div>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div className="rounded-[14px] bg-[var(--accent)] p-3 text-center">
                  <p className="text-2xl font-black text-[var(--foreground)]">{pmDash.submissions_30d}</p>
                  <p className="text-[9px] font-bold uppercase text-[var(--muted-foreground)]">Subs (30d)</p>
                </div>
                <div className="rounded-[14px] bg-[var(--accent)] p-3 text-center">
                  <p className="text-2xl font-black text-[var(--foreground)]">{pmDash.avg_score_90d}</p>
                  <p className="text-[9px] font-bold uppercase text-[var(--muted-foreground)]">Avg Score</p>
                </div>
                <div className="rounded-[14px] bg-[var(--accent)] p-3 text-center">
                  <p className="text-2xl font-black text-emerald-400">{pmDash.pass_count}</p>
                  <p className="text-[9px] font-bold uppercase text-[var(--muted-foreground)]">Pass</p>
                </div>
                <div className="rounded-[14px] bg-[var(--accent)] p-3 text-center">
                  <p className="text-2xl font-black text-red-400">{pmDash.fail_count}</p>
                  <p className="text-[9px] font-bold uppercase text-[var(--muted-foreground)]">Fail</p>
                </div>
              </div>
              <div className="mt-3 flex items-center gap-4 text-[10px] text-[var(--muted-foreground)]">
                <span><strong className="text-[var(--foreground)]">{pmDash.crews}</strong> active crews</span>
                <span><strong className="text-[var(--foreground)]">{pmDash.training_completed}</strong>/{pmDash.training_total} training completed</span>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Crew Leader Performance */}
        {crewLeaders && crewLeaders.leaders?.length > 0 && (
          <Card className="rounded-[24px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="widget-crew-leaders">
            <CardContent className="p-5">
              <div className="flex items-center gap-2 mb-4">
                <Users className="h-4 w-4 text-[#34d399]" />
                <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Crew Leader Performance</p>
              </div>
              <div className="space-y-2">
                {crewLeaders.leaders.map((leader, i) => (
                  <div key={i} className="flex items-center gap-3 rounded-[14px] bg-[var(--accent)] p-3" data-testid={`crew-leader-${i}`}>
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--card)] text-xs font-black text-[var(--foreground)]">{i + 1}</div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-bold text-[var(--foreground)] truncate">{leader.leader_name || "Unnamed"}</p>
                      <p className="text-[10px] text-[var(--muted-foreground)]">{leader.crew_label} — {leader.division}</p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-lg font-black text-[var(--foreground)]">{leader.avg_score}</p>
                      <p className="text-[9px] text-[var(--muted-foreground)]">{leader.submissions_90d} subs · {leader.pass_count}P/{leader.fail_count}F</p>
                    </div>
                    <div className="h-2 w-20 rounded-full bg-[var(--border)] overflow-hidden shrink-0">
                      <div className="h-full rounded-full transition-all" style={{ width: `${Math.min((leader.avg_score / 5) * 100, 100)}%`, backgroundColor: leader.avg_score >= 4 ? "#34d399" : leader.avg_score >= 3 ? "#f59e0b" : "#ef4444" }} />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* AM Client Report */}
        {amReport && (user?.title === "Account Manager" || isOwnerOrGM) && amReport.properties?.length > 0 && (
          <Card className="rounded-[24px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="widget-am-report">
            <CardContent className="p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Boxes className="h-4 w-4 text-[#59a5d8]" />
                  <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Client Quality Report — {amReport.total_properties} Properties</p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 gap-1.5 text-[10px] font-bold uppercase"
                  data-testid="am-export-pdf-btn"
                  onClick={() => {
                    const token = localStorage.getItem("field-quality-token");
                    const url = `${process.env.REACT_APP_BACKEND_URL}/api/exports/am-report-pdf`;
                    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
                      .then(r => r.blob())
                      .then(blob => {
                        const a = document.createElement("a");
                        a.href = URL.createObjectURL(blob);
                        a.download = `SarverLandscape_ClientReport.pdf`;
                        a.click();
                        toast.success("PDF downloaded");
                      })
                      .catch(() => toast.error("PDF export failed"));
                  }}
                >
                  <Download className="h-3 w-3" /> Export PDF
                </Button>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-border/60">
                      <th className="pb-2 text-[10px] font-bold uppercase text-[var(--muted-foreground)]">Property</th>
                      <th className="pb-2 text-[10px] font-bold uppercase text-[var(--muted-foreground)] text-center">Subs</th>
                      <th className="pb-2 text-[10px] font-bold uppercase text-[var(--muted-foreground)] text-center">Avg Score</th>
                      <th className="pb-2 text-[10px] font-bold uppercase text-[var(--muted-foreground)] text-center">Pass</th>
                      <th className="pb-2 text-[10px] font-bold uppercase text-[var(--muted-foreground)] text-center">Fail</th>
                      <th className="pb-2 text-[10px] font-bold uppercase text-[var(--muted-foreground)]">Divisions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {amReport.properties.map((p, i) => (
                      <tr key={i} className="border-b border-border/30" data-testid={`am-property-${i}`}>
                        <td className="py-2 font-medium text-[var(--foreground)] text-xs">{p.property}</td>
                        <td className="py-2 text-center text-xs text-[var(--foreground)]">{p.submissions}</td>
                        <td className="py-2 text-center text-xs font-black text-[var(--foreground)]">{p.avg_score}</td>
                        <td className="py-2 text-center text-xs text-emerald-400">{p.pass_count}</td>
                        <td className="py-2 text-center text-xs text-red-400">{p.fail_count}</td>
                        <td className="py-2"><div className="flex gap-1 flex-wrap">{p.divisions.map(d => <Badge key={d} className="border-0 bg-[var(--accent)] text-[9px] text-[var(--foreground)]">{d}</Badge>)}</div></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Supervisor Daily Checklist */}
        {supervisorCheck && (user?.title === "Supervisor" || isOwnerOrGM) && (
          <Card className="rounded-[24px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="widget-supervisor-checklist">
            <CardContent className="p-5">
              <div className="flex items-center gap-2 mb-4">
                <ClipboardCheck className="h-4 w-4 text-[#7c6cf0]" />
                <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Supervisor Daily Checklist</p>
              </div>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div className="rounded-[14px] bg-[var(--accent)] p-3 text-center">
                  <p className="text-2xl font-black text-[var(--foreground)]">{supervisorCheck.today_equipment_checks}</p>
                  <p className="text-[9px] font-bold uppercase text-[var(--muted-foreground)]">Equipment Checks</p>
                </div>
                <div className="rounded-[14px] bg-[var(--accent)] p-3 text-center">
                  <p className="text-2xl font-black text-[var(--foreground)]">{supervisorCheck.today_submissions}</p>
                  <p className="text-[9px] font-bold uppercase text-[var(--muted-foreground)]">Submissions Today</p>
                </div>
                <div className="rounded-[14px] bg-[var(--accent)] p-3 text-center">
                  <p className="text-2xl font-black text-[var(--foreground)]">{supervisorCheck.active_crews}</p>
                  <p className="text-[9px] font-bold uppercase text-[var(--muted-foreground)]">Active Crews</p>
                </div>
                <div className="rounded-[14px] bg-[var(--accent)] p-3 text-center">
                  <p className={`text-2xl font-black ${supervisorCheck.red_tags_this_week > 0 ? "text-red-400" : "text-emerald-400"}`}>{supervisorCheck.red_tags_this_week}</p>
                  <p className="text-[9px] font-bold uppercase text-[var(--muted-foreground)]">Red Tags (7d)</p>
                </div>
              </div>
              {supervisorCheck.equipment_checked_today?.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  <span className="text-[10px] font-bold text-[var(--muted-foreground)]">Checked:</span>
                  {supervisorCheck.equipment_checked_today.map(eq => (
                    <Badge key={eq} className="border-0 bg-emerald-500/15 text-[9px] text-emerald-400">{eq}</Badge>
                  ))}
                </div>
              )}
              {supervisorCheck.red_tag_details?.length > 0 && (
                <div className="mt-3 space-y-1">
                  <p className="text-[10px] font-bold uppercase text-red-400">Recent Red Tags</p>
                  {supervisorCheck.red_tag_details.map((rt, i) => (
                    <div key={i} className="flex items-center gap-2 rounded-lg bg-red-500/10 px-2.5 py-1.5 text-[10px] text-red-300">
                      <AlertTriangle className="h-3 w-3 shrink-0" />
                      <span className="font-bold">{rt.equipment_number}</span>
                      <span className="truncate">{rt.notes}</span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Weekly Digest */}
        {digest && (digest.top_performers?.length > 0 || digest.bottom_performers?.length > 0) && (
          <Card className="rounded-[24px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="widget-weekly-digest">
            <CardContent className="p-5">
              <div className="flex items-center gap-2 mb-4">
                <Zap className="h-4 w-4 text-[#f59e0b]" />
                <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Weekly Digest — {digest.total_crews_active} Active Crews</p>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                {/* Top Performers */}
                {digest.top_performers?.length > 0 && (
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-widest text-emerald-400 mb-2">Top Performers</p>
                    <div className="space-y-1.5">
                      {digest.top_performers.map((p, i) => (
                        <div key={i} className="flex items-center gap-2 rounded-[12px] bg-emerald-500/10 p-2.5" data-testid={`digest-top-${i}`}>
                          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500/20 text-[10px] font-black text-emerald-400">{i + 1}</div>
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-bold text-[var(--foreground)] truncate">{p.crew}</p>
                            <p className="text-[9px] text-[var(--muted-foreground)]">{p.submissions} subs this week</p>
                          </div>
                          <div className="text-right shrink-0">
                            <p className="text-sm font-black text-emerald-400">{p.avg_score}</p>
                            {p.delta !== 0 && (
                              <p className={`text-[9px] font-bold ${p.delta > 0 ? "text-emerald-400" : "text-red-400"}`}>
                                {p.delta > 0 ? "+" : ""}{p.delta}
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {/* Bottom Performers */}
                {digest.bottom_performers?.length > 0 && (
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-widest text-red-400 mb-2">Needs Attention</p>
                    <div className="space-y-1.5">
                      {digest.bottom_performers.map((p, i) => (
                        <div key={i} className="flex items-center gap-2 rounded-[12px] bg-red-500/10 p-2.5" data-testid={`digest-bottom-${i}`}>
                          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-red-500/20 text-[10px] font-black text-red-400">{i + 1}</div>
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-bold text-[var(--foreground)] truncate">{p.crew}</p>
                            <p className="text-[9px] text-[var(--muted-foreground)]">{p.submissions} subs this week</p>
                          </div>
                          <div className="text-right shrink-0">
                            <p className="text-sm font-black text-red-400">{p.avg_score}</p>
                            {p.delta !== 0 && (
                              <p className={`text-[9px] font-bold ${p.delta > 0 ? "text-emerald-400" : "text-red-400"}`}>
                                {p.delta > 0 ? "+" : ""}{p.delta}
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Onboarding Progress Tracker */}
        {onboarding && onboarding.crews?.length > 0 && (
          <Card className="rounded-[24px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="widget-onboarding-tracker">
            <CardContent className="p-5">
              <div className="flex items-center gap-2 mb-4">
                <Target className="h-4 w-4 text-[#38a89d]" />
                <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Crew Onboarding Progress</p>
              </div>
              <div className="space-y-3">
                {onboarding.crews.map((crew, i) => (
                  <div key={i} className="rounded-[14px] bg-[var(--accent)] p-3" data-testid={`onboarding-crew-${i}`}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-bold text-[var(--foreground)] truncate">{crew.crew_label}</p>
                        <p className="text-[10px] text-[var(--muted-foreground)]">{crew.leader_name} — {crew.division}</p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className={`text-sm font-black ${crew.progress_pct === 100 ? "text-emerald-400" : crew.progress_pct >= 50 ? "text-[#f59e0b]" : "text-red-400"}`}>
                          {crew.progress_pct}%
                        </span>
                      </div>
                    </div>
                    <div className="h-2 w-full rounded-full bg-[var(--border)] overflow-hidden mb-2">
                      <div className="h-full rounded-full transition-all" style={{ width: `${crew.progress_pct}%`, backgroundColor: crew.progress_pct === 100 ? "#34d399" : crew.progress_pct >= 50 ? "#f59e0b" : "#ef4444" }} />
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {onboarding.milestone_definitions.map(m => {
                        const done = crew.milestones[m.key]?.done;
                        return (
                          <span key={m.key} className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[9px] font-semibold ${done ? "bg-emerald-500/15 text-emerald-400" : "bg-[var(--border)] text-[var(--muted-foreground)]"}`} title={m.description}>
                            {done ? <CheckCircle2 className="h-2.5 w-2.5" /> : <CircleDot className="h-2.5 w-2.5" />}
                            {m.label}
                          </span>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Coaching Loop Report */}
        {coachingLoop && (
          <Card className="rounded-[24px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="widget-coaching-loop">
            <CardContent className="p-5">
              <div className="flex items-center gap-2 mb-4">
                <Target className="h-4 w-4 text-[#f06292]" />
                <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Coaching Completion Loop</p>
              </div>
              {/* Summary stats */}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 mb-4">
                <div className="rounded-[14px] bg-[var(--accent)] p-3 text-center">
                  <p className="text-2xl font-black text-[var(--foreground)]">{coachingLoop.summary.total_offenders}</p>
                  <p className="text-[9px] font-bold uppercase text-[var(--muted-foreground)]">Repeat Offenders</p>
                </div>
                <div className="rounded-[14px] bg-red-500/10 p-3 text-center">
                  <p className="text-2xl font-black text-red-400">{coachingLoop.summary.open_loops}</p>
                  <p className="text-[9px] font-bold uppercase text-[var(--muted-foreground)]">Open Loops</p>
                </div>
                <div className="rounded-[14px] bg-[#f59e0b]/10 p-3 text-center">
                  <p className="text-2xl font-black text-[#f59e0b]">{coachingLoop.summary.in_progress}</p>
                  <p className="text-[9px] font-bold uppercase text-[var(--muted-foreground)]">In Progress</p>
                </div>
                <div className="rounded-[14px] bg-emerald-500/10 p-3 text-center">
                  <p className="text-2xl font-black text-emerald-400">{coachingLoop.summary.closed_loops}</p>
                  <p className="text-[9px] font-bold uppercase text-[var(--muted-foreground)]">Closed</p>
                </div>
              </div>
              {coachingLoop.report.length > 0 && (
                <div className="space-y-2">
                  {coachingLoop.report.map((entry, i) => (
                    <div key={i} className="flex items-center gap-3 rounded-[12px] bg-[var(--accent)] p-2.5" data-testid={`coaching-entry-${i}`}>
                      <div className={`flex h-2.5 w-2.5 shrink-0 rounded-full ${entry.loop_status === "closed" ? "bg-emerald-400" : entry.loop_status === "in_progress" ? "bg-[#f59e0b]" : "bg-red-400"}`} />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-bold text-[var(--foreground)] truncate">{entry.crew_label}</p>
                        <p className="text-[9px] text-[var(--muted-foreground)]">{entry.division} — {entry.total_issues} issues</p>
                      </div>
                      <div className="flex gap-1 flex-wrap shrink-0">
                        {entry.top_issues.slice(0, 3).map(iss => (
                          <Badge key={iss.tag} className="border-0 bg-red-500/15 text-[8px] text-red-400">{iss.tag} ({iss.count})</Badge>
                        ))}
                      </div>
                      <Badge className={`border-0 text-[9px] font-bold ${entry.loop_status === "closed" ? "bg-emerald-500/15 text-emerald-400" : entry.loop_status === "in_progress" ? "bg-[#f59e0b]/15 text-[#f59e0b]" : "bg-red-500/15 text-red-400"}`}>
                        {entry.loop_status}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
              {coachingLoop.report.length === 0 && (
                <p className="text-center text-xs text-[var(--muted-foreground)] py-4">No repeat offenders detected in the last 180 days.</p>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
