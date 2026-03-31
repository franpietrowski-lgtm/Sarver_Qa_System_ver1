import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, ArrowRight, ChevronDown, ChevronUp, MessageSquareQuote, MoonStar, Paintbrush, Sparkles, SunMedium, X } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

import { useTheme } from "@/components/theme/ThemeProvider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { authGet, authPost } from "@/lib/api";
import { toast } from "sonner";


const QUICK_TAGS = ["quality-concern", "property-damage", "cleanup-missed", "training-follow-up"];
const RATING_MULTIPLIERS = { fail: 0.2, concern: 0.55, standard: 0.82, exemplary: 1.0 };
const RATING_CONFIG = {
  fail: { label: "Fail", swipeHint: "Swipe left", hotkey: "←", color: "bg-[#7a2323] hover:bg-[#621b1b]" },
  concern: { label: "Concern", swipeHint: "Swipe down", hotkey: "↓", color: "bg-[#9a5b15] hover:bg-[#7d4a11]" },
  standard: { label: "Standard", swipeHint: "Swipe right", hotkey: "→", color: "bg-[#2d5a27] hover:bg-[#22441d]" },
  exemplary: { label: "Exemplary", swipeHint: "Swipe up", hotkey: "↑", color: "bg-[#2a5f73] hover:bg-[#204b5b]" },
};


