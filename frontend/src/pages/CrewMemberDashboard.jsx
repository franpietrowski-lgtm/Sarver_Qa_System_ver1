import { useEffect, useRef, useState } from "react";
import { AlertTriangle, BookOpen, Camera, ClipboardList, Copy, Crosshair, GraduationCap, MapPinned, Upload, X } from "lucide-react";
import { useParams } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { authPostForm, publicGet } from "@/lib/api";
import { toast } from "sonner";


const DIVISION_TASKS = {
  Maintenance: ["Bed edging", "Spring/Fall Cleanup", "Property Maintenance", "Pruning", "Weeding", "Mulching"],
  Install: ["Softscape", "Hardscape", "Tree/Plant Install/Removal", "Drainage/Trenching", "Lighting"],
  Tree: ["Pruning", "Tree/Plant Install/Removal", "Removal", "Stump Grinding"],
  "Plant Healthcare": ["Fert and Chem treatments", "Air Spade", "Dormant pruning", "Deer fencing and shrub treatment"],
  "Winter Services": ["Snow removal", "Plow", "Salting"],
};

const INCIDENT_TYPES = ["Slip / trip / fall", "Cut / laceration", "Struck by object", "Equipment malfunction / injury", "Heat / cold illness", "Chemical exposure", "Vehicle accident", "Near miss (no injury)", "Other"];
const BODY_PARTS = ["Head / face", "Neck", "Back", "Shoulder", "Arm / hand", "Leg / foot", "Torso / abdomen", "Multiple areas"];

const GPS_TARGET = 2;
const GPS_POLL_MS = 10000;


