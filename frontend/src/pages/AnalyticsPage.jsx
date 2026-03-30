import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Card, CardContent } from "@/components/ui/card";
import { authGet } from "@/lib/api";


export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState(null);

  useEffect(() => {
    authGet("/analytics/summary").then(setAnalytics);
  }, []);

  if (!analytics) {
    return <div className="rounded-[28px] border border-border bg-white p-10 text-center text-[#243e36]" data-testid="analytics-loading-state">Loading analytics...</div>;
  }

  const heatmapRows = Array.from(new Set((analytics.calibration_heatmap || []).map((item) => item.crew)));
  const heatmapColumns = Array.from(new Set((analytics.calibration_heatmap || []).map((item) => item.service_type)));
  const maxVariance = Math.max(...(analytics.calibration_heatmap || []).map((item) => item.variance_average || 0), 1);
  const getHeatCell = (crew, serviceType) => analytics.calibration_heatmap.find((item) => item.crew === crew && item.service_type === serviceType);

  return (
    <div className="space-y-6" data-testid="analytics-page">
      <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="analytics-hero-card">
        <CardContent className="p-8">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Owner calibration dashboard</p>
          <h2 className="mt-3 font-[Cabinet_Grotesk] text-4xl font-black tracking-tight text-[#111815]">Owner-only calibration, reviewer drift, and training signal quality.</h2>
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
            <div className="mt-6 h-[320px]" data-testid="analytics-crew-chart">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={analytics.average_score_by_crew}>
                  <CartesianGrid stroke="#e2e2dc" vertical={false} />
                  <XAxis dataKey="crew" tick={{ fill: "#41534a", fontSize: 12 }} />
                  <YAxis tick={{ fill: "#41534a", fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="average_score" fill="#243e36" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="analytics-volume-chart-card">
          <CardContent className="p-8">
            <h3 className="font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]">Submission volume trends</h3>
            <div className="mt-6 h-[320px]" data-testid="analytics-volume-chart">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={analytics.submission_volume_trends}>
                  <CartesianGrid stroke="#e2e2dc" vertical={false} />
                  <XAxis dataKey="day" tick={{ fill: "#41534a", fontSize: 12 }} />
                  <YAxis tick={{ fill: "#41534a", fontSize: 12 }} />
                  <Tooltip />
                  <Line type="monotone" dataKey="count" stroke="#7ca982" strokeWidth={3} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="analytics-fail-chart-card">
        <CardContent className="p-8">
          <h3 className="font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]">Fail reason frequency</h3>
          <div className="mt-6 h-[320px]" data-testid="analytics-fail-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={analytics.fail_reason_frequency}>
                <CartesianGrid stroke="#e2e2dc" vertical={false} />
                <XAxis dataKey="reason" tick={{ fill: "#41534a", fontSize: 12 }} interval={0} angle={-20} textAnchor="end" height={80} />
                <YAxis tick={{ fill: "#41534a", fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#e07a5f" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="analytics-heatmap-card">
        <CardContent className="p-8">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Calibration heatmap</p>
          <h3 className="mt-2 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]">Where reviewer calibration varies by crew and service</h3>
          <div className="mt-6 overflow-x-auto">
            <div className="grid min-w-[720px] gap-3" style={{ gridTemplateColumns: `180px repeat(${Math.max(heatmapColumns.length, 1)}, minmax(140px, 1fr))` }} data-testid="analytics-heatmap-grid">
              <div />
              {heatmapColumns.map((column) => (
                <div key={column} className="rounded-2xl bg-[#edf0e7] px-3 py-2 text-sm font-semibold text-[#243e36]" data-testid={`analytics-heatmap-column-${column.replace(/[^a-z0-9]+/gi, '-').toLowerCase()}`}>{column}</div>
              ))}
              {heatmapRows.map((crew) => (
                <div key={crew} className="contents">
                  <div key={`${crew}-label`} className="rounded-2xl bg-[#243e36] px-3 py-3 text-sm font-semibold text-white" data-testid={`analytics-heatmap-row-${crew.replace(/[^a-z0-9]+/gi, '-').toLowerCase()}`}>{crew}</div>
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