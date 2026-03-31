import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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
      {data.map((item) => {
        const height = `${Math.max(((item[valueKey] || 0) / maxValue) * 100, 6)}%`;
        return (
          <div key={item[labelKey]} className="flex h-full flex-col justify-end gap-3">
            <div className="flex-1 rounded-[24px] bg-[#f6f6f2] p-3">
              <div className="flex h-full items-end justify-center rounded-[20px] bg-[#edf0e7] px-3 pb-3">
                <div className="w-full rounded-[18px] bg-[#243e36]" style={{ height }} />
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
      {data.map((item) => {
        const height = `${Math.max(((item.count || 0) / maxValue) * 100, 8)}%`;
        return (
          <div key={item.day} className="flex h-full flex-1 flex-col justify-end gap-3">
            <div className="flex-1 rounded-[24px] bg-[#f6f6f2] p-3">
              <div className="flex h-full items-end rounded-[20px] bg-[#edf0e7] px-3 pb-3">
                <div className="w-full rounded-[18px] bg-[#7ca982]" style={{ height }} />
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
      {data.map((item) => (
        <div key={item.reason} className="rounded-[22px] bg-[#f6f6f2] p-4">
          <div className="mb-2 flex items-center justify-between gap-3">
            <p className="text-sm font-semibold text-[#243e36]">{item.reason}</p>
            <p className="text-xs text-[#5c6d64]">{item.count}</p>
          </div>
          <div className="h-3 rounded-full bg-[#edf0e7]">
            <div className="h-3 rounded-full bg-[#e07a5f]" style={{ width: `${Math.max(((item.count || 0) / maxValue) * 100, 6)}%` }} />
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

  useEffect(() => {
    const loadAnalytics = async () => {
      setLoading(true);
      const response = await authGet(`/analytics/summary?period=${period}`);
      setAnalytics(response);
      setLoading(false);
    };

    loadAnalytics();
  }, [period]);

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
            variant="outline"
            onClick={() => setPeriod(option.value)}
            className={`h-10 rounded-full px-4 ${period === option.value ? "border-[#243e36] bg-[#243e36] text-white hover:bg-[#1a2c26]" : "border-[#243e36]/10 bg-white text-[#243e36] hover:bg-[#edf0e7]"}`}
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
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            <div className="rounded-[28px] border border-border bg-[#f6f6f2] p-5" data-testid="analytics-approved-card">
              <p className="text-sm text-[#5c6d64]">Training-approved records</p>
              <p className="mt-3 font-[Cabinet_Grotesk] text-5xl font-black text-[#111815]" data-testid="analytics-approved-value">{analytics.training_approved_count}</p>
            </div>
            <div className="rounded-[28px] border border-border bg-[#f6f6f2] p-5" data-testid="analytics-variance-card">
              <p className="text-sm text-[#5c6d64]">Average score variance</p>
              <p className="mt-3 font-[Cabinet_Grotesk] text-5xl font-black text-[#111815]" data-testid="analytics-variance-value">{analytics.score_variance_average}</p>
            </div>
            <div className="rounded-[28px] border border-border bg-[#f6f6f2] p-5" data-testid="analytics-fail-reasons-card">
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
            <div className="mt-6" data-testid="analytics-crew-chart">
              <VerticalBars data={analytics.average_score_by_crew} valueKey="average_score" labelKey="crew" testId="analytics-crew-bars" />
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="analytics-volume-chart-card">
          <CardContent className="p-8">
            <h3 className="font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]">Submission volume trends</h3>
            <div className="mt-6" data-testid="analytics-volume-chart">
              <TrendBars data={analytics.submission_volume_trends} testId="analytics-volume-bars" />
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="analytics-fail-chart-card">
        <CardContent className="p-8">
          <h3 className="font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]">Fail reason frequency</h3>
          <div className="mt-6" data-testid="analytics-fail-chart">
            <HorizontalBars data={analytics.fail_reason_frequency} testId="analytics-fail-bars" />
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="analytics-heatmap-card">
        <CardContent className="p-8">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Calibration heatmap</p>
          <h3 className="mt-2 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]">Where reviewer calibration varies by crew and service</h3>
          <div className="mt-5 grid gap-4 rounded-[24px] border border-border bg-[#f6f6f2] p-5 lg:grid-cols-[1fr_1fr]" data-testid="analytics-heatmap-legend">
            <div>
              <p className="text-sm font-semibold text-[#243e36]">Metric key</p>
              <div className="mt-3 space-y-2 text-sm text-[#5c6d64]">
                <p>Δ = average variance between management and owner scores</p>
                <p>M = management score average</p>
                <p>O = owner score average</p>
                <p>Samples = total reviewed records in that crew/service group</p>
              </div>
            </div>
            <div>
              <p className="text-sm font-semibold text-[#243e36]">Color key</p>
              <div className="mt-3 flex flex-wrap gap-3 text-sm text-[#5c6d64]">
                <div className="flex items-center gap-2"><span className="h-4 w-4 rounded-full bg-[rgba(224,122,95,0.18)]" />Low variance</div>
                <div className="flex items-center gap-2"><span className="h-4 w-4 rounded-full bg-[rgba(224,122,95,0.42)]" />Moderate variance</div>
                <div className="flex items-center gap-2"><span className="h-4 w-4 rounded-full bg-[rgba(224,122,95,0.72)]" />High variance</div>
              </div>
            </div>
          </div>
          <div className="mt-6 overflow-x-auto">
            <div className="grid min-w-[720px] gap-3" style={{ gridTemplateColumns: `180px repeat(${Math.max(heatmapColumns.length, 1)}, minmax(140px, 1fr))` }} data-testid="analytics-heatmap-grid">
              <div />
              {heatmapColumns.map((column) => (
                <div key={column} className="rounded-2xl bg-[#edf0e7] px-3 py-2 text-sm font-semibold text-[#243e36]" data-testid={`analytics-heatmap-column-${column.replace(/[^a-z0-9]+/gi, '-').toLowerCase()}`}>{column}</div>
              ))}
              {heatmapRows.map((crew) => (
                <div key={crew} className="contents">
                  <div className="rounded-2xl bg-[#243e36] px-3 py-3 text-sm font-semibold text-white" data-testid={`analytics-heatmap-row-${crew.replace(/[^a-z0-9]+/gi, '-').toLowerCase()}`}>{crew}</div>
                  {heatmapColumns.map((column) => {
                    const cell = getHeatCell(crew, column);
                    const intensity = cell ? Math.min((cell.variance_average || 0) / maxVariance, 1) : 0;
                    const background = cell ? `rgba(224, 122, 95, ${0.12 + intensity * 0.6})` : "#f6f6f2";
                    return (
                      <div key={`${crew}-${column}`} className="rounded-2xl border border-border px-3 py-4 text-sm" style={{ background }} data-testid={`analytics-heatmap-cell-${crew.replace(/[^a-z0-9]+/gi, '-').toLowerCase()}-${column.replace(/[^a-z0-9]+/gi, '-').toLowerCase()}`}>
                        {cell ? (
                          <>
                            <p className="font-semibold text-[#243e36]">Δ {cell.variance_average}</p>
                            <p className="mt-1 text-xs text-[#41534a]">M {cell.management_average} · O {cell.owner_average}</p>
                            <p className="mt-1 text-xs text-[#41534a]">{cell.sample_count} samples</p>
                          </>
                        ) : (
                          <p className="text-xs text-[#7d8b84]">No data</p>
                        )}
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}