export default function CrewMemberDashboard() {
  const { code } = useParams();
  const [member, setMember] = useState(null);
  const [loadError, setLoadError] = useState("");

  // Capture state
  const [jobName, setJobName] = useState("");
  const [truckNumber, setTruckNumber] = useState("");
  const [note, setNote] = useState("");
  const [areaTag, setAreaTag] = useState("");
  const [photos, setPhotos] = useState([]);
  const [taskType, setTaskType] = useState("");
  const [workDate, setWorkDate] = useState(new Date().toISOString().slice(0, 10));
  const [gps, setGps] = useState(null);
  const [locating, setLocating] = useState(false);
  const [gpsPolling, setGpsPolling] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const watchIdRef = useRef(null);
  const pollTimerRef = useRef(null);
  const bestReadingRef = useRef(null);

  // Standards state
  const [standards, setStandards] = useState([]);
  const [selectedStandard, setSelectedStandard] = useState(null);

  // Training state
  const [trainingSessions, setTrainingSessions] = useState([]);

  // Submissions state
  const [submissions, setSubmissions] = useState([]);

  // Incident state
  const [incidentEnabled, setIncidentEnabled] = useState(false);
  const [incidentType, setIncidentType] = useState("");
  const [incidentDateTime, setIncidentDateTime] = useState("");
  const [incidentLocation, setIncidentLocation] = useState("");
  const [incidentDescription, setIncidentDescription] = useState("");
  const [injuredPerson, setInjuredPerson] = useState("");
  const [bodyPart, setBodyPart] = useState("");
  const [treatmentGiven, setTreatmentGiven] = useState("");
  const [witnessName, setWitnessName] = useState("");
  const [incidentPhotos, setIncidentPhotos] = useState([]);

  const availableTasks = DIVISION_TASKS[member?.division] || DIVISION_TASKS.Maintenance;

  useEffect(() => {
    const load = async () => {
      try {
        const m = await publicGet(`/public/crew-member/${code}`);
        setMember(m);
        setTruckNumber(m.parent_truck_number || "");
      } catch {
        setLoadError("This crew member link is invalid or has been deactivated.");
      }
    };
    load();
  }, [code]);

  // Load standards, training, submissions
  useEffect(() => {
    if (!member) return;
    const loadData = async () => {
      try {
        const [stdRes, trainRes, subRes] = await Promise.all([
          publicGet(`/public/crew-member/${code}/standards`),
          publicGet(`/public/crew-member/${code}/training`),
          publicGet(`/public/crew-member/${code}/submissions`),
        ]);
        setStandards(stdRes.standards || []);
        setTrainingSessions(trainRes.training_sessions || []);
        setSubmissions(subRes.submissions || []);
      } catch {
        // Silently handle — member profile already loaded
      }
    };
    loadData();
  }, [member, code]);

  // GPS
  const stopGpsPolling = () => {
    if (watchIdRef.current !== null) { navigator.geolocation.clearWatch(watchIdRef.current); watchIdRef.current = null; }
    if (pollTimerRef.current) { clearTimeout(pollTimerRef.current); pollTimerRef.current = null; }
    setGpsPolling(false);
    setLocating(false);
  };

  const requestGps = () => {
    if (!navigator.geolocation) { toast.error("Geolocation not supported."); return; }
    stopGpsPolling();
    setLocating(true);
    setGpsPolling(true);
    bestReadingRef.current = null;
    watchIdRef.current = navigator.geolocation.watchPosition(
      (position) => {
        const reading = { lat: Number(position.coords.latitude.toFixed(6)), lng: Number(position.coords.longitude.toFixed(6)), accuracy: Number(position.coords.accuracy?.toFixed(1) || 0) };
        if (!bestReadingRef.current || reading.accuracy < bestReadingRef.current.accuracy) { bestReadingRef.current = reading; setGps({ ...reading }); }
        if (reading.accuracy <= GPS_TARGET) { stopGpsPolling(); toast.success(`GPS locked — ±${reading.accuracy}m`); }
      },
      () => { stopGpsPolling(); if (!bestReadingRef.current) toast.error("GPS permission required."); },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 },
    );
    pollTimerRef.current = setTimeout(() => {
      stopGpsPolling();
      const best = bestReadingRef.current;
      if (best) {
        if (best.accuracy > GPS_TARGET) toast.warning(`Best GPS: ±${best.accuracy}m — flagged for review.`);
        else toast.success(`GPS locked — ±${best.accuracy}m`);
      }
    }, GPS_POLL_MS);
  };

  useEffect(() => { requestGps(); return () => stopGpsPolling(); }, []);
  useEffect(() => { if (!taskType && availableTasks.length) setTaskType(availableTasks[0]); }, [availableTasks, taskType]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const isEmergency = incidentEnabled && incidentType;
    if (!jobName || !truckNumber || !gps) { toast.error("Job name, truck number, and GPS are required."); return; }
    if (!isEmergency && !photos.length) { toast.error("Add photos before submitting."); return; }

    const formData = new FormData();
    formData.append("access_code", member.parent_access_code);
    formData.append("job_name", jobName);
    formData.append("task_type", taskType);
    formData.append("truck_number", truckNumber);
    formData.append("gps_lat", gps.lat);
    formData.append("gps_lng", gps.lng);
    formData.append("gps_accuracy", gps.accuracy || 0);
    formData.append("note", `[Member: ${member.name}] ${note}`);
    formData.append("area_tag", areaTag);
    formData.append("work_date", workDate);
    formData.append("member_code", code);
    photos.forEach((photo) => formData.append("photos", photo));

    if (isEmergency) {
      const incidentPayload = [
        `INCIDENT REPORT — ${incidentType}`,
        `Date/Time: ${incidentDateTime || "Not specified"}`,
        `Location: ${incidentLocation}`,
        `Injured person: ${injuredPerson || "N/A"}`,
        `Body part affected: ${bodyPart || "N/A"}`,
        `First aid / treatment: ${treatmentGiven || "None given"}`,
        `Witness: ${witnessName || "None listed"}`,
        `Description: ${incidentDescription}`,
      ].join("\n");
      formData.append("issue_type", `Incident: ${incidentType}`);
      formData.append("issue_notes", incidentPayload);
      incidentPhotos.forEach((photo) => formData.append("issue_photos", photo));
    }

    setSubmitting(true);
    try {
      await authPostForm("/public/submissions", formData);
      toast.success(isEmergency ? "Emergency report filed — all admins notified." : "Submission captured — sent to review queue.");
      setJobName(""); setNote(""); setAreaTag(""); setPhotos([]);
      setIncidentEnabled(false); setIncidentType(""); setIncidentDateTime(""); setIncidentLocation("");
      setIncidentDescription(""); setInjuredPerson(""); setBodyPart(""); setTreatmentGiven("");
      setWitnessName(""); setIncidentPhotos([]);
      requestGps();
      const subRes = await publicGet(`/public/crew-member/${code}/submissions`);
      setSubmissions(subRes.submissions || []);
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Submission failed");
    } finally {
      setSubmitting(false);
    }
  };

  if (loadError) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[linear-gradient(180deg,_#f6f6f2_0%,_#edf0e7_100%)] px-4">
        <Card className="max-w-md rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="member-dashboard-error-card">
          <CardContent className="p-8 text-center">
            <p className="text-lg font-semibold text-[#243e36]">Link Unavailable</p>
            <p className="mt-2 text-sm text-[#5c6d64]">{loadError}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!member) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[linear-gradient(180deg,_#f6f6f2_0%,_#edf0e7_100%)]" data-testid="member-dashboard-loading">
        <p className="text-lg font-semibold text-[#243e36]">Loading dashboard...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,_#f6f6f2_0%,_#edf0e7_100%)] px-4 py-5 sm:px-6">
      <div className="mx-auto max-w-md space-y-5">
        {/* Header */}
        <Card className="overflow-hidden rounded-[32px] border-border/80 bg-[#243e36] text-white shadow-sm" data-testid="member-dashboard-header">
          <CardContent className="p-6">
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#d8f3dc]" data-testid="member-dashboard-kicker">Crew member</p>
            <h1 className="mt-3 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight" data-testid="member-dashboard-name">{member.name}</h1>
            <div className="mt-3 flex flex-wrap gap-2">
              <Badge className="border-0 bg-white/12 px-3 py-1 text-white" data-testid="member-dashboard-crew-badge">{member.parent_crew_label}</Badge>
              <Badge className="border-0 bg-white/12 px-3 py-1 text-white" data-testid="member-dashboard-division-badge">{member.division}</Badge>
              <Badge className="border-0 bg-white/12 px-3 py-1 text-white" data-testid="member-dashboard-truck-badge">{member.parent_truck_number}</Badge>
            </div>
          </CardContent>
        </Card>

        {/* Tabs */}
        <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="member-dashboard-tabs-card">
          <CardContent className="p-6">
            <Tabs defaultValue="capture" className="space-y-4" data-testid="member-portal-tabs">
              <TabsList className="grid h-auto w-full grid-cols-4 rounded-[22px] bg-[#edf0e7] p-1" data-testid="member-portal-tab-list">
                <TabsTrigger value="capture" className="flex items-center justify-center gap-1 rounded-[18px] py-3 text-xs font-semibold" data-testid="member-capture-tab"><Camera className="h-4 w-4 shrink-0" /><span className="hidden sm:inline">Capture</span></TabsTrigger>
                <TabsTrigger value="standards" className="flex items-center justify-center gap-1 rounded-[18px] py-3 text-xs font-semibold" data-testid="member-standards-tab"><BookOpen className="h-4 w-4 shrink-0" /><span className="hidden sm:inline">Standards</span></TabsTrigger>
                <TabsTrigger value="training" className="flex items-center justify-center gap-1 rounded-[18px] py-3 text-xs font-semibold" data-testid="member-training-tab"><GraduationCap className="h-4 w-4 shrink-0" /><span className="hidden sm:inline">Training</span></TabsTrigger>
                <TabsTrigger value="history" className="flex items-center justify-center gap-1 rounded-[18px] py-3 text-xs font-semibold" data-testid="member-history-tab"><ClipboardList className="h-4 w-4 shrink-0" /><span className="hidden sm:inline">History</span></TabsTrigger>
              </TabsList>

              {/* ── CAPTURE TAB ── */}
              <TabsContent value="capture">
                <form className="space-y-5" onSubmit={handleSubmit} data-testid="member-capture-form">
                  <div className="space-y-2">
                    <label className="text-sm font-semibold text-[#243e36]" htmlFor="member-job-name">Job Name</label>
                    <Input id="member-job-name" value={jobName} onChange={(e) => setJobName(e.target.value)} placeholder="Enter the job name" className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="member-job-name-input" />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-semibold text-[#243e36]" htmlFor="member-truck">Truck number</label>
                    <Input id="member-truck" value={truckNumber} onChange={(e) => setTruckNumber(e.target.value)} className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="member-truck-input" />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-semibold text-[#243e36]" htmlFor="member-task-select">Current task</label>
                    <select id="member-task-select" value={taskType} onChange={(e) => setTaskType(e.target.value)} className="glass-dropdown h-12 w-full rounded-2xl border border-transparent bg-[var(--accent)] px-4 text-sm text-[var(--foreground)]" data-testid="member-task-select">
                      {availableTasks.map((t) => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="space-y-2">
                      <label className="text-sm font-semibold text-[#243e36]" htmlFor="member-area-tag">Area tag</label>
                      <Input id="member-area-tag" value={areaTag} onChange={(e) => setAreaTag(e.target.value)} placeholder="Front entry" className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="member-area-tag-input" />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-semibold text-[#243e36]" htmlFor="member-work-date">Work date</label>
                      <Input id="member-work-date" type="date" value={workDate} onChange={(e) => setWorkDate(e.target.value)} className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="member-work-date-input" />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-semibold text-[#243e36]" htmlFor="member-photo-input">Photos</label>
                    <label htmlFor="member-photo-input" className="flex h-12 cursor-pointer items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-[#cdd3c8] bg-[#edf0e7] text-sm font-semibold text-[#243e36]" data-testid="member-photo-upload"><Upload className="h-4 w-4" />Add photos</label>
                    <input id="member-photo-input" type="file" multiple accept="image/*" className="hidden" onChange={(e) => setPhotos(Array.from(e.target.files || []))} data-testid="member-photo-file-input" />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-semibold text-[#243e36]" htmlFor="member-note">Optional note</label>
                    <Textarea id="member-note" value={note} onChange={(e) => setNote(e.target.value)} placeholder="Anything reviewers should know?" className="min-h-[70px] rounded-2xl border-transparent bg-[#edf0e7]" data-testid="member-note-input" />
                  </div>

                  {/* GPS */}
                  <div className="rounded-[24px] border border-border bg-[#f6f6f2] p-4" data-testid="member-gps-card">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold text-[#243e36]">GPS lock</p>
                        {gps ? (
                          <>
                            <p className="mt-1 text-sm text-[#5c6d64]">{gps.lat}, {gps.lng}</p>
                            <span className={`mt-1.5 inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ${gps.accuracy <= GPS_TARGET ? "bg-emerald-100 text-emerald-800" : gps.accuracy <= 5 ? "bg-amber-100 text-amber-800" : "bg-red-100 text-red-800"}`} data-testid="member-gps-badge">
                              <span className={`inline-block h-1.5 w-1.5 rounded-full ${gps.accuracy <= GPS_TARGET ? "bg-emerald-500" : gps.accuracy <= 5 ? "bg-amber-500" : "bg-red-500"}`} />
                              ±{gps.accuracy}m {gps.accuracy <= GPS_TARGET ? "— Precise" : gps.accuracy <= 5 ? "— Fair" : "— Low"}
                            </span>
                            {gpsPolling && <p className="mt-1.5 text-xs text-[#5c6d64] animate-pulse">Refining...</p>}
                          </>
                        ) : (
                          <p className="mt-1 text-sm text-[#5c6d64]">{locating ? "Acquiring lock..." : "Waiting for location"}</p>
                        )}
                      </div>
                      <Button type="button" onClick={requestGps} variant="outline" className="shrink-0 rounded-2xl border-[#243e36]/10 bg-white" disabled={locating} data-testid="member-gps-refresh">
                        <Crosshair className="mr-2 h-4 w-4" />{locating ? "Locating" : "Refresh"}
                      </Button>
                    </div>
                  </div>

                  {photos.length > 0 && (
                    <div className="grid grid-cols-2 gap-3" data-testid="member-photo-preview-grid">
                      {photos.map((photo, i) => (
                        <div key={`${photo.name}-${i}`} className="rounded-[24px] border border-border bg-[#f6f6f2] p-3">
                          <div className="aspect-[4/3] overflow-hidden rounded-2xl bg-[#dde4d6]"><img src={URL.createObjectURL(photo)} alt={photo.name} className="h-full w-full object-cover" /></div>
                          <p className="mt-2 truncate text-xs font-semibold text-[#243e36]">{photo.name}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* ──────────── INCIDENT / ACCIDENT REPORTING ──────────── */}
                  <div className="rounded-[24px] border border-[#ead2d2] bg-[#fef5f5] p-4" data-testid="member-incident-report-card">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-sm font-semibold text-[#7a2323]">Workplace incident / accident</p>
                        <p className="mt-1 text-xs text-[#9e6060]">Report injuries, near-misses, or safety events. Submits immediately without photo requirement.</p>
                      </div>
                      <div className="flex items-center gap-2 rounded-full bg-white px-3 py-2" data-testid="member-incident-toggle-box">
                        <span className="text-[10px] font-bold uppercase tracking-[0.24em] text-[#7a2323]">Incident</span>
                        <Switch checked={incidentEnabled} onCheckedChange={setIncidentEnabled} data-testid="member-incident-toggle" />
                      </div>
                    </div>
                    {incidentEnabled && (
                      <div className="mt-4 grid gap-3" data-testid="member-incident-fields">
                        <select value={incidentType} onChange={(e) => setIncidentType(e.target.value)} className="glass-dropdown h-12 w-full rounded-2xl border border-transparent bg-[var(--accent)] px-4 text-sm text-[var(--foreground)]" data-testid="member-incident-type-select">
                          <option value="">Select incident type</option>
                          {INCIDENT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                        </select>
                        <Input type="datetime-local" value={incidentDateTime} onChange={(e) => setIncidentDateTime(e.target.value)} className="h-12 rounded-2xl border-transparent bg-white" data-testid="member-incident-datetime" />
                        <Input value={incidentLocation} onChange={(e) => setIncidentLocation(e.target.value)} placeholder="Where on the jobsite?" className="h-12 rounded-2xl border-transparent bg-white" data-testid="member-incident-location" />
                        <Input value={injuredPerson} onChange={(e) => setInjuredPerson(e.target.value)} placeholder="Name of injured person (or 'self')" className="h-12 rounded-2xl border-transparent bg-white" data-testid="member-incident-injured" />
                        <select value={bodyPart} onChange={(e) => setBodyPart(e.target.value)} className="glass-dropdown h-12 w-full rounded-2xl border border-transparent bg-[var(--accent)] px-4 text-sm text-[var(--foreground)]" data-testid="member-incident-body-part">
                          <option value="">Body part affected (if applicable)</option>
                          {BODY_PARTS.map((b) => <option key={b} value={b}>{b}</option>)}
                        </select>
                        <Textarea value={incidentDescription} onChange={(e) => setIncidentDescription(e.target.value)} placeholder="Describe exactly what happened" className="min-h-[80px] rounded-2xl border-transparent bg-white" data-testid="member-incident-description" />
                        <Input value={treatmentGiven} onChange={(e) => setTreatmentGiven(e.target.value)} placeholder="First aid or treatment given" className="h-12 rounded-2xl border-transparent bg-white" data-testid="member-incident-treatment" />
                        <Input value={witnessName} onChange={(e) => setWitnessName(e.target.value)} placeholder="Witness name and contact" className="h-12 rounded-2xl border-transparent bg-white" data-testid="member-incident-witness" />
                        <label htmlFor="member-incident-photo-input" className="flex h-12 cursor-pointer items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-[#ead2d2] bg-white text-sm font-semibold text-[#7a2323]"><Upload className="h-4 w-4" />Add incident photos</label>
                        <input id="member-incident-photo-input" type="file" multiple accept="image/*" className="hidden" onChange={(e) => setIncidentPhotos(Array.from(e.target.files || []))} data-testid="member-incident-photo-input" />
                        <div className="rounded-2xl bg-[#fbeded] px-4 py-3 text-xs text-[#9e6060]">
                          <strong>Notice:</strong> Only record what you personally saw or experienced. This report may be used for safety records and OSHA compliance.
                        </div>
                      </div>
                    )}
                  </div>

                  <Button type="submit" disabled={submitting || !gps} className={`h-14 w-full rounded-[22px] text-base font-semibold text-white ${incidentEnabled && incidentType ? "bg-red-600 hover:bg-red-700 animate-pulse" : "bg-[#243e36] hover:bg-[#1a2c26]"}`} data-testid="member-submit-button">
                    {incidentEnabled && incidentType ? (
                      <><AlertTriangle className="mr-2 h-5 w-5" />{submitting ? "Filing emergency..." : "FILE EMERGENCY REPORT"}</>
                    ) : (
                      <><Camera className="mr-2 h-5 w-5" />{submitting ? "Submitting..." : "Submit capture set"}</>
                    )}
                  </Button>
                </form>
              </TabsContent>

              {/* ── STANDARDS TAB ── */}
              <TabsContent value="standards" data-testid="member-standards-panel">
                <div className="space-y-4">
                  <div className="rounded-[24px] border border-border bg-[#f6f6f2] p-4">
                    <p className="text-sm font-semibold text-[#243e36]">Standards for {member.division}</p>
                    <p className="mt-1 text-sm text-[#5c6d64]">Review these before shooting a proof set.</p>
                  </div>
                  {standards.length === 0 && (
                    <p className="py-8 text-center text-sm text-[#5c6d64]" data-testid="member-standards-empty">No standards available for your division yet.</p>
                  )}
                  {standards.map((item) => (
                    <button key={item.id} type="button" onClick={() => setSelectedStandard(item)} className="w-full overflow-hidden rounded-[24px] border border-border bg-[#f6f6f2] text-left transition hover:border-[#243e36]/30 hover:shadow-md" data-testid={`member-standard-card-${item.id}`}>
                      {item.image_url && <div className="aspect-[5/3] overflow-hidden bg-[#dde4d6]"><img src={item.image_url} alt={item.title} className="h-full w-full object-cover" /></div>}
                      <div className="space-y-2 p-4">
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-sm font-semibold text-[#243e36]">{item.title}</p>
                          <Badge className="border-0 bg-white text-[#243e36]">{item.category}</Badge>
                        </div>
                        <p className="text-sm text-[#5c6d64] line-clamp-2">{item.notes}</p>
                      </div>
                    </button>
                  ))}
                </div>
                {selectedStandard && (
                  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4" onClick={() => setSelectedStandard(null)} data-testid="member-standard-overlay">
                    <div className="max-h-[85vh] w-full max-w-md overflow-hidden rounded-[28px] border border-border/80 bg-white shadow-2xl" onClick={(e) => e.stopPropagation()}>
                      {selectedStandard.image_url && <div className="aspect-[5/3] bg-[#dbe3d7]"><img src={selectedStandard.image_url} alt={selectedStandard.title} className="h-full w-full object-cover" /></div>}
                      <div className="max-h-[45vh] overflow-y-auto p-5">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <Badge className="border-0 bg-[#edf0e7] text-xs text-[#243e36]">{selectedStandard.category}</Badge>
                            <h3 className="mt-2 font-[Cabinet_Grotesk] text-xl font-black tracking-tight text-[#111815]">{selectedStandard.title}</h3>
                          </div>
                          <button type="button" onClick={() => setSelectedStandard(null)} className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#edf0e7] text-[#243e36] hover:bg-[#dbe3d7]"><X className="h-4 w-4" /></button>
                        </div>
                        <p className="mt-3 text-sm leading-relaxed text-[#41534a]">{selectedStandard.notes}</p>
                        {selectedStandard.checklist?.length > 0 && (
                          <div className="mt-4 rounded-[16px] bg-[#f6f6f2] p-4">
                            <p className="text-xs font-bold uppercase tracking-widest text-[#5f7464]">Checklist</p>
                            <ul className="mt-2 space-y-1">{selectedStandard.checklist.map((c, i) => <li key={i} className="text-sm text-[#41534a]">- {c}</li>)}</ul>
                          </div>
                        )}
                        {selectedStandard.shoutout && (
                          <p className="mt-3 text-xs font-semibold text-[#5f7464]">{selectedStandard.shoutout}</p>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </TabsContent>

              {/* ── TRAINING TAB ── */}
              <TabsContent value="training" data-testid="member-training-panel">
                <div className="space-y-4">
                  <div className="rounded-[24px] border border-border bg-[#f6f6f2] p-4">
                    <p className="text-sm font-semibold text-[#243e36]">Training sessions</p>
                    <p className="mt-1 text-sm text-[#5c6d64]">Complete assigned training to build your standards knowledge.</p>
                  </div>
                  {trainingSessions.length === 0 && (
                    <p className="py-8 text-center text-sm text-[#5c6d64]" data-testid="member-training-empty">No training sessions assigned yet.</p>
                  )}
                  {trainingSessions.map((s) => (
                    <div key={s.code} className="rounded-[24px] border border-border bg-[#f6f6f2] p-4" data-testid={`member-training-card-${s.code}`}>
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-[#243e36]">{s.crew_label} — {s.division}</p>
                          <p className="mt-1 text-xs text-[#5c6d64]">{s.item_count} items</p>
                        </div>
                        {s.status === "completed" ? (
                          <Badge className="border-0 bg-emerald-100 text-emerald-800" data-testid={`member-training-status-${s.code}`}>
                            {s.score_percent != null ? `${s.score_percent}%` : "Done"}
                          </Badge>
                        ) : (
                          <Button
                            size="sm"
                            className="rounded-2xl bg-[#243e36] text-white hover:bg-[#1a2c26]"
                            onClick={() => window.open(`/training/${s.code}`, "_blank")}
                            data-testid={`member-training-start-${s.code}`}
                          >
                            Start
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </TabsContent>

              {/* ── HISTORY TAB ── */}
              <TabsContent value="history" data-testid="member-history-panel">
                <div className="space-y-4">
                  <div className="rounded-[24px] border border-border bg-[#f6f6f2] p-4">
                    <p className="text-sm font-semibold text-[#243e36]">Your submissions</p>
                    <p className="mt-1 text-sm text-[#5c6d64]">Track your individual work history.</p>
                  </div>
                  {submissions.length === 0 && (
                    <p className="py-8 text-center text-sm text-[#5c6d64]" data-testid="member-history-empty">No submissions yet. Start capturing!</p>
                  )}
                  {submissions.map((s) => (
                    <div key={s.id} className="rounded-[24px] border border-border bg-[#f6f6f2] p-4" data-testid={`member-submission-${s.id}`}>
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-semibold text-[#243e36]">{s.job_name_input}</p>
                          <p className="mt-1 text-xs text-[#5c6d64]">{s.task_type} — {s.work_date}</p>
                        </div>
                        <Badge className={`shrink-0 border-0 ${s.status === "Ready for Review" ? "bg-amber-100 text-amber-800" : s.status === "Management Reviewed" ? "bg-blue-100 text-blue-800" : "bg-emerald-100 text-emerald-800"}`} data-testid={`member-submission-status-${s.id}`}>
                          {s.status === "Ready for Review" ? "In Review" : s.status === "Management Reviewed" ? "Reviewed" : s.status}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        <Card className="rounded-[32px] border-border/80 bg-white/90 shadow-sm" data-testid="member-dashboard-tips-card">
          <CardContent className="space-y-4 p-6">
            <div className="flex items-center gap-3 text-[#243e36]"><MapPinned className="h-5 w-5" /><p className="text-sm font-semibold">Best results: wide shot first, detail shots after.</p></div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
