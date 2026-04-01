import { Activity, Boxes, Copy, FolderInput, QrCode, ShieldCheck, Smartphone, UploadCloud, Wrench } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { QRCodeSVG } from "qrcode.react";

import StatCard from "@/components/common/StatCard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { authGet, authPatch, authPost } from "@/lib/api";
import { toast } from "sonner";


const DIVISIONS = ["Maintenance", "Install", "Tree", "Plant Healthcare", "Winter Services"];


export default function OverviewPage({ user }) {
  const [overview, setOverview] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [crewLinks, setCrewLinks] = useState([]);
  const [selectedCrewId, setSelectedCrewId] = useState("");
  const [crewForm, setCrewForm] = useState({ label: "", truck_number: "", division: DIVISIONS[0], assignment: "" });
  const [equipmentLogs, setEquipmentLogs] = useState([]);
  const rapidReviewUrl = useMemo(() => (typeof window !== "undefined" ? `${window.location.origin}/rapid-review/mobile` : ""), []);

  useEffect(() => {
    const load = async () => {
      const [overviewResponse, submissionsResponse, crewResponse, equipmentResponse] = await Promise.all([
        authGet("/dashboard/overview"),
        authGet("/submissions?scope=all&page=1&limit=6"),
        authGet("/crew-access-links?status=active&page=1&limit=20"),
        authGet("/equipment-logs?page=1&limit=6"),
      ]);
      setOverview(overviewResponse);
      setSubmissions(submissionsResponse.items || []);
      setCrewLinks(crewResponse.items || []);
      setEquipmentLogs(equipmentResponse.items || []);
      if (crewResponse.items?.[0]) {
        setSelectedCrewId(crewResponse.items[0].id);
        setCrewForm({
          label: crewResponse.items[0].label,
          truck_number: crewResponse.items[0].truck_number,
          division: crewResponse.items[0].division,
          assignment: crewResponse.items[0].assignment || "",
        });
      }
    };

    load();
  }, []);

  if (!overview) {
    return <div className="rounded-[28px] border border-border bg-white p-10 text-center text-[#243e36]" data-testid="overview-loading-state">Loading overview...</div>;
  }

  const storage = overview.storage || overview.drive;
  const selectedCrew = crewLinks.find((item) => item.id === selectedCrewId);
  const copyRapidReviewLink = async () => {
    await navigator.clipboard.writeText(rapidReviewUrl);
    toast.success("Rapid review link copied.");
  };

  const handleCrewSelection = (crewId) => {
    setSelectedCrewId(crewId);
    const nextCrew = crewLinks.find((item) => item.id === crewId);
    if (!nextCrew) return;
    setCrewForm({ label: nextCrew.label, truck_number: nextCrew.truck_number, division: nextCrew.division, assignment: nextCrew.assignment || "" });
  };

  const saveCrewMetadata = async () => {
    if (!selectedCrewId) return;
    try {
      const response = await authPatch(`/crew-access-links/${selectedCrewId}`, crewForm);
      setCrewLinks((current) => current.map((item) => item.id === selectedCrewId ? response : item));
      toast.success("Crew QR metadata updated.");
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Unable to update crew QR");
    }
  };

  const forwardEquipmentLog = async (logId) => {
    try {
      await authPost(`/equipment-logs/${logId}/forward-to-owner`, {});
      setEquipmentLogs((current) => current.map((item) => item.id === logId ? { ...item, forwarded_to_owner: true } : item));
      toast.success("Red-tag forwarded to Owner.");
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Unable to forward red-tag");
    }
  };

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
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Rapid review mobile launch</p>
            <h3 className="mt-2 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]">Scan the phone link and open the swipe lane where admins actually review.</h3>
            <p className="mt-2 text-sm text-[#5c6d64]">This is a mobile-only admin flow. Scan the QR from an admin phone, or copy the link to send directly.</p>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            <div className="rounded-[28px] border border-border bg-[#f6f6f2] p-4" data-testid="overview-rapid-review-qr-card">
              <QRCodeSVG value={rapidReviewUrl} size={128} bgColor="transparent" fgColor="#243e36" />
            </div>
            <div className="space-y-3">
              <Button asChild className="h-11 rounded-2xl bg-[#243e36] hover:bg-[#1a2c26]" data-testid="overview-open-mobile-rapid-review-button">
                <Link to="/rapid-review/mobile"><Smartphone className="mr-2 h-4 w-4" />Open mobile link</Link>
              </Button>
              <Button type="button" variant="outline" onClick={copyRapidReviewLink} className="h-11 rounded-2xl border-[#243e36]/15 bg-white text-[#243e36] hover:bg-[#edf0e7]" data-testid="overview-copy-rapid-review-link-button">
                <Copy className="mr-2 h-4 w-4" />Copy phone link
              </Button>
              <div className="flex items-center gap-2 text-sm text-[#5c6d64]"><QrCode className="h-4 w-4" />Admin phones only</div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="overview-crew-qr-editor-card">
          <CardContent className="p-6 sm:p-8">
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Crew QR updates</p>
            <h3 className="mt-2 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]">Any admin role can update active crew QR metadata from the dashboard.</h3>
            <div className="mt-6 space-y-4">
              <Select value={selectedCrewId} onValueChange={handleCrewSelection}>
                <SelectTrigger className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="overview-crew-select"><SelectValue placeholder="Choose crew" /></SelectTrigger>
                <SelectContent>
                  {crewLinks.map((item) => <SelectItem key={item.id} value={item.id}>{item.label} · {item.division}</SelectItem>)}
                </SelectContent>
              </Select>
              <Input value={crewForm.label} onChange={(event) => setCrewForm((current) => ({ ...current, label: event.target.value }))} placeholder="Crew label" className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="overview-crew-label-input" />
              <div className="grid gap-4 sm:grid-cols-2">
                <Input value={crewForm.truck_number} onChange={(event) => setCrewForm((current) => ({ ...current, truck_number: event.target.value }))} placeholder="Vehicle / truck" className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="overview-crew-truck-input" />
                <Select value={crewForm.division} onValueChange={(value) => setCrewForm((current) => ({ ...current, division: value }))}>
                  <SelectTrigger className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="overview-crew-division-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {DIVISIONS.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <Input value={crewForm.assignment} onChange={(event) => setCrewForm((current) => ({ ...current, assignment: event.target.value }))} placeholder="Assignment / route note" className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="overview-crew-assignment-input" />
              <Button type="button" onClick={saveCrewMetadata} className="h-12 w-full rounded-2xl bg-[#243e36] hover:bg-[#1a2c26]" data-testid="overview-save-crew-button">Save crew QR updates</Button>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="overview-equipment-log-card">
          <CardContent className="p-6 sm:p-8">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Equipment records</p>
                <h3 className="mt-2 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]">Recent maintenance + red-tag records</h3>
              </div>
              <Wrench className="h-6 w-6 text-[#243e36]" />
            </div>
            <div className="mt-6 space-y-3">
              {equipmentLogs.map((item) => (
                <div key={item.id} className="rounded-[24px] border border-border bg-[#f6f6f2] p-4" data-testid={`overview-equipment-log-${item.id}`}>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-[#243e36]">{item.equipment_number}</p>
                      <p className="mt-1 text-sm text-[#5c6d64]">{item.crew_label} · {item.division}</p>
                    </div>
                    <Badge className="border-0 bg-white text-[#243e36]">{item.status}</Badge>
                  </div>
                  {item.red_tag_note && <p className="mt-3 rounded-2xl bg-[#fdeaea] px-3 py-2 text-sm text-[#8b4c4c]" data-testid={`overview-equipment-red-tag-${item.id}`}>{item.red_tag_note}</p>}
                  {user?.title === "GM" && item.red_tag_note && !item.forwarded_to_owner && <Button type="button" variant="outline" onClick={() => forwardEquipmentLog(item.id)} className="mt-3 rounded-2xl border-[#243e36]/10 bg-white text-[#243e36] hover:bg-[#edf0e7]" data-testid={`overview-forward-equipment-${item.id}`}>Forward to Owner</Button>}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}