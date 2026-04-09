import { useEffect, useRef, useState } from "react";
import { AlertTriangle, BrainCircuit, ChevronDown, ChevronLeft, ChevronRight, Loader2, Radar } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Link, useNavigate } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { HelpPopover } from "@/components/common/HelpPopover";
import { authGet, authPost } from "@/lib/api";
import { toast } from "sonner";


const STANDARD_ACTIONS = {
  "Watch": "Monitor — crew flagged for awareness; include in next scheduled training rotation.",
  "Warning": "Corrective Training Required — auto-generate a focused training session covering the top issue type.",
  "Critical": "Escalation — suspend solo assignments, require ride-along supervision, and complete full retraining before returning to independent work.",
};


function CrewCarousel({ entries, onCreateTraining }) {
  const scrollRef = useRef(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  const checkScroll = () => {
    if (!scrollRef.current) return;
    const { scrollLeft, scrollWidth, clientWidth } = scrollRef.current;
    setCanScrollLeft(scrollLeft > 4);
    setCanScrollRight(scrollLeft + clientWidth < scrollWidth - 4);
  };

  useEffect(() => {
    checkScroll();
    const el = scrollRef.current;
    if (el) el.addEventListener("scroll", checkScroll, { passive: true });
    return () => el?.removeEventListener("scroll", checkScroll);
  }, [entries]);

  const scroll = (direction) => {
    if (!scrollRef.current) return;
    const amount = scrollRef.current.clientWidth * 0.72;
    scrollRef.current.scrollBy({ left: direction === "left" ? -amount : amount, behavior: "smooth" });
  };

  if (entries.length === 0) {
    return <p className="py-6 text-center text-sm text-[var(--muted-foreground)]" data-testid="crew-carousel-empty">No repeat offenders found in this window.</p>;
  }

  return (
    <div className="relative" data-testid="crew-recommendations-carousel">
      {canScrollLeft && (
        <button type="button" onClick={() => scroll("left")} className="absolute -left-2 top-1/2 z-10 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full border border-border bg-white shadow-md transition hover:bg-[#edf0e7]" data-testid="crew-carousel-prev"><ChevronLeft className="h-4 w-4 text-[#243e36]" /></button>
      )}
      {canScrollRight && (
        <button type="button" onClick={() => scroll("right")} className="absolute -right-2 top-1/2 z-10 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full border border-border bg-white shadow-md transition hover:bg-[#edf0e7]" data-testid="crew-carousel-next"><ChevronRight className="h-4 w-4 text-[#243e36]" /></button>
      )}
      <div ref={scrollRef} className="flex snap-x snap-mandatory gap-4 overflow-x-auto scroll-smooth pb-2" style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}>
        {entries.map((entry) => (
          <div key={entry.crew} className="w-[320px] flex-shrink-0 snap-start rounded-[28px] border border-border bg-[#f6f6f2] p-5" data-testid={`repeat-offender-card-${entry.crew.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}`}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">{entry.division}</p>
                <h3 className="mt-1 font-[Cabinet_Grotesk] text-xl font-black tracking-tight text-[var(--foreground)]">{entry.crew}</h3>
              </div>
              <Badge className="border-0 bg-white text-[#243e36]">{entry.incident_count}</Badge>
            </div>
            <div className="mt-3 rounded-[16px] border p-3" style={{ borderColor: `var(--status-${(entry.level || 'watch').toLowerCase()}-border)`, backgroundColor: `var(--status-${(entry.level || 'watch').toLowerCase()}-bg)` }}>
              <div className="flex items-center gap-2 text-xs font-semibold" style={{ color: `var(--status-${(entry.level || 'watch').toLowerCase()}-text)` }}><AlertTriangle className="h-3.5 w-3.5" />{entry.level}</div>
              <p className="mt-1 text-xs" style={{ color: 'var(--tier-desc-text)' }}>Top: {entry.top_issue_type}</p>
            </div>
            <div className="mt-3 rounded-[16px] border border-border bg-white p-3">
              <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted-foreground)]">Recommended action</p>
              <p className="mt-1 text-xs leading-relaxed text-[#41534a]">{STANDARD_ACTIONS[entry.level] || STANDARD_ACTIONS["Watch"]}</p>
            </div>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {Object.entries(entry.issue_types).map(([issue, count]) => <Badge key={issue} className="border-0 bg-white text-[10px] text-[#243e36]">{issue} · {count}</Badge>)}
            </div>
            <Button onClick={() => onCreateTraining(entry)} className="mt-4 h-9 w-full rounded-xl bg-[var(--btn-accent)] text-xs hover:bg-[var(--btn-accent-hover)]" data-testid={`repeat-offender-create-training-${entry.crew.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}`}>Create training session</Button>
            <p className="mt-2 text-center text-[10px] text-[var(--muted-foreground)]">View generated session in Standards Library.</p>
          </div>
        ))}
      </div>
    </div>
  );
}


