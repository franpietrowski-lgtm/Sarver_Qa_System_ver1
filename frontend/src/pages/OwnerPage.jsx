import { useEffect, useMemo, useState } from "react";
import { Scale, ShieldCheck, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { authGet, authPost } from "@/lib/api";
import { toast } from "sonner";


export default function OwnerPage() {
  const [submissions, setSubmissions] = useState([]);
  const [rubrics, setRubrics] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState(null);
  const [scores, setScores] = useState({});
  const [comments, setComments] = useState("");
  const [finalDisposition, setFinalDisposition] = useState("pass");
  const [trainingInclusion, setTrainingInclusion] = useState("approved");
  const [exclusionReason, setExclusionReason] = useState("");
  const [saving, setSaving] = useState(false);

  const loadPage = async () => {
    const [submissionResponse, rubricResponse] = await Promise.all([
      authGet("/submissions?scope=owner&filter_by=all"),
      authGet("/rubrics"),
    ]);
    setSubmissions(submissionResponse);
    setRubrics(rubricResponse);
    if (!selectedId && submissionResponse[0]) {
      setSelectedId(submissionResponse[0].id);
    }
  };

  useEffect(() => {
    loadPage();
  }, []);

  useEffect(() => {
    if (selectedId) {
      authGet(`/submissions/${selectedId}`).then((response) => {
        setDetail(response);
        setComments(response.owner_review?.comments || "");
        setFinalDisposition(response.owner_review?.final_disposition || response.management_review?.disposition || "pass");
        setTrainingInclusion(response.owner_review?.training_inclusion || "approved");
        setExclusionReason(response.owner_review?.exclusion_reason || "");
        const nextScores = {};
        (response.rubric?.categories || []).forEach((category) => {
          nextScores[category.key] = response.owner_review?.category_scores?.[category.key] ?? response.management_review?.category_scores?.[category.key] ?? category.max_score;
        });
        setScores(nextScores);
      });
    }
  }, [selectedId]);

  const rubric = useMemo(() => {
    if (detail?.rubric) return detail.rubric;
    return rubrics.find((item) => item.service_type === detail?.submission?.service_type);
  }, [detail, rubrics]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!detail?.submission) return;
    setSaving(true);
    try {
      await authPost("/reviews/owner", {
        submission_id: detail.submission.id,
        category_scores: scores,
        comments,
        final_disposition: finalDisposition,
        training_inclusion: trainingInclusion,
        exclusion_reason: exclusionReason,
      });
      toast.success("Owner calibration saved.");
      await loadPage();
      const refreshed = await authGet(`/submissions/${detail.submission.id}`);
      setDetail(refreshed);
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Owner review failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="grid gap-6 xl:grid-cols-[360px_1fr]" data-testid="owner-page">
      <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="owner-queue-card">
        <CardContent className="p-6">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Owner queue</p>
          <h2 className="mt-2 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]">Calibration & dataset approval</h2>
          <div className="mt-5 space-y-3">
            {submissions.map((submission) => (
              <button key={submission.id} type="button" onClick={() => setSelectedId(submission.id)} className={`w-full rounded-[24px] border p-4 text-left ${selectedId === submission.id ? "border-[#243e36] bg-[#edf0e7]" : "border-border bg-[#f6f6f2]"}`} data-testid={`owner-queue-item-${submission.id}`}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-[#243e36]">{submission.job_name_input || submission.job_id || submission.submission_code}</p>
                    <p className="mt-1 text-sm text-[#5c6d64]">{submission.service_type} · {submission.crew_label}</p>
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
          <Card className="rounded-[32px] border-border/80 bg-[#243e36] text-white shadow-sm" data-testid="owner-summary-card">
            <CardContent className="grid gap-4 p-8 md:grid-cols-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#d8f3dc]">Submission</p>
                <p className="mt-2 text-2xl font-bold" data-testid="owner-summary-job-id">{detail.submission.job_name_input || detail.submission.job_id}</p>
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#d8f3dc]">Management score</p>
                <p className="mt-2 text-2xl font-bold" data-testid="owner-summary-management-score">{detail.management_review?.total_score ?? "—"}</p>
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#d8f3dc]">Variance</p>
                <p className="mt-2 text-2xl font-bold" data-testid="owner-summary-variance">{detail.owner_review?.variance_from_management ?? "Pending"}</p>
              </div>
            </CardContent>
          </Card>

          {detail.submission.field_report?.reported && (
            <Card className="rounded-[32px] border-[#f2c9bc] bg-[#fff6f1] shadow-sm" data-testid="owner-field-report-card">
              <CardContent className="p-8">
                <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#b45a42]">Field issue intake</p>
                <h3 className="mt-2 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]">Issue, damage, and note reporting</h3>
                <div className="mt-4 grid gap-4 lg:grid-cols-[0.85fr_1.15fr]">
                  <div className="space-y-2 text-sm text-[#5c6d64]">
                    <p data-testid="owner-field-report-type">Type: {detail.submission.field_report.type || "General field report"}</p>
                    <p data-testid="owner-field-report-notes">Notes: {detail.submission.field_report.notes || "No extra details"}</p>
                  </div>
                  {!!detail.submission.field_report.photo_files?.length && (
                    <div className="grid gap-4 sm:grid-cols-2" data-testid="owner-field-report-photo-grid">
                      {detail.submission.field_report.photo_files.map((photo) => (
                        <div key={photo.id} className="overflow-hidden rounded-[24px] border border-[#f2c9bc] bg-white">
                          <div className="aspect-[4/3] overflow-hidden bg-[#f5e3db]"><img src={photo.media_url} alt={photo.filename} className="h-full w-full object-cover" /></div>
                          <div className="p-4 text-sm font-semibold text-[#243e36]">{photo.filename}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="owner-form-card">
            <CardContent className="p-8">
              <form className="space-y-6" onSubmit={handleSubmit} data-testid="owner-review-form">
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {rubric?.categories?.map((category) => (
                    <div key={category.key} className="rounded-[24px] border border-border bg-[#f6f6f2] p-4" data-testid={`owner-score-card-${category.key}`}>
                      <label className="text-sm font-semibold text-[#243e36]">{category.label}</label>
                      <Input type="number" min="0" max={category.max_score} step="0.5" value={scores[category.key] ?? ""} onChange={(event) => setScores((current) => ({ ...current, [category.key]: Number(event.target.value) }))} className="mt-3 h-11 rounded-2xl border-transparent bg-white" data-testid={`owner-score-input-${category.key}`} />
                    </div>
                  ))}
                </div>

                <div className="grid gap-4 md:grid-cols-3">
                  <div>
                    <label className="mb-2 block text-sm font-semibold text-[#243e36]">Final disposition</label>
                    <select value={finalDisposition} onChange={(event) => setFinalDisposition(event.target.value)} className="h-12 w-full rounded-2xl border border-transparent bg-[#edf0e7] px-4 text-sm" data-testid="owner-final-disposition-select">
                      <option value="pass">pass</option>
                      <option value="pass with notes">pass with notes</option>
                      <option value="correction required">correction required</option>
                      <option value="insufficient evidence">insufficient evidence</option>
                    </select>
                  </div>
                  <div>
                    <label className="mb-2 block text-sm font-semibold text-[#243e36]">Training inclusion</label>
                    <select value={trainingInclusion} onChange={(event) => setTrainingInclusion(event.target.value)} className="h-12 w-full rounded-2xl border border-transparent bg-[#edf0e7] px-4 text-sm" data-testid="owner-training-inclusion-select">
                      <option value="approved">approved</option>
                      <option value="excluded">excluded</option>
                    </select>
                  </div>
                  <div>
                    <label className="mb-2 block text-sm font-semibold text-[#243e36]">Exclusion reason</label>
                    <Input value={exclusionReason} onChange={(event) => setExclusionReason(event.target.value)} className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="owner-exclusion-reason-input" />
                  </div>
                </div>

                <div className="grid gap-4 xl:grid-cols-[1fr_0.85fr]">
                  <div>
                    <Textarea value={comments} onChange={(event) => setComments(event.target.value)} className="min-h-[130px] rounded-2xl border-transparent bg-[#edf0e7]" data-testid="owner-comments-input" />
                    <p className="mt-2 text-xs text-[#5c6d64]" data-testid="owner-followup-hint">Choosing correction required or insufficient evidence automatically creates a crew-facing follow-up notification.</p>
                  </div>
                  <div className="rounded-[26px] border border-border bg-[#f6f6f2] p-5">
                    <div className="flex items-center gap-2 text-[#243e36]"><Scale className="h-5 w-5" /><p className="text-sm font-semibold">Calibration notes</p></div>
                    <div className="mt-3 space-y-2 text-sm text-[#5c6d64]">
                      <p data-testid="owner-management-disposition">Management disposition: {detail.management_review?.disposition || "Not reviewed yet"}</p>
                      <p data-testid="owner-current-inclusion">Current inclusion: {detail.owner_review?.training_inclusion || trainingInclusion}</p>
                    </div>
                  </div>
                </div>

                <Button type="submit" disabled={saving} className="h-12 rounded-2xl bg-[#243e36] hover:bg-[#1a2c26]" data-testid="owner-submit-button"><ShieldCheck className="mr-2 h-4 w-4" />{saving ? "Saving owner review..." : "Finalize owner calibration"}</Button>
              </form>
            </CardContent>
          </Card>

          <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="owner-photos-card">
            <CardContent className="p-8">
              <div className="flex items-center gap-2 text-[#243e36]"><Sparkles className="h-5 w-5" /><p className="text-sm font-semibold">Reference photos</p></div>
              <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {detail.submission.photo_files?.map((photo) => (
                  <div key={photo.id} className="overflow-hidden rounded-[28px] border border-border bg-[#f6f6f2]" data-testid={`owner-photo-card-${photo.id}`}>
                    <div className="aspect-[4/3] overflow-hidden bg-[#dde4d6]"><img src={photo.media_url} alt={photo.filename} className="h-full w-full object-cover" /></div>
                    <div className="p-4 text-sm font-semibold text-[#243e36]">{photo.filename}</div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="owner-ai-readiness-card">
            <CardContent className="p-8">
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Future AI grading path</p>
              <h3 className="mt-2 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]">The current human reviews are already building the learning dataset.</h3>
              <div className="mt-5 grid gap-4 md:grid-cols-3">
                {[
                  'Images stay linked to jobs, crews, service types, and timestamps.',
                  'Management and owner scores preserve calibration variance for training.',
                  'Owner-approved records can become the gold dataset for future automated checks.',
                ].map((item, index) => (
                  <div key={item} className="rounded-[24px] border border-border bg-[#f6f6f2] p-4 text-sm text-[#5c6d64]" data-testid={`owner-ai-readiness-item-${index + 1}`}>{item}</div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      ) : (
        <Card className="rounded-[32px] border-border/80 bg-white p-12 text-center text-[#243e36]" data-testid="owner-empty-state">Select an owner queue item to calibrate.</Card>
      )}
    </div>
  );
}