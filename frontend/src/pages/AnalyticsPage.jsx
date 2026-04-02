import { useEffect, useMemo, useState } from "react";
import { BrainCircuit, Dice5, Loader2, Search, Sparkles, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { HelpPopover } from "@/components/common/HelpPopover";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { authGet } from "@/lib/api";


const PERIOD_OPTIONS = [
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
  { value: "quarterly", label: "Quarterly" },
  { value: "annual", label: "Annual" },
];


function VerticalBars({ data, valueKey, labelKey, testId }) {
  const maxValue = Math.max(...data.map((item) => item[valueKey] || 0), 1);
  return (
    <div className="grid h-[320px] grid-cols-3 items-end gap-4" data-testid={testId}>
      {data.map((item, index) => {
        const height = `${Math.max(((item[valueKey] || 0) / maxValue) * 100, 6)}%`;
        return (
          <div key={`${item[labelKey] || "bar"}-${index}`} className="flex h-full flex-col justify-end gap-3">
            <div className="flex-1 rounded-[24px] p-3" style={{ backgroundColor: "var(--heat-empty)" }}>
              <div className="flex h-full items-end justify-center rounded-[20px] px-3 pb-3" style={{ backgroundColor: "var(--chip-bg)" }}>
                <div className="w-full rounded-[18px]" style={{ height, backgroundColor: "var(--btn-accent)" }} />
              </div>
            </div>
            <div className="text-center">
              <p className="text-sm font-semibold text-[#243e36]">{item[labelKey]}</p>
              <p className="text-xs text-[#5c6d64]">{item[valueKey]}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}


function TrendBars({ data, testId }) {
  const maxValue = Math.max(...data.map((item) => item.count || 0), 1);
  return (
    <div className="flex h-[320px] items-end gap-4" data-testid={testId}>
      {data.map((item, index) => {
        const height = `${Math.max(((item.count || 0) / maxValue) * 100, 8)}%`;
        return (
          <div key={`${item.day}-${index}`} className="flex h-full flex-1 flex-col justify-end gap-3">
            <div className="flex-1 rounded-[24px] p-3" style={{ backgroundColor: "var(--heat-empty)" }}>
              <div className="flex h-full items-end rounded-[20px] px-3 pb-3" style={{ backgroundColor: "var(--chip-bg)" }}>
                <div className="w-full rounded-[18px]" style={{ height, backgroundColor: "var(--btn-accent)", opacity: 0.7 }} />
              </div>
            </div>
            <div className="text-center">
              <p className="text-xs font-semibold text-[#243e36]">{item.day}</p>
              <p className="text-xs text-[#5c6d64]">{item.count}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}


function HorizontalBars({ data, testId }) {
  const maxValue = Math.max(...data.map((item) => item.count || 0), 1);
  return (
    <div className="space-y-3" data-testid={testId}>
      {data.map((item, index) => (
        <div key={`${item.reason}-${index}`} className="rounded-[22px] p-4" style={{ backgroundColor: "var(--heat-empty)" }}>
          <div className="mb-2 flex items-center justify-between gap-3">
            <p className="text-sm font-semibold text-[#243e36]">{item.reason}</p>
            <p className="text-xs text-[#5c6d64]">{item.count}</p>
          </div>
          <div className="h-3 rounded-full" style={{ backgroundColor: "var(--chip-bg)" }}>
            <div className="h-3 rounded-full" style={{ width: `${Math.max(((item.count || 0) / maxValue) * 100, 6)}%`, backgroundColor: "var(--status-critical-text)", opacity: 0.6 }} />
          </div>
        </div>
      ))}
    </div>
  );
}


export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState(null);
  const [period, setPeriod] = useState("monthly");
  const [loading, setLoading] = useState(true);

  // Random sampling state
  const [sampleData, setSampleData] = useState(null);
  const [sampleLoading, setSampleLoading] = useState(false);
  const [sampleSize, setSampleSize] = useState(10);
  const [filterCrew, setFilterCrew] = useState("");
  const [filterDivision, setFilterDivision] = useState("");
  const [filterService, setFilterService] = useState("");

  // Variance drilldown state
  const [drilldown, setDrilldown] = useState(null);
  const [drilldownLoading, setDrilldownLoading] = useState(false);

  useEffect(() => {
    const loadAnalytics = async () => {
      setLoading(true);
      const response = await authGet(`/analytics/summary?period=${period}`);
      setAnalytics(response);
      setLoading(false);
    };
    loadAnalytics();
  }, [period]);

  const drawSample = async () => {
    setSampleLoading(true);
    const params = new URLSearchParams({ size: sampleSize, period });
    if (filterCrew) params.set("crew", filterCrew);
    if (filterDivision) params.set("division", filterDivision);
    if (filterService) params.set("service_type", filterService);
    const res = await authGet(`/analytics/random-sample?${params}`);
    setSampleData(res);
    setSampleLoading(false);
  };

  const openDrilldown = async (crew, serviceType) => {
    setDrilldownLoading(true);
    const params = new URLSearchParams({ crew, service_type: serviceType, period });
    const res = await authGet(`/analytics/variance-drilldown?${params}`);
    setDrilldown(res);
    setDrilldownLoading(false);
  };

  // Load filter options on mount
  useEffect(() => {
    drawSample();
  }, []);

  const heatmapRows = useMemo(
    () => Array.from(new Set((analytics?.calibration_heatmap || []).map((item) => item.crew))),
    [analytics],
  );
  const heatmapColumns = useMemo(
    () => Array.from(new Set((analytics?.calibration_heatmap || []).map((item) => item.service_type))),
    [analytics],
  );
  const maxVariance = Math.max(...(analytics?.calibration_heatmap || []).map((item) => item.variance_average || 0), 1);
  const getHeatCell = (crew, serviceType) => analytics?.calibration_heatmap?.find((item) => item.crew === crew && item.service_type === serviceType);

  if (loading || !analytics) {
    return <div className="rounded-[28px] border border-border bg-white p-10 text-center text-[#243e36]" data-testid="analytics-loading-state">Loading analytics...</div>;
  }

  return (
    <div className="space-y-6" data-testid="analytics-page">
      <div className="flex flex-wrap gap-2" data-testid="analytics-period-tabs">
        {PERIOD_OPTIONS.map((option) => (
          <Button
            key={option.value}
            type="button"
            variant={period === option.value ? "default" : "outline"}
            size="sm"
            onClick={() => setPeriod(option.value)}
            className="h-10 rounded-full px-4"
            style={period === option.value ? { backgroundColor: "var(--btn-accent)", color: "#fff" } : {}}
            data-testid={`analytics-period-button-${option.value}`}
          >
            {option.label}
          </Button>
        ))}
      </div>

      <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="analytics-hero-card">
        <CardContent className="p-8">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Owner calibration dashboard</p>
          <h2 className="mt-3 font-[Cabinet_Grotesk] text-4xl font-black tracking-tight text-[#111815]">Owner-only calibration, reviewer drift, and training signal quality by {analytics.period_label.toLowerCase()} window.</h2>
          <p className="mt-2 flex items-center gap-1.5 text-sm text-[#5c6d64]">
            <HelpPopover title="Analytics & calibration guide">
              <p className="mb-2"><strong>What this page shows:</strong></p>
              <ul className="mb-2 list-inside list-disc space-y-1 text-xs">
                <li><strong>Score by crew</strong> — average review score per crew, ranked highest to lowest</li>
                <li><strong>Variance</strong> — the gap between management and owner scores (lower = better calibration)</li>
                <li><strong>Fail reasons</strong> — most common issues flagged across all reviews</li>
                <li><strong>Volume trends</strong> — submission count over time, bucketed by period</li>
                <li><strong>Random sample</strong> — draw a random subset for spot-check review</li>
                <li><strong>Calibration heatmap</strong> — click a cell to drill into individual submissions</li>
              </ul>
            </HelpPopover>
          </p>
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            <div className="rounded-[28px] border border-border p-5" style={{ backgroundColor: "var(--heat-empty)" }} data-testid="analytics-approved-card">
              <p className="text-sm text-[#5c6d64]">Training-approved records</p>
              <p className="mt-3 font-[Cabinet_Grotesk] text-5xl font-black text-[#111815]" data-testid="analytics-approved-value">{analytics.training_approved_count}</p>
            </div>
            <div className="rounded-[28px] border border-border p-5" style={{ backgroundColor: "var(--heat-empty)" }} data-testid="analytics-variance-card">
              <p className="text-sm text-[#5c6d64]">Average score variance</p>
              <p className="mt-3 font-[Cabinet_Grotesk] text-5xl font-black text-[#111815]" data-testid="analytics-variance-value">{analytics.score_variance_average}</p>
            </div>
            <div className="rounded-[28px] border border-border p-5" style={{ backgroundColor: "var(--heat-empty)" }} data-testid="analytics-fail-reasons-card">
              <p className="text-sm text-[#5c6d64]">Tracked fail reasons</p>
              <p className="mt-3 font-[Cabinet_Grotesk] text-5xl font-black text-[#111815]" data-testid="analytics-fail-reasons-value">{analytics.fail_reason_frequency.length}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="analytics-crew-chart-card">
          <CardContent className="p-8">
            <h3 className="font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]">Average score by crew</h3>
            <div className="mt-6"><VerticalBars data={analytics.average_score_by_crew} valueKey="average_score" labelKey="crew" testId="analytics-crew-bars" /></div>
          </CardContent>
        </Card>
        <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="analytics-volume-chart-card">
          <CardContent className="p-8">
            <h3 className="font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]">Submission volume trends</h3>
            <div className="mt-6"><TrendBars data={analytics.submission_volume_trends} testId="analytics-volume-bars" /></div>
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="analytics-fail-chart-card">
        <CardContent className="p-8">
          <h3 className="font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]">Fail reason frequency</h3>
          <div className="mt-6"><HorizontalBars data={analytics.fail_reason_frequency} testId="analytics-fail-bars" /></div>
        </CardContent>
      </Card>

      {/* Random Sampling */}
      <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="analytics-sampling-card">
        <CardContent className="p-8">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Spot check</p>
          <div className="mt-2 flex flex-wrap items-end gap-3">
            <h3 className="font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]">Random sampling</h3>
            <HelpPopover title="Random sampling" side="right">
              <p className="text-xs">Draw a random subset of submissions for spot-check review. Use the filters to narrow by crew, division, or service type. Each draw is independent — click again for a new random set.</p>
            </HelpPopover>
          </div>

          <div className="mt-5 flex flex-wrap items-end gap-3">
            <div className="min-w-[130px]">
              <label className="mb-1 block text-xs font-semibold text-[#5f7464]">Crew</label>
              <Select value={filterCrew} onValueChange={setFilterCrew}>
                <SelectTrigger className="h-10 rounded-xl" data-testid="sample-filter-crew"><SelectValue placeholder="All crews" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">All crews</SelectItem>
                  {(sampleData?.filter_options?.crews || []).map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="min-w-[130px]">
              <label className="mb-1 block text-xs font-semibold text-[#5f7464]">Division</label>
              <Select value={filterDivision} onValueChange={setFilterDivision}>
                <SelectTrigger className="h-10 rounded-xl" data-testid="sample-filter-division"><SelectValue placeholder="All divisions" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">All divisions</SelectItem>
                  {(sampleData?.filter_options?.divisions || []).map((d) => <SelectItem key={d} value={d}>{d}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="min-w-[130px]">
              <label className="mb-1 block text-xs font-semibold text-[#5f7464]">Service type</label>
              <Select value={filterService} onValueChange={setFilterService}>
                <SelectTrigger className="h-10 rounded-xl" data-testid="sample-filter-service"><SelectValue placeholder="All types" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">All types</SelectItem>
                  {(sampleData?.filter_options?.service_types || []).map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="min-w-[80px]">
              <label className="mb-1 block text-xs font-semibold text-[#5f7464]">Sample size</label>
              <Select value={String(sampleSize)} onValueChange={(v) => setSampleSize(Number(v))}>
                <SelectTrigger className="h-10 rounded-xl" data-testid="sample-filter-size"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {[5, 10, 20, 30, 50].map((n) => <SelectItem key={n} value={String(n)}>{n}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <Button type="button" onClick={drawSample} disabled={sampleLoading} className="h-10 rounded-xl text-white" style={{ backgroundColor: "var(--btn-accent)" }} data-testid="sample-draw-button">
              {sampleLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Dice5 className="mr-2 h-4 w-4" />}Draw sample
            </Button>
          </div>

          {sampleData && (
            <div className="mt-5" data-testid="sample-results">
              <p className="mb-3 text-xs font-semibold" style={{ color: "var(--tier-desc-text)" }}>
                Showing {sampleData.sample_size} of {sampleData.pool_size} eligible submissions
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm" data-testid="sample-table">
                  <thead>
                    <tr className="border-b border-border text-left">
                      <th className="px-3 py-2 text-xs font-bold uppercase" style={{ color: "var(--tier-desc-text)" }}>Crew</th>
                      <th className="px-3 py-2 text-xs font-bold uppercase" style={{ color: "var(--tier-desc-text)" }}>Service</th>
                      <th className="px-3 py-2 text-xs font-bold uppercase" style={{ color: "var(--tier-desc-text)" }}>Mgmt</th>
                      <th className="px-3 py-2 text-xs font-bold uppercase" style={{ color: "var(--tier-desc-text)" }}>Owner</th>
                      <th className="px-3 py-2 text-xs font-bold uppercase" style={{ color: "var(--tier-desc-text)" }}>Variance</th>
                      <th className="px-3 py-2 text-xs font-bold uppercase" style={{ color: "var(--tier-desc-text)" }}>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sampleData.samples.map((row) => {
                      const absV = Math.abs(row.variance ?? 0);
                      const vColor = absV > 15 ? "var(--status-critical-text)" : absV > 8 ? "var(--status-warning-text)" : "var(--status-watch-text)";
                      return (
                        <tr key={row.submission_id} className="border-b border-border/40">
                          <td className="px-3 py-2 font-medium text-[#243e36]">{row.crew}</td>
                          <td className="px-3 py-2 text-[#5c6d64]">{row.service_type}</td>
                          <td className="px-3 py-2 text-[#243e36]">{row.management_score ?? "—"}</td>
                          <td className="px-3 py-2 text-[#243e36]">{row.owner_score ?? "—"}</td>
                          <td className="px-3 py-2 font-bold" style={{ color: row.variance != null ? vColor : "var(--tier-desc-text)" }}>{row.variance ?? "—"}</td>
                          <td className="px-3 py-2">
                            <Badge className="border-0 text-[10px]" style={{ backgroundColor: "var(--chip-bg)", color: "var(--tier-desc-text)" }}>{row.status}</Badge>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Calibration Heatmap with clickable drilldown */}
      <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="analytics-heatmap-card">
        <CardContent className="p-8">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Calibration heatmap</p>
          <h3 className="mt-2 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]">Click a cell to drill into individual submissions</h3>
          <div className="mt-5 grid gap-4 rounded-[24px] border border-border p-5 lg:grid-cols-[1fr_1fr]" style={{ backgroundColor: "var(--heat-empty)" }} data-testid="analytics-heatmap-legend">
            <div>
              <p className="text-sm font-semibold text-[#243e36]">Metric key</p>
              <div className="mt-3 space-y-2 text-sm text-[#5c6d64]">
                <p>&#916; = average variance between management and owner scores</p>
                <p>M = management score average</p>
                <p>O = owner score average</p>
                <p>Samples = total reviewed records in that crew/service group</p>
              </div>
            </div>
            <div>
              <p className="text-sm font-semibold text-[#243e36]">Color key</p>
              <div className="mt-3 flex flex-wrap gap-3 text-sm text-[#5c6d64]">
                <div className="flex items-center gap-2"><span className="h-4 w-4 rounded-full" style={{ backgroundColor: `rgba(var(--heat-r),var(--heat-g),var(--heat-b),0.18)` }} />Low variance</div>
                <div className="flex items-center gap-2"><span className="h-4 w-4 rounded-full" style={{ backgroundColor: `rgba(var(--heat-r),var(--heat-g),var(--heat-b),0.42)` }} />Moderate variance</div>
                <div className="flex items-center gap-2"><span className="h-4 w-4 rounded-full" style={{ backgroundColor: `rgba(var(--heat-r),var(--heat-g),var(--heat-b),0.72)` }} />High variance</div>
              </div>
            </div>
          </div>
          <div className="mt-6 overflow-x-auto">
            <div className="grid min-w-[720px] gap-3" style={{ gridTemplateColumns: `180px repeat(${Math.max(heatmapColumns.length, 1)}, minmax(140px, 1fr))` }} data-testid="analytics-heatmap-grid">
              <div />
              {heatmapColumns.map((column, columnIndex) => (
                <div key={`${column}-${columnIndex}`} className="rounded-2xl px-3 py-2 text-sm font-semibold" style={{ backgroundColor: "var(--chip-bg)", color: "var(--tier-desc-text)" }} data-testid={`analytics-heatmap-column-${column.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}`}>{column}</div>
              ))}
              {heatmapRows.map((crew, crewIndex) => (
                <div key={`${crew}-${crewIndex}`} className="contents">
                  <div className="rounded-2xl px-3 py-3 text-sm font-semibold text-white" style={{ backgroundColor: "var(--btn-accent)" }} data-testid={`analytics-heatmap-row-${crew.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}`}>{crew}</div>
                  {heatmapColumns.map((column, columnIndex) => {
                    const cell = getHeatCell(crew, column);
                    const intensity = cell ? Math.min((cell.variance_average || 0) / maxVariance, 1) : 0;
                    const background = cell
                      ? `rgba(var(--heat-r),var(--heat-g),var(--heat-b),${(0.12 + intensity * 0.6).toFixed(2)})`
                      : "var(--heat-empty)";
                    return (
                      <button
                        key={`${crew}-${column}-${columnIndex}`}
                        type="button"
                        className="cursor-pointer rounded-2xl border border-border px-3 py-4 text-left text-sm transition hover:ring-2 hover:ring-[var(--btn-accent)]/30"
                        style={{ background }}
                        onClick={() => cell && openDrilldown(crew, column)}
                        data-testid={`analytics-heatmap-cell-${crew.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}-${column.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}`}
                      >
                        {cell ? (
                          <>
                            <p className="font-semibold text-[#243e36]">&#916; {cell.variance_average}</p>
                            <p className="mt-1 text-xs text-[#41534a]">M {cell.management_average} &middot; O {cell.owner_average}</p>
                            <p className="mt-1 text-xs text-[#41534a]">{cell.sample_count} samples</p>
                          </>
                        ) : (
                          <p className="text-xs text-[#7d8b84]">No data</p>
                        )}
                      </button>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>

          {/* Variance Drilldown Panel */}
          {drilldownLoading && <p className="mt-4 text-center text-sm text-[#5c6d64]">Loading drilldown...</p>}
          {drilldown && !drilldownLoading && (
            <div className="mt-6 rounded-[24px] border border-border p-5" style={{ backgroundColor: "var(--heat-empty)" }} data-testid="variance-drilldown-panel">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.2em]" style={{ color: "var(--tier-desc-text)" }}>Variance drilldown</p>
                  <h4 className="mt-1 font-[Cabinet_Grotesk] text-xl font-bold text-[#111815]">{drilldown.crew} &mdash; {drilldown.service_type}</h4>
                  <p className="text-xs" style={{ color: "var(--tier-desc-text)" }}>{drilldown.total_reviewed} reviewed submissions, sorted by largest variance</p>
                </div>
                <Button type="button" variant="ghost" size="sm" onClick={() => setDrilldown(null)} data-testid="drilldown-close"><X className="h-4 w-4" /></Button>
              </div>
              {drilldown.rows.length > 0 ? (
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full text-sm" data-testid="drilldown-table">
                    <thead>
                      <tr className="border-b border-border text-left">
                        <th className="px-3 py-2 text-xs font-bold uppercase" style={{ color: "var(--tier-desc-text)" }}>Date</th>
                        <th className="px-3 py-2 text-xs font-bold uppercase" style={{ color: "var(--tier-desc-text)" }}>Mgmt Score</th>
                        <th className="px-3 py-2 text-xs font-bold uppercase" style={{ color: "var(--tier-desc-text)" }}>Owner Score</th>
                        <th className="px-3 py-2 text-xs font-bold uppercase" style={{ color: "var(--tier-desc-text)" }}>Variance</th>
                        <th className="px-3 py-2 text-xs font-bold uppercase" style={{ color: "var(--tier-desc-text)" }}>Rating</th>
                        <th className="px-3 py-2 text-xs font-bold uppercase" style={{ color: "var(--tier-desc-text)" }}>Training</th>
                        <th className="px-3 py-2 text-xs font-bold uppercase" style={{ color: "var(--tier-desc-text)" }}>Issues</th>
                      </tr>
                    </thead>
                    <tbody>
                      {drilldown.rows.map((row) => {
                        const absV = Math.abs(row.variance ?? 0);
                        const vColor = absV > 15 ? "var(--status-critical-text)" : absV > 8 ? "var(--status-warning-text)" : "var(--status-watch-text)";
                        return (
                          <tr key={row.submission_id} className="border-b border-border/40">
                            <td className="px-3 py-2 text-[#5c6d64]">{row.created_at?.slice(0, 10) || "—"}</td>
                            <td className="px-3 py-2 text-[#243e36]">{row.management_score ?? "—"}</td>
                            <td className="px-3 py-2 text-[#243e36]">{row.owner_score ?? "—"}</td>
                            <td className="px-3 py-2 font-bold" style={{ color: row.variance != null ? vColor : "var(--tier-desc-text)" }}>{row.variance ?? "—"}</td>
                            <td className="px-3 py-2 text-[#5c6d64]">{row.management_rating || "—"}</td>
                            <td className="px-3 py-2">
                              <Badge className="border-0 text-[10px]" style={{
                                backgroundColor: row.owner_training === "approved" ? "var(--status-watch-bg)" : row.owner_training === "excluded" ? "var(--status-critical-bg)" : "var(--chip-bg)",
                                color: row.owner_training === "approved" ? "var(--status-watch-text)" : row.owner_training === "excluded" ? "var(--status-critical-text)" : "var(--tier-desc-text)",
                              }}>{row.owner_training || "pending"}</Badge>
                            </td>
                            <td className="px-3 py-2 text-xs text-[#5c6d64]">{(row.management_issues || []).join(", ") || "—"}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="mt-4 text-sm text-[#5c6d64]">No reviewed submissions found for this crew/service combination in the current period.</p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* AI-Assisted Scoring — Placeholder */}
      <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="analytics-ai-placeholder-card">
        <CardContent className="p-8">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl" style={{ backgroundColor: "var(--panel-gradient-from)" }}>
              <Sparkles className="h-5 w-5" style={{ color: "var(--btn-accent)" }} />
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Coming soon</p>
              <h3 className="mt-1 font-[Cabinet_Grotesk] text-xl font-bold tracking-tight text-[#111815]">AI-assisted scoring & quality checks</h3>
            </div>
          </div>
          <p className="mt-4 text-sm leading-relaxed" style={{ color: "var(--tier-desc-text)" }}>
            Automated quality analysis using the rubric dataset and photo submissions you're building.
            AI will pre-score incoming submissions, flag quality anomalies, and surface calibration drift
            before management review — reducing manual effort while maintaining grading accuracy.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Badge className="border-0" style={{ backgroundColor: "var(--chip-bg)", color: "var(--tier-desc-text)" }}>
              <BrainCircuit className="mr-1 h-3 w-3" />Auto-grading
            </Badge>
            <Badge className="border-0" style={{ backgroundColor: "var(--chip-bg)", color: "var(--tier-desc-text)" }}>
              <Search className="mr-1 h-3 w-3" />Anomaly detection
            </Badge>
            <Badge className="border-0" style={{ backgroundColor: "var(--chip-bg)", color: "var(--tier-desc-text)" }}>
              <Sparkles className="mr-1 h-3 w-3" />Calibration drift alerts
            </Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
