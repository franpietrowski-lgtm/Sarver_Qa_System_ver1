import { useCallback, useEffect, useRef, useState } from "react";
import { Download, FileText, Search, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { authGet } from "@/lib/api";
import { toast } from "sonner";


const PERIODS = [
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
  { value: "quarterly", label: "Quarterly" },
];


export default function ClientReportPage({ user }) {
  const [period, setPeriod] = useState("monthly");
  const [jobQuery, setJobQuery] = useState("");
  const [jobResults, setJobResults] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [searching, setSearching] = useState(false);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const searchRef = useRef(null);

  // Close dropdown on click outside
  useEffect(() => {
    const handler = (e) => {
      if (searchRef.current && !searchRef.current.contains(e.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const loadReport = useCallback(async (p, jobId) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ period: p, job_id: jobId || "all" });
      const data = await authGet(`/reports/client-quality?${params}`);
      setReport(data);
    } catch {
      toast.error("Failed to load report data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadReport(period, selectedJob?.id || "all");
  }, [period, selectedJob, loadReport]);

  const searchJobs = useCallback(async (q) => {
    setSearching(true);
    try {
      const data = await authGet(`/reports/job-search?q=${encodeURIComponent(q)}`);
      setJobResults(data.results || []);
      setShowDropdown(true);
    } catch {
      setJobResults([]);
    } finally {
      setSearching(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (jobQuery.length >= 1) {
        searchJobs(jobQuery);
      } else if (jobQuery.length === 0) {
        searchJobs("");
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [jobQuery, searchJobs]);

  const handleSelectJob = (job) => {
    setSelectedJob(job);
    setJobQuery(job.job_name || job.property_name || job.job_id);
    setShowDropdown(false);
  };

  const handleClearJob = () => {
    setSelectedJob(null);
    setJobQuery("");
    setShowDropdown(false);
  };

  const handleExportPdf = async () => {
    setExporting(true);
    try {
      const token = localStorage.getItem("field-quality-token");
      const params = new URLSearchParams({ period, job_id: selectedJob?.id || "all" });
      const url = `${process.env.REACT_APP_BACKEND_URL}/api/exports/am-report-pdf?${params}`;
      const resp = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
      if (!resp.ok) throw new Error("Export failed");
      const blob = await resp.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `SarverLandscape_ClientReport_${period}.pdf`;
      a.click();
      URL.revokeObjectURL(a.href);
      toast.success("PDF downloaded");
    } catch {
      toast.error("PDF export failed");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-5" data-testid="client-report-page">
      <Card className="overflow-hidden rounded-[24px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="client-report-header">
        <CardContent className="p-5 lg:p-6">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]" data-testid="client-report-kicker">Account Management</p>
          <h2 className="mt-2 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[var(--foreground)] lg:text-4xl" data-testid="client-report-title">Client Quality Report</h2>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[var(--muted-foreground)]" data-testid="client-report-description">
            Search by job, cycle through timeframes, preview data, and export PDF reports for client delivery.
          </p>
        </CardContent>
      </Card>

      {/* Controls Row */}
      <div className="grid gap-3 sm:grid-cols-[1fr_auto_auto]" data-testid="client-report-controls">
        {/* Job Search */}
        <div className="relative" ref={searchRef} data-testid="client-report-job-search-wrapper">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--muted-foreground)]" />
            <Input
              value={jobQuery}
              onChange={(e) => setJobQuery(e.target.value)}
              onFocus={() => { if (jobResults.length || jobQuery === "") searchJobs(jobQuery); }}
              placeholder="Search by job name, property, or ID..."
              className="h-12 rounded-2xl border-border bg-[var(--card)] pl-10 pr-10 text-sm text-[var(--foreground)]"
              data-testid="client-report-job-search-input"
            />
            {selectedJob && (
              <button
                type="button"
                onClick={handleClearJob}
                className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full p-1 hover:bg-[var(--accent)]"
                data-testid="client-report-clear-job-btn"
              >
                <X className="h-4 w-4 text-[var(--muted-foreground)]" />
              </button>
            )}
          </div>
          {showDropdown && jobResults.length > 0 && (
            <div
              className="absolute left-0 right-0 top-full z-30 mt-1 max-h-64 overflow-y-auto rounded-2xl border border-border bg-[var(--card)] shadow-xl"
              data-testid="client-report-job-dropdown"
            >
              {jobResults.map((job) => (
                <button
                  key={job.id}
                  type="button"
                  onClick={() => handleSelectJob(job)}
                  className="flex w-full items-center gap-3 px-4 py-3 text-left transition hover:bg-[var(--accent)]"
                  data-testid={`client-report-job-option-${job.id}`}
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-[var(--foreground)]">{job.job_name || job.property_name}</p>
                    <p className="text-[10px] text-[var(--muted-foreground)]">{job.job_id} · {job.division} · {job.service_type}</p>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Timeframe Cycling */}
        <div className="flex items-center gap-1 rounded-2xl border border-border bg-[var(--card)] p-1" data-testid="client-report-timeframe-selector">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              type="button"
              onClick={() => setPeriod(p.value)}
              className={`rounded-xl px-4 py-2.5 text-xs font-bold transition ${
                period === p.value
                  ? "bg-[#243e36] text-white shadow-sm"
                  : "text-[var(--muted-foreground)] hover:bg-[var(--accent)]"
              }`}
              data-testid={`client-report-period-${p.value}`}
            >
              {p.label}
            </button>
          ))}
        </div>

        {/* Export Button */}
        <Button
          onClick={handleExportPdf}
          disabled={exporting || loading}
          className="h-12 gap-2 rounded-2xl bg-[#243e36] px-5 text-sm font-bold text-white hover:bg-[#1a2c26]"
          data-testid="client-report-export-pdf-btn"
        >
          <Download className="h-4 w-4" />
          {exporting ? "Exporting..." : "Export PDF"}
        </Button>
      </div>

      {/* Active Filters */}
      <div className="flex flex-wrap items-center gap-2" data-testid="client-report-active-filters">
        <Badge className="border-0 bg-[var(--accent)] px-3 py-1 text-xs font-semibold text-[var(--foreground)]" data-testid="client-report-period-badge">
          {PERIODS.find((p) => p.value === period)?.label || period}
        </Badge>
        {selectedJob && (
          <Badge className="border-0 bg-[#243e36]/10 px-3 py-1 text-xs font-semibold text-[var(--foreground)]" data-testid="client-report-job-badge">
            Job: {selectedJob.job_name || selectedJob.property_name}
          </Badge>
        )}
        {report && (
          <span className="text-xs text-[var(--muted-foreground)]" data-testid="client-report-summary-text">
            {report.total_properties} properties · {report.total_submissions} submissions
          </span>
        )}
      </div>

      {/* Loading State */}
      {loading && (
        <div className="py-12 text-center" data-testid="client-report-loading">
          <p className="text-sm text-[var(--muted-foreground)] animate-pulse">Loading report data...</p>
        </div>
      )}

      {/* Report Preview */}
      {!loading && report && report.properties?.length > 0 && (
        <div className="space-y-4" data-testid="client-report-preview">
          {/* Summary Table */}
          <Card className="rounded-[24px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="client-report-summary-table-card">
            <CardContent className="p-5">
              <div className="flex items-center gap-2 mb-4">
                <FileText className="h-4 w-4 text-[var(--foreground)]" />
                <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Executive Summary</p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm" data-testid="client-report-summary-table">
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
                    {report.properties.map((p, i) => (
                      <tr key={i} className="border-b border-border/30" data-testid={`client-report-property-row-${i}`}>
                        <td className="py-2.5 font-medium text-[var(--foreground)] text-xs">{p.property}</td>
                        <td className="py-2.5 text-center text-xs text-[var(--foreground)]">{p.submissions_count}</td>
                        <td className="py-2.5 text-center text-xs font-black text-[var(--foreground)]">{p.avg_score}</td>
                        <td className="py-2.5 text-center text-xs text-emerald-400">{p.pass_count}</td>
                        <td className="py-2.5 text-center text-xs text-red-400">{p.fail_count}</td>
                        <td className="py-2.5">
                          <div className="flex gap-1 flex-wrap">
                            {p.divisions.map((d) => (
                              <Badge key={d} className="border-0 bg-[var(--accent)] text-[9px] text-[var(--foreground)]">{d}</Badge>
                            ))}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* Per-Property Detail Cards */}
          {report.properties.map((prop, pi) => (
            <Card key={pi} className="rounded-[24px] border-border/80 bg-[var(--card)] shadow-sm" data-testid={`client-report-property-detail-${pi}`}>
              <CardContent className="p-5">
                <div className="flex items-center justify-between gap-3 mb-3">
                  <div>
                    <h3 className="font-[Outfit] text-lg font-bold text-[var(--foreground)]">{prop.property}</h3>
                    <p className="text-xs text-[var(--muted-foreground)]">
                      {prop.submissions_count} submissions · Avg: {prop.avg_score} · Pass: {prop.pass_count} · Fail: {prop.fail_count}
                    </p>
                  </div>
                  <div className="flex gap-1 flex-wrap shrink-0">
                    {prop.divisions.map((d) => (
                      <Badge key={d} className="border-0 bg-[var(--accent)] text-[9px] text-[var(--foreground)]">{d}</Badge>
                    ))}
                  </div>
                </div>

                <div className="space-y-2">
                  {prop.submissions.slice(0, 5).map((sub, si) => (
                    <div key={si} className="rounded-[14px] border border-border bg-[var(--accent)] p-3" data-testid={`client-report-sub-${pi}-${si}`}>
                      <div className="flex items-center justify-between gap-2">
                        <div className="min-w-0">
                          <p className="text-xs font-semibold text-[var(--foreground)] truncate">
                            {sub.crew_label} · {sub.division} · {sub.service_type}
                          </p>
                          <p className="text-[10px] text-[var(--muted-foreground)]">
                            Truck: {sub.truck_number} · Area: {sub.area_tag} · {sub.work_date}
                          </p>
                        </div>
                        {sub.management_review && (
                          <div className="text-right shrink-0">
                            <p className={`text-sm font-black ${
                              sub.management_review.verdict?.toLowerCase().includes("pass") ? "text-emerald-400" :
                              sub.management_review.verdict?.toLowerCase().includes("fail") ? "text-red-400" :
                              "text-[var(--foreground)]"
                            }`}>
                              {sub.management_review.score || "-"}
                            </p>
                            <p className="text-[9px] text-[var(--muted-foreground)]">{sub.management_review.verdict}</p>
                          </div>
                        )}
                      </div>
                      {sub.note && (
                        <p className="mt-1.5 text-[10px] italic text-[var(--muted-foreground)]">"{sub.note}"</p>
                      )}
                      {sub.photos?.length > 0 && (
                        <p className="mt-1 text-[9px] text-[var(--muted-foreground)]">{sub.photos.length} photo(s) attached</p>
                      )}
                    </div>
                  ))}
                  {prop.submissions.length > 5 && (
                    <p className="text-center text-[10px] text-[var(--muted-foreground)] py-1">
                      +{prop.submissions.length - 5} more submissions (visible in PDF)
                    </p>
                  )}
                </div>

                {prop.equipment_logs?.length > 0 && (
                  <div className="mt-3 border-t border-border/60 pt-3">
                    <p className="text-[10px] font-bold uppercase text-[var(--muted-foreground)] mb-1.5">Equipment Logs ({prop.equipment_logs.length})</p>
                    {prop.equipment_logs.slice(0, 3).map((eq, ei) => (
                      <div key={ei} className="flex items-center gap-2 text-[10px] text-[var(--muted-foreground)]">
                        <span className="font-bold text-[var(--foreground)]">{eq.equipment_number}</span>
                        {eq.red_tag && <Badge className="border-0 bg-red-500/15 text-[8px] text-red-400">RED TAG</Badge>}
                        <span className="truncate">{eq.notes}</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && report && report.properties?.length === 0 && (
        <Card className="rounded-[24px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="client-report-empty">
          <CardContent className="flex flex-col items-center gap-3 py-16">
            <FileText className="h-10 w-10 text-[var(--muted-foreground)]" />
            <p className="text-sm font-semibold text-[var(--foreground)]">No data for this timeframe</p>
            <p className="text-xs text-[var(--muted-foreground)]">Try a wider timeframe or clear the job filter.</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
