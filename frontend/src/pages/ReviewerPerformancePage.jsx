import { useEffect, useState } from "react";
import { Activity, BarChart3, Clock, Gauge, ShieldAlert, TrendingUp, Users, Zap } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { HelpPopover } from "@/components/common/HelpPopover";
import { authGet } from "@/lib/api";


const RATING_COLORS = {
  fail: { bg: "var(--status-critical-bg)", text: "var(--status-critical-text)", label: "Fail" },
  concern: { bg: "var(--status-warning-bg)", text: "var(--status-warning-text)", label: "Concern" },
  standard: { bg: "var(--status-watch-bg)", text: "var(--status-watch-text)", label: "Standard" },
  exemplary: { bg: "var(--chip-bg)", text: "var(--tier-desc-text)", label: "Exemplary" },
};

const PERIOD_OPTIONS = [
  { value: 30, label: "30 days" },
  { value: 90, label: "90 days" },
  { value: 180, label: "6 months" },
  { value: 365, label: "1 year" },
];


function StatTile({ icon: Icon, label, value, sub, testId }) {
  return (
    <div className="rounded-2xl border border-border p-4" style={{ backgroundColor: "var(--heat-empty)" }} data-testid={testId}>
      <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em]" style={{ color: "var(--tier-desc-text)" }}>
        <Icon className="h-3.5 w-3.5" />{label}
      </div>
      <p className="mt-2 font-[Cabinet_Grotesk] text-2xl font-black text-[#243e36]">{value}</p>
      {sub && <p className="mt-0.5 text-xs" style={{ color: "var(--tier-desc-text)" }}>{sub}</p>}
    </div>
  );
}


function RatingBar({ distribution, total }) {
  if (!total) return <p className="text-xs" style={{ color: "var(--tier-desc-text)" }}>No reviews</p>;
  return (
    <div className="space-y-1.5" data-testid="reviewer-rating-bar">
      {["exemplary", "standard", "concern", "fail"].map((key) => {
        const count = distribution[key] || 0;
        const pct = Math.round((count / total) * 100);
        const cfg = RATING_COLORS[key];
        return (
          <div key={key} className="flex items-center gap-2">
            <span className="w-16 text-right text-[10px] font-semibold" style={{ color: cfg.text }}>{cfg.label}</span>
            <div className="h-2.5 flex-1 overflow-hidden rounded-full" style={{ backgroundColor: "var(--heat-empty)" }}>
              <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: cfg.text, opacity: 0.7 }} />
            </div>
            <span className="w-10 text-right text-[10px] font-semibold" style={{ color: "var(--tier-desc-text)" }}>{pct}%</span>
          </div>
        );
      })}
    </div>
  );
}


function SpeedTrend({ trend }) {
  if (!trend || !trend.length) return <p className="text-xs" style={{ color: "var(--tier-desc-text)" }}>No trend data</p>;
  const maxMs = Math.max(...trend.map((t) => t.avg_ms), 1);
  return (
    <div className="flex items-end gap-1" style={{ height: "60px" }} data-testid="reviewer-speed-trend">
      {trend.map((point, i) => {
        const h = Math.max((point.avg_ms / maxMs) * 100, 8);
        const isFast = point.avg_ms < 4000;
        return (
          <div key={i} className="group relative flex-1">
            <div
              className="w-full rounded-t-sm transition-all"
              style={{ height: `${h}%`, backgroundColor: isFast ? "var(--status-critical-text)" : "var(--btn-accent)", opacity: 0.7 }}
              title={`${point.week}: ${(point.avg_ms / 1000).toFixed(1)}s avg (${point.count} reviews)`}
            />
          </div>
        );
      })}
    </div>
  );
}


function DriftGauge({ drift, direction }) {
  const maxDrift = 30;
  const clampedDrift = Math.min(drift, maxDrift);
  const pct = (clampedDrift / maxDrift) * 100;
  const isHigh = drift > 15;
  const isMod = drift > 8;
  const color = isHigh ? "var(--status-critical-text)" : isMod ? "var(--status-warning-text)" : "var(--status-watch-text)";
  const label = isHigh ? "High" : isMod ? "Moderate" : "Low";
  const arrow = direction > 2 ? "Lenient" : direction < -2 ? "Strict" : "Aligned";

  return (
    <div data-testid="reviewer-drift-gauge">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold" style={{ color }}>{label} ({drift}pt)</span>
        <span className="text-[10px] font-semibold" style={{ color: "var(--tier-desc-text)" }}>{arrow}</span>
      </div>
      <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full" style={{ backgroundColor: "var(--heat-empty)" }}>
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
    </div>
  );
}


