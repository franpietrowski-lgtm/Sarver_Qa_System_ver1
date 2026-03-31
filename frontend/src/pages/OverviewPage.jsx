import { Activity, Boxes, FolderInput, ShieldCheck, Smartphone, UploadCloud, Zap } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import StatCard from "@/components/common/StatCard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { authGet } from "@/lib/api";


export default function OverviewPage({ user }) {
  const [overview, setOverview] = useState(null);
  const [submissions, setSubmissions] = useState([]);

  useEffect(() => {
    const load = async () => {
      const [overviewResponse, submissionsResponse] = await Promise.all([
        authGet("/dashboard/overview"),
        authGet("/submissions?scope=all&page=1&limit=6"),
      ]);
      setOverview(overviewResponse);
      setSubmissions(submissionsResponse.items || []);
    };

    load();
  }, []);

  if (!overview) {
    return <div className="rounded-[28px] border border-border bg-white p-10 text-center text-[#243e36]" data-testid="overview-loading-state">Loading overview...</div>;
  }

  const storage = overview.storage || overview.drive;

  const stats = [
    { icon: Activity, label: "Submissions", value: overview.totals.submissions, hint: "All captured proof records", testId: "overview-stat-submissions" },
    { icon: FolderInput, label: "Imported jobs", value: overview.totals.jobs, hint: "Alignment records available for admin review", testId: "overview-stat-jobs" },
    { icon: ShieldCheck, label: "Owner queue", value: overview.queues.owner, hint: "Items needing final calibration", testId: "overview-stat-owner-queue" },
    { icon: UploadCloud, label: "Export ready", value: overview.queues.export_ready, hint: "Records ready for dataset packaging", testId: "overview-stat-export-ready" },
  ];

  return (
    <div className="space-y-6" data-testid="overview-page">
      <Card className="overflow-hidden rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="overview-hero-card">
        <CardContent className="grid gap-6 p-8 lg:grid-cols-[1.2fr_0.8fr] lg:p-10">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]" data-testid="overview-kicker-text">Operations pulse</p>
            <h2 className="mt-3 font-[Cabinet_Grotesk] text-5xl font-black tracking-tight text-[#111815]" data-testid="overview-title">Keep crews fast. Keep labels consistent. Keep training data clean.</h2>
            <p className="mt-4 max-w-3xl text-sm leading-6 text-[#5c6d64]" data-testid="overview-description">This workspace gives {user?.role} users a shared view of capture volume, review queues, storage readiness, and export momentum.</p>
          </div>
          <div className="grid gap-4 rounded-[28px] border border-border bg-[#edf0e7] p-6" data-testid="overview-workflow-health-card">
            <div>
              <p className="text-sm font-semibold text-[#243e36]">Review velocity</p>
              <p className="mt-2 font-[Cabinet_Grotesk] text-5xl font-black text-[#111815]" data-testid="overview-review-velocity-value">{overview.workflow_health.review_velocity_percent}%</p>
              <p className="mt-2 text-sm text-[#5c6d64]" data-testid="overview-review-velocity-hint">Share of captured work already moving through review and export stages.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge className="border-0 bg-white px-3 py-1 text-[#243e36]" data-testid="overview-drive-config-badge">Storage configured: {storage?.configured ? "Yes" : "No"}</Badge>
              <Badge className="border-0 bg-white px-3 py-1 text-[#243e36]" data-testid="overview-drive-connected-badge">Storage ready: {storage?.connected ? "Yes" : "No"}</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {stats.map((item) => <StatCard key={item.label} {...item} />)}
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="overview-recent-submissions-card">
          <CardContent className="p-6 sm:p-8">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Recent submissions</p>
                <h3 className="mt-2 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]">Current field activity</h3>
              </div>
              <Boxes className="h-6 w-6 text-[#243e36]" />
            </div>

            <div className="mt-6 space-y-3">
              {submissions.map((submission) => (
                <div key={submission.id} className="rounded-[26px] border border-border bg-[#f6f6f2] p-4" data-testid={`overview-submission-card-${submission.id}`}>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-[#243e36]" data-testid={`overview-submission-job-${submission.id}`}>{submission.job_name_input || submission.job_id || submission.submission_code}</p>
                      <p className="mt-1 text-sm text-[#5c6d64]" data-testid={`overview-submission-meta-${submission.id}`}>{submission.crew_label} · {submission.truck_number} · {submission.service_type}</p>
                    </div>
                    <Badge className="border-0 bg-white px-3 py-1 text-[#243e36]" data-testid={`overview-submission-status-${submission.id}`}>{submission.status}</Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-[32px] border-border/80 bg-[#243e36] text-white shadow-sm" data-testid="overview-lifecycle-card">
          <CardContent className="p-6 sm:p-8">
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#d8f3dc]">Workflow lifecycle</p>
            <h3 className="mt-2 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight">Submission state machine</h3>
            <div className="mt-6 space-y-3">
              {["Draft", "Submitted", "Pending Match", "Ready for Review", "Management Reviewed", "Owner Reviewed", "Finalized", "Export Ready", "Exported"].map((step, index) => (
                <div key={step} className="flex items-center gap-4 rounded-[24px] border border-white/10 bg-white/5 px-4 py-3" data-testid={`overview-lifecycle-step-${index + 1}`}>
                  <div className="flex h-9 w-9 items-center justify-center rounded-full bg-white/10 text-sm font-bold">{index + 1}</div>
                  <p className="text-sm font-semibold text-white/90">{step}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="overview-rapid-review-launch-card">
        <CardContent className="flex flex-wrap items-center justify-between gap-4 p-6 sm:p-8">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Rapid review lane</p>
            <h3 className="mt-2 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]">Open the swipe lane for quick admin image qualification.</h3>
            <p className="mt-2 text-sm text-[#5c6d64]">Use the desktop lane or jump straight into the mobile-focused link version.</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button asChild className="h-11 rounded-2xl bg-[#243e36] hover:bg-[#1a2c26]" data-testid="overview-open-rapid-review-button">
              <Link to="/rapid-review"><Zap className="mr-2 h-4 w-4" />Open rapid review</Link>
            </Button>
            <Button asChild variant="outline" className="h-11 rounded-2xl border-[#243e36]/15 bg-white text-[#243e36] hover:bg-[#edf0e7]" data-testid="overview-open-mobile-rapid-review-button">
              <Link to="/rapid-review/mobile"><Smartphone className="mr-2 h-4 w-4" />Open mobile link</Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}