export default function RepeatOffendersPage() {
  const [windowDays, setWindowDays] = useState(30);
  const [summary, setSummary] = useState(null);
  const [heatmapOpen, setHeatmapOpen] = useState(false);
  const [coachLoading, setCoachLoading] = useState(false);
  const [coachResult, setCoachResult] = useState(null);
  const navigate = useNavigate();

  const loadData = async (nextWindow = windowDays) => {
    const response = await authGet(`/repeat-offenders?window_days=${nextWindow}&threshold_one=3&threshold_two=5&threshold_three=7`);
    setSummary(response);
  };

  useEffect(() => {
    loadData();
  }, []);

  const createTrainingSession = async (entry) => {
    try {
      await authPost("/training-sessions", {
        access_code: entry.access_code,
        division: entry.division,
        item_count: 5,
      });
      toast.success("Training session created. Navigate to Standards Library to copy the session link.");
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Unable to create training session");
    }
  };

  const runAutoCoach = async () => {
    setCoachLoading(true);
    setCoachResult(null);
    try {
      const result = await authPost(`/coaching/auto-generate?window_days=${windowDays}`);
      setCoachResult(result);
      if (result.generated > 0) {
        toast.success(`${result.generated} coaching session(s) generated.`);
      } else {
        toast.info("No new coaching sessions needed — all crews already have active sessions or no eligible standards.");
      }
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Unable to auto-generate coaching");
    }
    setCoachLoading(false);
  };

  if (!summary) {
    return <div className="rounded-[28px] border border-border bg-white p-10 text-center text-[#243e36]" data-testid="repeat-offenders-loading-state">Loading repeat-offender tracking...</div>;
  }

  return (
    <div className="space-y-5" data-testid="repeat-offenders-page">
      <Card className="rounded-[32px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="repeat-offenders-hero-card">
        <CardContent className="p-6 lg:p-8">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Repeat offender tracking</p>
              <h1 className="mt-3 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[var(--foreground)] lg:text-4xl">Spot recurring quality misses, escalate them, and launch training fast.</h1>
              <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[var(--muted-foreground)]">
                The window below sets the look-back period in days. Incidents within this range are aggregated per crew.
                <HelpPopover title="Repeat offender tracking">
                  <p className="mb-2"><strong>How thresholds work:</strong></p>
                  <ul className="mb-2 list-inside list-disc space-y-1 text-xs">
                    <li><strong>Watch (3+)</strong> — crew flagged for awareness; include in next training rotation</li>
                    <li><strong>Warning (5+)</strong> — corrective training required; auto-generate a focused session</li>
                    <li><strong>Critical (7+)</strong> — escalation: suspend solo work, require ride-along, full retraining</li>
                  </ul>
                  <p className="mb-2 font-semibold">Using the heatmap:</p>
                  <p className="mb-2 text-xs">The collapsible heatmap below shows issue density across crews and time buckets. Darker cells = more incidents.</p>
                  <p className="font-semibold">Creating training:</p>
                  <p className="text-xs">Click "Create training session" on any crew card to auto-generate a quiz targeting their division's standards.</p>
                </HelpPopover>
              </p>
            </div>
            <div className="flex items-center gap-3 rounded-[24px] bg-[#edf0e7] px-4 py-3">
              <Radar className="h-5 w-5 text-[#243e36]" />
              <div>
                <label className="mb-1 block text-[10px] font-bold uppercase tracking-widest text-[var(--muted-foreground)]">Days</label>
                <Input type="number" min="7" max="365" value={windowDays} onChange={(event) => setWindowDays(Number(event.target.value) || 30)} className="h-10 w-28 rounded-xl border-transparent bg-white" data-testid="repeat-offenders-window-input" />
              </div>
              <Button onClick={() => loadData(windowDays)} className="rounded-2xl bg-[var(--btn-accent)] hover:bg-[var(--btn-accent-hover)]" data-testid="repeat-offenders-refresh-button">Refresh</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Standard Courses of Action */}
      <Card className="rounded-[32px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="repeat-offenders-actions-card">
        <CardContent className="p-6 lg:p-8">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Standard courses of action</p>
          <p className="mt-2 text-sm text-[var(--muted-foreground)]">These are the default escalation responses assigned when a crew reaches each threshold tier.</p>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {Object.entries(STANDARD_ACTIONS).map(([level, description]) => (
                <div key={level} className="rounded-[20px] border p-4" style={{
                  backgroundColor: `var(--status-${level.toLowerCase()}-bg)`,
                  borderColor: `var(--status-${level.toLowerCase()}-border)`,
                }} data-testid={`action-tier-${level.toLowerCase()}`}>
                  <p className="text-sm font-bold" style={{ color: `var(--status-${level.toLowerCase()}-text)` }}>{level}</p>
                  <p className="mt-2 text-xs leading-relaxed" style={{ color: 'var(--tier-desc-text)' }}>{description}</p>
                </div>
              ))}
          </div>
        </CardContent>
      </Card>

      {/* Closed-Loop Auto-Coaching */}
      <Card className="rounded-[32px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="repeat-offenders-coaching-card">
        <CardContent className="p-6 lg:p-8">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Closed-loop coaching</p>
              <p className="mt-2 text-sm text-[var(--muted-foreground)]">
                Auto-generate training sessions for all crews at Warning or Critical levels. Sessions are pre-loaded with standards matching each crew's division.
                <HelpPopover title="Closed-loop coaching" side="right">
                  <p className="mb-2 text-xs">Clicking "Auto-Coach" reads the current repeat offender data, identifies crews at Warning (5+ incidents) or Critical (7+ incidents), and creates a training session for each one.</p>
                  <p className="mb-2 text-xs"><strong>Critical crews</strong> get 5 training items. <strong>Warning crews</strong> get 3.</p>
                  <p className="text-xs">Crews that already have an active coaching session are skipped to avoid duplicates.</p>
                </HelpPopover>
              </p>
            </div>
            <Button
              type="button"
              onClick={runAutoCoach}
              disabled={coachLoading}
              className="rounded-2xl text-white"
              style={{ backgroundColor: "var(--btn-accent)" }}
              data-testid="auto-coach-button"
            >
              {coachLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <BrainCircuit className="mr-2 h-4 w-4" />}
              Auto-Coach
            </Button>
          </div>

          {coachResult && (
            <div className="mt-4 space-y-3" data-testid="auto-coach-results">
              <div className="flex flex-wrap gap-2">
                <Badge className="border-0" style={{ backgroundColor: "var(--status-watch-bg)", color: "var(--status-watch-text)" }}>
                  {coachResult.generated} generated
                </Badge>
                {coachResult.skipped > 0 && (
                  <Badge className="border-0" style={{ backgroundColor: "var(--status-warning-bg)", color: "var(--status-warning-text)" }}>
                    {coachResult.skipped} skipped
                  </Badge>
                )}
              </div>
              {coachResult.sessions?.length > 0 && (
                <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
                  {coachResult.sessions.map((s) => (
                    <div key={s.session_id} className="rounded-2xl border border-border p-3" style={{ backgroundColor: "var(--heat-empty)" }} data-testid={`coach-session-${s.session_id}`}>
                      <p className="text-sm font-semibold text-[#243e36]">{s.crew}</p>
                      <p className="mt-0.5 text-xs font-bold" style={{ color: `var(--status-${s.level.toLowerCase()}-text)` }}>{s.level}</p>
                      <p className="mt-1 text-xs" style={{ color: "var(--tier-desc-text)" }}>{s.item_count} items &middot; {s.top_issues.join(", ")}</p>
                    </div>
                  ))}
                </div>
              )}
              {coachResult.skipped_details?.length > 0 && (
                <details className="text-xs" style={{ color: "var(--tier-desc-text)" }}>
                  <summary className="cursor-pointer font-semibold">Skipped details</summary>
                  <ul className="mt-1 space-y-0.5 pl-4 list-disc">
                    {coachResult.skipped_details.map((s, i) => (
                      <li key={i}>{s.crew}: {s.reason}</li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Heatmap — Collapsible */}
      <Card className="rounded-[32px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="repeat-offenders-heatmap-card">
        <CardContent className="p-6 lg:p-8">
          <button type="button" onClick={() => setHeatmapOpen(!heatmapOpen)} className="flex w-full items-center justify-between gap-3 text-left" data-testid="repeat-offenders-heatmap-toggle">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Heatmap</p>
              <p className="mt-1 text-sm text-[var(--muted-foreground)]">{summary.heatmap.length} crew/issue combinations tracked</p>
            </div>
            <ChevronDown className={`h-5 w-5 text-[var(--muted-foreground)] transition-transform ${heatmapOpen ? "rotate-180" : ""}`} />
          </button>
          <AnimatePresence initial={false}>
            {heatmapOpen && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.25, ease: "easeInOut" }}
                className="overflow-hidden"
              >
                <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3" data-testid="repeat-offenders-heatmap-grid">
                  {summary.heatmap.map((cell) => (
                      <div key={`${cell.crew}-${cell.issue_type}`} className="rounded-[20px] border border-border p-4" style={{ backgroundColor: 'var(--heat-empty)' }} data-testid={`repeat-offender-cell-${cell.crew.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}-${cell.issue_type.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}`}>
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-sm font-semibold text-[#243e36]">{cell.crew}</p>
                          <Badge className="border-0 bg-white text-[#243e36]">{cell.count}</Badge>
                        </div>
                        <p className="mt-1.5 text-sm text-[var(--muted-foreground)]">{cell.issue_type}</p>
                        <p className="mt-1.5 text-xs font-semibold uppercase tracking-[0.2em]" style={{ color: `var(--status-${(cell.level || 'watch').toLowerCase()}-text)` }}>{cell.level}</p>
                      </div>
                    ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </CardContent>
      </Card>

      {/* Crew Training Recommendations — Carousel */}
      <Card className="rounded-[32px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="repeat-offenders-recommendations-card">
        <CardContent className="p-6 lg:p-8">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Crew training recommendations</p>
          <p className="mt-2 text-sm text-[var(--muted-foreground)]">Generate sessions here, then navigate to <button type="button" onClick={() => navigate("/standards")} className="font-semibold text-[#243e36] underline">Standards Library</button> to copy the training link.</p>
          <div className="mt-5">
            <CrewCarousel entries={summary.crew_summaries} onCreateTraining={createTrainingSession} />
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-3 sm:grid-cols-2" data-testid="repeat-offenders-crosslinks">
        <Link to="/standards" className="rounded-[20px] border border-border bg-[#f6f6f2] p-4 transition hover:bg-white" data-testid="repeat-link-standards">
          <p className="text-xs font-bold uppercase tracking-wider text-[var(--muted-foreground)]">Related</p>
          <p className="mt-1 font-semibold text-[#243e36]">Standards Library</p>
          <p className="mt-0.5 text-xs text-[var(--muted-foreground)]">Build and manage quality standards for training sessions.</p>
        </Link>
        <Link to="/rubric-editor" className="rounded-[20px] border border-border bg-[#f6f6f2] p-4 transition hover:bg-white" data-testid="repeat-link-rubric-editor">
          <p className="text-xs font-bold uppercase tracking-wider text-[var(--muted-foreground)]">Related</p>
          <p className="mt-1 font-semibold text-[#243e36]">Rubric Matrices</p>
          <p className="mt-0.5 text-xs text-[var(--muted-foreground)]">View and edit grading criteria linked to quality standards.</p>
        </Link>
      </div>
    </div>
  );
}
