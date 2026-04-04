import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronLeft, ChevronRight, Network, Upload, User, Users, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { authGet } from "@/lib/api";
import { toast } from "sonner";

/* ── Level accent colours (theme-reactive fallback to brand) ── */
const ACCENT = {
  Owner:              { bar: "#d4a843", card: "rgba(212,168,67,0.12)", text: "#d4a843" },
  GM:                 { bar: "#9b7cd8", card: "rgba(155,124,216,0.12)", text: "#9b7cd8" },
  "Account Manager":  { bar: "#59a5d8", card: "rgba(89,165,216,0.12)", text: "#59a5d8" },
  "Production Manager":{ bar: "#38a89d", card: "rgba(56,168,157,0.12)", text: "#38a89d" },
  Supervisor:         { bar: "#7c6cf0", card: "rgba(124,108,240,0.12)", text: "#7c6cf0" },
  "Crew Leader":      { bar: "#34d399", card: "rgba(52,211,153,0.12)", text: "#34d399" },
  "Crew Member":      { bar: "#94a3b8", card: "rgba(148,163,184,0.12)", text: "#94a3b8" },
};
function accent(role) { return ACCENT[role] || ACCENT["Crew Member"]; }

/* ── Hex avatar ── */
const HEX_CLIP = "polygon(50% 0%,100% 25%,100% 75%,50% 100%,0% 75%,0% 25%)";
const BG = ["#1a2c26","#243e36","#344e41","#3a5a40","#4a7c59","#588157","#5c6d64","#6b7c5e"];
function ini(n){ return n.split(" ").filter(Boolean).map(w=>w[0]).join("").toUpperCase().slice(0,2); }
function hIdx(n){ let h=0; for(let i=0;i<n.length;i++) h=n.charCodeAt(i)+((h<<5)-h); return Math.abs(h)%BG.length; }

function HexAvatar({ name, url, size = 56, className = "" }) {
  const s = { width: size, height: size, clipPath: HEX_CLIP };
  if (url) return <img src={url} alt={name} style={s} className={`shrink-0 object-cover ${className}`} />;
  const fs = size < 40 ? "text-[10px]" : size < 60 ? "text-sm" : "text-xl";
  return <div style={{ ...s, backgroundColor: BG[hIdx(name)] }} className={`flex shrink-0 items-center justify-center font-bold text-white ${fs} ${className}`}>{ini(name)}</div>;
}

/* ════════════ INFOGRAPHIC ORG-NODE ════════════
   Hex avatar overlaps left edge of a rounded white card.
   Coloured accent bar underneath the name.                 */
function OrgCard({ profile, onClick, compact = false }) {
  const a = accent(profile.role);
  const h = compact ? 42 : 56;
  return (
    <button type="button" onClick={() => onClick(profile)} className="group relative flex items-center text-left transition hover:scale-[1.02]" data-testid={`org-card-${profile.profile_id}`}>
      {/* avatar overlapping left edge */}
      <div className="relative z-10 -mr-3 shrink-0">
        <div style={{ padding: 3, clipPath: HEX_CLIP, backgroundColor: a.bar }}>
          <HexAvatar name={profile.name} url={profile.avatar_url} size={h} />
        </div>
      </div>
      {/* card body */}
      <div className="relative flex min-w-0 flex-col justify-center rounded-r-[16px] rounded-l-[8px] bg-[var(--card)] py-2 pl-5 pr-4 shadow-md ring-1 ring-[var(--border)]" style={{ minHeight: h + 8 }}>
        <p className={`truncate font-semibold text-[var(--foreground)] ${compact ? "text-xs" : "text-sm"}`}>{profile.name}</p>
        {/* accent bar */}
        <div className="mt-1 h-[3px] w-16 rounded-full" style={{ backgroundColor: a.bar }} />
        <p className={`mt-0.5 text-[var(--muted-foreground)] ${compact ? "text-[9px]" : "text-[10px]"} font-semibold uppercase tracking-wider`}>{profile.role}</p>
        {profile.division && <p className="text-[9px] text-[var(--muted-foreground)]">{profile.division}</p>}
      </div>
    </button>
  );
}

/* ════════ CONNECTOR LINES ════════ */
function VLine({ h = 28, color = "var(--border)", dashed = false }) {
  return <div className="mx-auto" style={{ width: 2, height: h, backgroundColor: dashed ? "transparent" : color, borderLeft: dashed ? `2px dashed ${color}` : "none" }} />;
}

