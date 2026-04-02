import { useEffect, useState } from "react";
import { ChevronDown, Edit, FileSpreadsheet, Plus, QrCode, UploadCloud, X } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { motion, AnimatePresence } from "framer-motion";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { HelpPopover } from "@/components/common/HelpPopover";
import { authGet, authPatch, authPost, authPostForm, getApiOrigin } from "@/lib/api";
import { toast } from "sonner";


const DIVISIONS = ["Maintenance", "Install", "Tree", "Plant Healthcare", "Winter Services"];
const PAGE_SIZE = 10;


function ToggleSection({ title, subtitle, icon: Icon, count, defaultOpen = false, testId, children }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid={testId}>
      <CardContent className="p-6 lg:p-8">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="flex w-full items-center justify-between gap-3 text-left"
          data-testid={`${testId}-toggle`}
        >
          <div className="flex items-center gap-3">
            {Icon && <Icon className="h-5 w-5 text-[#243e36]" />}
            <div>
              <h3 className="font-[Cabinet_Grotesk] text-2xl font-black tracking-tight text-[#111815] lg:text-3xl">{title}</h3>
              {subtitle && <p className="mt-1 text-sm text-[#5c6d64]">{subtitle}</p>}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {count !== undefined && <Badge className="border-0 bg-[#edf0e7] text-[#243e36]">{count}</Badge>}
            <ChevronDown className={`h-5 w-5 text-[#5c6d64] transition-transform ${open ? "rotate-180" : ""}`} />
          </div>
        </button>
        <AnimatePresence initial={false}>
          {open && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25, ease: "easeInOut" }}
              className="overflow-hidden"
            >
              <div className="pt-5">{children}</div>
            </motion.div>
          )}
        </AnimatePresence>
      </CardContent>
    </Card>
  );
}


