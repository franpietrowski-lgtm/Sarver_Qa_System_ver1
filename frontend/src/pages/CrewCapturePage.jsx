import { useEffect, useMemo, useState } from "react";
import { Camera, Crosshair, MapPinned, Upload } from "lucide-react";
import { useParams } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { authPostForm, publicGet } from "@/lib/api";
import { toast } from "sonner";


export default function CrewCapturePage() {
  const { code } = useParams();
  const [crewLink, setCrewLink] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [jobSearch, setJobSearch] = useState("");
  const [jobId, setJobId] = useState("");
  const [truckNumber, setTruckNumber] = useState("");
  const [note, setNote] = useState("");
  const [areaTag, setAreaTag] = useState("");
  const [photos, setPhotos] = useState([]);
  const [gps, setGps] = useState(null);
  const [locating, setLocating] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [crewNotifications, setCrewNotifications] = useState([]);

  const loadCrewContext = async () => {
    try {
      const [link, jobsResponse] = await Promise.all([
        publicGet(`/public/crew-access/${code}`),
        publicGet(`/public/jobs?access_code=${code}`),
      ]);
      setCrewLink(link);
      setCrewNotifications(link.notifications || []);
      setTruckNumber(link.truck_number || "");
      setJobs(jobsResponse.jobs || []);
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

  const filteredJobs = useMemo(() => {
    const searchValue = jobSearch.toLowerCase();
    return jobs.filter((job) => {
      const text = `${job.job_id} ${job.job_name} ${job.property_name}`.toLowerCase();
      return text.includes(searchValue);
    });
  }, [jobSearch, jobs]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!jobId || !truckNumber || !gps) {
      toast.error("Job, truck number, and GPS are required.");
      return;
    }
    if (!photos.length) {
      toast.error("Please attach photos before submitting.");
      return;
    }

    const formData = new FormData();
    formData.append("access_code", code);
    formData.append("job_id", jobId);
    formData.append("truck_number", truckNumber);
    formData.append("gps_lat", gps.lat);
    formData.append("gps_lng", gps.lng);
    formData.append("gps_accuracy", gps.accuracy || 0);
    formData.append("note", note);
    formData.append("area_tag", areaTag);
    photos.forEach((photo) => formData.append("photos", photo));

    setSubmitting(true);
    try {
      await authPostForm("/public/submissions", formData);
      toast.success("Submission captured — your proof is now in review queue.");
      setNote("");
      setAreaTag("");
      setPhotos([]);
      requestGps();
      loadCrewContext();
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Submission failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,_#f6f6f2_0%,_#edf0e7_100%)] px-4 py-5 sm:px-6">
      <div className="mx-auto max-w-md space-y-5">
        <Card className="overflow-hidden rounded-[32px] border-border/80 bg-[#243e36] text-white shadow-sm" data-testid="crew-capture-header-card">
          <CardContent className="p-6">
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#d8f3dc]" data-testid="crew-capture-kicker">Crew capture portal</p>
            <h1 className="mt-3 font-[Cabinet_Grotesk] text-4xl font-black tracking-tight" data-testid="crew-capture-title">Submit work proof in one pass</h1>
            <p className="mt-3 text-sm text-white/80" data-testid="crew-capture-description">No login. Just select the job, confirm the truck, capture photos, and send.</p>

            {crewLink && (
              <div className="mt-5 flex flex-wrap gap-2">
                <Badge className="border-0 bg-white/12 px-3 py-1 text-white" data-testid="crew-capture-crew-badge">{crewLink.label}</Badge>
                <Badge className="border-0 bg-white/12 px-3 py-1 text-white" data-testid="crew-capture-crew-id-badge">ID {crewLink.crew_member_id}</Badge>
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
            <form className="space-y-5" onSubmit={handleSubmit} data-testid="crew-capture-form">
              <div className="space-y-2">
                <label className="text-sm font-semibold text-[#243e36]" htmlFor="crew-job-search">Search job</label>
                <Input id="crew-job-search" value={jobSearch} onChange={(event) => setJobSearch(event.target.value)} placeholder="Search by LMN tag or property" className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="crew-job-search-input" />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-semibold text-[#243e36]" htmlFor="crew-job-select">Job tag</label>
                <select id="crew-job-select" value={jobId} onChange={(event) => setJobId(event.target.value)} className="h-12 w-full rounded-2xl border border-transparent bg-[#edf0e7] px-4 text-sm focus:outline-none focus:ring-2 focus:ring-[#243e36]/20" data-testid="job-selection-dropdown">
                  <option value="">Select the job you’re at</option>
                  {filteredJobs.map((job) => (
                    <option key={job.id} value={job.id}>{job.job_id} · {job.property_name} · {job.service_type}</option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-semibold text-[#243e36]" htmlFor="crew-truck-input">Truck number</label>
                <Input id="crew-truck-input" value={truckNumber} onChange={(event) => setTruckNumber(event.target.value)} className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="crew-truck-number-input" />
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