/* ════════ GRID CARD (Individual view) ════════ */
function GridCard({ profile, onClick }) {
  const a = accent(profile.role);
  return (
    <button type="button" onClick={() => onClick(profile)}
      className="group flex w-[184px] flex-col items-center rounded-[22px] bg-[var(--card)] p-4 shadow-md ring-1 ring-[var(--border)] transition hover:scale-[1.03] hover:shadow-lg"
      data-testid={`profile-card-${profile.profile_id}`}
    >
      <div style={{ padding: 3, clipPath: HEX_CLIP, backgroundColor: a.bar }}>
        <HexAvatar name={profile.name} url={profile.avatar_url} size={60} />
      </div>
      <p className="mt-2 w-full truncate text-center text-sm font-semibold text-[var(--foreground)]">{profile.name}</p>
      <div className="mt-1 h-[3px] w-12 rounded-full" style={{ backgroundColor: a.bar }} />
      <p className="mt-1 text-[10px] font-semibold uppercase tracking-wider" style={{ color: a.text }}>{profile.role}</p>
      {profile.age && <p className="text-[10px] text-[var(--muted-foreground)]">Age {profile.age}</p>}
    </button>
  );
}

/* ════════ PROFILE DETAIL OVERLAY ════════ */
function ProfileOverlay({ profile, onClose, onAvatarDone }) {
  const [detail, setDetail] = useState(null);
  const [showStats, setShowStats] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef(null);

  useEffect(() => { if (profile) authGet(`/team/profiles/${profile.profile_id}`).then(setDetail).catch(() => setDetail(profile)); }, [profile]);
  if (!profile) return null;
  const d = detail || profile;
  const stats = d.stats || {};
  const a = accent(d.role);

  const upload = async (e) => {
    const file = e.target.files?.[0]; if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData(); fd.append("file", file);
      const r = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/team/profiles/${d.profile_id}/avatar`, { method: "POST", headers: { Authorization: `Bearer ${localStorage.getItem("auth_token")}` }, body: fd });
      const data = await r.json(); if (!r.ok) throw new Error(data.detail);
      toast.success("Avatar uploaded!");
      setDetail(prev => prev ? { ...prev, avatar_url: data.avatar_url } : prev);
      onAvatarDone?.(d.profile_id, data.avatar_url);
    } catch (err) { toast.error(err.message || "Upload failed"); }
    finally { setUploading(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4" onClick={onClose} data-testid="profile-detail-overlay">
      <motion.div initial={{ opacity:0, y:20 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0, y:20 }}
        className="w-full max-w-sm overflow-hidden rounded-[28px] bg-[var(--card)] shadow-2xl ring-1 ring-[var(--border)]"
        onClick={e => e.stopPropagation()} data-testid="profile-detail-popup">
        <div className="relative p-6 text-center" style={{ background: `linear-gradient(135deg, ${a.bar}22 0%, ${a.bar}08 100%)` }}>
          <button type="button" onClick={onClose} className="absolute right-4 top-4 flex h-8 w-8 items-center justify-center rounded-full bg-[var(--accent)] text-[var(--foreground)] hover:opacity-80" data-testid="profile-detail-close"><X className="h-4 w-4" /></button>
          <div className="relative mx-auto w-fit">
            <div style={{ padding: 4, clipPath: HEX_CLIP, backgroundColor: a.bar }}>
              <HexAvatar name={d.name} url={d.avatar_url} size={80} />
            </div>
            <button type="button" onClick={() => fileRef.current?.click()} className="absolute -bottom-1 -right-1 flex h-7 w-7 items-center justify-center rounded-full bg-[var(--card)] shadow-md ring-1 ring-[var(--border)]" data-testid="profile-avatar-upload-btn"><Upload className="h-3.5 w-3.5 text-[var(--foreground)]" /></button>
            <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={upload} data-testid="profile-avatar-file-input" />
          </div>
          {uploading && <p className="mt-2 text-xs animate-pulse text-[var(--muted-foreground)]">Uploading...</p>}
          <h2 className="mt-3 font-[Cabinet_Grotesk] text-2xl font-black tracking-tight text-[var(--foreground)]">{d.name}</h2>
          <div className="mx-auto mt-1 h-[3px] w-16 rounded-full" style={{ backgroundColor: a.bar }} />
          <div className="mt-2 flex flex-wrap justify-center gap-1.5">
            <Badge className="border-0 text-white text-[10px]" style={{ backgroundColor: a.bar }}>{d.role}</Badge>
            {d.division && <Badge className="border-0 bg-[var(--accent)] text-[var(--foreground)] text-[10px]">{d.division}</Badge>}
          </div>
        </div>
        <div className="max-h-[40vh] overflow-y-auto p-5 space-y-3">
          {d.parent_crew_label && <div className="rounded-[16px] bg-[var(--accent)] p-3"><p className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted-foreground)]">Team</p><p className="mt-1 text-sm font-semibold text-[var(--foreground)]">{d.parent_crew_label}</p></div>}
          {d.truck_number && <div className="rounded-[16px] bg-[var(--accent)] p-3"><p className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted-foreground)]">Truck</p><p className="mt-1 text-sm font-semibold text-[var(--foreground)]">{d.truck_number}</p></div>}
          <button type="button" onClick={() => setShowStats(!showStats)} className="flex w-full items-center justify-between rounded-[16px] bg-[var(--accent)] px-4 py-3 text-left text-sm font-semibold text-[var(--foreground)] transition hover:opacity-80" data-testid="profile-toggle-stats">
            Performance & Records
            <svg className={`h-4 w-4 transition-transform ${showStats ? "rotate-90" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
          </button>
          <AnimatePresence>
            {showStats && (
              <motion.div initial={{ height:0, opacity:0 }} animate={{ height:"auto", opacity:1 }} exit={{ height:0, opacity:0 }} className="overflow-hidden">
                <div className="grid grid-cols-2 gap-2 pt-1" data-testid="profile-stats-grid">
                  {[["review_count","Reviews"],["submission_count","Submissions"],["training_completed","Trained"],["training_total","Sessions"]].map(([k,l])=>(
                    <div key={k} className="rounded-[14px] bg-[var(--accent)] p-3 text-center">
                      <p className="text-xl font-black text-[var(--foreground)]">{stats[k] ?? "—"}</p>
                      <p className="text-[10px] font-semibold uppercase text-[var(--muted-foreground)]">{l}</p>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );
}

/* ═══════ INDIVIDUAL VIEW — 3×5 GRID ═══════ */
const PER_PAGE = 15;
function IndividualView({ profiles, onCardClick }) {
  const [page, setPage] = useState(1);
  const total = Math.max(1, Math.ceil(profiles.length / PER_PAGE));
  const vis = profiles.slice((page-1)*PER_PAGE, page*PER_PAGE);
  const rows = []; for (let i=0;i<vis.length;i+=5) rows.push(vis.slice(i,i+5));
  while (rows.length < 3) rows.push([]);
  return (
    <div className="flex h-full flex-col" data-testid="individual-view">
      <div className="flex flex-1 flex-col justify-center gap-5">
        {rows.slice(0,3).map((row,ri) => (
          <div key={ri} className="flex justify-center gap-4" data-testid={`grid-row-${ri}`}>
            {row.map(p => <GridCard key={p.profile_id} profile={p} onClick={onCardClick} />)}
            {Array.from({ length: 5-row.length }).map((_,i) => <div key={`e${i}`} className="w-[184px]" />)}
          </div>
        ))}
      </div>
      {total > 1 && (
        <div className="flex shrink-0 items-center justify-center gap-3 pt-4" data-testid="grid-pagination">
          <Button variant="outline" size="sm" disabled={page<=1} onClick={() => setPage(page-1)} className="rounded-xl"><ChevronLeft className="h-4 w-4" /></Button>
          <span className="text-sm font-semibold text-[var(--foreground)]">{page} / {total}</span>
          <Button variant="outline" size="sm" disabled={page>=total} onClick={() => setPage(page+1)} className="rounded-xl"><ChevronRight className="h-4 w-4" /></Button>
        </div>
      )}
    </div>
  );
}

/* ═══════ TEAM STRUCTURE — HOVER EXPAND ═══════ */
function CrewHoverCard({ team, onCardClick }) {
  const [hovered, setHovered] = useState(false);
  const a = accent("Crew Leader");
  return (
    <div className="flex flex-col items-center" onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)} data-testid={`team-hover-${team.lead.profile_id}`}>
      {/* Crew label pill */}
      <div className="rounded-[18px] px-5 py-3 text-center shadow-md ring-1 ring-[var(--border)] transition" style={{ backgroundColor: hovered ? a.card : "var(--card)" }}>
        <p className="text-sm font-bold text-[var(--foreground)]">{team.lead.name}</p>
        <div className="mx-auto mt-1 h-[3px] w-10 rounded-full" style={{ backgroundColor: a.bar }} />
        <p className="mt-0.5 text-[10px] font-semibold uppercase tracking-wider" style={{ color: a.text }}>{team.division}</p>
      </div>

      {/* Expanded on hover */}
      <AnimatePresence>
        {hovered && (
          <motion.div initial={{ opacity:0, height:0 }} animate={{ opacity:1, height:"auto" }} exit={{ opacity:0, height:0 }} className="overflow-hidden">
            <VLine h={16} color={a.bar} />
            {/* Crew leader detail */}
            <div className="flex items-center gap-3 rounded-[18px] bg-[var(--card)] px-4 py-2 shadow ring-1 ring-[var(--border)]">
              <button type="button" onClick={() => onCardClick(team.lead)}>
                <div style={{ padding: 2, clipPath: HEX_CLIP, backgroundColor: a.bar }}>
                  <HexAvatar name={team.lead.name} url={team.lead.avatar_url} size={44} />
                </div>
              </button>
              <div>
                <p className="text-xs font-semibold text-[var(--foreground)]">{team.lead.name}</p>
                <Badge className="mt-0.5 border-0 text-[9px] text-white" style={{ backgroundColor: a.bar }}>Crew Leader</Badge>
              </div>
              {team.lead.truck_number && <Badge className="border-0 bg-[var(--accent)] text-[var(--foreground)] text-[9px]">{team.lead.truck_number}</Badge>}
            </div>

            {/* Members */}
            {team.members.length > 0 && (
              <>
                <VLine h={12} color={accent("Crew Member").bar} dashed />
                <div className="space-y-1.5">
                  {team.members.map(m => (
                    <button key={m.profile_id} type="button" onClick={() => onCardClick(m)}
                      className="flex w-full items-center gap-2.5 rounded-[14px] bg-[var(--card)] px-3 py-2 text-left shadow-sm ring-1 ring-[var(--border)] transition hover:ring-2"
                      data-testid={`team-member-${m.profile_id}`}>
                      <div style={{ padding: 2, clipPath: HEX_CLIP, backgroundColor: accent("Crew Member").bar }}>
                        <HexAvatar name={m.name} url={m.avatar_url} size={32} />
                      </div>
                      <p className="truncate text-xs font-medium text-[var(--foreground)]">{m.name}</p>
                    </button>
                  ))}
                </div>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function TeamStructureView({ teams, onCardClick }) {
  return (
    <div className="flex h-full items-start justify-center gap-8 overflow-x-auto py-4" data-testid="team-structure-view">
      {teams.map((t,i) => <CrewHoverCard key={i} team={t} onCardClick={onCardClick} />)}
    </div>
  );
}

/* ═══════ DIVISION HIERARCHY — FULL ORG CHART ═══════ */
function DivisionHierarchyView({ hierarchy, onCardClick }) {
  if (!hierarchy) return null;
  return (
    <div className="h-full overflow-y-auto pb-6" data-testid="hierarchy-view">
      <div className="flex flex-col items-center gap-0">
        {/* Owner */}
        <div className="flex flex-wrap justify-center gap-4">
          {hierarchy.owners.map(p => <OrgCard key={p.profile_id} profile={p} onClick={onCardClick} />)}
        </div>
        <VLine h={28} color={accent("Owner").bar} />

        {/* GM */}
        <div className="flex flex-wrap justify-center gap-4">
          {hierarchy.general_managers.map(p => <OrgCard key={p.profile_id} profile={p} onClick={onCardClick} />)}
        </div>
        <VLine h={24} color={accent("GM").bar} />

        {/* Two branches: AMs ←→ PMs & Field */}
        <div className="flex flex-wrap justify-center gap-16">
          {/* AM branch */}
          <div className="flex flex-col items-center">
            <p className="rounded-xl bg-[var(--accent)] px-4 py-1.5 text-xs font-bold text-[var(--foreground)]">Account Managers</p>
            <VLine h={14} color={accent("Account Manager").bar} dashed />
            <div className="flex flex-wrap justify-center gap-3">
              {hierarchy.account_managers.map(p => <OrgCard key={p.profile_id} profile={p} onClick={onCardClick} compact />)}
            </div>
          </div>

          {/* Production & Field branch */}
          <div className="flex flex-col items-center">
            <p className="rounded-xl bg-[var(--accent)] px-4 py-1.5 text-xs font-bold text-[var(--foreground)]">Production & Field</p>
            <VLine h={14} color={accent("Production Manager").bar} />
            <div className="flex flex-wrap justify-center gap-3">
              {hierarchy.production_managers.map(p => <OrgCard key={p.profile_id} profile={{...p, role: "Production Manager"}} onClick={onCardClick} compact />)}
            </div>
            <VLine h={14} color={accent("Supervisor").bar} dashed />
            <div className="flex flex-wrap justify-center gap-3">
              {hierarchy.supervisors.map(p => <OrgCard key={p.profile_id} profile={p} onClick={onCardClick} compact />)}
            </div>

            {/* Divisions */}
            {hierarchy.divisions.map(div => (
              <div key={div.name} className="mt-5 flex flex-col items-center">
                <p className="rounded-xl px-4 py-1.5 text-xs font-bold text-white" style={{ backgroundColor: accent("Crew Leader").bar }}>{div.name}</p>
                <VLine h={14} color={accent("Crew Leader").bar} />
                <div className="flex flex-wrap justify-center gap-6">
                  {div.teams.map(team => (
                    <div key={team.lead.profile_id} className="flex flex-col items-center">
                      <OrgCard profile={team.lead} onClick={onCardClick} compact />
                      {team.members.length > 0 && (
                        <>
                          <VLine h={12} color={accent("Crew Member").bar} dashed />
                          <div className="flex gap-2">
                            {team.members.map(m => <OrgCard key={m.profile_id} profile={m} onClick={onCardClick} compact />)}
                          </div>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══════ MAIN PAGE ═══════ */
export default function TeamMembersPage() {
  const [view, setView] = useState("individual");
  const [profiles, setProfiles] = useState([]);
  const [teams, setTeams] = useState([]);
  const [hierarchy, setHierarchy] = useState(null);
  const [selected, setSelected] = useState(null);

  const load = () => {
    if (view === "individual") authGet("/team/profiles").then(d => setProfiles(d.profiles || [])).catch(() => {});
    else if (view === "team") authGet("/team/structure").then(d => setTeams(d.teams || [])).catch(() => {});
    else authGet("/team/hierarchy").then(setHierarchy).catch(() => {});
  };
  useEffect(load, [view]);

  return (
    <div className="flex h-[calc(100vh-64px)] flex-col" data-testid="team-members-page">
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-4 pb-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">People</p>
          <h1 className="mt-1 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[var(--foreground)] lg:text-4xl" data-testid="team-page-title">Team Members</h1>
        </div>
        <Select value={view} onValueChange={setView}>
          <SelectTrigger className="h-11 w-52 rounded-2xl border-transparent bg-[var(--accent)]" data-testid="team-view-selector"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="individual"><span className="flex items-center gap-2"><User className="h-3.5 w-3.5" /> Individual</span></SelectItem>
            <SelectItem value="team"><span className="flex items-center gap-2"><Users className="h-3.5 w-3.5" /> Team Structure</span></SelectItem>
            <SelectItem value="hierarchy"><span className="flex items-center gap-2"><Network className="h-3.5 w-3.5" /> Division Hierarchy</span></SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="min-h-0 flex-1 overflow-hidden">
        <Card className="h-full rounded-[32px] border-border/80 bg-[var(--card)] shadow-sm">
          <CardContent className="h-full p-6">
            {view === "individual" && <IndividualView profiles={profiles} onCardClick={setSelected} />}
            {view === "team" && <TeamStructureView teams={teams} onCardClick={setSelected} />}
            {view === "hierarchy" && <DivisionHierarchyView hierarchy={hierarchy} onCardClick={setSelected} />}
          </CardContent>
        </Card>
      </div>
      <AnimatePresence>
        {selected && <ProfileOverlay profile={selected} onClose={() => setSelected(null)} onAvatarDone={(id, url) => { load(); }} />}
      </AnimatePresence>
    </div>
  );
}
