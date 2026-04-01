import { useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ChevronLeft, ChevronRight, Copy, LibraryBig, Plus, Wrench } from "lucide-react";
import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { authGet, authPatch, authPost } from "@/lib/api";
import { toast } from "sonner";


const DIVISIONS = ["Maintenance", "Install", "Tree", "Plant Healthcare", "Winter Services"];
const CATEGORIES = ["Edging", "Mulch", "Cleanup", "Pruning", "Damage Prevention"];

const emptyForm = {
  title: "",
  category: CATEGORIES[0],
  audience: "crew",
  division_targets: [],
  checklistText: "",
  notes: "",
  owner_notes: "",
  shoutout: "",
  image_url: "",
  training_enabled: true,
  question_type: "multiple_choice",
  question_prompt: "",
  choice_options_text: "",
  correct_answer: "",
  is_active: true,
};


function ToggleSection({ title, subtitle, icon: Icon, defaultOpen = false, testId, children }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div data-testid={testId}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between gap-3 rounded-2xl px-1 py-2 text-left transition hover:bg-[#edf0e7]/40"
        data-testid={`${testId}-toggle`}
      >
        <div className="flex items-center gap-3">
          {Icon && <Icon className="h-5 w-5 text-[#243e36]" />}
          <div>
            <p className="text-sm font-semibold text-[#111815]">{title}</p>
            {subtitle && <p className="text-xs text-[#5c6d64]">{subtitle}</p>}
          </div>
        </div>
        <ChevronDown className={`h-4 w-4 text-[#5c6d64] transition-transform ${open ? "rotate-180" : ""}`} />
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
            <div className="pt-3">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}


function LibraryCarousel({ items, onEdit }) {
  const scrollRef = useRef(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  const checkScroll = () => {
    if (!scrollRef.current) return;
    const { scrollLeft, scrollWidth, clientWidth } = scrollRef.current;
    setCanScrollLeft(scrollLeft > 4);
    setCanScrollRight(scrollLeft + clientWidth < scrollWidth - 4);
  };

  useEffect(() => {
    checkScroll();
    const el = scrollRef.current;
    if (el) el.addEventListener("scroll", checkScroll, { passive: true });
    return () => el?.removeEventListener("scroll", checkScroll);
  }, [items]);

  const scroll = (direction) => {
    if (!scrollRef.current) return;
    const amount = scrollRef.current.clientWidth * 0.72;
    scrollRef.current.scrollBy({ left: direction === "left" ? -amount : amount, behavior: "smooth" });
  };

  if (items.length === 0) {
    return <p className="py-6 text-center text-sm text-[#5c6d64]" data-testid="library-carousel-empty">No standards match this filter.</p>;
  }

  return (
    <div className="relative" data-testid="library-carousel">
      {canScrollLeft && (
        <button type="button" onClick={() => scroll("left")} className="absolute -left-2 top-1/2 z-10 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full border border-border bg-white shadow-md transition hover:bg-[#edf0e7]" data-testid="library-carousel-prev">
          <ChevronLeft className="h-4 w-4 text-[#243e36]" />
        </button>
      )}
      {canScrollRight && (
        <button type="button" onClick={() => scroll("right")} className="absolute -right-2 top-1/2 z-10 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full border border-border bg-white shadow-md transition hover:bg-[#edf0e7]" data-testid="library-carousel-next">
          <ChevronRight className="h-4 w-4 text-[#243e36]" />
        </button>
      )}
      <div ref={scrollRef} className="flex snap-x snap-mandatory gap-4 overflow-x-auto scroll-smooth pb-2" style={{ scrollbarWidth: "none", msOverflowStyle: "none", WebkitOverflowScrolling: "touch" }}>
        {items.map((item) => (
          <div key={item.id} className="w-[280px] flex-shrink-0 snap-start overflow-hidden rounded-[24px] border border-border bg-[#f6f6f2]" data-testid={`standard-item-card-${item.id}`}>
            <div className="aspect-[5/3] bg-[#dbe3d7]">
              {item.image_url && <img src={item.image_url} alt={item.title} className="h-full w-full object-cover" loading="lazy" />}
            </div>
            <div className="space-y-2.5 p-3.5">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-[#243e36]">{item.title}</p>
                  <p className="mt-0.5 line-clamp-2 text-xs text-[#5c6d64]">{item.notes}</p>
                </div>
                <Button type="button" variant="outline" size="sm" onClick={() => onEdit(item)} className="h-7 shrink-0 rounded-xl border-[#243e36]/10 bg-white text-xs text-[#243e36] hover:bg-[#edf0e7]" data-testid={`standard-edit-button-${item.id}`}>Edit</Button>
              </div>
              <div className="flex flex-wrap gap-1.5">
                <Badge className="border-0 bg-white text-[10px] text-[#243e36]">{item.category}</Badge>
                <Badge className="border-0 bg-white text-[10px] text-[#243e36]">{item.audience}</Badge>
                {(item.division_targets || []).slice(0, 2).map((d) => <Badge key={d} className="border-0 bg-white text-[10px] text-[#243e36]">{d}</Badge>)}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}


export default function StandardsLibraryPage() {
  const [items, setItems] = useState([]);
  const [pagination, setPagination] = useState({ page: 1, pages: 1, total: 0 });
  const [crewLinks, setCrewLinks] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [equipmentLogs, setEquipmentLogs] = useState([]);
  const [equipmentPagination, setEquipmentPagination] = useState({ page: 1, pages: 1, total: 0 });
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [division, setDivision] = useState("all");
  const [editingId, setEditingId] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [creating, setCreating] = useState(false);
  const [sessionForm, setSessionForm] = useState({ access_code: "", division: "use-crew-division", item_count: 5 });
  const [sessionUrl, setSessionUrl] = useState("");

  const loadPage = async () => {
    const [standardsResponse, crewResponse, sessionsResponse, eqResponse] = await Promise.all([
      authGet(`/standards?search=${encodeURIComponent(search)}&category=${category}&division=${division}&audience=all&page=1&limit=20`),
      authGet("/crew-access-links?status=active&page=1&limit=50"),
      authGet("/training-sessions?page=1&limit=8"),
      authGet("/equipment-logs?page=1&limit=8"),
    ]);
    setItems(standardsResponse.items || []);
    setPagination(standardsResponse.pagination || { page: 1, pages: 1, total: 0 });
    setCrewLinks(crewResponse.items || []);
    setSessions(sessionsResponse.items || []);
    setEquipmentLogs(eqResponse.items || []);
    setEquipmentPagination(eqResponse.pagination || { page: 1, pages: 1, total: 0 });
    setSessionForm((current) => ({ ...current, access_code: current.access_code || crewResponse.items?.[0]?.code || "" }));
  };

  const loadEquipmentPage = async (page) => {
    const eqResponse = await authGet(`/equipment-logs?page=${page}&limit=8`);
    setEquipmentLogs(eqResponse.items || []);
    setEquipmentPagination(eqResponse.pagination || { page, pages: 1, total: 0 });
  };

  useEffect(() => {
    loadPage();
  }, [search, category, division]);

  const selectedCrew = useMemo(() => crewLinks.find((item) => item.code === sessionForm.access_code), [crewLinks, sessionForm.access_code]);

  const toggleDivision = (targetDivision) => {
    setForm((current) => ({
      ...current,
      division_targets: current.division_targets.includes(targetDivision)
        ? current.division_targets.filter((item) => item !== targetDivision)
        : [...current.division_targets, targetDivision],
    }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setCreating(true);
    try {
      const payload = {
        title: form.title,
        category: form.category,
        audience: form.audience,
        division_targets: form.division_targets,
        checklist: form.checklistText.split("\n").map((item) => item.trim()).filter(Boolean),
        notes: form.notes,
        owner_notes: form.owner_notes,
        shoutout: form.shoutout,
        image_url: form.image_url,
        training_enabled: form.training_enabled,
        question_type: form.question_type,
        question_prompt: form.question_prompt,
        choice_options: form.choice_options_text.split(",").map((item) => item.trim()).filter(Boolean),
        correct_answer: form.correct_answer,
        is_active: form.is_active,
      };
      if (editingId) {
        await authPatch(`/standards/${editingId}`, payload);
        toast.success("Standard updated.");
      } else {
        await authPost("/standards", payload);
        toast.success("Standard added to the library.");
      }
      setEditingId("");
      setForm(emptyForm);
      setSessionUrl("");
      await loadPage();
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Unable to save standard item");
    } finally {
      setCreating(false);
    }
  };

  const handleEdit = (item) => {
    setEditingId(item.id);
    setForm({
      title: item.title,
      category: item.category,
      audience: item.audience,
      division_targets: item.division_targets || [],
      checklistText: (item.checklist || []).join("\n"),
      notes: item.notes || "",
      owner_notes: item.owner_notes || "",
      shoutout: item.shoutout || "",
      image_url: item.image_url,
      training_enabled: item.training_enabled,
      question_type: item.question_type,
      question_prompt: item.question_prompt,
      choice_options_text: (item.choice_options || []).join(", "),
      correct_answer: item.correct_answer,
      is_active: item.is_active,
    });
  };

  const createTrainingSession = async () => {
    try {
      const response = await authPost("/training-sessions", {
        access_code: sessionForm.access_code,
        division: sessionForm.division === "use-crew-division" ? (selectedCrew?.division || "") : sessionForm.division,
        item_count: sessionForm.item_count,
      });
      setSessionUrl(response.session_url);
      toast.success("Training session generated.");
      await loadPage();
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Unable to create training session");
    }
  };

  const copyValue = async (value) => {
    await navigator.clipboard.writeText(value);
    toast.success("Copied to clipboard.");
  };

  return (
    <div className="space-y-5" data-testid="standards-library-page">
      {/* Hero + Training session launch */}
      <div className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="standards-library-hero-card">
          <CardContent className="p-6 lg:p-8">
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Standards Library</p>
            <h1 className="mt-3 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815] lg:text-4xl">Author company standards and turn them into crew-ready training material.</h1>
            <p className="mt-3 text-sm leading-6 text-[#5c6d64]">Use universal categories like edging, mulch, cleanup, pruning, and damage prevention, then narrow the content by division when a task needs omissions or division-specific focus.</p>

            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search standards" className="h-11 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="standards-search-input" />
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger className="h-11 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="standards-category-filter"><SelectValue placeholder="Category" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All categories</SelectItem>
                  {CATEGORIES.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}
                </SelectContent>
              </Select>
              <Select value={division} onValueChange={setDivision}>
                <SelectTrigger className="h-11 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="standards-division-filter"><SelectValue placeholder="Division" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All divisions</SelectItem>
                  {DIVISIONS.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <p className="mt-3 text-sm text-[#5c6d64]" data-testid="standards-total-count">{pagination.total} standards in the current view.</p>
          </CardContent>
        </Card>

        <Card className="rounded-[32px] border-border/80 bg-[#243e36] text-white shadow-sm" data-testid="standards-training-session-card">
          <CardContent className="p-6 lg:p-8">
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#d8f3dc]">Training Mode launch</p>
            <h2 className="mt-3 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight lg:text-4xl">Generate a no-login crew session from the library.</h2>
            <div className="mt-5 grid gap-3">
              <Select value={sessionForm.access_code} onValueChange={(value) => setSessionForm((current) => ({ ...current, access_code: value }))}>
                <SelectTrigger className="h-11 rounded-2xl border-white/10 bg-white/10 text-white" data-testid="training-session-crew-select"><SelectValue placeholder="Choose crew" /></SelectTrigger>
                <SelectContent>
                  {crewLinks.map((item) => <SelectItem key={item.code} value={item.code}>{item.label} · {item.division}</SelectItem>)}
                </SelectContent>
              </Select>
              <div className="grid gap-3 sm:grid-cols-2">
                <Select value={sessionForm.division} onValueChange={(value) => setSessionForm((current) => ({ ...current, division: value }))}>
                  <SelectTrigger className="h-11 rounded-2xl border-white/10 bg-white/10 text-white" data-testid="training-session-division-select"><SelectValue placeholder="Division override" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="use-crew-division">Use crew division</SelectItem>
                    {DIVISIONS.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}
                  </SelectContent>
                </Select>
                <Input type="number" min="1" max="5" value={sessionForm.item_count} onChange={(event) => setSessionForm((current) => ({ ...current, item_count: Number(event.target.value) || 5 }))} className="h-11 rounded-2xl border-white/10 bg-white/10 text-white" data-testid="training-session-count-input" />
              </div>
              <Button onClick={createTrainingSession} className="h-11 rounded-2xl bg-white text-[#243e36] hover:bg-[#edf0e7]" data-testid="training-session-create-button"><Plus className="mr-2 h-4 w-4" />Create training session</Button>
            </div>

            {sessionUrl && (
              <div className="mt-5 rounded-[24px] bg-white/10 p-4" data-testid="training-session-link-card">
                <p className="text-sm font-semibold">Session ready for {selectedCrew?.label}</p>
                <p className="mt-1 break-all text-sm text-white/70">{sessionUrl}</p>
                <Button type="button" variant="outline" onClick={() => copyValue(sessionUrl)} className="mt-3 h-10 rounded-2xl border-white/15 bg-white/10 text-white hover:bg-white/15" data-testid="training-session-copy-link-button"><Copy className="mr-2 h-4 w-4" />Copy link</Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Library items — Carousel */}
      <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="standards-list-card">
        <CardContent className="p-6 lg:p-8">
          <ToggleSection title="Library items" subtitle={`${items.length} standards loaded`} icon={LibraryBig} defaultOpen testId="standards-library-section">
            <LibraryCarousel items={items} onEdit={handleEdit} />
          </ToggleSection>
        </CardContent>
      </Card>

      {/* Authoring + Equipment Records */}
      <div className="grid gap-5 xl:grid-cols-2">
        <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="standards-author-form-card">
          <CardContent className="p-6 lg:p-8">
            <ToggleSection title={editingId ? "Edit standard" : "Author new standard"} subtitle="Create or modify company standards" icon={LibraryBig} defaultOpen={false} testId="standards-authoring-section">
              <form className="space-y-4" onSubmit={handleSubmit} data-testid="standards-author-form">
                <Input value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} placeholder="Title" className="h-11 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="standards-title-input" />
                <div className="grid gap-3 sm:grid-cols-2">
                  <Select value={form.category} onValueChange={(value) => setForm((current) => ({ ...current, category: value }))}>
                    <SelectTrigger className="h-11 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="standards-form-category-select"><SelectValue /></SelectTrigger>
                    <SelectContent>{CATEGORIES.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent>
                  </Select>
                  <Select value={form.audience} onValueChange={(value) => setForm((current) => ({ ...current, audience: value }))}>
                    <SelectTrigger className="h-11 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="standards-form-audience-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="crew">Crew-facing</SelectItem>
                      <SelectItem value="internal">Internal</SelectItem>
                      <SelectItem value="both">Both</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Input value={form.image_url} onChange={(event) => setForm((current) => ({ ...current, image_url: event.target.value }))} placeholder="Image URL" className="h-11 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="standards-image-url-input" />
                <div className="rounded-[20px] bg-[#f6f6f2] p-4">
                  <p className="text-sm font-semibold text-[#243e36]">Division targets</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {DIVISIONS.map((item) => (
                      <button key={item} type="button" onClick={() => toggleDivision(item)} className={`rounded-full px-3 py-1.5 text-sm font-semibold ${form.division_targets.includes(item) ? "bg-[#243e36] text-white" : "bg-white text-[#243e36]"}`} data-testid={`standards-division-chip-${item.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
                        {item}
                      </button>
                    ))}
                  </div>
                </div>
                <Textarea value={form.checklistText} onChange={(event) => setForm((current) => ({ ...current, checklistText: event.target.value }))} placeholder="Checklist items, one per line" className="min-h-[90px] rounded-2xl border-transparent bg-[#edf0e7]" data-testid="standards-checklist-input" />
                <Textarea value={form.notes} onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))} placeholder="Crew-facing notes" className="min-h-[70px] rounded-2xl border-transparent bg-[#edf0e7]" data-testid="standards-notes-input" />
                <Textarea value={form.owner_notes} onChange={(event) => setForm((current) => ({ ...current, owner_notes: event.target.value }))} placeholder="Owner/admin notes" className="min-h-[70px] rounded-2xl border-transparent bg-[#edf0e7]" data-testid="standards-owner-notes-input" />
                <Input value={form.shoutout} onChange={(event) => setForm((current) => ({ ...current, shoutout: event.target.value }))} placeholder="@CrewID shoutout" className="h-11 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="standards-shoutout-input" />
                <div className="grid gap-3 sm:grid-cols-2">
                  <Select value={form.question_type} onValueChange={(value) => setForm((current) => ({ ...current, question_type: value }))}>
                    <SelectTrigger className="h-11 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="standards-question-type-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="multiple_choice">Multiple choice</SelectItem>
                      <SelectItem value="free_text">Free text</SelectItem>
                    </SelectContent>
                  </Select>
                  <Input value={form.correct_answer} onChange={(event) => setForm((current) => ({ ...current, correct_answer: event.target.value }))} placeholder="Correct answer" className="h-11 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="standards-correct-answer-input" />
                </div>
                <Input value={form.question_prompt} onChange={(event) => setForm((current) => ({ ...current, question_prompt: event.target.value }))} placeholder="Question prompt" className="h-11 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="standards-question-prompt-input" />
                <Input value={form.choice_options_text} onChange={(event) => setForm((current) => ({ ...current, choice_options_text: event.target.value }))} placeholder="Multiple choice options, comma-separated" className="h-11 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="standards-choice-options-input" />
                <div className="flex items-center justify-between rounded-[20px] bg-[#f6f6f2] px-4 py-3" data-testid="standards-toggle-row">
                  <div>
                    <p className="text-sm font-semibold text-[#243e36]">Training enabled</p>
                    <p className="text-xs text-[#5c6d64]">Allow this standard to appear in training sessions.</p>
                  </div>
                  <Switch checked={form.training_enabled} onCheckedChange={(value) => setForm((current) => ({ ...current, training_enabled: value }))} data-testid="standards-training-enabled-switch" />
                </div>
                <Button type="submit" disabled={creating} className="h-11 w-full rounded-2xl bg-[#243e36] hover:bg-[#1a2c26]" data-testid="standards-save-button">{creating ? "Saving..." : editingId ? "Update standard" : "Create standard"}</Button>
              </form>
            </ToggleSection>
          </CardContent>
        </Card>

        <div className="space-y-5">
          {/* Equipment Records */}
          <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="standards-equipment-records-card">
            <CardContent className="p-6 lg:p-8">
              <ToggleSection title="Equipment records" subtitle={`${equipmentPagination.total} maintenance logs`} icon={Wrench} defaultOpen={false} testId="standards-equipment-section">
                <div className="space-y-3">
                  {equipmentLogs.map((log) => (
                    <div key={log.id} className="rounded-[20px] border border-border bg-[#f6f6f2] p-4" data-testid={`equipment-log-card-${log.id}`}>
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-[#243e36]">#{log.equipment_number}</p>
                          <p className="mt-0.5 text-xs text-[#5c6d64]">{log.crew_label} · {log.division}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          {log.red_tag && <Badge className="border-0 bg-[#fbf0ef] text-xs text-[#7a2323]">Red tag</Badge>}
                          {log.forwarded_to_owner && <Badge className="border-0 bg-[#edf0e7] text-xs text-[#243e36]">Forwarded</Badge>}
                        </div>
                      </div>
                      {log.notes && <p className="mt-2 text-xs text-[#5c6d64]">{log.notes}</p>}
                      {log.red_tag_note && <p className="mt-1 text-xs font-medium text-[#7a2323]">{log.red_tag_note}</p>}
                      <p className="mt-2 text-[10px] text-[#5c6d64]">{log.created_at?.slice(0, 16)}</p>
                    </div>
                  ))}
                  {equipmentLogs.length === 0 && <p className="py-4 text-center text-sm text-[#5c6d64]">No equipment logs recorded yet.</p>}
                  {equipmentPagination.total > 8 && (
                    <div className="flex items-center justify-between pt-1" data-testid="equipment-logs-pagination">
                      <span className="text-xs text-[#5c6d64]">Page {equipmentPagination.page} of {equipmentPagination.pages}</span>
                      <div className="flex gap-1.5">
                        <Button type="button" variant="outline" size="sm" disabled={!equipmentPagination.has_prev} onClick={() => loadEquipmentPage(equipmentPagination.page - 1)} className="h-7 rounded-lg text-xs" data-testid="equipment-prev-btn">Prev</Button>
                        <Button type="button" variant="outline" size="sm" disabled={!equipmentPagination.has_next} onClick={() => loadEquipmentPage(equipmentPagination.page + 1)} className="h-7 rounded-lg text-xs" data-testid="equipment-next-btn">Next</Button>
                      </div>
                    </div>
                  )}
                </div>
              </ToggleSection>
            </CardContent>
          </Card>

          {/* Recent Training Sessions */}
          <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="recent-training-sessions-card">
            <CardContent className="p-6 lg:p-8">
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Recent training sessions</p>
              <div className="mt-4 space-y-3">
                {sessions.map((item) => (
                  <div key={item.id} className="rounded-[20px] border border-border bg-[#f6f6f2] p-4" data-testid={`training-session-row-${item.id}`}>
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-[#243e36]">{item.crew_label}</p>
                        <p className="mt-1 text-xs text-[#5c6d64]">{item.division} · {item.status}</p>
                      </div>
                      <Button type="button" variant="outline" size="sm" onClick={() => copyValue(`${window.location.origin}/training/${item.code}`)} className="h-7 rounded-xl border-[#243e36]/10 bg-white text-xs text-[#243e36] hover:bg-[#edf0e7]" data-testid={`training-session-copy-button-${item.id}`}><Copy className="mr-2 h-3 w-3" />Copy</Button>
                    </div>
                  </div>
                ))}
                {sessions.length === 0 && <p className="py-4 text-center text-sm text-[#5c6d64]">No training sessions created yet.</p>}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Cross-links */}
      <div className="grid gap-3 sm:grid-cols-2" data-testid="standards-crosslinks">
        <Link to="/repeat-offenders" className="rounded-[20px] border border-border bg-[#f6f6f2] p-4 transition hover:bg-white" data-testid="standards-link-repeat-offenders">
          <p className="text-xs font-bold uppercase tracking-wider text-[#5f7464]">Related</p>
          <p className="mt-1 font-semibold text-[#243e36]">Repeat Offenders</p>
          <p className="mt-0.5 text-xs text-[#5c6d64]">Track crews who repeat quality issues and trigger training.</p>
        </Link>
        <Link to="/rubric-editor" className="rounded-[20px] border border-border bg-[#f6f6f2] p-4 transition hover:bg-white" data-testid="standards-link-rubric-editor">
          <p className="text-xs font-bold uppercase tracking-wider text-[#5f7464]">Related</p>
          <p className="mt-1 font-semibold text-[#243e36]">Rubric Matrices</p>
          <p className="mt-0.5 text-xs text-[#5c6d64]">Manage grading factors and thresholds by division.</p>
        </Link>
      </div>
    </div>
  );
}
