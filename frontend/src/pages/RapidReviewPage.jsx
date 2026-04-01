import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, ArrowRight, ChevronDown, ChevronUp, MoonStar, SunMedium, X } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

import { useTheme } from "@/components/theme/ThemeProvider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { authGet, authPost } from "@/lib/api";
import { toast } from "sonner";


const QUICK_TAGS = ["quality-concern", "property-damage", "cleanup-missed", "training-follow-up"];
const RATING_CONFIG = {
  fail: { label: "Fail", color: "bg-[#7a2323] hover:bg-[#621b1b]" },
  concern: { label: "Concern", color: "bg-[#9a5b15] hover:bg-[#7d4a11]" },
  standard: { label: "Standard", color: "bg-[#2d5a27] hover:bg-[#22441d]" },
  exemplary: { label: "Exemplary", color: "bg-[#2a5f73] hover:bg-[#204b5b]" },
};


export default function RapidReviewPage({ user }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { isDark, toggleTheme } = useTheme();
  const mobileLane = location.pathname.endsWith("/mobile");
  const [queue, setQueue] = useState([]);
  const [detailMap, setDetailMap] = useState({});
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [autoStandard, setAutoStandard] = useState(false);
  const [issueTag] = useState(QUICK_TAGS[0]);
  const [annotationMode] = useState(false);
  const [drawings, setDrawings] = useState({});
  const [draftPath, setDraftPath] = useState("");
  const [drawingActive, setDrawingActive] = useState(false);
  const [pendingRating, setPendingRating] = useState("");
  const [reviewerComment, setReviewerComment] = useState("");
  const [hudDirection, setHudDirection] = useState("");
  const surfaceRef = useRef(null);

  const currentItem = queue[currentIndex] || null;
  const currentDetail = currentItem ? detailMap[currentItem.id] : null;
  const currentPhoto = currentDetail?.submission?.photo_files?.[0] || null;
  const currentDrawings = drawings[currentItem?.id] || [];

  const loadQueue = async () => {
    setLoading(true);
    try {
      const response = await authGet(`/rapid-reviews/queue?page=1&limit=${mobileLane ? 20 : 40}`);
      setQueue(response.items || []);
      setDetailMap({});
      setCurrentIndex(0);
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Unable to load rapid review queue");
    } finally {
      setLoading(false);
    }
  };

  const preloadDetail = async (submissionId) => {
    if (!submissionId || detailMap[submissionId]) return;
    try {
      const detail = await authGet(`/submissions/${submissionId}`);
      setDetailMap((current) => ({ ...current, [submissionId]: detail }));
    } catch {
      toast.error("Unable to preload one rapid review item.");
    }
  };

  useEffect(() => {
    loadQueue();
  }, [mobileLane]);

  useEffect(() => {
    if (currentItem?.id) preloadDetail(currentItem.id);
    if (queue[currentIndex + 1]?.id) preloadDetail(queue[currentIndex + 1].id);
  }, [currentItem?.id, currentIndex, queue]);

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (pendingRating) return;
      const tag = event.target?.tagName?.toLowerCase();
      if (["input", "textarea", "select"].includes(tag)) return;
      if (event.key === "ArrowLeft") { event.preventDefault(); requestRating("fail"); }
      if (event.key === "ArrowDown") { event.preventDefault(); requestRating("concern"); }
      if (event.key === "ArrowRight") { event.preventDefault(); requestRating("standard"); }
      if (event.key === "ArrowUp") { event.preventDefault(); requestRating("exemplary"); }
      if (event.key.toLowerCase() === "s") { event.preventDefault(); skipCurrent(); }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [currentItem?.id, autoStandard, currentDetail, pendingRating]);

  const skipCurrent = async () => {
    if (autoStandard && currentDetail?.submission?.field_report?.reported === false) {
      await submitRating("standard");
      return;
    }
    setDraftPath("");
    setCurrentIndex((current) => Math.min(current + 1, Math.max(queue.length - 1, 0)));
  };

  const removeFromQueue = (submissionId) => {
    setQueue((current) => {
      const nextQueue = current.filter((item) => item.id !== submissionId);
      setCurrentIndex((currentIndexValue) => Math.min(currentIndexValue, Math.max(nextQueue.length - 1, 0)));
      return nextQueue;
    });
    setPendingRating("");
    setReviewerComment("");
  };

  const submitRating = async (rating, submissionId = currentItem?.id, commentOverride = reviewerComment) => {
    if (!submissionId) return;
    const detail = detailMap[submissionId] || await authGet(`/submissions/${submissionId}`);
    setDetailMap((current) => ({ ...current, [submissionId]: detail }));
    setSaving(true);
    try {
      await authPost("/rapid-reviews", {
        submission_id: submissionId,
        overall_rating: rating,
        comment: commentOverride,
        issue_tag: issueTag,
        annotation_count: (drawings[submissionId] || []).length,
        entry_mode: mobileLane ? "mobile" : "desktop",
      });
      toast.success(`Rapid review marked ${RATING_CONFIG[rating].label.toLowerCase()}.`);
      removeFromQueue(submissionId);
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Rapid review save failed");
    } finally {
      setSaving(false);
    }
  };

  const requestRating = async (rating) => {
    if (saving) return;
    if (["fail", "exemplary"].includes(rating)) {
      setPendingRating(rating);
      setReviewerComment("");
      return;
    }
    await submitRating(rating, currentItem?.id, "");
  };

  const handleDragEnd = async (_, info) => {
    setHudDirection("");
    if (saving) return;
    if (info.offset.x <= -140) return requestRating("fail");
    if (info.offset.x >= 140) return requestRating("standard");
    if (info.offset.y <= -120) return requestRating("exemplary");
    if (info.offset.y >= 120) return requestRating("concern");
  };

  const handleDrag = (_, info) => {
    const { x, y } = info.offset;
    if (Math.abs(x) > Math.abs(y)) {
      setHudDirection(x <= -60 ? "fail" : x >= 60 ? "standard" : "");
      return;
    }
    setHudDirection(y <= -60 ? "exemplary" : y >= 60 ? "concern" : "");
  };

  const getRelativePoint = (event) => {
    const bounds = surfaceRef.current?.getBoundingClientRect();
    if (!bounds) return null;
    return {
      x: Number((((event.clientX - bounds.left) / bounds.width) * 100).toFixed(2)),
      y: Number((((event.clientY - bounds.top) / bounds.height) * 100).toFixed(2)),
    };
  };

  const handlePointerDown = (event) => {
    if (!annotationMode) return;
    const point = getRelativePoint(event);
    if (!point) return;
    setDrawingActive(true);
    setDraftPath(`M ${point.x} ${point.y}`);
  };

  const handlePointerMove = (event) => {
    if (!annotationMode || !drawingActive) return;
    const point = getRelativePoint(event);
    if (!point) return;
    setDraftPath((current) => `${current} L ${point.x} ${point.y}`);
  };

  const handlePointerUp = () => {
    if (!annotationMode || !drawingActive || !draftPath || !currentItem?.id) return;
    setDrawings((current) => ({
      ...current,
      [currentItem.id]: [...(current[currentItem.id] || []), draftPath],
    }));
    setDrawingActive(false);
    setDraftPath("");
  };

  if (loading) {
    return <div className="workspace-shell flex min-h-[100dvh] items-center justify-center bg-[#0d120e] text-white" data-testid="rapid-review-loading-state">Loading rapid review...</div>;
  }

  return (
    <div className={`workspace-shell flex min-h-[100dvh] flex-col overflow-hidden px-3 py-3 text-white ${isDark ? "theme-dark bg-[#0d120e]" : "bg-[#18241d]"}`} data-testid="rapid-review-page">
      <div className="mb-2 flex shrink-0 items-center justify-between gap-3 rounded-[20px] border border-white/10 bg-black/15 px-4 py-2.5 backdrop-blur-xl" data-testid="rapid-review-topbar">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-white/55">Rapid review</p>
          <h1 className="mt-0.5 font-[Outfit] text-lg font-semibold" data-testid="rapid-review-title">Swipe lane</h1>
        </div>
        <div className="flex items-center gap-2">
          <Button type="button" variant="outline" onClick={toggleTheme} className="h-8 w-8 rounded-full border-white/20 bg-white/10 p-0 text-white hover:bg-white/15" data-testid="rapid-review-theme-button">
            {isDark ? <SunMedium className="h-3.5 w-3.5" /> : <MoonStar className="h-3.5 w-3.5" />}
          </Button>
          <Button type="button" variant="outline" onClick={() => navigate(user?.role === "owner" ? "/owner" : "/review")} className="h-8 w-8 rounded-full border-white/20 bg-white/10 p-0 text-white hover:bg-white/15" data-testid="rapid-review-exit-button">
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-2">
        {currentItem && currentDetail ? (
          <>
            <AnimatePresence mode="wait">
              <motion.div key={currentItem.id} className="min-h-0 flex-1" initial={{ opacity: 0, x: 28 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -28 }} transition={{ duration: 0.18 }}>
                <motion.div drag dragMomentum={false} onDrag={handleDrag} onDragEnd={handleDragEnd} className="flex h-full flex-col overflow-hidden rounded-[20px] border border-white/10 bg-black/15 shadow-2xl backdrop-blur-xl" data-testid="rapid-review-image-surface">
                  <div className="flex shrink-0 items-center justify-between gap-3 border-b border-white/10 px-4 py-2 text-sm text-white/70">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-white" data-testid="rapid-review-current-job">{currentDetail.submission.job_name_input || currentDetail.submission.job_id || currentDetail.submission.submission_code}</p>
                      <p className="truncate text-xs text-white/60" data-testid="rapid-review-current-meta">{currentDetail.submission.crew_label} &middot; {currentDetail.submission.service_type}</p>
                    </div>
                    <Badge className="shrink-0 border-0 bg-white/10 text-xs text-white" data-testid="rapid-review-current-status">{currentIndex + 1}/{queue.length}</Badge>
                  </div>

                  <div className="relative min-h-0 flex-1 bg-[#101612]" ref={surfaceRef} onPointerDown={handlePointerDown} onPointerMove={handlePointerMove} onPointerUp={handlePointerUp} onPointerLeave={handlePointerUp}>
                    {currentPhoto ? <img src={currentPhoto.media_url} alt={currentPhoto.filename} className="h-full w-full object-cover" data-testid="rapid-review-main-image" /> : <div className="flex h-full items-center justify-center text-white/60">No image available</div>}
                    <div className={`pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 rounded-full px-3 py-2 text-xs font-semibold transition ${hudDirection === "fail" ? "bg-[#7a2323]/80 text-white" : "bg-[#7a2323]/30 text-white/60"}`} data-testid="rapid-review-hud-left"><ArrowLeft className="mb-0.5 h-3.5 w-3.5" />Fail</div>
                    <div className={`pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 rounded-full px-3 py-2 text-xs font-semibold transition ${hudDirection === "standard" ? "bg-[#2d5a27]/80 text-white" : "bg-[#2d5a27]/30 text-white/60"}`} data-testid="rapid-review-hud-right"><ArrowRight className="mb-0.5 h-3.5 w-3.5" />Pass</div>
                    <div className={`pointer-events-none absolute left-1/2 top-2 -translate-x-1/2 rounded-full px-3 py-2 text-xs font-semibold transition ${hudDirection === "exemplary" ? "bg-[#2a5f73]/80 text-white" : "bg-[#2a5f73]/30 text-white/60"}`} data-testid="rapid-review-hud-up"><ChevronUp className="mb-0.5 h-3.5 w-3.5" />Top</div>
                    <div className={`pointer-events-none absolute bottom-2 left-1/2 -translate-x-1/2 rounded-full px-3 py-2 text-xs font-semibold transition ${hudDirection === "concern" ? "bg-[#9a5b15]/80 text-white" : "bg-[#9a5b15]/30 text-white/60"}`} data-testid="rapid-review-hud-down"><ChevronDown className="mb-0.5 h-3.5 w-3.5" />Flag</div>
                    <svg className="pointer-events-none absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none" data-testid="rapid-review-annotation-layer">
                      {currentDrawings.map((path, index) => <path key={`${currentItem.id}-stroke-${index}`} d={path} fill="none" stroke="#fbbf24" strokeWidth="0.6" strokeLinecap="round" strokeLinejoin="round" />)}
                      {draftPath ? <path d={draftPath} fill="none" stroke="#fbbf24" strokeWidth="0.6" strokeLinecap="round" strokeLinejoin="round" /> : null}
                    </svg>
                  </div>
                </motion.div>
              </motion.div>
            </AnimatePresence>

            <div className="grid shrink-0 grid-cols-2 gap-2" data-testid="rapid-review-action-row">
              {Object.entries(RATING_CONFIG).map(([key, config]) => (
                <Button key={key} type="button" disabled={saving} onClick={() => requestRating(key)} className={`h-11 rounded-[14px] text-sm text-white ${config.color}`} data-testid={`rapid-review-${key}-button`}>
                  {config.label}
                </Button>
              ))}
            </div>

            <Button type="button" disabled={saving} onClick={skipCurrent} className="h-9 w-full shrink-0 rounded-[14px] bg-white/10 text-sm text-white hover:bg-white/15" data-testid="rapid-review-skip-button">Skip</Button>
          </>
        ) : (
          <Card className="flex flex-1 items-center justify-center rounded-[20px] border-white/10 bg-black/15 text-white backdrop-blur-xl" data-testid="rapid-review-empty-state">
            <CardContent className="flex flex-col items-center p-8 text-center">
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-white/50">Queue clear</p>
              <h2 className="mt-3 font-[Outfit] text-2xl font-semibold">You&apos;re caught up.</h2>
              <Button type="button" onClick={loadQueue} className="mt-5 rounded-full bg-white/10 text-white hover:bg-white/15" data-testid="rapid-review-refresh-button">Refresh queue</Button>
            </CardContent>
          </Card>
        )}
      </div>

      {pendingRating ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 px-3 pb-4" data-testid="rapid-review-comment-modal">
          <div className="w-full max-w-lg rounded-[22px] border border-white/10 bg-[#162019] p-5 shadow-2xl">
            <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-white/50">Comment required</p>
            <h2 className="mt-2 font-[Outfit] text-xl font-semibold text-white">{RATING_CONFIG[pendingRating].label} needs context</h2>
            <Textarea value={reviewerComment} onChange={(event) => setReviewerComment(event.target.value)} className="mt-3 min-h-[100px] rounded-[16px] border-white/15 bg-black/20 text-white" placeholder="Add reviewer context..." data-testid="rapid-review-comment-input" />
            <div className="mt-4 flex gap-2">
              <Button type="button" variant="outline" onClick={() => { setPendingRating(""); setReviewerComment(""); }} className="flex-1 rounded-xl border-white/15 bg-transparent text-white hover:bg-white/10" data-testid="rapid-review-comment-cancel-button">Cancel</Button>
              <Button type="button" disabled={!reviewerComment.trim()} onClick={() => submitRating(pendingRating, currentItem?.id, reviewerComment)} className="flex-1 rounded-xl bg-[#2d5a27] hover:bg-[#22441d] disabled:opacity-50" data-testid="rapid-review-comment-commit-button">Commit</Button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
