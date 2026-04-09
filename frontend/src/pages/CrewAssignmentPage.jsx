import { useCallback, useEffect, useState } from "react";
import { CalendarDays, ChevronLeft, ChevronRight, GripVertical, MapPin, Plus, Trash2, Truck, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { authDelete, authGet, authPost } from "@/lib/api";
import { toast } from "sonner";

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"];

function getMonday(dateStr) {
  const d = dateStr ? new Date(dateStr + "T12:00:00") : new Date();
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1);
  const mon = new Date(d.setDate(diff));
  return mon.toISOString().split("T")[0];
}

function addDays(dateStr, n) {
  const d = new Date(dateStr + "T12:00:00");
  d.setDate(d.getDate() + n);
  return d.toISOString().split("T")[0];
}

function formatDate(dateStr) {
  const d = new Date(dateStr + "T12:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export default function CrewAssignmentPage() {
  const [weekStart, setWeekStart] = useState(() => getMonday());
  const [weekData, setWeekData] = useState(null);
  const [crews, setCrews] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dragItem, setDragItem] = useState(null);
  const [showAssignModal, setShowAssignModal] = useState(null);
  const [assignForm, setAssignForm] = useState({ crew_code: "", job_id: "", notes: "", priority: "normal" });
  const [jobSearch, setJobSearch] = useState("");

  const dates = Array.from({ length: 5 }, (_, i) => addDays(weekStart, i));

  const loadWeek = useCallback(async () => {
    setLoading(true);
    try {
      const [weekRes, crewRes, jobRes] = await Promise.all([
        authGet(`/crew-assignments/week?start=${weekStart}`),
        authGet("/crew-access-links"),
        authGet("/jobs"),
      ]);
      setWeekData(weekRes.week || {});
      const crewList = Array.isArray(crewRes) ? crewRes : crewRes.items || [];
      setCrews(crewList.filter(c => c.enabled !== false));
      const jobList = Array.isArray(jobRes) ? jobRes : jobRes.items || [];
      setJobs(jobList);
    } catch {
      toast.error("Unable to load crew assignments");
    } finally {
      setLoading(false);
    }
  }, [weekStart]);

  useEffect(() => { loadWeek(); }, [loadWeek]);

  const prevWeek = () => setWeekStart(addDays(weekStart, -7));
  const nextWeek = () => setWeekStart(addDays(weekStart, 7));
  const goToday = () => setWeekStart(getMonday());

  const handleAssign = async () => {
    if (!assignForm.crew_code || !assignForm.job_id || !showAssignModal) return;
    try {
      await authPost("/crew-assignments", { ...assignForm, date: showAssignModal });
      toast.success("Job assigned");
      setShowAssignModal(null);
      setAssignForm({ crew_code: "", job_id: "", notes: "", priority: "normal" });
      await loadWeek();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Assignment failed");
    }
  };

  const handleDelete = async (id) => {
    try {
      await authDelete(`/crew-assignments/${id}`);
      toast.success("Assignment removed");
      await loadWeek();
    } catch {
      toast.error("Unable to remove assignment");
    }
  };

  const handleDrop = async (date) => {
    if (!dragItem) return;
    try {
      await authPost("/crew-assignments", { crew_code: dragItem.crew_code, job_id: dragItem.job_id, date, priority: "normal", notes: "" });
      toast.success(`Assigned to ${formatDate(date)}`);
      await loadWeek();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Drop assignment failed");
    }
    setDragItem(null);
  };

  const handlePreloadWeek = async () => {
    const assignments = [];
    for (const crew of crews) {
      const matchingJobs = jobs.filter(j => j.division === crew.division || j.truck_number === crew.truck_number);
      for (const job of matchingJobs.slice(0, 2)) {
        for (const date of dates) {
          assignments.push({ crew_code: crew.code, job_id: job.job_id, date, priority: "normal", notes: "Auto-assigned (week forecast)" });
        }
      }
    }
    if (!assignments.length) { toast.info("No matching jobs found for auto-assignment"); return; }
    try {
      const res = await authPost("/crew-assignments/bulk", { assignments });
      toast.success(`${res.created} assignments created, ${res.skipped} skipped (duplicates)`);
      await loadWeek();
    } catch {
      toast.error("Bulk assignment failed");
    }
  };

  const filteredJobs = jobs.filter(j => {
    if (!jobSearch) return true;
    const q = jobSearch.toLowerCase();
    return (j.job_id || "").toLowerCase().includes(q) || (j.job_name || "").toLowerCase().includes(q) || (j.property_name || "").toLowerCase().includes(q);
  });

  if (loading && !weekData) {
    return <div className="rounded-[28px] border border-border bg-[var(--card)] p-10 text-center text-[var(--foreground)]" data-testid="assignments-loading">Loading assignments...</div>;
  }

  return (
    <div className="space-y-5" data-testid="crew-assignment-page">
      {/* Header */}
      <Card className="rounded-[24px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="assignments-header-card">
        <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
          <div className="flex items-center gap-3">
            <CalendarDays className="h-5 w-5 text-[var(--foreground)]" />
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Daily crew assignment</p>
              <p className="font-[Outfit] text-lg font-bold text-[var(--foreground)]">
                Week of {formatDate(weekStart)} — {formatDate(addDays(weekStart, 4))}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={prevWeek} className="h-8 rounded-xl border-[var(--form-card-border)] text-[var(--foreground)]" data-testid="assignments-prev-week"><ChevronLeft className="h-4 w-4" /></Button>
            <Button variant="outline" size="sm" onClick={goToday} className="h-8 rounded-xl border-[var(--form-card-border)] text-xs text-[var(--foreground)]" data-testid="assignments-today-btn">Today</Button>
            <Button variant="outline" size="sm" onClick={nextWeek} className="h-8 rounded-xl border-[var(--form-card-border)] text-[var(--foreground)]" data-testid="assignments-next-week"><ChevronRight className="h-4 w-4" /></Button>
            <Button size="sm" onClick={handlePreloadWeek} className="h-8 rounded-xl bg-[var(--btn-accent)] text-xs hover:bg-[var(--btn-accent-hover)]" data-testid="assignments-preload-btn">
              Pre-load week forecast
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Week Grid */}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-5" data-testid="assignments-week-grid">
        {dates.map((date, dayIdx) => {
          const dayAssignments = (weekData || {})[date] || [];
          const isToday = date === new Date().toISOString().split("T")[0];

          return (
            <Card
              key={date}
              className={`rounded-[20px] border-border/80 shadow-sm transition-all ${isToday ? "ring-2 ring-[var(--btn-accent)]/40" : ""}`}
              style={{ backgroundColor: "var(--card)" }}
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => handleDrop(date)}
              data-testid={`assignment-day-${date}`}
            >
              <CardContent className="p-3">
                <div className="mb-3 flex items-center justify-between">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-wider text-[var(--muted-foreground)]">{WEEKDAYS[dayIdx]}</p>
                    <p className={`text-sm font-semibold ${isToday ? "text-[var(--btn-accent)]" : "text-[var(--foreground)]"}`}>{formatDate(date)}</p>
                  </div>
                  <button
                    onClick={() => { setShowAssignModal(date); setAssignForm({ crew_code: "", job_id: "", notes: "", priority: "normal" }); }}
                    className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--chip-bg)] text-[var(--foreground)] transition-colors hover:bg-[var(--btn-accent)] hover:text-white"
                    data-testid={`assignment-add-${date}`}
                  >
                    <Plus className="h-3.5 w-3.5" />
                  </button>
                </div>

                <div className="space-y-2">
                  {dayAssignments.map((a) => (
                    <div
                      key={a.id}
                      draggable
                      onDragStart={() => setDragItem({ crew_code: a.crew_code, job_id: a.job_id })}
                      className="group rounded-[14px] border border-[var(--form-card-border)] bg-[var(--form-card-bg)] p-2.5 transition-shadow hover:shadow-md cursor-grab active:cursor-grabbing"
                      data-testid={`assignment-card-${a.id}`}
                    >
                      <div className="flex items-start justify-between gap-1">
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-xs font-semibold text-[var(--foreground)]">{a.job?.job_name || a.job_id}</p>
                          <p className="mt-0.5 flex items-center gap-1 truncate text-[10px] text-[var(--muted-foreground)]">
                            <Truck className="h-2.5 w-2.5 shrink-0" />{a.crew?.label || a.crew_code}
                          </p>
                          {a.job?.address && <p className="mt-0.5 flex items-center gap-1 truncate text-[10px] text-[var(--muted-foreground)]"><MapPin className="h-2.5 w-2.5 shrink-0" />{a.job.address}</p>}
                        </div>
                        <div className="flex shrink-0 items-center gap-0.5">
                          <GripVertical className="h-3 w-3 text-[var(--muted-foreground)] opacity-0 transition-opacity group-hover:opacity-100" />
                          <button onClick={() => handleDelete(a.id)} className="rounded p-0.5 text-[var(--muted-foreground)] hover:text-red-500" data-testid={`assignment-delete-${a.id}`}>
                            <Trash2 className="h-3 w-3" />
                          </button>
                        </div>
                      </div>
                      {a.priority === "high" && <span className="mt-1 inline-block rounded-full bg-red-500/15 px-2 py-0.5 text-[9px] font-bold text-red-500">HIGH</span>}
                    </div>
                  ))}

                  {dayAssignments.length === 0 && (
                    <div className="rounded-[14px] border border-dashed border-[var(--form-card-border)] p-4 text-center text-[10px] text-[var(--muted-foreground)]" data-testid={`assignment-empty-${date}`}>
                      Drop a job here or click +
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Unassigned Jobs Pool */}
      <Card className="rounded-[24px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="assignments-job-pool">
        <CardContent className="p-4">
          <p className="mb-3 text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Job pool — drag onto a day</p>
          <Input
            placeholder="Search jobs..."
            value={jobSearch}
            onChange={(e) => setJobSearch(e.target.value)}
            className="mb-3 h-9 rounded-xl border-[var(--form-card-border)] bg-[var(--chip-bg)] text-sm"
            data-testid="assignments-job-search"
          />
          <div className="flex flex-wrap gap-2">
            {filteredJobs.slice(0, 20).map((job) => (
              <div
                key={job.id || job.job_id}
                draggable
                onDragStart={() => setDragItem({ crew_code: crews[0]?.code || "", job_id: job.job_id })}
                className="cursor-grab rounded-[12px] border border-[var(--form-card-border)] bg-[var(--form-card-bg)] px-3 py-1.5 text-xs text-[var(--foreground)] transition-shadow hover:shadow active:cursor-grabbing"
                data-testid={`job-pool-${job.job_id}`}
              >
                <span className="font-semibold">{job.job_id}</span> · {job.property_name || job.job_name}
                <span className="ml-1 text-[var(--muted-foreground)]">({job.division})</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Assign Modal */}
      {showAssignModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4" data-testid="assignment-modal-overlay">
          <Card className="w-full max-w-md rounded-[24px] border border-white/10 shadow-2xl" style={{ background: "var(--modal-bg, var(--card))", backdropFilter: "blur(24px)", WebkitBackdropFilter: "blur(24px)" }}>
            <CardContent className="p-6">
              <div className="mb-4 flex items-center justify-between">
                <p className="text-sm font-bold text-[var(--foreground)]">Assign job — {formatDate(showAssignModal)}</p>
                <button onClick={() => setShowAssignModal(null)} className="text-[var(--muted-foreground)] hover:text-[var(--foreground)]"><X className="h-4 w-4" /></button>
              </div>
              <div className="space-y-3">
                <div>
                  <label className="mb-1 block text-xs font-semibold text-[var(--foreground)]">Crew</label>
                  <select value={assignForm.crew_code} onChange={(e) => setAssignForm(f => ({ ...f, crew_code: e.target.value }))} className="glass-dropdown h-10 w-full rounded-xl border border-[var(--form-card-border)] bg-[var(--chip-bg)] px-3 text-sm text-[var(--foreground)]" data-testid="assignment-modal-crew-select">
                    <option value="">Select crew...</option>
                    {crews.map(c => <option key={c.code} value={c.code}>{c.label} ({c.division} · {c.truck_number})</option>)}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-semibold text-[var(--foreground)]">Job</label>
                  <select value={assignForm.job_id} onChange={(e) => setAssignForm(f => ({ ...f, job_id: e.target.value }))} className="glass-dropdown h-10 w-full rounded-xl border border-[var(--form-card-border)] bg-[var(--chip-bg)] px-3 text-sm text-[var(--foreground)]" data-testid="assignment-modal-job-select">
                    <option value="">Select job...</option>
                    {jobs.map(j => <option key={j.id || j.job_id} value={j.job_id}>{j.job_id} — {j.property_name || j.job_name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-semibold text-[var(--foreground)]">Priority</label>
                  <select value={assignForm.priority} onChange={(e) => setAssignForm(f => ({ ...f, priority: e.target.value }))} className="glass-dropdown h-10 w-full rounded-xl border border-[var(--form-card-border)] bg-[var(--chip-bg)] px-3 text-sm text-[var(--foreground)]" data-testid="assignment-modal-priority-select">
                    <option value="normal">Normal</option>
                    <option value="high">High</option>
                  </select>
                </div>
                <Input placeholder="Notes (optional)" value={assignForm.notes} onChange={(e) => setAssignForm(f => ({ ...f, notes: e.target.value }))} className="h-10 rounded-xl border-[var(--form-card-border)] bg-[var(--chip-bg)]" data-testid="assignment-modal-notes" />
                <Button onClick={handleAssign} disabled={!assignForm.crew_code || !assignForm.job_id} className="h-10 w-full rounded-xl bg-[var(--btn-accent)] hover:bg-[var(--btn-accent-hover)]" data-testid="assignment-modal-submit">
                  Assign to {formatDate(showAssignModal)}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
