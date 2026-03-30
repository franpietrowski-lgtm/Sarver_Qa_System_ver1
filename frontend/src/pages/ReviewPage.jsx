import { useEffect, useMemo, useState } from "react";
import { ClipboardList, Flag, Link2, SearchCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { authGet, authPost } from "@/lib/api";
import { toast } from "sonner";


export default function ReviewPage() {
  const [submissions, setSubmissions] = useState([]);
  const [rubrics, setRubrics] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState(null);
  const [filterBy, setFilterBy] = useState("all");
  const [scores, setScores] = useState({});
  const [comments, setComments] = useState("");
  const [disposition, setDisposition] = useState("pass");
  const [flaggedIssues, setFlaggedIssues] = useState("");
  const [selectedJobId, setSelectedJobId] = useState("");
  const [saving, setSaving] = useState(false);

  const loadPage = async (nextFilter = filterBy) => {
    const [submissionResponse, rubricResponse, jobsResponse] = await Promise.all([
      authGet(`/submissions?scope=management&filter_by=${nextFilter}`),
      authGet("/rubrics"),
      authGet("/jobs"),
    ]);
    setSubmissions(submissionResponse);
    setRubrics(rubricResponse);
    setJobs(jobsResponse);
    if (!selectedId && submissionResponse[0]) {
      setSelectedId(submissionResponse[0].id);
    }
  };

  useEffect(() => {
    loadPage();
  }, []);

  useEffect(() => {
    if (selectedId) {
      authGet(`/submissions/${selectedId}`)
        .then((response) => {
          setDetail(response);
          setSelectedJobId(response.job?.id || response.submission?.matched_job_id || "");
          setComments(response.management_review?.comments || "");
          setDisposition(response.management_review?.disposition || "pass");
          setFlaggedIssues((response.management_review?.flagged_issues || []).join(", "));
          const rubricCategories = response.rubric?.categories || [];
          const nextScores = {};
          rubricCategories.forEach((category) => {
            nextScores[category.key] = response.management_review?.category_scores?.[category.key] ?? Math.max(category.max_score - 1, 1);
          });
          setScores(nextScores);
        })
        .catch(() => setDetail(null));
    }
  }, [selectedId]);

  const rubric = useMemo(() => {
    if (detail?.rubric) return detail.rubric;
    return rubrics.find((item) => item.service_type === detail?.submission?.service_type);
  }, [detail, rubrics]);

  const handleMatchOverride = async () => {
    if (!selectedJobId || !detail?.submission) return;
    try {
      const matchedJob = jobs.find((job) => job.id === selectedJobId);
      await authPost(`/submissions/${detail.submission.id}/match`, {
        job_id: selectedJobId,
        service_type: matchedJob?.service_type || detail.submission.service_type,
      });
      toast.success("Job match updated.");
      await loadPage(filterBy);
      const refreshed = await authGet(`/submissions/${detail.submission.id}`);
      setDetail(refreshed);
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Unable to update match");
    }
  };

  const handleSubmitReview = async (event) => {
    event.preventDefault();
    if (!detail?.submission || !rubric) return;
    setSaving(true);
    try {
      await authPost("/reviews/management", {
        submission_id: detail.submission.id,
        job_id: selectedJobId,
        service_type: detail.submission.service_type,
        category_scores: scores,
        comments,
        disposition,
        flagged_issues: flaggedIssues.split(",").map((item) => item.trim()).filter(Boolean),
      });
      toast.success("Management review saved.");
      await loadPage(filterBy);
      const refreshed = await authGet(`/submissions/${detail.submission.id}`);
      setDetail(refreshed);
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Review save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="grid gap-6 xl:grid-cols-[360px_1fr]" data-testid="review-page">
      <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="review-queue-card">
        <CardContent className="p-6">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Management review queue</p>
              <h2 className="mt-2 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]">Pending proof sets</h2>
            </div>
            <ClipboardList className="h-6 w-6 text-[#243e36]" />
          </div>

          <select value={filterBy} onChange={(event) => { setFilterBy(event.target.value); loadPage(event.target.value); }} className="mt-5 h-12 w-full rounded-2xl border border-transparent bg-[#edf0e7] px-4 text-sm" data-testid="review-filter-select">
            <option value="all">All items</option>
            <option value="low_confidence">Low confidence match</option>
            <option value="incomplete_photo_sets">Incomplete photo sets</option>
            <option value="flagged">Flagged submissions</option>
          </select>

          <div className="mt-5 space-y-3">
            {submissions.map((submission) => (
              <button key={submission.id} type="button" onClick={() => setSelectedId(submission.id)} className={`w-full rounded-[24px] border p-4 text-left transition-transform hover:-translate-y-0.5 ${selectedId === submission.id ? "border-[#243e36] bg-[#edf0e7]" : "border-border bg-[#f6f6f2]"}`} data-testid={`review-queue-item-${submission.id}`}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-[#243e36]">{submission.job_id || submission.submission_code}</p>
                    <p className="mt-1 text-sm text-[#5c6d64]">{submission.crew_label} · {submission.truck_number}</p>
                  </div>
                  <Badge className="border-0 bg-white px-3 py-1 text-[#243e36]">{submission.status}</Badge>
                </div>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {detail ? (
        <div className="space-y-6">
          <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="review-detail-card">
            <CardContent className="p-8">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Reviewing submission</p>
                  <h2 className="mt-2 font-[Cabinet_Grotesk] text-4xl font-black tracking-tight text-[#111815]" data-testid="review-detail-title">{detail.submission.job_id || detail.submission.submission_code}</h2>
                  <p className="mt-2 text-sm text-[#5c6d64]" data-testid="review-detail-meta">{detail.submission.crew_label} · {detail.submission.service_type} · Confidence {Math.round((detail.submission.match_confidence || 0) * 100)}%</p>
                </div>
                <Badge className="border-0 bg-[#edf0e7] px-3 py-1 text-[#243e36]" data-testid="review-match-status-badge">{detail.submission.match_status}</Badge>
              </div>

              <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3" data-testid="review-photo-grid">
                {detail.submission.photo_files?.map((photo) => (
                  <div key={photo.id} className="overflow-hidden rounded-[28px] border border-border bg-[#f6f6f2]" data-testid={`review-photo-card-${photo.id}`}>
                    <div className="aspect-[4/3] overflow-hidden bg-[#dde4d6]"><img src={photo.media_url} alt={photo.filename} className="h-full w-full object-cover" /></div>
                    <div className="p-4 text-sm font-semibold text-[#243e36]">{photo.filename}</div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="review-scoring-card">
            <CardContent className="p-8">
              <div className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
                <div className="space-y-4">
                  <div className="rounded-[24px] border border-border bg-[#f6f6f2] p-4">
                    <div className="flex items-center gap-2 text-[#243e36]"><SearchCheck className="h-5 w-5" /><p className="text-sm font-semibold">Suggested job match</p></div>
                    <select value={selectedJobId} onChange={(event) => setSelectedJobId(event.target.value)} className="mt-3 h-12 w-full rounded-2xl border border-transparent bg-white px-4 text-sm" data-testid="review-match-job-select">
                      {jobs.map((job) => (<option key={job.id} value={job.id}>{job.job_id} · {job.property_name}</option>))}
                    </select>
                    <Button type="button" onClick={handleMatchOverride} className="mt-3 h-11 w-full rounded-2xl bg-[#243e36] hover:bg-[#1a2c26]" data-testid="review-confirm-match-button"><Link2 className="mr-2 h-4 w-4" />Confirm / override match</Button>
                  </div>

                  <div className="rounded-[24px] border border-border bg-[#f6f6f2] p-4">
                    <p className="text-sm font-semibold text-[#243e36]">Submission metadata</p>
                    <div className="mt-3 space-y-2 text-sm text-[#5c6d64]">
                      <p data-testid="review-metadata-truck">Truck: {detail.submission.truck_number}</p>
                      <p data-testid="review-metadata-area">Area: {detail.submission.area_tag || "Not tagged"}</p>
                      <p data-testid="review-metadata-note">Note: {detail.submission.note || "No note"}</p>
                    </div>
                  </div>
                </div>

                <form className="space-y-4" onSubmit={handleSubmitReview} data-testid="review-scoring-form">
                  <div className="grid gap-4 md:grid-cols-2">
                    {rubric?.categories?.map((category) => (
                      <div key={category.key} className="rounded-[24px] border border-border bg-[#f6f6f2] p-4" data-testid={`review-score-card-${category.key}`}>
                        <label className="text-sm font-semibold text-[#243e36]">{category.label}</label>
                        <Input type="number" min="0" max={category.max_score} step="0.5" value={scores[category.key] ?? ""} onChange={(event) => setScores((current) => ({ ...current, [category.key]: Number(event.target.value) }))} className="mt-3 h-11 rounded-2xl border-transparent bg-white" data-testid={`rubric-score-input-${category.key}`} />
                        <p className="mt-2 text-xs text-[#5c6d64]">Weight {Math.round(category.weight * 100)}% · Max {category.max_score}</p>
                      </div>
                    ))}
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <label className="mb-2 block text-sm font-semibold text-[#243e36]">Disposition</label>
                      <select value={disposition} onChange={(event) => setDisposition(event.target.value)} className="h-12 w-full rounded-2xl border border-transparent bg-[#edf0e7] px-4 text-sm" data-testid="review-disposition-select">
                        <option value="pass">pass</option>
                        <option value="pass with notes">pass with notes</option>
                        <option value="correction required">correction required</option>
                        <option value="insufficient evidence">insufficient evidence</option>
                        <option value="escalate to owner">escalate to owner</option>
                      </select>
                    </div>
                    <div>
                      <label className="mb-2 block text-sm font-semibold text-[#243e36]">Flagged issues</label>
                      <Input value={flaggedIssues} onChange={(event) => setFlaggedIssues(event.target.value)} placeholder="comma,separated,issues" className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="review-flagged-issues-input" />
                    </div>
                  </div>

                  <div>
                    <label className="mb-2 block text-sm font-semibold text-[#243e36]">Reviewer comments</label>
                    <Textarea value={comments} onChange={(event) => setComments(event.target.value)} className="min-h-[110px] rounded-2xl border-transparent bg-[#edf0e7]" data-testid="review-comments-input" />
                  </div>

                  <Button type="submit" disabled={saving} className="h-12 rounded-2xl bg-[#243e36] hover:bg-[#1a2c26]" data-testid="review-submit-button"><Flag className="mr-2 h-4 w-4" />{saving ? "Saving review..." : "Save management review"}</Button>
                </form>
              </div>
            </CardContent>
          </Card>
        </div>
      ) : (
        <Card className="rounded-[32px] border-border/80 bg-white p-12 text-center text-[#243e36]" data-testid="review-empty-state">Select a queue item to review.</Card>
      )}
    </div>
  );
}