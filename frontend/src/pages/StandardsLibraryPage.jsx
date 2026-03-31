import { useEffect, useMemo, useState } from "react";
import { Copy, LibraryBig, Plus, QrCode } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { authGet, authPatch, authPost } from "@/lib/api";
import { toast } from "sonner";


const DIVISIONS = ["Maintenance", "Install", "PHC - Plant Healthcare", "Sarver Tree"];
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


export default function StandardsLibraryPage() {
  const [items, setItems] = useState([]);
  const [pagination, setPagination] = useState({ page: 1, pages: 1, total: 0 });
  const [crewLinks, setCrewLinks] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [division, setDivision] = useState("all");
  const [editingId, setEditingId] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [creating, setCreating] = useState(false);
  const [sessionForm, setSessionForm] = useState({ access_code: "", division: "use-crew-division", item_count: 5 });
  const [sessionUrl, setSessionUrl] = useState("");

  const loadPage = async () => {
    const [standardsResponse, crewResponse, sessionsResponse] = await Promise.all([
      authGet(`/standards?search=${encodeURIComponent(search)}&category=${category}&division=${division}&audience=all&page=1&limit=12`),
      authGet("/crew-access-links?status=active&page=1&limit=100"),
      authGet("/training-sessions?page=1&limit=8"),
    ]);
    setItems(standardsResponse.items || []);
    setPagination(standardsResponse.pagination || { page: 1, pages: 1, total: 0 });
    setCrewLinks(crewResponse.items || []);
    setSessions(sessionsResponse.items || []);
    setSessionForm((current) => ({ ...current, access_code: current.access_code || crewResponse.items?.[0]?.code || "" }));
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
    <div className="space-y-6" data-testid="standards-library-page">
      <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="standards-library-hero-card">
          <CardContent className="p-8">
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Standards Library</p>
            <h1 className="mt-3 font-[Cabinet_Grotesk] text-4xl font-black tracking-tight text-[#111815]">Author company standards and turn them into crew-ready training material.</h1>
            <p className="mt-3 text-sm leading-6 text-[#5c6d64]">Use universal categories like edging, mulch, cleanup, pruning, and damage prevention, then narrow the content by division when a task needs omissions or division-specific focus.</p>

            <div className="mt-6 grid gap-3 sm:grid-cols-3">
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
            <p className="mt-4 text-sm text-[#5c6d64]" data-testid="standards-total-count">{pagination.total} standards in the current view.</p>
          </CardContent>
        </Card>

        <Card className="rounded-[32px] border-border/80 bg-[#243e36] text-white shadow-sm" data-testid="standards-training-session-card">
          <CardContent className="p-8">
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#d8f3dc]">Training Mode launch</p>
            <h2 className="mt-3 font-[Cabinet_Grotesk] text-4xl font-black tracking-tight">Generate a no-login crew session from the library.</h2>
            <div className="mt-6 grid gap-4">
              <Select value={sessionForm.access_code} onValueChange={(value) => setSessionForm((current) => ({ ...current, access_code: value }))}>
                <SelectTrigger className="h-12 rounded-2xl border-white/10 bg-white/10 text-white" data-testid="training-session-crew-select"><SelectValue placeholder="Choose crew" /></SelectTrigger>
                <SelectContent>
                  {crewLinks.map((item) => <SelectItem key={item.code} value={item.code}>{item.label} · {item.division}</SelectItem>)}
                </SelectContent>
              </Select>
              <Select value={sessionForm.division} onValueChange={(value) => setSessionForm((current) => ({ ...current, division: value }))}>
                <SelectTrigger className="h-12 rounded-2xl border-white/10 bg-white/10 text-white" data-testid="training-session-division-select"><SelectValue placeholder="Division override" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="use-crew-division">Use crew division</SelectItem>
                  {DIVISIONS.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}
                </SelectContent>
              </Select>
              <Input type="number" min="1" max="5" value={sessionForm.item_count} onChange={(event) => setSessionForm((current) => ({ ...current, item_count: Number(event.target.value) || 5 }))} className="h-12 rounded-2xl border-white/10 bg-white/10 text-white" data-testid="training-session-count-input" />
              <Button onClick={createTrainingSession} className="h-12 rounded-2xl bg-white text-[#243e36] hover:bg-[#edf0e7]" data-testid="training-session-create-button"><Plus className="mr-2 h-4 w-4" />Create training session</Button>
            </div>

            {sessionUrl && (
              <div className="mt-6 rounded-[28px] bg-white/10 p-5" data-testid="training-session-link-card">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold">Session ready for {selectedCrew?.label}</p>
                    <p className="mt-1 break-all text-sm text-white/70">{sessionUrl}</p>
                  </div>
                  <QRCodeSVG value={sessionUrl} size={120} bgColor="transparent" fgColor="#ffffff" />
                </div>
                <Button type="button" variant="outline" onClick={() => copyValue(sessionUrl)} className="mt-4 h-11 rounded-2xl border-white/15 bg-white/10 text-white hover:bg-white/15" data-testid="training-session-copy-link-button"><Copy className="mr-2 h-4 w-4" />Copy link</Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="standards-author-form-card">
          <CardContent className="p-8">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Authoring</p>
                <h2 className="mt-2 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]">{editingId ? "Edit standard" : "Add standard"}</h2>
              </div>
              <LibraryBig className="h-6 w-6 text-[#243e36]" />
            </div>

            <form className="mt-6 space-y-4" onSubmit={handleSubmit} data-testid="standards-author-form">
              <Input value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} placeholder="Title" className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="standards-title-input" />
              <div className="grid gap-4 sm:grid-cols-2">
                <Select value={form.category} onValueChange={(value) => setForm((current) => ({ ...current, category: value }))}>
                  <SelectTrigger className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="standards-form-category-select"><SelectValue /></SelectTrigger>
                  <SelectContent>{CATEGORIES.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent>
                </Select>
                <Select value={form.audience} onValueChange={(value) => setForm((current) => ({ ...current, audience: value }))}>
                  <SelectTrigger className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="standards-form-audience-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="crew">Crew-facing</SelectItem>
                    <SelectItem value="internal">Internal</SelectItem>
                    <SelectItem value="both">Both</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Input value={form.image_url} onChange={(event) => setForm((current) => ({ ...current, image_url: event.target.value }))} placeholder="Image URL" className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="standards-image-url-input" />
              <div className="rounded-[24px] bg-[#f6f6f2] p-4">
                <p className="text-sm font-semibold text-[#243e36]">Division targets</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {DIVISIONS.map((item) => (
                    <button key={item} type="button" onClick={() => toggleDivision(item)} className={`rounded-full px-4 py-2 text-sm font-semibold ${form.division_targets.includes(item) ? "bg-[#243e36] text-white" : "bg-white text-[#243e36]"}`} data-testid={`standards-division-chip-${item.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
                      {item}
                    </button>
                  ))}
                </div>
              </div>
              <Textarea value={form.checklistText} onChange={(event) => setForm((current) => ({ ...current, checklistText: event.target.value }))} placeholder="Checklist items, one per line" className="min-h-[110px] rounded-2xl border-transparent bg-[#edf0e7]" data-testid="standards-checklist-input" />
              <Textarea value={form.notes} onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))} placeholder="Crew-facing notes" className="min-h-[90px] rounded-2xl border-transparent bg-[#edf0e7]" data-testid="standards-notes-input" />
              <Textarea value={form.owner_notes} onChange={(event) => setForm((current) => ({ ...current, owner_notes: event.target.value }))} placeholder="Owner/admin notes" className="min-h-[90px] rounded-2xl border-transparent bg-[#edf0e7]" data-testid="standards-owner-notes-input" />
              <Input value={form.shoutout} onChange={(event) => setForm((current) => ({ ...current, shoutout: event.target.value }))} placeholder="@CrewID shoutout" className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="standards-shoutout-input" />
              <div className="grid gap-4 sm:grid-cols-2">
                <Select value={form.question_type} onValueChange={(value) => setForm((current) => ({ ...current, question_type: value }))}>
                  <SelectTrigger className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="standards-question-type-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="multiple_choice">Multiple choice</SelectItem>
                    <SelectItem value="free_text">Free text</SelectItem>
                  </SelectContent>
                </Select>
                <Input value={form.correct_answer} onChange={(event) => setForm((current) => ({ ...current, correct_answer: event.target.value }))} placeholder="Correct answer" className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="standards-correct-answer-input" />
              </div>
              <Input value={form.question_prompt} onChange={(event) => setForm((current) => ({ ...current, question_prompt: event.target.value }))} placeholder="Question prompt" className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="standards-question-prompt-input" />
              <Input value={form.choice_options_text} onChange={(event) => setForm((current) => ({ ...current, choice_options_text: event.target.value }))} placeholder="Multiple choice options, comma-separated" className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="standards-choice-options-input" />
              <div className="flex items-center justify-between rounded-[24px] bg-[#f6f6f2] px-4 py-3" data-testid="standards-toggle-row">
                <div>
                  <p className="text-sm font-semibold text-[#243e36]">Training enabled</p>
                  <p className="text-sm text-[#5c6d64]">Allow this standard to appear in training sessions.</p>
                </div>
                <Switch checked={form.training_enabled} onCheckedChange={(value) => setForm((current) => ({ ...current, training_enabled: value }))} data-testid="standards-training-enabled-switch" />
              </div>
              <Button type="submit" disabled={creating} className="h-12 w-full rounded-2xl bg-[#243e36] hover:bg-[#1a2c26]" data-testid="standards-save-button">{creating ? "Saving..." : editingId ? "Update standard" : "Create standard"}</Button>
            </form>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="standards-list-card">
            <CardContent className="p-8">
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Library items</p>
              <div className="mt-6 space-y-4">
                {items.map((item) => (
                  <div key={item.id} className="overflow-hidden rounded-[24px] border border-border bg-[#f6f6f2]" data-testid={`standard-item-card-${item.id}`}>
                    <div className="aspect-[5/3] bg-[#dbe3d7]">
                      <img src={item.image_url} alt={item.title} className="h-full w-full object-cover" />
                    </div>
                    <div className="space-y-3 p-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-[#243e36]">{item.title}</p>
                          <p className="mt-1 text-sm text-[#5c6d64]">{item.notes}</p>
                        </div>
                        <Button type="button" variant="outline" onClick={() => handleEdit(item)} className="rounded-2xl border-[#243e36]/10 bg-white text-[#243e36] hover:bg-[#edf0e7]" data-testid={`standard-edit-button-${item.id}`}>Edit</Button>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Badge className="border-0 bg-white text-[#243e36]">{item.category}</Badge>
                        <Badge className="border-0 bg-white text-[#243e36]">{item.audience}</Badge>
                        {(item.division_targets || []).map((divisionItem) => <Badge key={divisionItem} className="border-0 bg-white text-[#243e36]">{divisionItem}</Badge>)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="recent-training-sessions-card">
            <CardContent className="p-8">
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Recent training sessions</p>
              <div className="mt-4 space-y-3">
                {sessions.map((item) => (
                  <div key={item.id} className="rounded-[24px] border border-border bg-[#f6f6f2] p-4" data-testid={`training-session-row-${item.id}`}>
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-[#243e36]">{item.crew_label}</p>
                        <p className="mt-1 text-sm text-[#5c6d64]">{item.division} · {item.status}</p>
                      </div>
                      <Button type="button" variant="outline" onClick={() => copyValue(`${window.location.origin}/training/${item.code}`)} className="rounded-2xl border-[#243e36]/10 bg-white text-[#243e36] hover:bg-[#edf0e7]" data-testid={`training-session-copy-button-${item.id}`}><Copy className="mr-2 h-4 w-4" />Copy</Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}