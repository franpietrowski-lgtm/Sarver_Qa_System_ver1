import { useEffect, useRef, useState } from "react";
import { AlertTriangle, ChevronDown, ChevronLeft, ChevronRight, Radar } from "lucide-react";
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
    return <p className="py-6 text-center text-sm text-[#5c6d64]" data-testid="crew-carousel-empty">No repeat offenders found in this window.</p>;
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
                <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">{entry.division}</p>
                <h3 className="mt-1 font-[Cabinet_Grotesk] text-xl font-black tracking-tight text-[#111815]">{entry.crew}</h3>
              </div>
              <Badge className="border-0 bg-white text-[#243e36]">{entry.incident_count}</Badge>
            </div>
            <div className="mt-3 rounded-[16px] border border-[#ead2d2] bg-[#fbf0ef] p-3">
              <div className="flex items-center gap-2 text-xs font-semibold text-[#7a2323]"><AlertTriangle className="h-3.5 w-3.5" />{entry.level}</div>
              <p className="mt-1 text-xs text-[#5c6d64]">Top: {entry.top_issue_type}</p>
            </div>
            <div className="mt-3 rounded-[16px] border border-border bg-white p-3">
              <p className="text-[10px] font-bold uppercase tracking-widest text-[#5f7464]">Recommended action</p>
              <p className="mt-1 text-xs leading-relaxed text-[#41534a]">{STANDARD_ACTIONS[entry.level] || STANDARD_ACTIONS["Watch"]}</p>
            </div>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {Object.entries(entry.issue_types).map(([issue, count]) => <Badge key={issue} className="border-0 bg-white text-[10px] text-[#243e36]">{issue} · {count}</Badge>)}
            </div>
            <Button onClick={() => onCreateTraining(entry)} className="mt-4 h-9 w-full rounded-xl bg-[#243e36] text-xs hover:bg-[#1a2c26]" data-testid={`repeat-offender-create-training-${entry.crew.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}`}>Create training session</Button>
            <p className="mt-2 text-center text-[10px] text-[#5c6d64]">View generated session in Standards Library.</p>
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

  if (!summary) {
    return <div className="rounded-[28px] border border-border bg-white p-10 text-center text-[#243e36]" data-testid="repeat-offenders-loading-state">Loading repeat-offender tracking...</div>;
  }

  return (
    <div className="space-y-5" data-testid="repeat-offenders-page">
      <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="repeat-offenders-hero-card">
        <CardContent className="p-6 lg:p-8">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Repeat offender tracking</p>
              <h1 className="mt-3 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815] lg:text-4xl">Spot recurring quality misses, escalate them, and launch training fast.</h1>
              <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#5c6d64]">
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
                <label className="mb-1 block text-[10px] font-bold uppercase tracking-widest text-[#5f7464]">Days</label>
                <Input type="number" min="7" max="365" value={windowDays} onChange={(event) => setWindowDays(Number(event.target.value) || 30)} className="h-10 w-28 rounded-xl border-transparent bg-white" data-testid="repeat-offenders-window-input" />
              </div>
              <Button onClick={() => loadData(windowDays)} className="rounded-2xl bg-[#243e36] hover:bg-[#1a2c26]" data-testid="repeat-offenders-refresh-button">Refresh</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Standard Courses of Action */}
      <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="repeat-offenders-actions-card">
        <CardContent className="p-6 lg:p-8">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Standard courses of action</p>
          <p className="mt-2 text-sm text-[#5c6d64]">These are the default escalation responses assigned when a crew reaches each threshold tier.</p>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {Object.entries(STANDARD_ACTIONS).map(([level, description]) => {
              const colors = { Watch: "border-[#d8e4da] bg-[#edf5ee]", Warning: "border-[#f0ddb4] bg-[#fdf8ed]", Critical: "border-[#ead2d2] bg-[#fbf0ef]" };
              const textColors = { Watch: "text-[#2d5a27]", Warning: "text-[#8a6d1b]", Critical: "text-[#7a2323]" };
              return (
                <div key={level} className={`rounded-[20px] border p-4 ${colors[level]}`} data-testid={`action-tier-${level.toLowerCase()}`}>
                  <p className={`text-sm font-bold ${textColors[level]}`}>{level}</p>
                  <p className="mt-2 text-xs leading-relaxed text-[#41534a]">{description}</p>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Heatmap — Collapsible */}
      <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="repeat-offenders-heatmap-card">
        <CardContent className="p-6 lg:p-8">
          <button type="button" onClick={() => setHeatmapOpen(!heatmapOpen)} className="flex w-full items-center justify-between gap-3 text-left" data-testid="repeat-offenders-heatmap-toggle">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Heatmap</p>
              <p className="mt-1 text-sm text-[#5c6d64]">{summary.heatmap.length} crew/issue combinations tracked</p>
            </div>
            <ChevronDown className={`h-5 w-5 text-[#5c6d64] transition-transform ${heatmapOpen ? "rotate-180" : ""}`} />
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
                  {summary.heatmap.map((cell) => {
                    const levelColors = { Watch: "text-[#2d5a27]", Warning: "text-[#8a6d1b]", Critical: "text-[#7a2323]" };
                    return (
                      <div key={`${cell.crew}-${cell.issue_type}`} className="rounded-[20px] border border-border bg-[#f6f6f2] p-4" data-testid={`repeat-offender-cell-${cell.crew.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}-${cell.issue_type.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}`}>
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-sm font-semibold text-[#243e36]">{cell.crew}</p>
                          <Badge className="border-0 bg-white text-[#243e36]">{cell.count}</Badge>
                        </div>
                        <p className="mt-1.5 text-sm text-[#5c6d64]">{cell.issue_type}</p>
                        <p className={`mt-1.5 text-xs font-semibold uppercase tracking-[0.2em] ${levelColors[cell.level] || "text-[#8b4c4c]"}`}>{cell.level}</p>
                      </div>
                    );
                  })}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </CardContent>
      </Card>

      {/* Crew Training Recommendations — Carousel */}
      <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="repeat-offenders-recommendations-card">
        <CardContent className="p-6 lg:p-8">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Crew training recommendations</p>
          <p className="mt-2 text-sm text-[#5c6d64]">Generate sessions here, then navigate to <button type="button" onClick={() => navigate("/standards")} className="font-semibold text-[#243e36] underline">Standards Library</button> to copy the training link.</p>
          <div className="mt-5">
            <CrewCarousel entries={summary.crew_summaries} onCreateTraining={createTrainingSession} />
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-3 sm:grid-cols-2" data-testid="repeat-offenders-crosslinks">
        <Link to="/standards" className="rounded-[20px] border border-border bg-[#f6f6f2] p-4 transition hover:bg-white" data-testid="repeat-link-standards">
          <p className="text-xs font-bold uppercase tracking-wider text-[#5f7464]">Related</p>
          <p className="mt-1 font-semibold text-[#243e36]">Standards Library</p>
          <p className="mt-0.5 text-xs text-[#5c6d64]">Build and manage quality standards for training sessions.</p>
        </Link>
        <Link to="/rubric-editor" className="rounded-[20px] border border-border bg-[#f6f6f2] p-4 transition hover:bg-white" data-testid="repeat-link-rubric-editor">
          <p className="text-xs font-bold uppercase tracking-wider text-[#5f7464]">Related</p>
          <p className="mt-1 font-semibold text-[#243e36]">Rubric Matrices</p>
          <p className="mt-0.5 text-xs text-[#5c6d64]">View and edit grading criteria linked to quality standards.</p>
        </Link>
      </div>
    </div>
  );
}
