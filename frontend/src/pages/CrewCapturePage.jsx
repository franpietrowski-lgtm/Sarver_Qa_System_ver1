import { useEffect, useState } from "react";
import { BookOpen, Camera, Crosshair, MapPinned, Upload, Wrench, X } from "lucide-react";
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

const STANDARDS_HIGHLIGHTS = [
  {
    id: "standard-edge-clean",
    title: "Clean bed edge finish",
    note: "Look for a confident edge line, contained turf, and a final pass that reads clean from the street.",
    image: "https://images.unsplash.com/photo-1734303023491-db8037a21f09?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
    category: "Edging",
  },
  {
    id: "standard-cleanup-reset",
    title: "Spring cleanup reset",
    note: "Wide shot first, detail shots after. Reviewers want the property reset to feel complete, not partial.",
    image: "https://images.pexels.com/photos/30467599/pexels-photo-30467599.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    category: "Cleanup",
  },
  {
    id: "standard-tree-work",
    title: "Tree work clarity",
    note: "Show the cut area clearly and keep one framing shot that proves the work zone is safe and tidy.",
    image: "https://images.unsplash.com/photo-1772764057845-121fd5f3ebe8?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
    category: "Sarver Tree",
  },
];

const DAMAGE_TYPES = ["Landscape feature", "Hardscape / paver", "Irrigation / plumbing", "Fence / gate", "Structure / building", "Vehicle", "Other"];
const INCIDENT_TYPES = ["Slip / trip / fall", "Cut / laceration", "Struck by object", "Equipment malfunction / injury", "Heat / cold illness", "Chemical exposure", "Vehicle accident", "Near miss (no injury)", "Other"];
const BODY_PARTS = ["Head / face", "Neck", "Back", "Shoulder", "Arm / hand", "Leg / foot", "Torso / abdomen", "Multiple areas"];


