import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, ArrowRight, BookOpen, ChevronDown, ChevronUp, X } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

import { useTheme } from "@/components/theme/ThemeProvider";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { authGet, authPost } from "@/lib/api";
import { toast } from "sonner";


const RATING_CONFIG = {
  fail: { label: "Fail", color: "bg-[#7a2323] hover:bg-[#621b1b]" },
  concern: { label: "Concern", color: "bg-[#9a5b15] hover:bg-[#7d4a11]" },
  standard: { label: "Standard", color: "bg-[#2d5a27] hover:bg-[#22441d]" },
  exemplary: { label: "Exemplary", color: "bg-[#2a5f73] hover:bg-[#204b5b]" },
};

const SUGGESTED_TIME_MS = 10000;
const ENFORCED_MIN_MS = 8000;
const FAST_TRIGGER_MS = 4000;


export default function RapidReviewPage({ user }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { theme } = useTheme();
  const mobileLane = location.pathname.endsWith("/mobile");

  const [queue, setQueue] = useState([]);
  const [detailMap, setDetailMap] = useState({});
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [pendingRating, setPendingRating] = useState("");
  const [reviewerComment, setReviewerComment] = useState("");
  const [hudDirection, setHudDirection] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [totalReviewed, setTotalReviewed] = useState(0);
  const [initialQueueSize, setInitialQueueSize] = useState(0);
  const [showGlow, setShowGlow] = useState(false);
  const [imageViewStart, setImageViewStart] = useState(0);
  const [timerDisplay, setTimerDisplay] = useState(0);
  const [tooFast, setTooFast] = useState(false);
  const [showRubricRef, setShowRubricRef] = useState(false);
  const [rubricCategories, setRubricCategories] = useState([]);

  const surfaceRef = useRef(null);
  const timerRef = useRef(null);

  const currentItem = queue[currentIndex] || null;
  const currentDetail = currentItem ? detailMap[currentItem.id] : null;
  const currentPhoto = currentDetail?.submission?.photo_files?.[0] || null;

  const remaining = queue.length;
  const progressPercent = initialQueueSize > 0 ? Math.round(((totalReviewed) / initialQueueSize) * 100) : 0;
  const nearComplete = initialQueueSize > 0 && remaining > 0 && remaining <= Math.ceil(initialQueueSize * 0.15);

  const loadQueue = async () => {
    setLoading(true);
    try {
      const response = await authGet(`/rapid-reviews/queue?page=1&limit=${mobileLane ? 30 : 50}`);
      const items = response.items || [];
      setQueue(items);
      setDetailMap({});
      setCurrentIndex(0);
      setInitialQueueSize(items.length);
      setTotalReviewed(0);
      if (items.length > 0) {
        try {
          const sessionResponse = await authPost("/rapid-review-sessions", {
            total_queue_size: items.length,
            entry_mode: mobileLane ? "mobile" : "desktop",
          });
          setSessionId(sessionResponse.session?.id || "");
        } catch { /* session tracking is optional */ }
      }
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
    } catch { /* silent */ }
  };

  useEffect(() => { loadQueue(); }, [mobileLane]);

  useEffect(() => {
    if (currentItem?.id) preloadDetail(currentItem.id);
    if (queue[currentIndex + 1]?.id) preloadDetail(queue[currentIndex + 1].id);
  }, [currentItem?.id, currentIndex, queue]);

  // Load rubric guidance for current submission
  useEffect(() => {
    if (!currentDetail?.submission) return;
    const sub = currentDetail.submission;
    const svcType = sub.service_type || sub.task_type || "";
    const div = sub.division || "";
    if (!svcType) { setRubricCategories([]); return; }
    authGet(`/rubrics/for-task?service_type=${encodeURIComponent(svcType)}&division=${encodeURIComponent(div)}`)
      .then((data) => setRubricCategories(data.rubric_categories || []))
      .catch(() => setRubricCategories([]));
  }, [currentDetail?.submission?.id]);

  useEffect(() => {
    setImageViewStart(Date.now());
    setTimerDisplay(0);
    setTooFast(false);
    if (timerRef.current) clearInterval(timerRef.current);
    if (currentItem) {
      timerRef.current = setInterval(() => {
        const elapsed = Date.now() - (imageViewStart || Date.now());
        setTimerDisplay(elapsed);
      }, 200);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [currentItem?.id]);

  useEffect(() => {
    if (nearComplete && !showGlow) setShowGlow(true);
  }, [nearComplete]);

  const getSwipeDuration = useCallback(() => {
    return imageViewStart > 0 ? Date.now() - imageViewStart : 0;
  }, [imageViewStart]);

  const endSession = useCallback(async (reason = "manual") => {
    if (sessionId) {
      try {
        await authPost(`/rapid-review-sessions/${sessionId}/complete`, { session_id: sessionId, exit_reason: reason });
      } catch { /* silent */ }
    }
    navigate(user?.role === "owner" ? "/owner" : "/review");
  }, [sessionId, navigate, user]);

  const removeFromQueue = (submissionId) => {
    setQueue((current) => {
      const nextQueue = current.filter((item) => item.id !== submissionId);
      setCurrentIndex((idx) => Math.min(idx, Math.max(nextQueue.length - 1, 0)));
      return nextQueue;
    });
    setTotalReviewed((prev) => prev + 1);
    setPendingRating("");
    setReviewerComment("");
  };

  const submitRating = async (rating, submissionId = currentItem?.id, commentOverride = reviewerComment) => {
    if (!submissionId) return;
    const detail = detailMap[submissionId] || await authGet(`/submissions/${submissionId}`);
    setDetailMap((current) => ({ ...current, [submissionId]: detail }));
    const swipeDuration = getSwipeDuration();
    setSaving(true);
    try {
      await authPost("/rapid-reviews", {
        submission_id: submissionId,
        overall_rating: rating,
        comment: commentOverride,
        issue_tag: "",
        annotation_count: 0,
        entry_mode: mobileLane ? "mobile" : "desktop",
        swipe_duration_ms: swipeDuration,
        session_id: sessionId,
      });
      const isFast = swipeDuration < FAST_TRIGGER_MS && ["standard", "exemplary"].includes(rating);
      if (isFast) {
        toast.warning("Fast swipe recorded", { description: `${Math.round(swipeDuration / 1000)}s — flagged for accuracy review` });
      } else {
        toast.success(`${RATING_CONFIG[rating].label}`);
      }
      removeFromQueue(submissionId);
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Rapid review save failed");
    } finally {
      setSaving(false);
    }
  };

  const requestRating = async (rating) => {
    if (saving) return;
    const swipeDuration = getSwipeDuration();
    if (swipeDuration < ENFORCED_MIN_MS && ["standard", "exemplary"].includes(rating)) {
      setTooFast(true);
      setTimeout(() => setTooFast(false), 2000);
    }
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

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (pendingRating) return;
      const tag = event.target?.tagName?.toLowerCase();
      if (["input", "textarea", "select"].includes(tag)) return;
      if (event.key === "ArrowLeft") { event.preventDefault(); requestRating("fail"); }
      if (event.key === "ArrowDown") { event.preventDefault(); requestRating("concern"); }
      if (event.key === "ArrowRight") { event.preventDefault(); requestRating("standard"); }
      if (event.key === "ArrowUp") { event.preventDefault(); requestRating("exemplary"); }
      if (event.key === "Escape") { event.preventDefault(); endSession("manual"); }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [currentItem?.id, pendingRating, saving, endSession]);

  useEffect(() => {
    if (queue.length === 0 && totalReviewed > 0 && !loading) {
      endSession("completed");
    }
  }, [queue.length, totalReviewed, loading]);

  if (loading) {
    return (
      <div className="flex min-h-[100dvh] items-center justify-center bg-[#0d120e] text-white" data-testid="rapid-review-loading-state">
        <div className="text-center">
          <div className="mx-auto mb-3 h-6 w-6 animate-spin rounded-full border-2 border-white/20 border-t-[#4a7c59]" />
          <p className="text-sm text-white/60">Loading rapid review queue...</p>
        </div>
      </div>
    );
  }

  const elapsedSec = Math.round((imageViewStart > 0 ? Date.now() - imageViewStart : 0) / 1000);

  return (
    <div className={`fixed inset-0 flex flex-col overflow-hidden text-white bg-[#0d120e]`} data-testid="rapid-review-page">
      {/* Progress bar */}
      <div className="relative h-1.5 shrink-0 bg-white/5" data-testid="rapid-review-progress-bar-container">
        <div
          className={`h-full transition-all duration-500 ease-out ${nearComplete ? "bg-[#4a7c59]" : "bg-[#2d5a27]"}`}
          style={{ width: `${progressPercent}%` }}
          data-testid="rapid-review-progress-bar"
        />
        {nearComplete && (
          <div
            className="absolute inset-0 h-full animate-pulse rounded-sm"
            style={{
              width: `${progressPercent}%`,
              boxShadow: "0 0 16px 4px rgba(74, 124, 89, 0.6), 0 0 32px 8px rgba(74, 124, 89, 0.3)",
            }}
            data-testid="rapid-review-progress-glow"
          />
        )}
      </div>

      {/* Minimal status strip */}
      <div className="flex shrink-0 items-center justify-between px-4 py-2" data-testid="rapid-review-status-strip">
        <div className="flex items-center gap-3">
          <span className="text-xs font-medium text-white/40" data-testid="rapid-review-counter">{totalReviewed}/{initialQueueSize}</span>
          {currentItem && (
            <span className={`text-xs font-mono tabular-nums ${elapsedSec < 4 ? "text-red-400/80" : elapsedSec < 8 ? "text-amber-400/60" : "text-white/30"}`} data-testid="rapid-review-timer">{elapsedSec}s</span>
          )}
          {tooFast && <span className="text-[10px] font-semibold uppercase tracking-wider text-amber-400/80" data-testid="rapid-review-fast-warning">Take your time</span>}
        </div>
        <Button
          type="button"
          variant="ghost"
          onClick={() => endSession("manual")}
          className="h-8 w-8 rounded-full p-0 text-white/40 hover:bg-white/10 hover:text-white"
          data-testid="rapid-review-exit-button"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Full-screen image surface */}
      <div className="relative min-h-0 flex-1" data-testid="rapid-review-surface-container">
        {currentItem && currentDetail ? (
          <AnimatePresence mode="wait">
            <motion.div
              key={currentItem.id}
              className="absolute inset-0"
              initial={{ opacity: 0, scale: 0.97 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.03 }}
              transition={{ duration: 0.2 }}
            >
              <motion.div
                drag
                dragMomentum={false}
                onDrag={handleDrag}
                onDragEnd={handleDragEnd}
                className="h-full w-full"
                data-testid="rapid-review-image-surface"
              >
                {/* Image */}
                <div className="absolute inset-0 bg-[#080c09]" ref={surfaceRef}>
                  {currentPhoto ? (
                    <img
                      src={currentPhoto.media_url}
                      alt={currentPhoto.filename}
                      className="h-full w-full object-contain"
                      data-testid="rapid-review-main-image"
                    />
                  ) : (
                    <div className="flex h-full items-center justify-center text-white/40">No image</div>
                  )}
                </div>

                {/* Swipe HUD overlays */}
                <div className={`pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 rounded-full px-3 py-2 text-xs font-bold uppercase tracking-wider transition-all duration-200 ${hudDirection === "fail" ? "scale-110 bg-[#7a2323]/90 text-white" : "scale-100 bg-[#7a2323]/20 text-white/30"}`} data-testid="rapid-review-hud-left">
                  <ArrowLeft className="mx-auto mb-0.5 h-4 w-4" />Fail
                </div>
                <div className={`pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 rounded-full px-3 py-2 text-xs font-bold uppercase tracking-wider transition-all duration-200 ${hudDirection === "standard" ? "scale-110 bg-[#2d5a27]/90 text-white" : "scale-100 bg-[#2d5a27]/20 text-white/30"}`} data-testid="rapid-review-hud-right">
                  <ArrowRight className="mx-auto mb-0.5 h-4 w-4" />Pass
                </div>
                <div className={`pointer-events-none absolute left-1/2 top-3 -translate-x-1/2 rounded-full px-3 py-2 text-xs font-bold uppercase tracking-wider transition-all duration-200 ${hudDirection === "exemplary" ? "scale-110 bg-[#2a5f73]/90 text-white" : "scale-100 bg-[#2a5f73]/20 text-white/30"}`} data-testid="rapid-review-hud-up">
                  <ChevronUp className="mx-auto mb-0.5 h-4 w-4" />Top
                </div>
                <div className={`pointer-events-none absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full px-3 py-2 text-xs font-bold uppercase tracking-wider transition-all duration-200 ${hudDirection === "concern" ? "scale-110 bg-[#9a5b15]/90 text-white" : "scale-100 bg-[#9a5b15]/20 text-white/30"}`} data-testid="rapid-review-hud-down">
                  <ChevronDown className="mx-auto mb-0.5 h-4 w-4" />Flag
                </div>

                {/* Bottom job info overlay */}
                <div className="pointer-events-none absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 via-black/30 to-transparent px-4 pb-4 pt-10" data-testid="rapid-review-job-overlay">
                  <div className="flex items-end justify-between pointer-events-auto">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-white/90" data-testid="rapid-review-current-job">
                        {currentDetail.submission.job_name_input || currentDetail.submission.job_id || currentDetail.submission.submission_code}
                      </p>
                      <p className="mt-0.5 truncate text-xs text-white/50" data-testid="rapid-review-current-meta">
                        {currentDetail.submission.crew_label} &middot; {currentDetail.submission.service_type} &middot; {currentDetail.submission.division}
                      </p>
                    </div>
                    {rubricCategories.length > 0 && (
                      <button
                        type="button"
                        onClick={() => setShowRubricRef(!showRubricRef)}
                        className={`ml-3 flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider transition-all ${showRubricRef ? "bg-[#4a7c59] text-white" : "bg-white/15 text-white/70 hover:bg-white/25"}`}
                        data-testid="rapid-review-rubric-toggle"
                      >
                        <BookOpen className="h-3.5 w-3.5" />Rubric
                      </button>
                    )}
                  </div>
                </div>

                {/* Rubric reference panel */}
                <AnimatePresence>
                  {showRubricRef && rubricCategories.length > 0 && (
                    <motion.div
                      initial={{ y: 200, opacity: 0 }}
                      animate={{ y: 0, opacity: 1 }}
                      exit={{ y: 200, opacity: 0 }}
                      transition={{ duration: 0.25, ease: "easeOut" }}
                      className="pointer-events-auto absolute bottom-16 left-2 right-2 z-30 max-h-[40vh] overflow-y-auto rounded-[18px] border border-white/10 p-4 shadow-2xl"
                      style={{ backdropFilter: "blur(24px)", WebkitBackdropFilter: "blur(24px)", background: "rgba(13,18,14,0.88)" }}
                      data-testid="rapid-review-rubric-panel"
                    >
                      <p className="text-[9px] font-bold uppercase tracking-[0.3em] text-white/40 mb-2">
                        Task rubric — {currentDetail.submission.service_type}
                      </p>
                      <div className="space-y-2.5">
                        {rubricCategories.map((cat, ci) => (
                          <div key={ci} className="rounded-[12px] border border-white/8 bg-white/5 p-3" data-testid={`rapid-review-rubric-cat-${ci}`}>
                            <div className="flex items-center justify-between gap-2">
                              <p className="text-xs font-bold text-white/90">{cat.name}</p>
                              {cat.weight > 0 && <span className="rounded-full bg-white/10 px-2 py-0.5 text-[9px] text-white/50">{cat.weight}%</span>}
                            </div>
                            {cat.criteria?.length > 0 && (
                              <div className="mt-1.5 space-y-0.5">
                                {cat.criteria.map((c, i) => (
                                  <p key={i} className="text-[10px] text-white/55">• {c}</p>
                                ))}
                              </div>
                            )}
                            <div className="mt-1.5 flex gap-2">
                              {cat.fail_indicators?.length > 0 && (
                                <div className="flex-1 rounded-lg bg-[#7a2323]/20 px-2 py-1.5">
                                  <p className="text-[8px] font-bold uppercase text-red-400/80 mb-0.5">Fail clues</p>
                                  {cat.fail_indicators.map((f, i) => <p key={i} className="text-[9px] text-red-300/60">- {f}</p>)}
                                </div>
                              )}
                              {cat.exemplary_indicators?.length > 0 && (
                                <div className="flex-1 rounded-lg bg-[#2a5f73]/20 px-2 py-1.5">
                                  <p className="text-[8px] font-bold uppercase text-cyan-400/80 mb-0.5">Top clues</p>
                                  {cat.exemplary_indicators.map((e, i) => <p key={i} className="text-[9px] text-cyan-300/60">- {e}</p>)}
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            </motion.div>
          </AnimatePresence>
        ) : (
          <div className="flex h-full flex-col items-center justify-center text-center" data-testid="rapid-review-empty-state">
            <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-white/30">Queue clear</p>
            <h2 className="mt-2 font-[Outfit] text-2xl font-semibold text-white/80">You&apos;re caught up.</h2>
            <Button type="button" onClick={loadQueue} className="mt-4 rounded-full bg-white/10 text-sm text-white hover:bg-white/15" data-testid="rapid-review-refresh-button">Refresh queue</Button>
          </div>
        )}
      </div>

      {/* Comment modal for Fail/Exemplary */}
      {pendingRating ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 px-3 pb-4" data-testid="rapid-review-comment-modal">
          <motion.div
            initial={{ y: 120, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="w-full max-w-lg rounded-[20px] border border-white/10 bg-[#141a15] p-5 shadow-2xl"
          >
            <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-white/40">Comment required</p>
            <h2 className="mt-1.5 font-[Outfit] text-lg font-semibold text-white">{RATING_CONFIG[pendingRating].label} &mdash; add context</h2>
            {/* Dynamic rubric hints */}
            {rubricCategories.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5" data-testid="rapid-review-rubric-hints">
                {rubricCategories.flatMap((cat) => {
                  const indicators = pendingRating === "fail" ? (cat.fail_indicators || []) : (cat.exemplary_indicators || []);
                  return indicators.map((hint, i) => (
                    <button
                      key={`${cat.name}-${i}`}
                      type="button"
                      onClick={() => setReviewerComment((prev) => prev ? `${prev}; ${hint}` : hint)}
                      className={`rounded-full px-2.5 py-1 text-[10px] font-medium transition-colors ${
                        pendingRating === "fail"
                          ? "bg-red-500/15 text-red-300/80 hover:bg-red-500/25"
                          : "bg-cyan-500/15 text-cyan-300/80 hover:bg-cyan-500/25"
                      }`}
                      data-testid={`rapid-review-hint-${i}`}
                    >
                      {hint}
                    </button>
                  ));
                })}
              </div>
            )}
            <Textarea
              value={reviewerComment}
              onChange={(event) => setReviewerComment(event.target.value)}
              className="mt-3 min-h-[90px] rounded-[14px] border-white/10 bg-black/30 text-sm text-white placeholder:text-white/30"
              placeholder="What did you observe?"
              autoFocus
              data-testid="rapid-review-comment-input"
            />
            <div className="mt-3 flex gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => { setPendingRating(""); setReviewerComment(""); }}
                className="flex-1 rounded-xl border-white/10 bg-transparent text-sm text-white hover:bg-white/10"
                data-testid="rapid-review-comment-cancel-button"
              >
                Cancel
              </Button>
              <Button
                type="button"
                disabled={!reviewerComment.trim()}
                onClick={() => submitRating(pendingRating, currentItem?.id, reviewerComment)}
                className="flex-1 rounded-xl bg-[#2d5a27] text-sm hover:bg-[#22441d] disabled:opacity-40"
                data-testid="rapid-review-comment-commit-button"
              >
                Commit
              </Button>
            </div>
          </motion.div>
        </div>
      ) : null}
    </div>
  );
}