function calculateProjectedSum(rubric, rating) {
  const totalWeight = (rubric?.categories || []).reduce((sum, category) => sum + category.weight, 0);
  return Math.round(totalWeight * RATING_MULTIPLIERS[rating] * 100);
}


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
  const [bulkSaving, setBulkSaving] = useState(false);
  const [selectedIds, setSelectedIds] = useState([]);
  const [autoStandard, setAutoStandard] = useState(false);
  const [issueTag, setIssueTag] = useState(QUICK_TAGS[0]);
  const [annotationMode, setAnnotationMode] = useState(false);
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
  const projectedSums = useMemo(() => {
    if (!currentDetail?.rubric) return {};
    return Object.keys(RATING_CONFIG).reduce((accumulator, key) => ({
      ...accumulator,
      [key]: calculateProjectedSum(currentDetail.rubric, key),
    }), {});
  }, [currentDetail]);

  const loadQueue = async () => {
    setLoading(true);
    try {
      const response = await authGet(`/rapid-reviews/queue?page=1&limit=${mobileLane ? 20 : 40}`);
      setQueue(response.items || []);
      setDetailMap({});
      setCurrentIndex(0);
      setSelectedIds([]);
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
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        requestRating("fail");
      }
      if (event.key === "ArrowDown") {
        event.preventDefault();
        requestRating("concern");
      }
      if (event.key === "ArrowRight") {
        event.preventDefault();
        requestRating("standard");
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        requestRating("exemplary");
      }
      if (event.key.toLowerCase() === "s") {
        event.preventDefault();
        skipCurrent();
      }
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
    setAnnotationMode(false);
    setCurrentIndex((current) => Math.min(current + 1, Math.max(queue.length - 1, 0)));
  };

  const removeFromQueue = (submissionId) => {
    setQueue((current) => {
      const nextQueue = current.filter((item) => item.id !== submissionId);
      setCurrentIndex((currentIndexValue) => Math.min(currentIndexValue, Math.max(nextQueue.length - 1, 0)));
      return nextQueue;
    });
    setSelectedIds((current) => current.filter((item) => item !== submissionId));
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

  const handleBulkStandard = async (rating) => {
    if (!selectedIds.length) {
      toast.error("Select at least one submission first.");
      return;
    }
    setBulkSaving(true);
    try {
      for (const submissionId of selectedIds) {
        await authPost("/rapid-reviews", {
          submission_id: submissionId,
          overall_rating: rating,
          comment: "",
          issue_tag: issueTag,
          annotation_count: 0,
          entry_mode: mobileLane ? "mobile" : "desktop",
        });
      }
      toast.success(`Bulk ${RATING_CONFIG[rating].label.toLowerCase()} complete.`);
      setQueue((current) => current.filter((item) => !selectedIds.includes(item.id)));
      setSelectedIds([]);
      setCurrentIndex(0);
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Bulk rapid review failed");
    } finally {
      setBulkSaving(false);
    }
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
    return <div className="workspace-shell min-h-screen bg-[#0d120e] px-6 py-8 text-white" data-testid="rapid-review-loading-state">Loading rapid review...</div>;
  }

  return (
    <div className={`workspace-shell min-h-screen px-4 py-4 text-white ${isDark ? "theme-dark bg-[#0d120e]" : "bg-[#18241d]"}`} data-testid="rapid-review-page">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-[28px] border border-white/10 bg-black/15 px-4 py-4 backdrop-blur-xl" data-testid="rapid-review-topbar">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-white/55">Rapid review</p>
          <h1 className="mt-2 font-[Outfit] text-3xl font-semibold" data-testid="rapid-review-title">Mobile swipe lane</h1>
          <p className="mt-1 text-sm text-white/70" data-testid="rapid-review-progress-text">Phone-first admin lane with swipe HUD guidance and summary scoring.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge className="border-0 bg-white/10 text-white" data-testid="rapid-review-entry-badge">Mobile link</Badge>
          <Button type="button" variant="outline" onClick={toggleTheme} className="rounded-full border-white/20 bg-white/10 text-white hover:bg-white/15" data-testid="rapid-review-theme-button">
            {isDark ? <SunMedium className="mr-2 h-4 w-4" /> : <MoonStar className="mr-2 h-4 w-4" />}
            {isDark ? "Default" : "Dark"}
          </Button>
          <Button type="button" variant="outline" onClick={() => navigate(user?.role === "owner" ? "/owner" : "/review")} className="rounded-full border-white/20 bg-white/10 text-white hover:bg-white/15" data-testid="rapid-review-exit-button">
            <X className="mr-2 h-4 w-4" />Exit
          </Button>
        </div>
      </div>

      <div className="grid gap-4">
        <div className="space-y-4">
          {currentItem && currentDetail ? (
            <>
              <AnimatePresence mode="wait">
                <motion.div key={currentItem.id} initial={{ opacity: 0, x: 28 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -28 }} transition={{ duration: 0.18 }}>
                  <motion.div drag dragMomentum={false} onDrag={handleDrag} onDragEnd={handleDragEnd} className="overflow-hidden rounded-[36px] border border-white/10 bg-black/15 shadow-2xl backdrop-blur-xl" data-testid="rapid-review-image-surface">
                    <div className="flex items-center justify-between gap-3 border-b border-white/10 px-5 py-4 text-sm text-white/70">
                      <div>
                        <p className="font-semibold text-white" data-testid="rapid-review-current-job">{currentDetail.submission.job_name_input || currentDetail.submission.job_id || currentDetail.submission.submission_code}</p>
                        <p className="mt-1 text-xs text-white/60" data-testid="rapid-review-current-meta">{currentDetail.submission.crew_label} · {currentDetail.submission.truck_number} · {currentDetail.submission.service_type}</p>
                      </div>
                      <Badge className="border-0 bg-white/10 text-white" data-testid="rapid-review-current-status">Edit full rubric later</Badge>
                    </div>

                    <div className="relative aspect-[4/5] w-full bg-[#101612]" ref={surfaceRef} onPointerDown={handlePointerDown} onPointerMove={handlePointerMove} onPointerUp={handlePointerUp} onPointerLeave={handlePointerUp}>
                      {currentPhoto ? <img src={currentPhoto.media_url} alt={currentPhoto.filename} className="h-full w-full object-cover" data-testid="rapid-review-main-image" /> : <div className="flex h-full items-center justify-center text-white/60">No image available</div>}
                      <div className={`pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 rounded-full px-4 py-3 text-sm font-semibold transition ${hudDirection === "fail" ? "bg-[#7a2323]/80 text-white" : "bg-[#7a2323]/35 text-white/80"}`} data-testid="rapid-review-hud-left"><ArrowLeft className="mb-1 h-4 w-4" />Fail</div>
                      <div className={`pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 rounded-full px-4 py-3 text-sm font-semibold transition ${hudDirection === "standard" ? "bg-[#2d5a27]/80 text-white" : "bg-[#2d5a27]/35 text-white/80"}`} data-testid="rapid-review-hud-right"><ArrowRight className="mb-1 h-4 w-4" />Standard</div>
                      <div className={`pointer-events-none absolute left-1/2 top-3 -translate-x-1/2 rounded-full px-4 py-3 text-sm font-semibold transition ${hudDirection === "exemplary" ? "bg-[#2a5f73]/80 text-white" : "bg-[#2a5f73]/35 text-white/80"}`} data-testid="rapid-review-hud-up"><ChevronUp className="mb-1 h-4 w-4" />Exemplary</div>
                      <div className={`pointer-events-none absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full px-4 py-3 text-sm font-semibold transition ${hudDirection === "concern" ? "bg-[#9a5b15]/80 text-white" : "bg-[#9a5b15]/35 text-white/80"}`} data-testid="rapid-review-hud-down"><ChevronDown className="mb-1 h-4 w-4" />Concern</div>
                      <svg className="pointer-events-none absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none" data-testid="rapid-review-annotation-layer">
                        {currentDrawings.map((path, index) => <path key={`${currentItem.id}-stroke-${index}`} d={path} fill="none" stroke="#fbbf24" strokeWidth="0.6" strokeLinecap="round" strokeLinejoin="round" />)}
                        {draftPath ? <path d={draftPath} fill="none" stroke="#fbbf24" strokeWidth="0.6" strokeLinecap="round" strokeLinejoin="round" /> : null}
                      </svg>
                    </div>
                  </motion.div>
                </motion.div>
              </AnimatePresence>

              <div className="grid gap-3 sm:grid-cols-2" data-testid="rapid-review-action-row">
                {Object.entries(RATING_CONFIG).map(([key, config]) => (
                  <Button key={key} type="button" disabled={saving} onClick={() => requestRating(key)} className={`h-14 rounded-[20px] text-white ${config.color}`} data-testid={`rapid-review-${key}-button`}>
                    {config.label}
                  </Button>
                ))}
              </div>

              <Button type="button" disabled={saving} onClick={skipCurrent} className="h-12 w-full rounded-[20px] bg-white/10 text-white hover:bg-white/15" data-testid="rapid-review-skip-button">Skip item</Button>
            </>
          ) : (
            <Card className="rounded-[36px] border-white/10 bg-black/15 text-white backdrop-blur-xl" data-testid="rapid-review-empty-state">
              <CardContent className="flex min-h-[420px] flex-col items-center justify-center p-10 text-center">
                <p className="text-xs font-semibold uppercase tracking-[0.3em] text-white/50">Rapid review queue clear</p>
                <h2 className="mt-4 font-[Outfit] text-4xl font-semibold">You’re caught up.</h2>
                <Button type="button" onClick={loadQueue} className="mt-6 rounded-full bg-white/10 text-white hover:bg-white/15" data-testid="rapid-review-refresh-button">Refresh queue</Button>
              </CardContent>
            </Card>
          )}
        </div>

        <Card className="rounded-[32px] border-white/10 bg-black/15 text-white backdrop-blur-xl" data-testid="rapid-review-queue-card">
          <CardContent className="p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.26em] text-white/55">Queue strip</p>
                <p className="mt-2 text-sm text-white/75">{queue.length} remaining submissions ready for summary rating.</p>
              </div>
              <Badge className="border-0 bg-white/12 text-white" data-testid="rapid-review-selected-count">{selectedIds.length} selected</Badge>
            </div>

            <div className="mt-4 grid gap-2 sm:grid-cols-2" data-testid="rapid-review-bulk-actions">
              <Button type="button" onClick={() => handleBulkStandard("standard")} disabled={bulkSaving} className="rounded-2xl bg-[#2d5a27] hover:bg-[#22441d]" data-testid="rapid-review-bulk-standard-button">Bulk standard</Button>
              <Button type="button" onClick={() => handleBulkStandard("concern")} disabled={bulkSaving} className="rounded-2xl bg-[#9a5b15] hover:bg-[#7d4a11]" data-testid="rapid-review-bulk-concern-button">Bulk concern</Button>
            </div>

            <div className="mt-4 space-y-3" data-testid="rapid-review-queue-list">
              {queue.map((item, index) => (
                <div key={item.id} className={`w-full rounded-[24px] border p-4 ${index === currentIndex ? "border-white/30 bg-white/15" : "border-white/10 bg-white/5"}`} data-testid={`rapid-review-queue-item-${item.id}`}>
                  <div className="flex items-start gap-3">
                    <Checkbox checked={selectedIds.includes(item.id)} onCheckedChange={(checked) => setSelectedIds((current) => checked ? [...new Set([...current, item.id])] : current.filter((value) => value !== item.id))} className="mt-1 border-white/40 data-[state=checked]:bg-white data-[state=checked]:text-[#18241d]" data-testid={`rapid-review-select-${item.id}`} />
                    <button type="button" onClick={() => setCurrentIndex(index)} className="min-w-0 flex-1 text-left" data-testid={`rapid-review-open-${item.id}`}>
                      <p className="truncate text-sm font-semibold text-white">{item.job_name_input || item.job_id || item.submission_code}</p>
                      <p className="mt-1 text-xs text-white/65">{item.crew_label} · {item.service_type}</p>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
        <Card className="rounded-[32px] border-white/10 bg-black/15 text-white backdrop-blur-xl" data-testid="rapid-review-side-panel">
          <CardContent className="space-y-5 p-5">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.26em] text-white/55">Summary scoring</p>
              <p className="mt-2 text-sm text-white/72">Each swipe writes one overall rating now. Reviewers can edit detailed category scores later in the standard review screens.</p>
            </div>

            <div className="rounded-[24px] border border-white/10 bg-white/5 p-4" data-testid="rapid-review-sum-card">
              <div className="flex items-center gap-2 text-sm font-semibold text-white"><Sparkles className="h-4 w-4" />Standardized rubric sums</div>
              <div className="mt-3 space-y-2 text-sm text-white/72">
                {Object.entries(RATING_CONFIG).map(([key, config]) => (
                  <div key={key} className="flex items-center justify-between gap-3">
                    <span>{config.label}</span>
                    <span data-testid={`rapid-review-sum-${key}`}>{projectedSums[key] ?? 0}%</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[24px] border border-white/10 bg-white/5 p-4" data-testid="rapid-review-autostandard-toggle">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-white">Auto-standard clean items</p>
                  <p className="mt-1 text-sm text-white/65">When enabled, skipping a clean item commits “Standard”.</p>
                </div>
                <Switch checked={autoStandard} onCheckedChange={setAutoStandard} data-testid="rapid-review-autostandard-switch" />
              </div>
            </div>

            <div className="rounded-[24px] border border-white/10 bg-white/5 p-4" data-testid="rapid-review-tag-card">
              <div className="flex items-center gap-2 text-sm font-semibold text-white"><MessageSquareQuote className="h-4 w-4" />Issue tag</div>
              <Select value={issueTag} onValueChange={setIssueTag}>
                <SelectTrigger className="mt-3 h-11 rounded-2xl border-white/15 bg-black/20 text-white" data-testid="rapid-review-tag-select">
                  <SelectValue placeholder="Choose tag" />
                </SelectTrigger>
                <SelectContent>
                  {QUICK_TAGS.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>

            <div className="rounded-[24px] border border-white/10 bg-white/5 p-4" data-testid="rapid-review-annotation-controls">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-sm font-semibold text-white"><Paintbrush className="h-4 w-4" />Inline annotation</div>
                <Switch checked={annotationMode} onCheckedChange={setAnnotationMode} data-testid="rapid-review-annotation-switch" />
              </div>
              <div className="mt-4 flex gap-2">
                <Button type="button" variant="outline" onClick={() => setDrawings((current) => ({ ...current, [currentItem?.id]: [] }))} className="flex-1 rounded-2xl border-white/15 bg-transparent text-white hover:bg-white/10" data-testid="rapid-review-clear-annotation-button">Clear</Button>
                <Button type="button" variant="outline" onClick={skipCurrent} className="flex-1 rounded-2xl border-white/15 bg-transparent text-white hover:bg-white/10" data-testid="rapid-review-side-skip-button">Skip</Button>
              </div>
            </div>

            <div className="rounded-[24px] border border-white/10 bg-white/5 p-4 text-sm text-white/72" data-testid="rapid-review-shortcuts-card">
              <p className="font-semibold text-white">Swipe + key map</p>
              <ul className="mt-3 space-y-2">
                <li>← fail</li>
                <li>↓ concern</li>
                <li>→ standard</li>
                <li>↑ exemplary</li>
                <li>S skip</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>

      {pendingRating ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 px-4" data-testid="rapid-review-comment-modal">
          <div className="w-full max-w-lg rounded-[30px] border border-white/10 bg-[#162019] p-6 shadow-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-white/50">Comment required</p>
            <h2 className="mt-3 font-[Outfit] text-3xl font-semibold text-white">{RATING_CONFIG[pendingRating].label} needs reviewer context</h2>
            <p className="mt-2 text-sm text-white/68">Add a short note before committing this rapid review rating.</p>
            <Textarea value={reviewerComment} onChange={(event) => setReviewerComment(event.target.value)} className="mt-4 min-h-[120px] rounded-[22px] border-white/15 bg-black/20 text-white" placeholder="Add reviewer context..." data-testid="rapid-review-comment-input" />
            <div className="mt-5 flex gap-3">
              <Button type="button" variant="outline" onClick={() => { setPendingRating(""); setReviewerComment(""); }} className="flex-1 rounded-2xl border-white/15 bg-transparent text-white hover:bg-white/10" data-testid="rapid-review-comment-cancel-button">Cancel</Button>
              <Button type="button" disabled={!reviewerComment.trim()} onClick={() => submitRating(pendingRating, currentItem?.id, reviewerComment)} className="flex-1 rounded-2xl bg-[#2d5a27] hover:bg-[#22441d] disabled:opacity-50" data-testid="rapid-review-comment-commit-button">Commit comment</Button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}