export default function ReviewerPerformancePage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(90);

  const load = async () => {
    setLoading(true);
    try {
      const res = await authGet(`/analytics/reviewer-performance?days=${days}`);
      setData(res);
    } catch { /* ignore */ }
    setLoading(false);
  };

  useEffect(() => { load(); }, [days]);

  const reviewers = data?.reviewers || [];
  const totalReviews = reviewers.reduce((s, r) => s + r.total_reviews, 0);
  const totalSessions = reviewers.reduce((s, r) => s + r.session_count, 0);
  const avgSpeed = reviewers.length
    ? Math.round(reviewers.reduce((s, r) => s + r.avg_swipe_ms, 0) / reviewers.length)
    : 0;

  return (
    <div className="space-y-6" data-testid="reviewer-performance-page">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Analytics</p>
        <div className="mt-2 flex flex-wrap items-end gap-3">
          <h2 className="font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]">
            Reviewer Performance
          </h2>
          <HelpPopover title="Reviewer Performance" content="Tracks per-reviewer swipe speed, rating patterns, and calibration drift against owner scores." />
        </div>
        <p className="mt-1 text-sm text-[#41534a]">Speed trends, accuracy patterns, and calibration drift per reviewer.</p>
      </div>

      {/* Period selector */}
      <div className="flex flex-wrap gap-2" data-testid="reviewer-period-selector">
        {PERIOD_OPTIONS.map((opt) => (
          <Button
            key={opt.value}
            type="button"
            variant={days === opt.value ? "default" : "outline"}
            size="sm"
            className="h-8 rounded-xl text-xs"
            style={days === opt.value ? { backgroundColor: "var(--btn-accent)", color: "#fff" } : {}}
            onClick={() => setDays(opt.value)}
            data-testid={`reviewer-period-${opt.value}`}
          >
            {opt.label}
          </Button>
        ))}
      </div>

      {loading ? (
        <p className="text-center text-sm text-[#5c6d64]">Loading reviewer data...</p>
      ) : (
        <>
          {/* Summary stats */}
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatTile icon={Users} label="Reviewers" value={reviewers.length} sub={`${PERIOD_OPTIONS.find((o) => o.value === days)?.label} window`} testId="stat-reviewer-count" />
            <StatTile icon={BarChart3} label="Total Reviews" value={totalReviews} sub={`${totalSessions} sessions`} testId="stat-total-reviews" />
            <StatTile icon={Clock} label="Avg Speed" value={avgSpeed ? `${(avgSpeed / 1000).toFixed(1)}s` : "—"} sub="per image swipe" testId="stat-avg-speed" />
            <StatTile icon={Gauge} label="Active Reviewers" value={reviewers.filter((r) => r.session_count > 0).length} sub="with sessions" testId="stat-active-reviewers" />
          </div>

          {/* Per-reviewer cards */}
          <div className="space-y-4" data-testid="reviewer-card-list">
            {reviewers.map((reviewer) => (
              <Card key={reviewer.reviewer_id} className="rounded-[20px] border-border/60 shadow-sm" data-testid={`reviewer-card-${reviewer.reviewer_id}`}>
                <CardContent className="p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h3 className="font-[Cabinet_Grotesk] text-lg font-bold text-[#111815]">{reviewer.name}</h3>
                      <p className="text-sm text-[#5c6d64]">{reviewer.title}</p>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      <Badge className="border-0" style={{ backgroundColor: "var(--chip-bg)", color: "var(--tier-desc-text)" }}>
                        <Activity className="mr-1 h-3 w-3" />{reviewer.total_reviews} reviews
                      </Badge>
                      <Badge className="border-0" style={{ backgroundColor: "var(--chip-bg)", color: "var(--tier-desc-text)" }}>
                        <Zap className="mr-1 h-3 w-3" />{reviewer.session_count} sessions
                      </Badge>
                      {reviewer.flagged_fast_pct > 20 && (
                        <Badge className="border-0" style={{ backgroundColor: "var(--status-critical-bg)", color: "var(--status-critical-text)" }}>
                          <ShieldAlert className="mr-1 h-3 w-3" />{reviewer.flagged_fast_pct}% fast
                        </Badge>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    {/* Speed */}
                    <div className="rounded-2xl border border-border p-3" style={{ backgroundColor: "var(--heat-empty)" }}>
                      <p className="text-[10px] font-bold uppercase tracking-[0.2em]" style={{ color: "var(--tier-desc-text)" }}>Avg Speed</p>
                      <p className="mt-1 text-xl font-black text-[#243e36]">
                        {reviewer.avg_swipe_ms ? `${(reviewer.avg_swipe_ms / 1000).toFixed(1)}s` : "—"}
                      </p>
                      <p className="text-[10px]" style={{ color: "var(--tier-desc-text)" }}>{reviewer.flagged_fast_count} flagged fast</p>
                    </div>

                    {/* Rating Distribution */}
                    <div className="rounded-2xl border border-border p-3" style={{ backgroundColor: "var(--heat-empty)" }}>
                      <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.2em]" style={{ color: "var(--tier-desc-text)" }}>Rating Spread</p>
                      <RatingBar distribution={reviewer.rating_distribution} total={reviewer.total_reviews} />
                    </div>

                    {/* Speed Trend */}
                    <div className="rounded-2xl border border-border p-3" style={{ backgroundColor: "var(--heat-empty)" }}>
                      <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.2em]" style={{ color: "var(--tier-desc-text)" }}>
                        <TrendingUp className="mr-1 inline h-3 w-3" />Speed Trend
                      </p>
                      <SpeedTrend trend={reviewer.speed_trend} />
                    </div>

                    {/* Calibration Drift */}
                    <div className="rounded-2xl border border-border p-3" style={{ backgroundColor: "var(--heat-empty)" }}>
                      <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.2em]" style={{ color: "var(--tier-desc-text)" }}>
                        Calibration Drift
                      </p>
                      <DriftGauge drift={reviewer.calibration_drift} direction={reviewer.drift_direction} />
                      <p className="mt-1 text-[10px]" style={{ color: "var(--tier-desc-text)" }}>
                        Avg score: {reviewer.avg_score}%
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
            {reviewers.length === 0 && (
              <Card className="rounded-[20px]">
                <CardContent className="p-8 text-center">
                  <Users className="mx-auto h-8 w-8 text-[#5c6d64]" />
                  <p className="mt-3 text-sm text-[#5c6d64]">No reviewer data for this period.</p>
                </CardContent>
              </Card>
            )}
          </div>
        </>
      )}
    </div>
  );
}
