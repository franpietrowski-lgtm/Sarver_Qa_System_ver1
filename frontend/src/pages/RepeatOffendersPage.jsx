import { useEffect, useState } from "react";
import { AlertTriangle, Copy, Radar } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { authGet, authPost } from "@/lib/api";
import { toast } from "sonner";


export default function RepeatOffendersPage() {
  const [windowDays, setWindowDays] = useState(30);
  const [summary, setSummary] = useState(null);
  const [createdLinks, setCreatedLinks] = useState({});

  const loadData = async (nextWindow = windowDays) => {
    const response = await authGet(`/repeat-offenders?window_days=${nextWindow}&threshold_one=3&threshold_two=5&threshold_three=7`);
    setSummary(response);
  };

  useEffect(() => {
    loadData();
  }, []);

  const createTrainingSession = async (entry) => {
    try {
      const response = await authPost("/training-sessions", {
        access_code: entry.access_code,
        division: entry.division,
        item_count: 5,
      });
      setCreatedLinks((current) => ({ ...current, [entry.crew]: response.session_url }));
      toast.success("Training session created from repeat-offender view.");
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Unable to create training session");
    }
  };

  const copyLink = async (value) => {
    await navigator.clipboard.writeText(value);
    toast.success("Copied to clipboard.");
  };

  if (!summary) {
    return <div className="rounded-[28px] border border-border bg-white p-10 text-center text-[#243e36]" data-testid="repeat-offenders-loading-state">Loading repeat-offender tracking...</div>;
  }

  return (
    <div className="space-y-6" data-testid="repeat-offenders-page">
      <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="repeat-offenders-hero-card">
        <CardContent className="p-8">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Repeat offender tracking</p>
              <h1 className="mt-3 font-[Cabinet_Grotesk] text-4xl font-black tracking-tight text-[#111815]">Spot recurring quality misses, escalate them, and launch training fast.</h1>
            </div>
            <div className="flex items-center gap-3 rounded-[24px] bg-[#edf0e7] px-4 py-3">
              <Radar className="h-5 w-5 text-[#243e36]" />
              <Input type="number" min="7" max="365" value={windowDays} onChange={(event) => setWindowDays(Number(event.target.value) || 30)} className="h-10 w-28 rounded-xl border-transparent bg-white" data-testid="repeat-offenders-window-input" />
              <Button onClick={() => loadData(windowDays)} className="rounded-2xl bg-[#243e36] hover:bg-[#1a2c26]" data-testid="repeat-offenders-refresh-button">Refresh</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="repeat-offenders-heatmap-card">
        <CardContent className="p-8">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Heatmap</p>
          <div className="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-3" data-testid="repeat-offenders-heatmap-grid">
            {summary.heatmap.map((cell) => (
              <div key={`${cell.crew}-${cell.issue_type}`} className="rounded-[24px] border border-border bg-[#f6f6f2] p-4" data-testid={`repeat-offender-cell-${cell.crew.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}-${cell.issue_type.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}`}>
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-[#243e36]">{cell.crew}</p>
                  <Badge className="border-0 bg-white text-[#243e36]">{cell.count}</Badge>
                </div>
                <p className="mt-2 text-sm text-[#5c6d64]">{cell.issue_type}</p>
                <p className="mt-2 text-xs font-semibold uppercase tracking-[0.2em] text-[#8b4c4c]">{cell.level}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-2">
        {summary.crew_summaries.map((entry) => (
          <Card key={entry.crew} className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid={`repeat-offender-card-${entry.crew.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}`}>
            <CardContent className="p-8">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">{entry.division}</p>
                  <h2 className="mt-2 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]">{entry.crew}</h2>
                </div>
                <Badge className="border-0 bg-[#edf0e7] text-[#243e36]">{entry.incident_count} incidents</Badge>
              </div>
              <div className="mt-4 rounded-[24px] border border-[#ead2d2] bg-[#fbf0ef] p-4">
                <div className="flex items-center gap-2 text-sm font-semibold text-[#7a2323]"><AlertTriangle className="h-4 w-4" />{entry.level}</div>
                <p className="mt-2 text-sm text-[#5c6d64]">Top issue: {entry.top_issue_type}</p>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {Object.entries(entry.issue_types).map(([issue, count]) => <Badge key={issue} className="border-0 bg-[#edf0e7] text-[#243e36]">{issue} · {count}</Badge>)}
              </div>
              <div className="mt-4 rounded-[24px] border border-border bg-[#f6f6f2] p-4">
                <p className="text-sm font-semibold text-[#243e36]">Related submissions</p>
                <div className="mt-3 space-y-2">
                  {entry.related_submissions.map((item) => (
                    <div key={item.submission_id} className="rounded-2xl bg-white px-3 py-2 text-sm text-[#41534a]" data-testid={`repeat-offender-related-${item.submission_id}`}>{item.label}</div>
                  ))}
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-3">
                <Button onClick={() => createTrainingSession(entry)} className="rounded-2xl bg-[#243e36] hover:bg-[#1a2c26]" data-testid={`repeat-offender-create-training-${entry.crew.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}`}>Create training session</Button>
                {createdLinks[entry.crew] && <Button type="button" variant="outline" onClick={() => copyLink(createdLinks[entry.crew])} className="rounded-2xl border-[#243e36]/10 bg-white text-[#243e36] hover:bg-[#edf0e7]" data-testid={`repeat-offender-copy-training-${entry.crew.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}`}><Copy className="mr-2 h-4 w-4" />Copy training link</Button>}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}