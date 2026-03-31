import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, ArrowRight, ChevronDown, ChevronUp, Flag, Highlighter, MoonStar, Paintbrush, SkipForward, SunMedium, X } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { authGet, authPost } from "@/lib/api";
import { useTheme } from "@/components/theme/ThemeProvider";
import { toast } from "sonner";


const QUICK_TAGS = [
  "quality-concern",
  "property-damage",
  "cleanup-missed",
  "training-follow-up",
];

const ownerModes = new Set(["owner"]);


function buildQuickScores(rubric, action) {
  const nextScores = {};
  (rubric?.categories || []).forEach((category) => {
    if (action === "pass") {
      nextScores[category.key] = category.max_score;
    } else if (action === "flag") {
      nextScores[category.key] = Math.max(Math.round(category.max_score * 0.6 * 2) / 2, 1);
    } else {
      nextScores[category.key] = 0;
    }
  });
  return nextScores;
}


export default function RapidReviewPage({ user }) {
  const navigate = useNavigate();
  const { isDark, toggleTheme } = useTheme();
  const scope = ownerModes.has(user?.role) ? "owner" : "management";
  const [queue, setQueue] = useState([]);
  const [detailMap, setDetailMap] = useState({});
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [bulkSaving, setBulkSaving] = useState(false);
  const [selectedIds, setSelectedIds] = useState([]);
  const [autoPass, setAutoPass] = useState(false);
  const [issueTag, setIssueTag] = useState(QUICK_TAGS[0]);
  const [annotationMode, setAnnotationMode] = useState(false);
  const [drawings, setDrawings] = useState({});
  const [draftPath, setDraftPath] = useState("");
  const [drawingActive, setDrawingActive] = useState(false);
  const surfaceRef = useRef(null);

  const currentItem = queue[currentIndex] || null;
  const currentDetail = currentItem ? detailMap[currentItem.id] : null;
  const currentPhoto = currentDetail?.submission?.photo_files?.[0] || null;
  const currentDrawings = drawings[currentItem?.id] || [];
  const filteredCount = useMemo(() => queue.filter((item) => item.service_type).length, [queue]);

  const loadQueue = async () => {
    setLoading(true);
    try {
      const response = await authGet(`/submissions?scope=${scope}&filter_by=all&page=1&limit=30`);
      const items = (response.items || []).filter((item) => item.service_type);
      setQueue(items);
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
      toast.error("Unable to preload one of the rapid review items.");
    }
  };

  useEffect(() => {
    loadQueue();
  }, [scope]);

  useEffect(() => {
    if (currentItem?.id) {
      preloadDetail(currentItem.id);
    }
    if (queue[currentIndex + 1]?.id) {
      preloadDetail(queue[currentIndex + 1].id);
    }
  }, [currentItem?.id, currentIndex, queue]);

  useEffect(() => {
    const handleKeyDown = (event) => {
      const tag = event.target?.tagName?.toLowerCase();
      if (["input", "textarea", "select"].includes(tag)) return;
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        submitRapidAction("fail");
      }
      if (event.key === "ArrowRight") {
        event.preventDefault();
        submitRapidAction("pass");
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        submitRapidAction("flag");
      }
      if (event.key === "ArrowDown") {
        event.preventDefault();
        moveNext();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  });

  const moveNext = () => {
    setDraftPath("");
    setAnnotationMode(false);
    if (!queue.length) return;
    setCurrentIndex((current) => Math.min(current + 1, Math.max(queue.length - 1, 0)));
  };

  const removeSubmissionFromQueue = (submissionId) => {
    setQueue((current) => {
      const nextQueue = current.filter((item) => item.id !== submissionId);
      setCurrentIndex((currentIndexValue) => Math.min(currentIndexValue, Math.max(nextQueue.length - 1, 0)));
      return nextQueue;
    });
    setSelectedIds((current) => current.filter((item) => item !== submissionId));
  };

  const buildPayload = (detail, action) => {
    const rubric = detail?.rubric;
    const serviceType = detail?.management_review?.service_type || detail?.submission?.service_type || detail?.job?.service_type;
    if (!rubric || !serviceType) {
      throw new Error("This submission needs a service type before rapid review.");
    }

    const annotationCount = (drawings[detail?.submission?.id] || []).length;
    const annotationNote = annotationCount ? `Annotation strokes: ${annotationCount}.` : "";
    const comments = [
      `Rapid review: ${action}`,
      action !== "pass" ? `Issue tag: ${issueTag}.` : "",
      annotationNote,
    ].filter(Boolean).join(" ");

    if (scope === "owner") {
      return {
        endpoint: "/reviews/owner",
        payload: {
          submission_id: detail.submission.id,
          category_scores: buildQuickScores(rubric, action),
          comments,
          final_disposition: action === "pass" ? "pass" : "correction required",
          training_inclusion: action === "pass" ? "approved" : "excluded",
          exclusion_reason: action === "pass" ? "" : issueTag,
        },
      };
    }

    return {
      endpoint: "/reviews/management",
      payload: {
        submission_id: detail.submission.id,
        job_id: detail.job?.id || detail.submission?.matched_job_id || null,
        service_type: serviceType,
        category_scores: buildQuickScores(rubric, action),
        comments,
        disposition: action === "pass" ? "pass" : "correction required",
        flagged_issues: action === "pass" ? [] : [issueTag],
      },
    };
  };

  const submitSingle = async (detail, action) => {
    const request = buildPayload(detail, action);
    await authPost(request.endpoint, request.payload);
  };

  const submitRapidAction = async (action, submissionId = currentItem?.id) => {
    if (!submissionId) return;
    const detail = detailMap[submissionId] || await authGet(`/submissions/${submissionId}`);
    setDetailMap((current) => ({ ...current, [submissionId]: detail }));
    setSaving(true);
    try {
      await submitSingle(detail, action);
      toast.success(`Rapid review marked ${action}.`);
      removeSubmissionFromQueue(submissionId);
    } catch (error) {
      toast.error(error?.response?.data?.detail || error.message || "Rapid review action failed");
    } finally {
      setSaving(false);
    }
  };

  const handleBulkAction = async (action) => {
    if (!selectedIds.length) {
      toast.error("Select at least one submission first.");
      return;
    }
    setBulkSaving(true);
    try {
      for (const submissionId of selectedIds) {
        const detail = detailMap[submissionId] || await authGet(`/submissions/${submissionId}`);
        setDetailMap((current) => ({ ...current, [submissionId]: detail }));
        await submitSingle(detail, action);
      }
      toast.success(`Bulk ${action} complete.`);
      setQueue((current) => current.filter((item) => !selectedIds.includes(item.id)));
      setSelectedIds([]);
      setCurrentIndex(0);
    } catch (error) {
      toast.error(error?.response?.data?.detail || error.message || "Bulk rapid review failed");
    } finally {
      setBulkSaving(false);
    }
  };

  const handleDragEnd = async (_, info) => {
    if (saving) return;
    if (info.offset.x >= 140) return submitRapidAction("pass");
    if (info.offset.x <= -140) return submitRapidAction("fail");
    if (info.offset.y <= -120) return submitRapidAction("flag");
    if (info.offset.y >= 120) return moveNext();
    if (autoPass && currentDetail?.submission?.field_report?.reported === false) {
      await submitRapidAction("pass");
    }
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

  const queueProgress = queue.length ? currentIndex + 1 : 0;

  if (loading) {
    return <div className="workspace-shell min-h-screen bg-[#0d120e] px-6 py-8 text-white" data-testid="rapid-review-loading-state">Loading rapid review...</div>;
  }

  return (
    <div className={`workspace-shell min-h-screen px-5 py-5 text-white ${isDark ? "theme-dark bg-[#0d120e]" : "bg-[#18241d]"}`} data-testid="rapid-review-page">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-[28px] border border-white/10 bg-black/15 px-5 py-4 backdrop-blur-xl" data-testid="rapid-review-topbar">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-white/55">Rapid review mode</p>
          <h1 className="mt-2 font-[Outfit] text-3xl font-semibold" data-testid="rapid-review-title">{scope === "owner" ? "Owner calibration sprint" : "Management QA sprint"}</h1>
          <p className="mt-1 text-sm text-white/70" data-testid="rapid-review-progress-text">{queue.length ? `${queueProgress} of ${queue.length} ready items` : "Queue complete"} · {filteredCount} reviewable service-tagged submissions</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-3 py-2" data-testid="rapid-review-autopass-toggle">
            <Switch checked={autoPass} onCheckedChange={setAutoPass} data-testid="rapid-review-autopass-switch" />
            <span className="text-sm text-white/80">Auto-pass if no flags</span>
          </div>
          <Button type="button" variant="outline" onClick={toggleTheme} className="rounded-full border-white/20 bg-white/10 text-white hover:bg-white/15" data-testid="rapid-review-theme-button">
            {isDark ? <SunMedium className="mr-2 h-4 w-4" /> : <MoonStar className="mr-2 h-4 w-4" />}
            {isDark ? "Default" : "Dark"}
          </Button>
          <Button type="button" variant="outline" onClick={() => navigate(scope === "owner" ? "/owner" : "/review")} className="rounded-full border-white/20 bg-white/10 text-white hover:bg-white/15" data-testid="rapid-review-exit-button">
            <X className="mr-2 h-4 w-4" />Exit mode
          </Button>
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-[320px_1fr_320px]">
        <Card className="rounded-[32px] border-white/10 bg-black/15 text-white backdrop-blur-xl" data-testid="rapid-review-queue-card">
          <CardContent className="p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.26em] text-white/55">Queue strip</p>
                <p className="mt-2 text-sm text-white/75">Select several items for bulk pass/fail.</p>
              </div>
              <Badge className="border-0 bg-white/12 text-white" data-testid="rapid-review-selected-count">{selectedIds.length} selected</Badge>
            </div>
            <div className="mt-4 flex gap-2">
              <Button type="button" onClick={() => handleBulkAction("pass")} disabled={bulkSaving} className="flex-1 rounded-2xl bg-[#2d5a27] hover:bg-[#22441d]" data-testid="rapid-review-bulk-pass-button">Bulk pass</Button>
              <Button type="button" onClick={() => handleBulkAction("fail")} disabled={bulkSaving} className="flex-1 rounded-2xl bg-[#8b2d2d] hover:bg-[#702222]" data-testid="rapid-review-bulk-fail-button">Bulk fail</Button>
            </div>
            <div className="mt-4 space-y-3" data-testid="rapid-review-queue-list">
              {queue.map((item, index) => (
                <div key={item.id} className={`w-full rounded-[24px] border p-4 transition-transform hover:-translate-y-0.5 ${index === currentIndex ? "border-white/30 bg-white/15" : "border-white/10 bg-white/5"}`} data-testid={`rapid-review-queue-item-${item.id}`}>
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

        <div className="space-y-4">
          {currentItem && currentDetail ? (
            <>
              <AnimatePresence mode="wait">
                <motion.div key={currentItem.id} initial={{ opacity: 0, x: 40 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -40 }} transition={{ duration: 0.18 }}>
                  <motion.div drag dragMomentum={false} onDragEnd={handleDragEnd} className="relative overflow-hidden rounded-[36px] border border-white/10 bg-black/15 shadow-2xl backdrop-blur-xl" data-testid="rapid-review-image-surface">
                    <div className="flex items-center justify-between gap-3 border-b border-white/10 px-5 py-4 text-sm text-white/70">
                      <div>
                        <p className="font-semibold text-white" data-testid="rapid-review-current-job">{currentDetail.submission.job_name_input || currentDetail.submission.job_id || currentDetail.submission.submission_code}</p>
                        <p className="mt-1 text-xs text-white/60" data-testid="rapid-review-current-meta">{currentDetail.submission.crew_label} · {currentDetail.submission.truck_number} · {currentDetail.submission.service_type}</p>
                      </div>
                      <Badge className="border-0 bg-white/10 text-white" data-testid="rapid-review-current-status">{currentDetail.submission.status}</Badge>
                    </div>

                    <div className="relative aspect-[16/10] w-full bg-[#101612]" ref={surfaceRef} onPointerDown={handlePointerDown} onPointerMove={handlePointerMove} onPointerUp={handlePointerUp} onPointerLeave={handlePointerUp}>
                      {currentPhoto ? <img src={currentPhoto.media_url} alt={currentPhoto.filename} className="h-full w-full object-contain" data-testid="rapid-review-main-image" /> : <div className="flex h-full items-center justify-center text-white/60" data-testid="rapid-review-image-empty">No image available</div>}
                      <svg className="pointer-events-none absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none" data-testid="rapid-review-annotation-layer">
                        {currentDrawings.map((path, index) => <path key={`${currentItem.id}-stroke-${index}`} d={path} fill="none" stroke="#fbbf24" strokeWidth="0.6" strokeLinecap="round" strokeLinejoin="round" />)}
                        {draftPath ? <path d={draftPath} fill="none" stroke="#fbbf24" strokeWidth="0.6" strokeLinecap="round" strokeLinejoin="round" /> : null}
                      </svg>
                      <div className="pointer-events-none absolute inset-x-0 bottom-0 flex items-center justify-between px-5 pb-5 text-xs uppercase tracking-[0.3em] text-white/45">
                        <span>← Fail</span>
                        <span>↑ Flag</span>
                        <span>↓ Skip</span>
                        <span>Pass →</span>
                      </div>
                    </div>
                  </motion.div>
                </motion.div>
              </AnimatePresence>

              <div className="grid gap-3 md:grid-cols-4" data-testid="rapid-review-action-row">
                <Button type="button" disabled={saving} onClick={() => submitRapidAction("fail")} className="h-14 rounded-[20px] bg-[#7a2323] text-white hover:bg-[#621b1b]" data-testid="rapid-review-fail-button"><ArrowLeft className="mr-2 h-4 w-4" />Fail</Button>
                <Button type="button" disabled={saving} onClick={() => submitRapidAction("flag")} className="h-14 rounded-[20px] bg-[#9a5b15] text-white hover:bg-[#7d4a11]" data-testid="rapid-review-flag-button"><ChevronUp className="mr-2 h-4 w-4" />Flag</Button>
                <Button type="button" disabled={saving} onClick={moveNext} className="h-14 rounded-[20px] bg-white/10 text-white hover:bg-white/15" data-testid="rapid-review-skip-button"><ChevronDown className="mr-2 h-4 w-4" />Skip</Button>
                <Button type="button" disabled={saving} onClick={() => submitRapidAction("pass")} className="h-14 rounded-[20px] bg-[#2d5a27] text-white hover:bg-[#22441d]" data-testid="rapid-review-pass-button"><ArrowRight className="mr-2 h-4 w-4" />Pass</Button>
              </div>
            </>
          ) : (
            <Card className="rounded-[36px] border-white/10 bg-black/15 text-white backdrop-blur-xl" data-testid="rapid-review-empty-state">
              <CardContent className="flex min-h-[620px] flex-col items-center justify-center p-10 text-center">
                <p className="text-xs font-semibold uppercase tracking-[0.3em] text-white/50">Rapid review queue clear</p>
                <h2 className="mt-4 font-[Outfit] text-4xl font-semibold">You’re caught up.</h2>
                <p className="mt-3 max-w-md text-sm text-white/70">All current submissions with a service type have been processed. Return to the main workflow or refresh for new work.</p>
                <Button type="button" onClick={loadQueue} className="mt-6 rounded-full bg-white/10 text-white hover:bg-white/15" data-testid="rapid-review-refresh-button">Refresh queue</Button>
              </CardContent>
            </Card>
          )}
        </div>

        <Card className="rounded-[32px] border-white/10 bg-black/15 text-white backdrop-blur-xl" data-testid="rapid-review-side-panel">
          <CardContent className="space-y-5 p-5">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.26em] text-white/55">Flagging tools</p>
              <p className="mt-2 text-sm text-white/72">Draw on the image surface, choose the issue tag, then flag or fail in one motion.</p>
            </div>
            <div className="rounded-[24px] border border-white/10 bg-white/5 p-4" data-testid="rapid-review-tag-card">
              <div className="flex items-center gap-2 text-sm font-semibold text-white"><Flag className="h-4 w-4" />Issue tag</div>
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
                <div className="flex items-center gap-2 text-sm font-semibold text-white"><Paintbrush className="h-4 w-4" />Annotation draw</div>
                <Switch checked={annotationMode} onCheckedChange={setAnnotationMode} data-testid="rapid-review-annotation-switch" />
              </div>
              <p className="mt-3 text-sm text-white/65">Annotation strokes stay visible while you process the current item.</p>
              <div className="mt-4 flex gap-2">
                <Button type="button" variant="outline" onClick={() => setDrawings((current) => ({ ...current, [currentItem?.id]: [] }))} className="flex-1 rounded-2xl border-white/15 bg-transparent text-white hover:bg-white/10" data-testid="rapid-review-clear-annotation-button"><Highlighter className="mr-2 h-4 w-4" />Clear</Button>
                <Button type="button" variant="outline" onClick={moveNext} className="flex-1 rounded-2xl border-white/15 bg-transparent text-white hover:bg-white/10" data-testid="rapid-review-skip-side-button"><SkipForward className="mr-2 h-4 w-4" />Skip</Button>
              </div>
            </div>
            <div className="rounded-[24px] border border-white/10 bg-white/5 p-4 text-sm text-white/72" data-testid="rapid-review-shortcuts-card">
              <p className="font-semibold text-white">Keyboard / gesture map</p>
              <ul className="mt-3 space-y-2">
                <li>Left / swipe left → fail</li>
                <li>Right / swipe right → pass</li>
                <li>Up / swipe up → flag</li>
                <li>Down / swipe down → skip</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}