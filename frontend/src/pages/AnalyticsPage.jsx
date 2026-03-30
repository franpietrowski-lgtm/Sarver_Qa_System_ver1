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

  return (
    <div className="space-y-6" data-testid="analytics-page">
      <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="analytics-hero-card">
        <CardContent className="p-8">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Analytics dashboard</p>
          <h2 className="mt-3 font-[Cabinet_Grotesk] text-4xl font-black tracking-tight text-[#111815]">Crew performance, reviewer variance, and training signal quality.</h2>
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
    </div>
  );
}