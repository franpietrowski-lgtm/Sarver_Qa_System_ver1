import { useEffect, useState } from "react";
import { GripVertical, Pencil, Plus, Save, Trash2, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { authGet, authPatch, authPost } from "@/lib/api";
import { toast } from "sonner";


const DIVISIONS = ["Maintenance", "Install", "Tree", "Plant Healthcare", "Winter Services"];


export default function RubricEditorPage({ user }) {
  const [rubrics, setRubrics] = useState([]);
  const [divisionFilter, setDivisionFilter] = useState("all");
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState(null);
  const [creating, setCreating] = useState(false);
  const [newForm, setNewForm] = useState(null);
  const [saving, setSaving] = useState(false);

  const isGmOrOwner = user?.title === "GM" || user?.title === "Owner" || user?.role === "owner";

  const loadRubrics = async () => {
    try {
      const data = await authGet(`/rubric-matrices?division=${divisionFilter}&include_inactive=true`);
      setRubrics(data || []);
    } catch {
      toast.error("Failed to load rubrics");
    }
  };

  useEffect(() => { loadRubrics(); }, [divisionFilter]);

  const startEdit = (rubric) => {
    setEditingId(rubric.id);
    setEditForm({
      title: rubric.title,
      division: rubric.division,
      min_photos: rubric.min_photos,
      pass_threshold: rubric.pass_threshold,
      hard_fail_conditions: [...(rubric.hard_fail_conditions || [])],
      categories: (rubric.categories || []).map((c) => ({ ...c })),
      is_active: rubric.is_active !== false,
    });
    setCreating(false);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditForm(null);
  };

  const startCreate = () => {
    setCreating(true);
    setEditingId(null);
    setNewForm({
      service_type: "",
      division: DIVISIONS[0],
      title: "",
      min_photos: 3,
      pass_threshold: 80,
      hard_fail_conditions: [],
      categories: [
        { key: "factor_1", label: "Factor 1", weight: 0.34, max_score: 5 },
        { key: "factor_2", label: "Factor 2", weight: 0.33, max_score: 5 },
        { key: "factor_3", label: "Factor 3", weight: 0.33, max_score: 5 },
      ],
    });
  };

  const addCategory = (form, setForm) => {
    const count = form.categories.length;
    if (count >= 10) return;
    const newWeight = Math.round((1 / (count + 1)) * 100) / 100;
    const redistributed = form.categories.map((c) => ({ ...c, weight: newWeight }));
    const remainder = Math.round((1 - newWeight * count) * 100) / 100;
    setForm({
      ...form,
      categories: [...redistributed, { key: `factor_${count + 1}`, label: `Factor ${count + 1}`, weight: remainder, max_score: 5 }],
    });
  };

  const removeCategory = (form, setForm, index) => {
    if (form.categories.length <= 1) return;
    const updated = form.categories.filter((_, i) => i !== index);
    const evenWeight = Math.round((1 / updated.length) * 100) / 100;
    const redistributed = updated.map((c, i) => ({
      ...c,
      weight: i === updated.length - 1 ? Math.round((1 - evenWeight * (updated.length - 1)) * 100) / 100 : evenWeight,
    }));
    setForm({ ...form, categories: redistributed });
  };

  const updateCategoryWeight = (form, setForm, index, newWeight) => {
    const clamped = Math.max(0.01, Math.min(0.99, newWeight));
    const others = form.categories.filter((_, i) => i !== index);
    const remaining = Math.max(0.01, 1 - clamped);
    const otherTotal = others.reduce((sum, c) => sum + c.weight, 0) || 1;
    const updated = form.categories.map((c, i) => {
      if (i === index) return { ...c, weight: Math.round(clamped * 100) / 100 };
      return { ...c, weight: Math.round((c.weight / otherTotal) * remaining * 100) / 100 };
    });
    setForm({ ...form, categories: updated });
  };

  const updateCategoryField = (form, setForm, index, field, value) => {
    const updated = form.categories.map((c, i) => (i === index ? { ...c, [field]: value } : c));
    if (field === "label") {
      updated[index].key = value.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
    }
    setForm({ ...form, categories: updated });
  };

  const saveEdit = async () => {
    if (!editForm || !editingId) return;
    setSaving(true);
    try {
      await authPatch(`/rubric-matrices/${editingId}`, editForm);
      toast.success("Rubric updated");
      cancelEdit();
      await loadRubrics();
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Update failed");
    } finally {
      setSaving(false);
    }
  };

  const saveCreate = async () => {
    if (!newForm || !newForm.service_type.trim() || !newForm.title.trim()) {
      toast.error("Service type and title are required");
      return;
    }
    setSaving(true);
    try {
      await authPost("/rubric-matrices", newForm);
      toast.success("Rubric created");
      setCreating(false);
      setNewForm(null);
      await loadRubrics();
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Create failed");
    } finally {
      setSaving(false);
    }
  };

  const toggleActive = async (rubric) => {
    try {
      if (rubric.is_active !== false) {
        await authPatch(`/rubric-matrices/${rubric.id}`, { is_active: false });
        toast.success("Rubric deactivated");
      } else {
        await authPatch(`/rubric-matrices/${rubric.id}`, { is_active: true });
        toast.success("Rubric reactivated");
      }
      await loadRubrics();
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Toggle failed");
    }
  };

  const renderCategoryEditor = (form, setForm) => (
    <div className="mt-4 space-y-3" data-testid="rubric-editor-categories">
      <div className="flex items-center justify-between">
        <p className="text-xs font-bold uppercase tracking-wider text-[#5f7464]">Grading factors ({form.categories.length})</p>
        <Button type="button" variant="outline" size="sm" onClick={() => addCategory(form, setForm)} disabled={form.categories.length >= 10} className="h-7 rounded-lg text-xs" data-testid="rubric-editor-add-factor">
          <Plus className="mr-1 h-3 w-3" />Add
        </Button>
      </div>
      {form.categories.map((cat, index) => (
        <div key={index} className="flex items-center gap-2 rounded-xl border border-border/60 bg-[#f6f6f2] p-3" data-testid={`rubric-editor-factor-${index}`}>
          <GripVertical className="h-4 w-4 shrink-0 text-[#5f7464]/50" />
          <Input
            value={cat.label}
            onChange={(e) => updateCategoryField(form, setForm, index, "label", e.target.value)}
            className="h-8 flex-1 rounded-lg border-transparent bg-white text-sm"
            placeholder="Factor name"
            data-testid={`rubric-editor-factor-label-${index}`}
          />
          <div className="flex shrink-0 items-center gap-1.5">
            <input
              type="range"
              min={1}
              max={99}
              value={Math.round(cat.weight * 100)}
              onChange={(e) => updateCategoryWeight(form, setForm, index, parseInt(e.target.value) / 100)}
              className="h-1 w-20 cursor-pointer accent-[#2d5a27]"
              data-testid={`rubric-editor-factor-weight-${index}`}
            />
            <span className="w-10 text-right text-xs font-semibold text-[#243e36]">{Math.round(cat.weight * 100)}%</span>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => removeCategory(form, setForm, index)}
            disabled={form.categories.length <= 1}
            className="h-7 w-7 rounded-lg p-0 text-red-500/60 hover:bg-red-50 hover:text-red-600"
            data-testid={`rubric-editor-factor-remove-${index}`}
          >
            <Trash2 className="h-3 w-3" />
          </Button>
        </div>
      ))}
      <div className="text-right text-xs text-[#5f7464]">
        Total: {Math.round(form.categories.reduce((s, c) => s + c.weight, 0) * 100)}%
      </div>
    </div>
  );

  const renderFormFields = (form, setForm, isNew = false) => (
    <div className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2">
        {isNew && (
          <div>
            <label className="mb-1 block text-xs font-semibold text-[#5f7464]">Service type</label>
            <Input value={form.service_type} onChange={(e) => setForm({ ...form, service_type: e.target.value })} className="h-9 rounded-lg" placeholder="e.g. mulching" data-testid="rubric-editor-service-type" />
          </div>
        )}
        <div>
          <label className="mb-1 block text-xs font-semibold text-[#5f7464]">Title</label>
          <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="h-9 rounded-lg" placeholder="Rubric title" data-testid="rubric-editor-title" />
        </div>
        <div>
          <label className="mb-1 block text-xs font-semibold text-[#5f7464]">Division</label>
          <Select value={form.division} onValueChange={(v) => setForm({ ...form, division: v })}>
            <SelectTrigger className="h-9 rounded-lg" data-testid="rubric-editor-division"><SelectValue /></SelectTrigger>
            <SelectContent>
              {DIVISIONS.map((d) => <SelectItem key={d} value={d}>{d}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs font-semibold text-[#5f7464]">Pass threshold (%)</label>
          <Input type="number" min={1} max={100} value={form.pass_threshold} onChange={(e) => setForm({ ...form, pass_threshold: parseInt(e.target.value) || 80 })} className="h-9 rounded-lg" data-testid="rubric-editor-threshold" />
        </div>
        <div>
          <label className="mb-1 block text-xs font-semibold text-[#5f7464]">Min photos required</label>
          <Input type="number" min={1} max={20} value={form.min_photos} onChange={(e) => setForm({ ...form, min_photos: parseInt(e.target.value) || 3 })} className="h-9 rounded-lg" data-testid="rubric-editor-min-photos" />
        </div>
      </div>
      {!isNew && (
        <div className="flex items-center gap-3">
          <label className="text-xs font-semibold text-[#5f7464]">Active</label>
          <Switch checked={form.is_active} onCheckedChange={(v) => setForm({ ...form, is_active: v })} data-testid="rubric-editor-active-toggle" />
        </div>
      )}
      {renderCategoryEditor(form, setForm)}
    </div>
  );

  return (
    <div className="space-y-6" data-testid="rubric-editor-page">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Rubric management</p>
          <h1 className="mt-2 font-[Outfit] text-3xl font-bold tracking-tight text-[#111815]" data-testid="rubric-editor-heading">Rubric matrices</h1>
          <p className="mt-1 text-sm text-[#5c6d64]">Create, edit, and version grading rubrics by division and task.</p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={divisionFilter} onValueChange={setDivisionFilter}>
            <SelectTrigger className="h-10 w-[170px] rounded-2xl border-transparent bg-[#edf0e7]" data-testid="rubric-editor-filter"><SelectValue placeholder="All divisions" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All divisions</SelectItem>
              {DIVISIONS.map((d) => <SelectItem key={d} value={d}>{d}</SelectItem>)}
            </SelectContent>
          </Select>
          {isGmOrOwner && (
            <Button type="button" onClick={startCreate} className="h-10 rounded-2xl bg-[#243e36] hover:bg-[#1a2e28]" data-testid="rubric-editor-create-button">
              <Plus className="mr-2 h-4 w-4" />New rubric
            </Button>
          )}
        </div>
      </div>

      {creating && newForm && (
        <Card className="rounded-[24px] border-2 border-[#4a7c59]/30 bg-[#f9faf8] shadow-sm" data-testid="rubric-editor-create-form">
          <CardContent className="p-6">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="font-[Outfit] text-lg font-semibold text-[#111815]">New rubric matrix</h3>
              <div className="flex gap-2">
                <Button type="button" variant="outline" onClick={() => { setCreating(false); setNewForm(null); }} className="h-8 rounded-lg text-xs" data-testid="rubric-editor-create-cancel"><X className="mr-1 h-3 w-3" />Cancel</Button>
                <Button type="button" disabled={saving} onClick={saveCreate} className="h-8 rounded-lg bg-[#2d5a27] text-xs hover:bg-[#22441d]" data-testid="rubric-editor-create-save"><Save className="mr-1 h-3 w-3" />Create</Button>
              </div>
            </div>
            {renderFormFields(newForm, setNewForm, true)}
          </CardContent>
        </Card>
      )}

      <div className="space-y-3" data-testid="rubric-editor-list">
        {rubrics.map((rubric) => (
          <Card key={rubric.id} className={`rounded-[20px] border-border/60 shadow-sm transition ${rubric.is_active === false ? "opacity-60" : ""}`} data-testid={`rubric-editor-item-${rubric.id}`}>
            <CardContent className="p-5">
              {editingId === rubric.id && editForm ? (
                <>
                  <div className="mb-4 flex items-center justify-between">
                    <h3 className="font-[Outfit] text-lg font-semibold capitalize text-[#111815]">{rubric.service_type}</h3>
                    <div className="flex gap-2">
                      <Button type="button" variant="outline" onClick={cancelEdit} className="h-8 rounded-lg text-xs" data-testid="rubric-editor-edit-cancel"><X className="mr-1 h-3 w-3" />Cancel</Button>
                      <Button type="button" disabled={saving} onClick={saveEdit} className="h-8 rounded-lg bg-[#2d5a27] text-xs hover:bg-[#22441d]" data-testid="rubric-editor-edit-save"><Save className="mr-1 h-3 w-3" />Save</Button>
                    </div>
                  </div>
                  {renderFormFields(editForm, setEditForm)}
                </>
              ) : (
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold capitalize text-[#243e36]">{rubric.service_type}</h3>
                      <Badge className="border-0 bg-[#edf0e7] text-[#243e36]" data-testid={`rubric-badge-division-${rubric.id}`}>{rubric.division || "General"}</Badge>
                      <span className="text-xs text-[#5c6d64]">v{rubric.version}</span>
                      {rubric.is_active === false && <Badge className="border-0 bg-red-100 text-red-700">Inactive</Badge>}
                    </div>
                    <p className="mt-1 text-sm text-[#5c6d64]">{rubric.title} &middot; Pass: {rubric.pass_threshold}% &middot; Min photos: {rubric.min_photos}</p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {(rubric.categories || []).map((cat) => (
                        <span key={cat.key} className="inline-block rounded-lg bg-[#edf0e7] px-2 py-0.5 text-xs font-medium text-[#5c6d64]">{cat.label} ({Math.round(cat.weight * 100)}%)</span>
                      ))}
                    </div>
                  </div>
                  {isGmOrOwner && (
                    <div className="flex shrink-0 gap-1.5">
                      <Button type="button" variant="outline" size="sm" onClick={() => startEdit(rubric)} className="h-8 w-8 rounded-lg p-0" data-testid={`rubric-editor-edit-${rubric.id}`}>
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                      <Button type="button" variant="outline" size="sm" onClick={() => toggleActive(rubric)} className="h-8 w-8 rounded-lg p-0" data-testid={`rubric-editor-toggle-${rubric.id}`}>
                        {rubric.is_active !== false ? <Trash2 className="h-3.5 w-3.5 text-red-500" /> : <Plus className="h-3.5 w-3.5 text-green-600" />}
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
        {rubrics.length === 0 && (
          <p className="text-center text-sm text-[#5c6d64]" data-testid="rubric-editor-empty">No rubrics found.</p>
        )}
      </div>
    </div>
  );
}
