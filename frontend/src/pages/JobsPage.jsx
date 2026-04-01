import { useEffect, useState } from "react";
import { FileSpreadsheet, Plus, QrCode, UploadCloud } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { authGet, authPatch, authPost, authPostForm, getApiOrigin } from "@/lib/api";
import { toast } from "sonner";


const DIVISIONS = ["Maintenance", "Install", "Tree", "Plant Healthcare", "Winter Services"];
const PAGE_SIZE = 10;


export default function JobsPage() {
  const [jobs, setJobs] = useState([]);
  const [activeLinks, setActiveLinks] = useState([]);
  const [inactiveLinks, setInactiveLinks] = useState([]);
  const [search, setSearch] = useState("");
  const [csvFile, setCsvFile] = useState(null);
  const [creating, setCreating] = useState(false);
  const [importing, setImporting] = useState(false);
  const [newLink, setNewLink] = useState({ label: "", truck_number: "", division: DIVISIONS[0], assignment: "" });
  const [jobPagination, setJobPagination] = useState({ page: 1, pages: 1, total: 0, limit: PAGE_SIZE });
  const [activeLinkPagination, setActiveLinkPagination] = useState({ page: 1, pages: 1, total: 0, limit: PAGE_SIZE });
  const [inactiveLinkPagination, setInactiveLinkPagination] = useState({ page: 1, pages: 1, total: 0, limit: PAGE_SIZE });

  const loadPage = async ({
    nextJobPage = jobPagination.page,
    nextActivePage = activeLinkPagination.page,
    nextInactivePage = inactiveLinkPagination.page,
    nextSearch = search,
  } = {}) => {
    const [jobsResponse, activeResponse, inactiveResponse] = await Promise.all([
      authGet(`/jobs?search=${encodeURIComponent(nextSearch)}&page=${nextJobPage}&limit=${PAGE_SIZE}`),
      authGet(`/crew-access-links?status=active&page=${nextActivePage}&limit=${PAGE_SIZE}`),
      authGet(`/crew-access-links?status=inactive&page=${nextInactivePage}&limit=${PAGE_SIZE}`),
    ]);
    setJobs(jobsResponse.items || []);
    setJobPagination(jobsResponse.pagination || { page: nextJobPage, pages: 1, total: 0, limit: PAGE_SIZE });
    setActiveLinks(activeResponse.items || []);
    setActiveLinkPagination(activeResponse.pagination || { page: nextActivePage, pages: 1, total: 0, limit: PAGE_SIZE });
    setInactiveLinks(inactiveResponse.items || []);
    setInactiveLinkPagination(inactiveResponse.pagination || { page: nextInactivePage, pages: 1, total: 0, limit: PAGE_SIZE });
  };

  useEffect(() => {
    loadPage({ nextJobPage: 1, nextActivePage: 1, nextInactivePage: 1 });
  }, []);

  const handleImport = async () => {
    if (!csvFile) {
      toast.error("Choose a CSV file before importing.");
      return;
    }
    const formData = new FormData();
    formData.append("file", csvFile);
    setImporting(true);
    try {
      const result = await authPostForm("/jobs/import-csv", formData);
      toast.success(`Imported ${result.imported} jobs and updated ${result.updated}.`);
      setCsvFile(null);
      await loadPage({ nextJobPage: 1, nextActivePage: 1, nextInactivePage: 1 });
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Import failed");
    } finally {
      setImporting(false);
    }
  };

  const handleCreateCrewLink = async (event) => {
    event.preventDefault();
    setCreating(true);
    try {
      await authPost("/crew-access-links", newLink);
      toast.success("New crew QR link created.");
      setNewLink({ label: "", truck_number: "", division: DIVISIONS[0], assignment: "" });
      await loadPage({ nextActivePage: 1, nextInactivePage: 1 });
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Unable to create crew link");
    } finally {
      setCreating(false);
    }
  };

  const appOrigin = getApiOrigin();

  const handleToggleCrewLink = async (crewLinkId, enabled) => {
    try {
      await authPatch(`/crew-access-links/${crewLinkId}/status`, { enabled });
      toast.success(enabled ? "Crew link reactivated." : "Crew link removed from active links.");
      await loadPage();
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Unable to update crew link");
    }
  };

  const handleSearchChange = async (event) => {
    const nextValue = event.target.value;
    setSearch(nextValue);
    await loadPage({ nextSearch: nextValue, nextJobPage: 1 });
  };

  return (
    <div className="space-y-6" data-testid="jobs-page">
      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="jobs-import-card">
          <CardContent className="p-8">
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Job alignment import</p>
            <h2 className="mt-3 font-[Cabinet_Grotesk] text-4xl font-black tracking-tight text-[#111815]">Import external job data for admin matching and review alignment.</h2>
            <p className="mt-3 text-sm leading-6 text-[#5c6d64]">Crews only enter Job Name in the field. Admins can use imported data here to align, match, and review submissions after the fact.</p>

            <div className="mt-6 rounded-[28px] border border-dashed border-[#cdd3c8] bg-[#edf0e7] p-5" data-testid="jobs-import-dropzone">
              <div className="flex items-center gap-3 text-[#243e36]"><FileSpreadsheet className="h-5 w-5" /><p className="text-sm font-semibold">Expected columns: Job ID, Job Name, Property Name, Address, Service Type, Scheduled Date, Division, Truck Number, Route.</p></div>
              <Input type="file" accept=".csv" onChange={(event) => setCsvFile(event.target.files?.[0] || null)} className="mt-4 h-12 rounded-2xl border-transparent bg-white" data-testid="jobs-csv-file-input" />
              <Button onClick={handleImport} disabled={importing} className="mt-4 h-12 w-full rounded-2xl bg-[#243e36] hover:bg-[#1a2c26]" data-testid="jobs-csv-import-button">
                <UploadCloud className="mr-2 h-4 w-4" />
                {importing ? "Importing jobs..." : "Import CSV jobs"}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-[32px] border-border/80 bg-[#243e36] text-white shadow-sm" data-testid="jobs-create-crew-link-card">
          <CardContent className="p-8">
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#d8f3dc]">Crew QR control</p>
            <h2 className="mt-3 font-[Cabinet_Grotesk] text-4xl font-black tracking-tight">Create unique QR entries for field access.</h2>
            <form className="mt-6 grid gap-4" onSubmit={handleCreateCrewLink} data-testid="jobs-create-crew-link-form">
              <Input value={newLink.label} onChange={(event) => setNewLink((current) => ({ ...current, label: event.target.value }))} placeholder="Crew label" className="h-12 rounded-2xl border-white/10 bg-white/10 text-white placeholder:text-white/60" data-testid="crew-link-label-input" />
              <Input value={newLink.truck_number} onChange={(event) => setNewLink((current) => ({ ...current, truck_number: event.target.value }))} placeholder="Truck number" className="h-12 rounded-2xl border-white/10 bg-white/10 text-white placeholder:text-white/60" data-testid="crew-link-truck-input" />
              <Input value={newLink.assignment} onChange={(event) => setNewLink((current) => ({ ...current, assignment: event.target.value }))} placeholder="Assignment / route note" className="h-12 rounded-2xl border-white/10 bg-white/10 text-white placeholder:text-white/60" data-testid="crew-link-assignment-input" />
              <select value={newLink.division} onChange={(event) => setNewLink((current) => ({ ...current, division: event.target.value }))} className="h-12 rounded-2xl border border-white/10 bg-white/10 px-4 text-sm text-white focus:outline-none" data-testid="crew-link-division-input">
                {DIVISIONS.map((division) => <option key={division} value={division} className="text-[#243e36]">{division}</option>)}
              </select>
              <Button type="submit" disabled={creating} className="h-12 rounded-2xl bg-white text-[#243e36] hover:bg-[#edf0e7]" data-testid="crew-link-create-button"><Plus className="mr-2 h-4 w-4" />{creating ? "Creating..." : "Create crew QR"}</Button>
            </form>
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="jobs-crew-qr-grid-card">
        <CardContent className="p-8">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Active crew links</p>
              <h3 className="mt-2 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]">Printable QR set</h3>
            </div>
            <QrCode className="h-6 w-6 text-[#243e36]" />
          </div>

          <div className="mt-4 flex items-center justify-between gap-3 text-sm text-[#5c6d64]">
            <p data-testid="jobs-active-pagination-label">Page {activeLinkPagination.page} of {activeLinkPagination.pages} · {activeLinkPagination.total} active links</p>
            <div className="flex gap-2">
              <Button type="button" variant="outline" disabled={!activeLinkPagination.has_prev} onClick={() => loadPage({ nextActivePage: Math.max(activeLinkPagination.page - 1, 1) })} className="h-9 rounded-2xl" data-testid="jobs-active-prev-button">Prev</Button>
              <Button type="button" variant="outline" disabled={!activeLinkPagination.has_next} onClick={() => loadPage({ nextActivePage: Math.min(activeLinkPagination.page + 1, activeLinkPagination.pages) })} className="h-9 rounded-2xl" data-testid="jobs-active-next-button">Next</Button>
            </div>
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {activeLinks.map((link) => {
              const crewUrl = `${appOrigin}/crew/${link.code}`;
              return (
                <div key={link.id} className="rounded-[28px] border border-border bg-[#f6f6f2] p-5" data-testid={`crew-qr-card-${link.code}`}>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-[#243e36]" data-testid={`crew-qr-label-${link.code}`}>{link.label}</p>
                      <p className="mt-1 text-sm text-[#5c6d64]" data-testid={`crew-qr-meta-${link.code}`}>{link.crew_member_id} · {link.truck_number} · {link.division}</p>
                      {link.assignment && <p className="mt-1 text-xs text-[#5c6d64]">{link.assignment}</p>}
                    </div>
                  </div>
                  <div className="mt-4 flex justify-center rounded-[28px] bg-white p-4">
                    <QRCodeSVG value={crewUrl} size={128} includeMargin data-testid={`crew-qr-svg-${link.code}`} />
                  </div>
                  <Input value={crewUrl} readOnly className="mt-4 h-11 rounded-2xl border-transparent bg-white" data-testid={`crew-qr-url-${link.code}`} />
                  <Button type="button" onClick={() => window.open(crewUrl, "_blank", "noopener,noreferrer")} className="mt-3 h-11 w-full rounded-2xl bg-[#243e36] hover:bg-[#1a2c26]" data-testid={`crew-qr-open-button-${link.code}`}>Open crew portal</Button>
                  <Button type="button" variant="outline" onClick={() => handleToggleCrewLink(link.id, false)} className="mt-3 h-11 w-full rounded-2xl border-[#243e36]/15 bg-white text-[#243e36] hover:bg-[#edf0e7]" data-testid={`crew-qr-deactivate-button-${link.code}`}>Remove from active links</Button>
                </div>
              );
            })}
            {activeLinks.length === 0 && <div className="rounded-[24px] bg-[#f6f6f2] p-5 text-sm text-[#5c6d64]" data-testid="jobs-active-empty-state">No active crew links on this page yet.</div>}
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="jobs-inactive-crew-card">
        <CardContent className="p-8">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Inactive crew links</p>
          <h3 className="mt-2 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]">Archived without touching prior submission history</h3>
          <div className="mt-4 flex items-center justify-between gap-3 text-sm text-[#5c6d64]">
            <p data-testid="jobs-inactive-pagination-label">Page {inactiveLinkPagination.page} of {inactiveLinkPagination.pages} · {inactiveLinkPagination.total} archived links</p>
            <div className="flex gap-2">
              <Button type="button" variant="outline" disabled={!inactiveLinkPagination.has_prev} onClick={() => loadPage({ nextInactivePage: Math.max(inactiveLinkPagination.page - 1, 1) })} className="h-9 rounded-2xl" data-testid="jobs-inactive-prev-button">Prev</Button>
              <Button type="button" variant="outline" disabled={!inactiveLinkPagination.has_next} onClick={() => loadPage({ nextInactivePage: Math.min(inactiveLinkPagination.page + 1, inactiveLinkPagination.pages) })} className="h-9 rounded-2xl" data-testid="jobs-inactive-next-button">Next</Button>
            </div>
          </div>
          <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {inactiveLinks.length === 0 ? <div className="rounded-[24px] bg-[#f6f6f2] p-5 text-sm text-[#5c6d64]">No inactive crew links yet.</div> : inactiveLinks.map((link) => (
              <div key={link.id} className="rounded-[28px] border border-border bg-[#f6f6f2] p-5" data-testid={`inactive-crew-card-${link.code}`}>
                <p className="text-sm font-semibold text-[#243e36]">{link.label}</p>
                <p className="mt-1 text-sm text-[#5c6d64]">{link.crew_member_id} · {link.truck_number} · {link.division}</p>
                {link.assignment && <p className="mt-1 text-xs text-[#5c6d64]">{link.assignment}</p>}
                <Button type="button" onClick={() => handleToggleCrewLink(link.id, true)} className="mt-4 h-11 w-full rounded-2xl bg-[#243e36] hover:bg-[#1a2c26]" data-testid={`inactive-crew-reactivate-button-${link.code}`}>Reactivate link</Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="jobs-table-card">
        <CardContent className="p-8">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Imported jobs</p>
              <h3 className="mt-2 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]">Alignment source for admins</h3>
            </div>
            <Input value={search} onChange={handleSearchChange} placeholder="Search jobs" className="h-11 max-w-sm rounded-2xl border-transparent bg-[#edf0e7]" data-testid="jobs-search-input" />
          </div>

          <div className="mt-4 flex items-center justify-between gap-3 text-sm text-[#5c6d64]">
            <p data-testid="jobs-table-pagination-label">Page {jobPagination.page} of {jobPagination.pages} · {jobPagination.total} jobs</p>
            <div className="flex gap-2">
              <Button type="button" variant="outline" disabled={!jobPagination.has_prev} onClick={() => loadPage({ nextJobPage: Math.max(jobPagination.page - 1, 1) })} className="h-9 rounded-2xl" data-testid="jobs-table-prev-button">Prev</Button>
              <Button type="button" variant="outline" disabled={!jobPagination.has_next} onClick={() => loadPage({ nextJobPage: Math.min(jobPagination.page + 1, jobPagination.pages) })} className="h-9 rounded-2xl" data-testid="jobs-table-next-button">Next</Button>
            </div>
          </div>

          <div className="mt-6 overflow-hidden rounded-[28px] border border-border">
            <div className="grid grid-cols-[1fr_1.3fr_1fr_0.9fr_1fr] gap-3 bg-[#edf0e7] px-4 py-3 text-xs font-bold uppercase tracking-[0.2em] text-[#5f7464]">
              <p>Job ID</p><p>Property</p><p>Service</p><p>Division</p><p>Scheduled</p>
            </div>
            {jobs.map((job) => (
              <div key={job.id} className="grid grid-cols-[1fr_1.3fr_1fr_0.9fr_1fr] gap-3 border-t border-border/80 px-4 py-4 text-sm text-[#243e36]" data-testid={`jobs-row-${job.id}`}>
                <p>{job.job_id}</p>
                <p>{job.property_name}</p>
                <p>{job.service_type}</p>
                <p>{job.division}</p>
                <p>{job.scheduled_date?.slice(0, 10)}</p>
              </div>
            ))}
            {jobs.length === 0 && <div className="border-t border-border/80 px-4 py-4 text-sm text-[#5c6d64]" data-testid="jobs-table-empty-state">No imported jobs match this search yet.</div>}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}