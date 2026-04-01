import { useEffect, useState } from "react";
import { Camera, Crosshair, MapPinned, Upload } from "lucide-react";
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


export default function CrewCapturePage() {
  const { code } = useParams();
  const [crewLink, setCrewLink] = useState(null);
  const [jobName, setJobName] = useState("");
  const [truckNumber, setTruckNumber] = useState("");
  const [note, setNote] = useState("");
  const [areaTag, setAreaTag] = useState("");
  const [photos, setPhotos] = useState([]);
  const [issueType, setIssueType] = useState("");
  const [issueNotes, setIssueNotes] = useState("");
  const [issuePhotos, setIssuePhotos] = useState([]);
  const [gps, setGps] = useState(null);
  const [locating, setLocating] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [crewNotifications, setCrewNotifications] = useState([]);
  const [incidentEnabled, setIncidentEnabled] = useState(false);
  const [taskType, setTaskType] = useState("");
  const [equipmentLog, setEquipmentLog] = useState({ equipment_number: "", general_note: "", red_tag_note: "", pre_photo: null, post_photo: null });
  const [equipmentSubmitting, setEquipmentSubmitting] = useState(false);
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

  useEffect(() => {
    loadCrewContext();
  }, [code]);

  const requestGps = () => {
    if (!navigator.geolocation) {
      toast.error("Geolocation is not supported on this device.");
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setGps({
          lat: Number(position.coords.latitude.toFixed(6)),
          lng: Number(position.coords.longitude.toFixed(6)),
          accuracy: Number(position.coords.accuracy?.toFixed(1) || 0),
        });
        setLocating(false);
        toast.success("GPS locked.");
      },
      () => {
        setLocating(false);
        toast.error("GPS permission is required before submitting.");
      },
      { enableHighAccuracy: true, timeout: 10000 },
    );
  };

  useEffect(() => {
    requestGps();
  }, []);

  useEffect(() => {
    if (!taskType && availableTasks.length) {
      setTaskType(availableTasks[0]);
    }
  }, [availableTasks, taskType]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!jobName || !truckNumber || !gps) {
      toast.error("Job Name, truck number, and GPS are required.");
      return;
    }
    if (!photos.length) {
      toast.error("Please attach photos before submitting.");
      return;
    }

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
    formData.append("issue_type", incidentEnabled ? issueType : "");
    formData.append("issue_notes", incidentEnabled ? issueNotes : "");
    photos.forEach((photo) => formData.append("photos", photo));
    if (incidentEnabled) {
      issuePhotos.forEach((photo) => formData.append("issue_photos", photo));
    }

    setSubmitting(true);
    try {
      await authPostForm("/public/submissions", formData);
      toast.success("Submission captured — your proof is now in review queue.");
      setJobName("");
      setNote("");
      setAreaTag("");
      setPhotos([]);
      setIssueType("");
      setIssueNotes("");
      setIssuePhotos([]);
      setIncidentEnabled(false);
      requestGps();
      loadCrewContext();
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Submission failed");
    } finally {
      setSubmitting(false);
    }
  };

  const handleEquipmentSubmit = async (event) => {
    event.preventDefault();
    if (!equipmentLog.equipment_number || !equipmentLog.pre_photo || !equipmentLog.post_photo) {
      toast.error("Equipment number and both maintenance photos are required.");
      return;
    }

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
    } finally {
      setEquipmentSubmitting(false);
    }
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
                <TabsTrigger value="capture" className="rounded-[18px] py-3 text-sm font-semibold" data-testid="crew-capture-tab-trigger">Work capture</TabsTrigger>
                <TabsTrigger value="standards" className="rounded-[18px] py-3 text-sm font-semibold" data-testid="crew-standards-tab-trigger">Standards highlights</TabsTrigger>
                <TabsTrigger value="equipment" className="rounded-[18px] py-3 text-sm font-semibold" data-testid="crew-equipment-tab-trigger">Equipment maintenance</TabsTrigger>
              </TabsList>

              <TabsContent value="capture">
                <form className="space-y-5" onSubmit={handleSubmit} data-testid="crew-capture-form">
              <div className="space-y-2">
                <label className="text-sm font-semibold text-[#243e36]" htmlFor="crew-job-name-input">Job Name</label>
                <Input id="crew-job-name-input" value={jobName} onChange={(event) => setJobName(event.target.value)} placeholder="Enter the job name exactly as given to the crew" className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="crew-job-name-input" />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-semibold text-[#243e36]" htmlFor="crew-truck-input">Truck number</label>
                <Input id="crew-truck-input" value={truckNumber} onChange={(event) => setTruckNumber(event.target.value)} className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="crew-truck-number-input" />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-semibold text-[#243e36]" htmlFor="crew-task-type-select">Current task</label>
                <select id="crew-task-type-select" value={taskType} onChange={(event) => setTaskType(event.target.value)} className="h-12 w-full rounded-2xl border border-transparent bg-[#edf0e7] px-4 text-sm" data-testid="crew-task-type-select">
                  {availableTasks.map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-[#243e36]" htmlFor="crew-area-tag-input">Area tag</label>
                  <Input id="crew-area-tag-input" value={areaTag} onChange={(event) => setAreaTag(event.target.value)} placeholder="Front entry / bed 2" className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="crew-area-tag-input" />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-[#243e36]" htmlFor="crew-photo-input">Photos</label>
                  <label htmlFor="crew-photo-input" className="flex h-12 cursor-pointer items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-[#cdd3c8] bg-[#edf0e7] text-sm font-semibold text-[#243e36]" data-testid="crew-photo-upload-field">
                    <Upload className="h-4 w-4" />
                    Add photos
                  </label>
                  <input id="crew-photo-input" type="file" multiple accept="image/*" className="hidden" onChange={(event) => setPhotos(Array.from(event.target.files || []))} data-testid="crew-photo-input" />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-semibold text-[#243e36]" htmlFor="crew-note-input">Optional note</label>
                <Textarea id="crew-note-input" value={note} onChange={(event) => setNote(event.target.value)} placeholder="Anything unusual the reviewers should know?" className="min-h-[96px] rounded-2xl border-transparent bg-[#edf0e7]" data-testid="crew-note-input" />
              </div>

              <div className="rounded-[24px] border border-border bg-[#f6f6f2] p-4" data-testid="crew-issue-report-card">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm font-semibold text-[#243e36]">Incident / damage reporting</p>
                    <p className="mt-1 text-sm text-[#5c6d64]">Turn this on only when you need to report an issue, damage event, or follow-up note.</p>
                  </div>
                  <div className="flex items-center gap-2 rounded-full bg-white px-3 py-2" data-testid="crew-issue-toggle-box">
                    <span className="text-xs font-bold uppercase tracking-[0.24em] text-[#5f7464]">Report</span>
                    <Switch checked={incidentEnabled} onCheckedChange={setIncidentEnabled} data-testid="crew-issue-toggle-switch" />
                  </div>
                </div>
                {incidentEnabled && (
                  <div className="mt-4 grid gap-3" data-testid="crew-issue-fields-wrap">
                    <Input value={issueType} onChange={(event) => setIssueType(event.target.value)} placeholder="Issue or damage type" className="h-12 rounded-2xl border-transparent bg-white" data-testid="crew-issue-type-input" />
                    <Textarea value={issueNotes} onChange={(event) => setIssueNotes(event.target.value)} placeholder="Describe what happened and where it happened" className="min-h-[90px] rounded-2xl border-transparent bg-white" data-testid="crew-issue-notes-input" />
                    <label htmlFor="crew-issue-photo-input" className="flex h-12 cursor-pointer items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-[#cdd3c8] bg-white text-sm font-semibold text-[#243e36]" data-testid="crew-issue-upload-field">
                      <Upload className="h-4 w-4" />
                      Add issue photo(s)
                    </label>
                    <input id="crew-issue-photo-input" type="file" multiple accept="image/*" className="hidden" onChange={(event) => setIssuePhotos(Array.from(event.target.files || []))} data-testid="crew-issue-photo-input" />
                  </div>
                )}
              </div>

              {incidentEnabled && issuePhotos.length > 0 && (
                <div className="grid grid-cols-2 gap-3" data-testid="crew-issue-preview-grid">
                  {issuePhotos.map((photo, index) => (
                    <div key={`${photo.name}-${index}`} className="rounded-[24px] border border-border bg-[#f6f6f2] p-3" data-testid={`crew-issue-preview-${index + 1}`}>
                      <div className="aspect-[4/3] overflow-hidden rounded-2xl bg-[#dde4d6]">
                        <img src={URL.createObjectURL(photo)} alt={photo.name} className="h-full w-full object-cover" />
                      </div>
                      <p className="mt-2 truncate text-xs font-semibold text-[#243e36]">{photo.name}</p>
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
                    <Crosshair className="mr-2 h-4 w-4" />
                    {locating ? "Locating" : "Refresh"}
                  </Button>
                </div>
              </div>

              {photos.length > 0 && (
                <div className="grid grid-cols-2 gap-3" data-testid="crew-photo-preview-grid">
                  {photos.map((photo, index) => (
                    <div key={`${photo.name}-${index}`} className="rounded-[24px] border border-border bg-[#f6f6f2] p-3" data-testid={`crew-photo-preview-${index + 1}`}>
                      <div className="aspect-[4/3] overflow-hidden rounded-2xl bg-[#dde4d6]">
                        <img src={URL.createObjectURL(photo)} alt={photo.name} className="h-full w-full object-cover" />
                      </div>
                      <p className="mt-2 truncate text-xs font-semibold text-[#243e36]">{photo.name}</p>
                    </div>
                  ))}
                </div>
              )}

              <Button type="submit" disabled={submitting || !gps} className="h-14 w-full rounded-[22px] bg-[#243e36] text-base font-semibold text-white hover:bg-[#1a2c26]" data-testid="crew-submit-photos-button">
                <Camera className="mr-2 h-5 w-5" />
                {submitting ? "Submitting proof..." : "Submit capture set"}
              </Button>
                </form>
              </TabsContent>

              <TabsContent value="standards" data-testid="crew-standards-tab-panel">
                <div className="space-y-4">
                  <div className="rounded-[24px] border border-border bg-[#f6f6f2] p-4">
                    <p className="text-sm font-semibold text-[#243e36]">Crew standards library</p>
                    <p className="mt-1 text-sm text-[#5c6d64]">Open this tab before you shoot a proof set when you want a fast reminder of what clean work should look like.</p>
                  </div>
                  {STANDARDS_HIGHLIGHTS.map((item) => (
                    <div key={item.id} className="overflow-hidden rounded-[24px] border border-border bg-[#f6f6f2]" data-testid={`crew-standard-card-${item.id}`}>
                      <div className="aspect-[5/3] overflow-hidden bg-[#dde4d6]">
                        <img src={item.image} alt={item.title} className="h-full w-full object-cover" />
                      </div>
                      <div className="space-y-2 p-4">
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-sm font-semibold text-[#243e36]">{item.title}</p>
                          <Badge className="border-0 bg-white text-[#243e36]" data-testid={`crew-standard-category-${item.id}`}>{item.category}</Badge>
                        </div>
                        <p className="text-sm text-[#5c6d64]">{item.note}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </TabsContent>
              <TabsContent value="equipment" data-testid="crew-equipment-tab-panel">
                <form className="space-y-5" onSubmit={handleEquipmentSubmit} data-testid="crew-equipment-form">
                  <div className="rounded-[24px] border border-border bg-[#f6f6f2] p-4">
                    <p className="text-sm font-semibold text-[#243e36]">Equipment maintenance record</p>
                    <p className="mt-1 text-sm text-[#5c6d64]">Capture pre-service and post-service photos, equipment number, general notes, and a Red-Tag Note for failures or newly found damage.</p>
                  </div>
                  <Input value={equipmentLog.equipment_number} onChange={(event) => setEquipmentLog((current) => ({ ...current, equipment_number: event.target.value }))} placeholder="Equipment##" className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="crew-equipment-number-input" />
                  <Textarea value={equipmentLog.general_note} onChange={(event) => setEquipmentLog((current) => ({ ...current, general_note: event.target.value }))} placeholder="General note" className="min-h-[90px] rounded-2xl border-transparent bg-[#edf0e7]" data-testid="crew-equipment-general-note-input" />
                  <Textarea value={equipmentLog.red_tag_note} onChange={(event) => setEquipmentLog((current) => ({ ...current, red_tag_note: event.target.value }))} placeholder="Red-Tag Note" className="min-h-[90px] rounded-2xl border-transparent bg-[#fdeaea]" data-testid="crew-equipment-red-tag-note-input" />
                  <div className="grid gap-4 sm:grid-cols-2">
                    <label className="flex h-24 cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-[#cdd3c8] bg-[#edf0e7] text-sm font-semibold text-[#243e36]" data-testid="crew-equipment-pre-upload-field">
                      <Upload className="h-4 w-4" />Pre-service photo
                      <input type="file" accept="image/*" className="hidden" onChange={(event) => setEquipmentLog((current) => ({ ...current, pre_photo: event.target.files?.[0] || null }))} data-testid="crew-equipment-pre-photo-input" />
                    </label>
                    <label className="flex h-24 cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-[#cdd3c8] bg-[#edf0e7] text-sm font-semibold text-[#243e36]" data-testid="crew-equipment-post-upload-field">
                      <Upload className="h-4 w-4" />Post-service photo
                      <input type="file" accept="image/*" className="hidden" onChange={(event) => setEquipmentLog((current) => ({ ...current, post_photo: event.target.files?.[0] || null }))} data-testid="crew-equipment-post-photo-input" />
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