export default function CrewCapturePage() {
  const { code } = useParams();
  const [crewLink, setCrewLink] = useState(null);
  const [jobName, setJobName] = useState("");
  const [truckNumber, setTruckNumber] = useState("");
  const [note, setNote] = useState("");
  const [areaTag, setAreaTag] = useState("");
  const [photos, setPhotos] = useState([]);
  const [gps, setGps] = useState(null);
  const [locating, setLocating] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [crewNotifications, setCrewNotifications] = useState([]);
  const [taskType, setTaskType] = useState("");

  // Damage Reporting State
  const [damageEnabled, setDamageEnabled] = useState(false);
  const [damageType, setDamageType] = useState("");
  const [damageDescription, setDamageDescription] = useState("");
  const [damageLocation, setDamageLocation] = useState("");
  const [damagePhotos, setDamagePhotos] = useState([]);

  // Incident Reporting State (OSHA-compliant)
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

  // Equipment State
  const [equipmentLog, setEquipmentLog] = useState({ equipment_number: "", general_note: "", red_tag_note: "", pre_photo: null, post_photo: null });
  const [equipmentSubmitting, setEquipmentSubmitting] = useState(false);
  const [selectedStandard, setSelectedStandard] = useState(null);

  const availableTasks = DIVISION_TASKS[crewLink?.division] || DIVISION_TASKS.Maintenance;

  const loadCrewContext = async () => {
    try {
      const link = await publicGet(`/public/crew-access/${code}`);
      setCrewLink(link);
      setCrewNotifications(link.notifications || []);
      setTruckNumber(link.truck_number || "");
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Crew access not found");
    }
  };

  useEffect(() => { loadCrewContext(); }, [code]);

  const requestGps = () => {
    if (!navigator.geolocation) { toast.error("Geolocation is not supported on this device."); return; }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setGps({ lat: Number(position.coords.latitude.toFixed(6)), lng: Number(position.coords.longitude.toFixed(6)), accuracy: Number(position.coords.accuracy?.toFixed(1) || 0) });
        setLocating(false);
        toast.success("GPS locked.");
      },
      () => { setLocating(false); toast.error("GPS permission is required before submitting."); },
      { enableHighAccuracy: true, timeout: 10000 },
    );
  };

  useEffect(() => { requestGps(); }, []);

  useEffect(() => {
    if (!taskType && availableTasks.length) setTaskType(availableTasks[0]);
  }, [availableTasks, taskType]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!jobName || !truckNumber || !gps) { toast.error("Job Name, truck number, and GPS are required."); return; }
    if (!photos.length) { toast.error("Please attach photos before submitting."); return; }

    const formData = new FormData();
    formData.append("access_code", code);
    formData.append("job_name", jobName);
    formData.append("task_type", taskType);
    formData.append("truck_number", truckNumber);
    formData.append("gps_lat", gps.lat);
    formData.append("gps_lng", gps.lng);
    formData.append("gps_accuracy", gps.accuracy || 0);
    formData.append("note", note);
    formData.append("area_tag", areaTag);
    photos.forEach((photo) => formData.append("photos", photo));

    // Damage report fields
    if (damageEnabled) {
      formData.append("issue_type", `Damage: ${damageType}`);
      formData.append("issue_notes", `Location: ${damageLocation}\n${damageDescription}`);
      damagePhotos.forEach((photo) => formData.append("issue_photos", photo));
    }

    // Incident report fields
    if (incidentEnabled) {
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
      formData.append("issue_type", damageEnabled ? formData.get("issue_type") + ` | Incident: ${incidentType}` : `Incident: ${incidentType}`);
      formData.append("issue_notes", (damageEnabled ? formData.get("issue_notes") + "\n\n" : "") + incidentPayload);
      incidentPhotos.forEach((photo) => formData.append("issue_photos", photo));
    }

    setSubmitting(true);
    try {
      await authPostForm("/public/submissions", formData);
      toast.success("Submission captured — your proof is now in review queue.");
      setJobName(""); setNote(""); setAreaTag(""); setPhotos([]);
      setDamageEnabled(false); setDamageType(""); setDamageDescription(""); setDamageLocation(""); setDamagePhotos([]);
      setIncidentEnabled(false); setIncidentType(""); setIncidentDateTime(""); setIncidentLocation(""); setIncidentDescription(""); setInjuredPerson(""); setBodyPart(""); setTreatmentGiven(""); setWitnessName(""); setIncidentPhotos([]);
      requestGps();
      loadCrewContext();
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Submission failed");
    } finally { setSubmitting(false); }
  };

  const handleEquipmentSubmit = async (event) => {
    event.preventDefault();
    if (!equipmentLog.equipment_number || !equipmentLog.pre_photo || !equipmentLog.post_photo) { toast.error("Equipment number and both maintenance photos are required."); return; }
    const formData = new FormData();
    formData.append("access_code", code);
    formData.append("equipment_number", equipmentLog.equipment_number);
    formData.append("general_note", equipmentLog.general_note);
    formData.append("red_tag_note", equipmentLog.red_tag_note);
    formData.append("pre_service_photo", equipmentLog.pre_photo);
    formData.append("post_service_photo", equipmentLog.post_photo);
    setEquipmentSubmitting(true);
    try {
      await authPostForm("/public/equipment-logs", formData);
      toast.success("Equipment record submitted.");
      setEquipmentLog({ equipment_number: "", general_note: "", red_tag_note: "", pre_photo: null, post_photo: null });
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Equipment record failed");
    } finally { setEquipmentSubmitting(false); }
  };

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,_#f6f6f2_0%,_#edf0e7_100%)] px-4 py-5 sm:px-6">
      <div className="mx-auto max-w-md space-y-5">
        <Card className="overflow-hidden rounded-[32px] border-border/80 bg-[#243e36] text-white shadow-sm" data-testid="crew-capture-header-card">
          <CardContent className="p-6">
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#d8f3dc]" data-testid="crew-capture-kicker">Sarver landscape field capture</p>
            <h1 className="mt-3 font-[Cabinet_Grotesk] text-4xl font-black tracking-tight" data-testid="crew-capture-title">Capture work proof in one clean pass</h1>
            <p className="mt-3 text-sm text-white/80" data-testid="crew-capture-description">Enter the job name, confirm the truck, add clear photos, and send the work set to review.</p>
            {crewLink && (
              <div className="mt-5 flex flex-wrap gap-2">
                <Badge className="border-0 bg-white/12 px-3 py-1 text-white" data-testid="crew-capture-crew-badge">{crewLink.label}</Badge>
                <Badge className="border-0 bg-white/12 px-3 py-1 text-white" data-testid="crew-capture-crew-id-badge">Crew pass active</Badge>
                <Badge className="border-0 bg-white/12 px-3 py-1 text-white" data-testid="crew-capture-truck-badge">{crewLink.truck_number}</Badge>
                <Badge className="border-0 bg-white/12 px-3 py-1 text-white" data-testid="crew-capture-division-badge">{crewLink.division}</Badge>
              </div>
            )}
          </CardContent>
        </Card>

        {crewNotifications.length > 0 && (
          <Card className="rounded-[32px] border-[#e07a5f]/30 bg-[#fff6f1] shadow-sm" data-testid="crew-notification-card">
            <CardContent className="space-y-3 p-6">
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#b45a42]">Work follow-up</p>
              {crewNotifications.map((item) => (
                <div key={item.id} className="rounded-[22px] border border-[#f2c9bc] bg-white px-4 py-3" data-testid={`crew-notification-item-${item.id}`}>
                  <p className="text-sm font-semibold text-[#243e36]">{item.title}</p>
                  <p className="mt-1 text-sm text-[#5c6d64]">{item.message}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="crew-capture-form-card">
          <CardContent className="p-6">
            <Tabs defaultValue="capture" className="space-y-4" data-testid="crew-portal-tabs">
              <TabsList className="grid h-auto w-full grid-cols-3 rounded-[22px] bg-[#edf0e7] p-1" data-testid="crew-portal-tab-list">
                <TabsTrigger value="capture" className="flex items-center justify-center gap-2 rounded-[18px] py-3 text-sm font-semibold" data-testid="crew-capture-tab-trigger"><Camera className="h-4 w-4 shrink-0" /><span className="hidden sm:inline">Capture</span></TabsTrigger>
                <TabsTrigger value="standards" className="flex items-center justify-center gap-2 rounded-[18px] py-3 text-sm font-semibold" data-testid="crew-standards-tab-trigger"><BookOpen className="h-4 w-4 shrink-0" /><span className="hidden sm:inline">Standards</span></TabsTrigger>
                <TabsTrigger value="equipment" className="flex items-center justify-center gap-2 rounded-[18px] py-3 text-sm font-semibold" data-testid="crew-equipment-tab-trigger"><Wrench className="h-4 w-4 shrink-0" /><span className="hidden sm:inline">Equipment</span></TabsTrigger>
              </TabsList>

              <TabsContent value="capture">
                <form className="space-y-5" onSubmit={handleSubmit} data-testid="crew-capture-form">
                  <div className="space-y-2">
                    <label className="text-sm font-semibold text-[#243e36]" htmlFor="crew-job-name-input">Job Name</label>
                    <Input id="crew-job-name-input" value={jobName} onChange={(e) => setJobName(e.target.value)} placeholder="Enter the job name exactly as given to the crew" className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="crew-job-name-input" />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-semibold text-[#243e36]" htmlFor="crew-truck-input">Truck number</label>
                    <Input id="crew-truck-input" value={truckNumber} onChange={(e) => setTruckNumber(e.target.value)} className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="crew-truck-number-input" />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-semibold text-[#243e36]" htmlFor="crew-task-type-select">Current task</label>
                    <select id="crew-task-type-select" value={taskType} onChange={(e) => setTaskType(e.target.value)} className="h-12 w-full rounded-2xl border border-transparent bg-[#edf0e7] px-4 text-sm" data-testid="crew-task-type-select">
                      {availableTasks.map((item) => <option key={item} value={item}>{item}</option>)}
                    </select>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="space-y-2">
                      <label className="text-sm font-semibold text-[#243e36]" htmlFor="crew-area-tag-input">Area tag</label>
                      <Input id="crew-area-tag-input" value={areaTag} onChange={(e) => setAreaTag(e.target.value)} placeholder="Front entry / bed 2" className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="crew-area-tag-input" />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-semibold text-[#243e36]" htmlFor="crew-photo-input">Photos</label>
                      <label htmlFor="crew-photo-input" className="flex h-12 cursor-pointer items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-[#cdd3c8] bg-[#edf0e7] text-sm font-semibold text-[#243e36]" data-testid="crew-photo-upload-field"><Upload className="h-4 w-4" />Add photos</label>
                      <input id="crew-photo-input" type="file" multiple accept="image/*" className="hidden" onChange={(e) => setPhotos(Array.from(e.target.files || []))} data-testid="crew-photo-input" />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-semibold text-[#243e36]" htmlFor="crew-note-input">Optional note</label>
                    <Textarea id="crew-note-input" value={note} onChange={(e) => setNote(e.target.value)} placeholder="Anything unusual the reviewers should know?" className="min-h-[80px] rounded-2xl border-transparent bg-[#edf0e7]" data-testid="crew-note-input" />
                  </div>

                  {/* ──────────── DAMAGE REPORTING ──────────── */}
                  <div className="rounded-[24px] border border-[#e8d5c4] bg-[#fdf8f3] p-4" data-testid="crew-damage-report-card">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-sm font-semibold text-[#8a6830]">Property damage reporting</p>
                        <p className="mt-1 text-xs text-[#8a7a5f]">Record damage to a client's property caused during work — fence strikes, irrigation hits, hardscape cracks, etc.</p>
                      </div>
                      <div className="flex items-center gap-2 rounded-full bg-white px-3 py-2" data-testid="crew-damage-toggle-box">
                        <span className="text-[10px] font-bold uppercase tracking-[0.24em] text-[#8a6830]">Damage</span>
                        <Switch checked={damageEnabled} onCheckedChange={setDamageEnabled} data-testid="crew-damage-toggle-switch" />
                      </div>
                    </div>
                    {damageEnabled && (
                      <div className="mt-4 grid gap-3" data-testid="crew-damage-fields">
                        <select value={damageType} onChange={(e) => setDamageType(e.target.value)} className="h-12 w-full rounded-2xl border border-transparent bg-white px-4 text-sm" data-testid="crew-damage-type-select">
                          <option value="">Select damage type</option>
                          {DAMAGE_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                        </select>
                        <Input value={damageLocation} onChange={(e) => setDamageLocation(e.target.value)} placeholder="Specific location on property (e.g., backyard fence line)" className="h-12 rounded-2xl border-transparent bg-white" data-testid="crew-damage-location-input" />
                        <Textarea value={damageDescription} onChange={(e) => setDamageDescription(e.target.value)} placeholder="Describe what was damaged, how it happened, and the visible extent" className="min-h-[80px] rounded-2xl border-transparent bg-white" data-testid="crew-damage-description-input" />
                        <label htmlFor="crew-damage-photo-input" className="flex h-12 cursor-pointer items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-[#e8d5c4] bg-white text-sm font-semibold text-[#8a6830]" data-testid="crew-damage-upload-field"><Upload className="h-4 w-4" />Add damage photos</label>
                        <input id="crew-damage-photo-input" type="file" multiple accept="image/*" className="hidden" onChange={(e) => setDamagePhotos(Array.from(e.target.files || []))} data-testid="crew-damage-photo-input" />
                      </div>
                    )}
                  </div>

                  {/* ──────────── INCIDENT / ACCIDENT REPORTING (OSHA) ──────────── */}
                  <div className="rounded-[24px] border border-[#ead2d2] bg-[#fef5f5] p-4" data-testid="crew-incident-report-card">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-sm font-semibold text-[#7a2323]">Workplace incident / accident</p>
                        <p className="mt-1 text-xs text-[#9e6060]">Use this section to report injuries, near-misses, or safety events. Information collected follows OSHA 300-A recordkeeping guidance. Only factual, first-person observations should be recorded.</p>
                      </div>
                      <div className="flex items-center gap-2 rounded-full bg-white px-3 py-2" data-testid="crew-incident-toggle-box">
                        <span className="text-[10px] font-bold uppercase tracking-[0.24em] text-[#7a2323]">Incident</span>
                        <Switch checked={incidentEnabled} onCheckedChange={setIncidentEnabled} data-testid="crew-incident-toggle-switch" />
                      </div>
                    </div>
                    {incidentEnabled && (
                      <div className="mt-4 grid gap-3" data-testid="crew-incident-fields">
                        <select value={incidentType} onChange={(e) => setIncidentType(e.target.value)} className="h-12 w-full rounded-2xl border border-transparent bg-white px-4 text-sm" data-testid="crew-incident-type-select">
                          <option value="">Select incident type</option>
                          {INCIDENT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                        </select>
                        <div className="space-y-1">
                          <label className="text-xs font-semibold text-[#7a2323]">Date and time of incident</label>
                          <Input type="datetime-local" value={incidentDateTime} onChange={(e) => setIncidentDateTime(e.target.value)} className="h-12 rounded-2xl border-transparent bg-white" data-testid="crew-incident-datetime-input" />
                        </div>
                        <Input value={incidentLocation} onChange={(e) => setIncidentLocation(e.target.value)} placeholder="Where on the jobsite did this occur?" className="h-12 rounded-2xl border-transparent bg-white" data-testid="crew-incident-location-input" />
                        <Input value={injuredPerson} onChange={(e) => setInjuredPerson(e.target.value)} placeholder="Name of injured person (or 'self')" className="h-12 rounded-2xl border-transparent bg-white" data-testid="crew-incident-injured-person-input" />
                        <select value={bodyPart} onChange={(e) => setBodyPart(e.target.value)} className="h-12 w-full rounded-2xl border border-transparent bg-white px-4 text-sm" data-testid="crew-incident-body-part-select">
                          <option value="">Body part affected (if applicable)</option>
                          {BODY_PARTS.map((b) => <option key={b} value={b}>{b}</option>)}
                        </select>
                        <Textarea value={incidentDescription} onChange={(e) => setIncidentDescription(e.target.value)} placeholder="Describe exactly what happened — stick to facts only, in your own words" className="min-h-[100px] rounded-2xl border-transparent bg-white" data-testid="crew-incident-description-input" />
                        <Input value={treatmentGiven} onChange={(e) => setTreatmentGiven(e.target.value)} placeholder="First aid or treatment given on-site (if any)" className="h-12 rounded-2xl border-transparent bg-white" data-testid="crew-incident-treatment-input" />
                        <Input value={witnessName} onChange={(e) => setWitnessName(e.target.value)} placeholder="Witness name and contact (if available)" className="h-12 rounded-2xl border-transparent bg-white" data-testid="crew-incident-witness-input" />
                        <label htmlFor="crew-incident-photo-input" className="flex h-12 cursor-pointer items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-[#ead2d2] bg-white text-sm font-semibold text-[#7a2323]" data-testid="crew-incident-upload-field"><Upload className="h-4 w-4" />Add incident scene photos</label>
                        <input id="crew-incident-photo-input" type="file" multiple accept="image/*" className="hidden" onChange={(e) => setIncidentPhotos(Array.from(e.target.files || []))} data-testid="crew-incident-photo-input" />
                        <div className="rounded-2xl bg-[#fbeded] px-4 py-3 text-xs text-[#9e6060]" data-testid="crew-incident-legal-notice">
                          <strong>Notice:</strong> Only record what you personally saw or experienced. Do not speculate about fault or cause. This report may be used for safety records, workers' compensation, and OSHA compliance.
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Photo previews */}
                  {(damageEnabled && damagePhotos.length > 0) && (
                    <div className="grid grid-cols-2 gap-3" data-testid="crew-damage-preview-grid">
                      {damagePhotos.map((photo, i) => (
                        <div key={`dmg-${photo.name}-${i}`} className="rounded-[24px] border border-[#e8d5c4] bg-[#fdf8f3] p-3">
                          <div className="aspect-[4/3] overflow-hidden rounded-2xl bg-[#f0e6d6]"><img src={URL.createObjectURL(photo)} alt={photo.name} className="h-full w-full object-cover" /></div>
                          <p className="mt-2 truncate text-xs font-semibold text-[#8a6830]">{photo.name}</p>
                        </div>
                      ))}
                    </div>
                  )}
                  {(incidentEnabled && incidentPhotos.length > 0) && (
                    <div className="grid grid-cols-2 gap-3" data-testid="crew-incident-preview-grid">
                      {incidentPhotos.map((photo, i) => (
                        <div key={`inc-${photo.name}-${i}`} className="rounded-[24px] border border-[#ead2d2] bg-[#fef5f5] p-3">
                          <div className="aspect-[4/3] overflow-hidden rounded-2xl bg-[#f0d6d6]"><img src={URL.createObjectURL(photo)} alt={photo.name} className="h-full w-full object-cover" /></div>
                          <p className="mt-2 truncate text-xs font-semibold text-[#7a2323]">{photo.name}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="rounded-[24px] border border-border bg-[#f6f6f2] p-4" data-testid="crew-gps-card">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-[#243e36]">GPS lock</p>
                        <p className="mt-1 text-sm text-[#5c6d64]" data-testid="crew-gps-status-text">{gps ? `${gps.lat}, ${gps.lng} · ±${gps.accuracy}m` : "Waiting for device location"}</p>
                      </div>
                      <Button type="button" onClick={requestGps} variant="outline" className="rounded-2xl border-[#243e36]/10 bg-white" disabled={locating} data-testid="crew-gps-refresh-button">
                        <Crosshair className="mr-2 h-4 w-4" />{locating ? "Locating" : "Refresh"}
                      </Button>
                    </div>
                  </div>

                  {photos.length > 0 && (
                    <div className="grid grid-cols-2 gap-3" data-testid="crew-photo-preview-grid">
                      {photos.map((photo, i) => (
                        <div key={`${photo.name}-${i}`} className="rounded-[24px] border border-border bg-[#f6f6f2] p-3" data-testid={`crew-photo-preview-${i + 1}`}>
                          <div className="aspect-[4/3] overflow-hidden rounded-2xl bg-[#dde4d6]"><img src={URL.createObjectURL(photo)} alt={photo.name} className="h-full w-full object-cover" /></div>
                          <p className="mt-2 truncate text-xs font-semibold text-[#243e36]">{photo.name}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  <Button type="submit" disabled={submitting || !gps} className="h-14 w-full rounded-[22px] bg-[#243e36] text-base font-semibold text-white hover:bg-[#1a2c26]" data-testid="crew-submit-photos-button">
                    <Camera className="mr-2 h-5 w-5" />{submitting ? "Submitting proof..." : "Submit capture set"}
                  </Button>
                </form>
              </TabsContent>

              <TabsContent value="standards" data-testid="crew-standards-tab-panel">
                <div className="space-y-4">
                  <div className="rounded-[24px] border border-border bg-[#f6f6f2] p-4">
                    <p className="text-sm font-semibold text-[#243e36]">Crew standards library</p>
                    <p className="mt-1 text-sm text-[#5c6d64]">Tap a standard for full details. Review before shooting a proof set.</p>
                  </div>
                  {STANDARDS_HIGHLIGHTS.map((item) => (
                    <button key={item.id} type="button" onClick={() => setSelectedStandard(item)} className="w-full overflow-hidden rounded-[24px] border border-border bg-[#f6f6f2] text-left transition hover:border-[#243e36]/30 hover:shadow-md" data-testid={`crew-standard-card-${item.id}`}>
                      <div className="aspect-[5/3] overflow-hidden bg-[#dde4d6]"><img src={item.image} alt={item.title} className="h-full w-full object-cover" /></div>
                      <div className="space-y-2 p-4">
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-sm font-semibold text-[#243e36]">{item.title}</p>
                          <Badge className="border-0 bg-white text-[#243e36]" data-testid={`crew-standard-category-${item.id}`}>{item.category}</Badge>
                        </div>
                        <p className="text-sm text-[#5c6d64] line-clamp-2">{item.note}</p>
                        <p className="text-xs font-semibold text-[#243e36]">Tap to view full details</p>
                      </div>
                    </button>
                  ))}
                </div>
                {selectedStandard && (
                  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4" onClick={() => setSelectedStandard(null)} data-testid="crew-standard-detail-overlay">
                    <div className="max-h-[85vh] w-full max-w-md overflow-hidden rounded-[28px] border border-border/80 bg-white shadow-2xl" onClick={(e) => e.stopPropagation()} data-testid="crew-standard-detail-popup">
                      <div className="aspect-[5/3] bg-[#dbe3d7]"><img src={selectedStandard.image} alt={selectedStandard.title} className="h-full w-full object-cover" /></div>
                      <div className="max-h-[45vh] overflow-y-auto p-5">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <Badge className="border-0 bg-[#edf0e7] text-xs text-[#243e36]">{selectedStandard.category}</Badge>
                            <h3 className="mt-2 font-[Cabinet_Grotesk] text-xl font-black tracking-tight text-[#111815]">{selectedStandard.title}</h3>
                          </div>
                          <button type="button" onClick={() => setSelectedStandard(null)} className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#edf0e7] text-[#243e36] hover:bg-[#dbe3d7]" data-testid="crew-standard-detail-close"><X className="h-4 w-4" /></button>
                        </div>
                        <p className="mt-3 text-sm leading-relaxed text-[#41534a]">{selectedStandard.note}</p>
                        {selectedStandard.checklist && (
                          <div className="mt-4 rounded-[16px] bg-[#f6f6f2] p-4">
                            <p className="text-xs font-bold uppercase tracking-widest text-[#5f7464]">Checklist</p>
                            <ul className="mt-2 space-y-1">{selectedStandard.checklist.map((c, i) => <li key={i} className="text-sm text-[#41534a]">- {c}</li>)}</ul>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </TabsContent>

              <TabsContent value="equipment" data-testid="crew-equipment-tab-panel">
                <form className="space-y-5" onSubmit={handleEquipmentSubmit} data-testid="crew-equipment-form">
                  <div className="rounded-[24px] border border-border bg-[#f6f6f2] p-4">
                    <p className="text-sm font-semibold text-[#243e36]">Equipment maintenance record</p>
                    <p className="mt-1 text-sm text-[#5c6d64]">Capture pre-service and post-service photos, equipment number, general notes, and a Red-Tag Note for failures or newly found damage.</p>
                  </div>
                  <Input value={equipmentLog.equipment_number} onChange={(e) => setEquipmentLog((c) => ({ ...c, equipment_number: e.target.value }))} placeholder="Equipment##" className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="crew-equipment-number-input" />
                  <Textarea value={equipmentLog.general_note} onChange={(e) => setEquipmentLog((c) => ({ ...c, general_note: e.target.value }))} placeholder="General note" className="min-h-[90px] rounded-2xl border-transparent bg-[#edf0e7]" data-testid="crew-equipment-general-note-input" />
                  <Textarea value={equipmentLog.red_tag_note} onChange={(e) => setEquipmentLog((c) => ({ ...c, red_tag_note: e.target.value }))} placeholder="Red-Tag Note" className="min-h-[90px] rounded-2xl border-transparent bg-[#fdeaea]" data-testid="crew-equipment-red-tag-note-input" />
                  <div className="grid gap-4 sm:grid-cols-2">
                    <label className="flex h-24 cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-[#cdd3c8] bg-[#edf0e7] text-sm font-semibold text-[#243e36]" data-testid="crew-equipment-pre-upload-field">
                      <Upload className="h-4 w-4" />Pre-service photo
                      <input type="file" accept="image/*" className="hidden" onChange={(e) => setEquipmentLog((c) => ({ ...c, pre_photo: e.target.files?.[0] || null }))} data-testid="crew-equipment-pre-photo-input" />
                    </label>
                    <label className="flex h-24 cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-[#cdd3c8] bg-[#edf0e7] text-sm font-semibold text-[#243e36]" data-testid="crew-equipment-post-upload-field">
                      <Upload className="h-4 w-4" />Post-service photo
                      <input type="file" accept="image/*" className="hidden" onChange={(e) => setEquipmentLog((c) => ({ ...c, post_photo: e.target.files?.[0] || null }))} data-testid="crew-equipment-post-photo-input" />
                    </label>
                  </div>
                  <Button type="submit" disabled={equipmentSubmitting} className="h-14 w-full rounded-[22px] bg-[#243e36] text-base font-semibold text-white hover:bg-[#1a2c26]" data-testid="crew-equipment-submit-button">
                    {equipmentSubmitting ? "Submitting record..." : "Submit equipment record"}
                  </Button>
                </form>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        <Card className="rounded-[32px] border-border/80 bg-white/90 shadow-sm" data-testid="crew-capture-tips-card">
          <CardContent className="space-y-4 p-6">
            <div className="flex items-center gap-3 text-[#243e36]"><MapPinned className="h-5 w-5" /><p className="text-sm font-semibold">Best results: wide shot first, detail shots after, keep the truck number accurate.</p></div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