export default function JobsPage() {
  const [jobs, setJobs] = useState([]);
  const [activeLinks, setActiveLinks] = useState([]);
  const [inactiveLinks, setInactiveLinks] = useState([]);
  const [search, setSearch] = useState("");
  const [csvFile, setCsvFile] = useState(null);
  const [creating, setCreating] = useState(false);
  const [importing, setImporting] = useState(false);
  const [newLink, setNewLink] = useState({ label: "", truck_number: "", division: DIVISIONS[0], assignment: "" });
  const [editingLink, setEditingLink] = useState(null);
  const [editForm, setEditForm] = useState({ label: "", truck_number: "", division: DIVISIONS[0], assignment: "" });
  const [updating, setUpdating] = useState(false);
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
    if (!csvFile) { toast.error("Choose a CSV file before importing."); return; }
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
    } finally { setImporting(false); }
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
    } finally { setCreating(false); }
  };

  const handleUpdateCrewLink = async (event) => {
    event.preventDefault();
    if (!editingLink) return;
    setUpdating(true);
    try {
      await authPatch(`/crew-access-links/${editingLink.id}`, editForm);
      toast.success("Crew link updated.");
      setEditingLink(null);
      await loadPage();
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Unable to update crew link");
    } finally { setUpdating(false); }
  };

  const startEditLink = (link) => {
    setEditingLink(link);
    setEditForm({ label: link.label, truck_number: link.truck_number, division: link.division, assignment: link.assignment || "" });
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
    <div className="space-y-5" data-testid="jobs-page">
      <div className="grid gap-5 xl:grid-cols-[0.95fr_1.05fr]">
        <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="jobs-import-card">
          <CardContent className="p-6 lg:p-8">
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Job alignment import</p>
            <h2 className="mt-3 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815] lg:text-4xl">Import external job data for admin matching and review alignment.</h2>
            <p className="mt-3 flex items-center gap-1.5 text-sm leading-6 text-[#5c6d64]">
              Crews only enter Job Name in the field. Admins can use imported data here to align, match, and review submissions after the fact.
              <HelpPopover title="CSV import format">
                <p className="mb-2"><strong>Required columns:</strong></p>
                <code className="mb-3 block rounded-lg bg-[#f6f6f2] px-3 py-2 text-xs leading-relaxed">job_id, job_name, property_name, address, service_type, scheduled_date, division, truck_number</code>
                <p className="mb-2"><strong>Optional:</strong> route, latitude, longitude</p>
                <p className="mb-2"><strong>Notes:</strong></p>
                <ul className="mb-2 list-inside list-disc space-y-1 text-xs">
                  <li><strong>job_id</strong> is the unique key — duplicates update existing records</li>
                  <li><strong>service_type</strong> must match a rubric (e.g., "bed edging", "spring cleanup")</li>
                  <li><strong>division</strong> defaults to "General" if blank</li>
                  <li><strong>scheduled_date</strong> should be ISO format (YYYY-MM-DD)</li>
                  <li><strong>truck_number</strong> links jobs to crew QR codes</li>
                </ul>
                <p className="text-xs italic">Tip: Save as UTF-8 CSV from Excel to avoid encoding issues.</p>
              </HelpPopover>
            </p>
            <div className="mt-5 rounded-[24px] border border-dashed border-[#cdd3c8] bg-[#edf0e7] p-5" data-testid="jobs-import-dropzone">
              <div className="flex items-center gap-3 text-[#243e36]"><FileSpreadsheet className="h-5 w-5" /><p className="text-sm font-semibold">Expected columns: Job ID, Job Name, Property Name, Address, Service Type, Scheduled Date, Division, Truck Number, Route.</p></div>
              <Input type="file" accept=".csv" onChange={(event) => setCsvFile(event.target.files?.[0] || null)} className="mt-4 h-12 rounded-2xl border-transparent bg-white" data-testid="jobs-csv-file-input" />
              <Button onClick={handleImport} disabled={importing} className="mt-4 h-12 w-full rounded-2xl bg-[#243e36] hover:bg-[#1a2c26]" data-testid="jobs-csv-import-button">
                <UploadCloud className="mr-2 h-4 w-4" />{importing ? "Importing jobs..." : "Import CSV jobs"}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-[32px] border-border/80 bg-[#243e36] text-white shadow-sm" data-testid="jobs-create-crew-link-card">
          <CardContent className="p-6 lg:p-8">
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#d8f3dc]">Crew QR control</p>
            <h2 className="mt-3 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight lg:text-4xl">Create or update QR entries for field access.</h2>
            <p className="mt-2 flex items-center gap-1.5 text-sm text-white/70">
              Each code links to a truck and division.
              <HelpPopover title="Crew QR links" side="left">
                <p className="mb-2">Each crew gets a <strong>unique QR code</strong> tied to their truck number and division.</p>
                <p className="mb-2"><strong>How it works:</strong></p>
                <ul className="mb-2 list-inside list-disc space-y-1 text-xs">
                  <li>Scanning the QR opens the mobile capture portal — no login needed</li>
                  <li>The portal auto-filters jobs by the linked truck number</li>
                  <li>Submissions are tagged with crew label and division</li>
                  <li>Deactivated codes can be re-enabled later</li>
                </ul>
                <p className="text-xs italic">Tip: Print QR codes and laminate them for truck dashboards.</p>
              </HelpPopover>
            </p>
            <form className="mt-5 grid gap-3" onSubmit={handleCreateCrewLink} data-testid="jobs-create-crew-link-form">
              <Input value={newLink.label} onChange={(event) => setNewLink((c) => ({ ...c, label: event.target.value }))} placeholder="Crew label" className="h-11 rounded-2xl border-white/10 bg-white/10 text-white placeholder:text-white/60" data-testid="crew-link-label-input" />
              <Input value={newLink.truck_number} onChange={(event) => setNewLink((c) => ({ ...c, truck_number: event.target.value }))} placeholder="Truck number" className="h-11 rounded-2xl border-white/10 bg-white/10 text-white placeholder:text-white/60" data-testid="crew-link-truck-input" />
              <Input value={newLink.assignment} onChange={(event) => setNewLink((c) => ({ ...c, assignment: event.target.value }))} placeholder="Assignment / route note" className="h-11 rounded-2xl border-white/10 bg-white/10 text-white placeholder:text-white/60" data-testid="crew-link-assignment-input" />
              <select value={newLink.division} onChange={(event) => setNewLink((c) => ({ ...c, division: event.target.value }))} className="h-11 rounded-2xl border border-white/10 bg-white/10 px-4 text-sm text-white focus:outline-none" data-testid="crew-link-division-input">
                {DIVISIONS.map((d) => <option key={d} value={d} className="text-[#243e36]">{d}</option>)}
              </select>
              <Button type="submit" disabled={creating} className="h-11 rounded-2xl bg-white text-[#243e36] hover:bg-[#edf0e7]" data-testid="crew-link-create-button"><Plus className="mr-2 h-4 w-4" />{creating ? "Creating..." : "Create crew QR"}</Button>
            </form>

            {/* Update existing crew link */}
            {editingLink && (
              <div className="mt-5 rounded-[24px] bg-white/10 p-5" data-testid="crew-link-update-section">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold">Editing: {editingLink.label}</p>
                  <button type="button" onClick={() => setEditingLink(null)} className="text-white/70 hover:text-white"><X className="h-4 w-4" /></button>
                </div>
                <form className="mt-3 grid gap-3" onSubmit={handleUpdateCrewLink} data-testid="crew-link-update-form">
                  <Input value={editForm.label} onChange={(e) => setEditForm((c) => ({ ...c, label: e.target.value }))} placeholder="Crew label" className="h-11 rounded-2xl border-white/10 bg-white/10 text-white placeholder:text-white/60" data-testid="crew-link-update-label" />
                  <Input value={editForm.truck_number} onChange={(e) => setEditForm((c) => ({ ...c, truck_number: e.target.value }))} placeholder="Truck number" className="h-11 rounded-2xl border-white/10 bg-white/10 text-white placeholder:text-white/60" data-testid="crew-link-update-truck" />
                  <Input value={editForm.assignment} onChange={(e) => setEditForm((c) => ({ ...c, assignment: e.target.value }))} placeholder="Assignment / route" className="h-11 rounded-2xl border-white/10 bg-white/10 text-white placeholder:text-white/60" data-testid="crew-link-update-assignment" />
                  <select value={editForm.division} onChange={(e) => setEditForm((c) => ({ ...c, division: e.target.value }))} className="h-11 rounded-2xl border border-white/10 bg-white/10 px-4 text-sm text-white focus:outline-none" data-testid="crew-link-update-division">
                    {DIVISIONS.map((d) => <option key={d} value={d} className="text-[#243e36]">{d}</option>)}
                  </select>
                  <Button type="submit" disabled={updating} className="h-11 rounded-2xl bg-white text-[#243e36] hover:bg-[#edf0e7]" data-testid="crew-link-update-save-button">
                    <Edit className="mr-2 h-4 w-4" />{updating ? "Updating..." : "Save changes"}
                  </Button>
                </form>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Active Crew Links — Toggle */}
      <ToggleSection title="Active crew links" subtitle="Printable QR set" icon={QrCode} count={activeLinkPagination.total} defaultOpen testId="jobs-crew-qr-grid-card">
        <div className="flex items-center justify-between gap-3 text-sm text-[#5c6d64]">
          <p data-testid="jobs-active-pagination-label">Page {activeLinkPagination.page} of {activeLinkPagination.pages} · {activeLinkPagination.total} active links</p>
          <div className="flex gap-2">
            <Button type="button" variant="outline" size="sm" disabled={!activeLinkPagination.has_prev} onClick={() => loadPage({ nextActivePage: Math.max(activeLinkPagination.page - 1, 1) })} className="h-8 rounded-xl" data-testid="jobs-active-prev-button">Prev</Button>
            <Button type="button" variant="outline" size="sm" disabled={!activeLinkPagination.has_next} onClick={() => loadPage({ nextActivePage: Math.min(activeLinkPagination.page + 1, activeLinkPagination.pages) })} className="h-8 rounded-xl" data-testid="jobs-active-next-button">Next</Button>
          </div>
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
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
                  <button type="button" onClick={() => startEditLink(link)} className="rounded-xl bg-white p-2 text-[#243e36] shadow-sm transition hover:bg-[#edf0e7]" data-testid={`crew-qr-edit-button-${link.code}`}><Edit className="h-3.5 w-3.5" /></button>
                </div>
                <div className="mt-4 flex justify-center rounded-[28px] bg-white p-4">
                  <QRCodeSVG value={crewUrl} size={128} includeMargin data-testid={`crew-qr-svg-${link.code}`} />
                </div>
                <Input value={crewUrl} readOnly className="mt-4 h-10 rounded-2xl border-transparent bg-white text-xs" data-testid={`crew-qr-url-${link.code}`} />
                <Button type="button" onClick={() => window.open(crewUrl, "_blank", "noopener,noreferrer")} className="mt-3 h-10 w-full rounded-2xl bg-[#243e36] text-sm hover:bg-[#1a2c26]" data-testid={`crew-qr-open-button-${link.code}`}>Open crew portal</Button>
                <Button type="button" variant="outline" onClick={() => handleToggleCrewLink(link.id, false)} className="mt-2 h-10 w-full rounded-2xl border-[#243e36]/15 bg-white text-sm text-[#243e36] hover:bg-[#edf0e7]" data-testid={`crew-qr-deactivate-button-${link.code}`}>Remove from active</Button>
              </div>
            );
          })}
          {activeLinks.length === 0 && <div className="rounded-[24px] bg-[#f6f6f2] p-5 text-sm text-[#5c6d64]" data-testid="jobs-active-empty-state">No active crew links on this page yet.</div>}
        </div>
      </ToggleSection>

      {/* Inactive Crew Links — Toggle */}
      <ToggleSection title="Inactive crew links" subtitle="Archived without touching prior submission history" icon={QrCode} count={inactiveLinkPagination.total} defaultOpen={false} testId="jobs-inactive-crew-card">
        <div className="flex items-center justify-between gap-3 text-sm text-[#5c6d64]">
          <p data-testid="jobs-inactive-pagination-label">Page {inactiveLinkPagination.page} of {inactiveLinkPagination.pages} · {inactiveLinkPagination.total} archived links</p>
          <div className="flex gap-2">
            <Button type="button" variant="outline" size="sm" disabled={!inactiveLinkPagination.has_prev} onClick={() => loadPage({ nextInactivePage: Math.max(inactiveLinkPagination.page - 1, 1) })} className="h-8 rounded-xl" data-testid="jobs-inactive-prev-button">Prev</Button>
            <Button type="button" variant="outline" size="sm" disabled={!inactiveLinkPagination.has_next} onClick={() => loadPage({ nextInactivePage: Math.min(inactiveLinkPagination.page + 1, inactiveLinkPagination.pages) })} className="h-8 rounded-xl" data-testid="jobs-inactive-next-button">Next</Button>
          </div>
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {inactiveLinks.length === 0 ? <div className="rounded-[24px] bg-[#f6f6f2] p-5 text-sm text-[#5c6d64]">No inactive crew links yet.</div> : inactiveLinks.map((link) => (
            <div key={link.id} className="rounded-[28px] border border-border bg-[#f6f6f2] p-5" data-testid={`inactive-crew-card-${link.code}`}>
              <p className="text-sm font-semibold text-[#243e36]">{link.label}</p>
              <p className="mt-1 text-sm text-[#5c6d64]">{link.crew_member_id} · {link.truck_number} · {link.division}</p>
              {link.assignment && <p className="mt-1 text-xs text-[#5c6d64]">{link.assignment}</p>}
              <Button type="button" onClick={() => handleToggleCrewLink(link.id, true)} className="mt-4 h-10 w-full rounded-2xl bg-[#243e36] hover:bg-[#1a2c26]" data-testid={`inactive-crew-reactivate-button-${link.code}`}>Reactivate link</Button>
            </div>
          ))}
        </div>
      </ToggleSection>

      {/* Imported Jobs — Toggle */}
      <ToggleSection title="Imported jobs" subtitle="Alignment source for admins" icon={FileSpreadsheet} count={jobPagination.total} defaultOpen={false} testId="jobs-table-card">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Input value={search} onChange={handleSearchChange} placeholder="Search jobs" className="h-10 max-w-sm rounded-2xl border-transparent bg-[#edf0e7]" data-testid="jobs-search-input" />
          <div className="flex items-center gap-2 text-sm text-[#5c6d64]">
            <span data-testid="jobs-table-pagination-label">Page {jobPagination.page}/{jobPagination.pages} · {jobPagination.total} jobs</span>
            <Button type="button" variant="outline" size="sm" disabled={!jobPagination.has_prev} onClick={() => loadPage({ nextJobPage: Math.max(jobPagination.page - 1, 1) })} className="h-8 rounded-xl" data-testid="jobs-table-prev-button">Prev</Button>
            <Button type="button" variant="outline" size="sm" disabled={!jobPagination.has_next} onClick={() => loadPage({ nextJobPage: Math.min(jobPagination.page + 1, jobPagination.pages) })} className="h-8 rounded-xl" data-testid="jobs-table-next-button">Next</Button>
          </div>
        </div>
        <div className="mt-4 overflow-hidden rounded-[24px] border border-border">
          <div className="grid grid-cols-[1fr_1.3fr_1fr_0.9fr_1fr] gap-3 bg-[#edf0e7] px-4 py-3 text-xs font-bold uppercase tracking-[0.2em] text-[#5f7464]">
            <p>Job ID</p><p>Property</p><p>Service</p><p>Division</p><p>Scheduled</p>
          </div>
          {jobs.map((job) => (
            <div key={job.id} className="grid grid-cols-[1fr_1.3fr_1fr_0.9fr_1fr] gap-3 border-t border-border/80 px-4 py-3 text-sm text-[#243e36]" data-testid={`jobs-row-${job.id}`}>
              <p>{job.job_id}</p><p>{job.property_name}</p><p>{job.service_type}</p><p>{job.division}</p><p>{job.scheduled_date?.slice(0, 10)}</p>
            </div>
          ))}
          {jobs.length === 0 && <div className="border-t border-border/80 px-4 py-4 text-sm text-[#5c6d64]" data-testid="jobs-table-empty-state">No imported jobs match this search yet.</div>}
        </div>
      </ToggleSection>
    </div>
  );
}
