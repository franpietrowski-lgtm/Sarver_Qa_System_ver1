import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronLeft, ChevronRight, Layers, Network, Upload, User, Users, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { authGet, authPatch } from "@/lib/api";
import { toast } from "sonner";

/* ─────── Colour palette per hierarchy level ─────── */
const LEVEL_THEMES = {
  Owner:              { bg: "bg-[#1a2c26]", text: "text-white",      badge: "bg-amber-400/20 text-amber-200",     ring: "ring-amber-400/40",    line: "#d4a843", hex: "#1a2c26" },
  GM:                 { bg: "bg-[#243e36]", text: "text-white",      badge: "bg-violet-400/20 text-violet-200",   ring: "ring-violet-400/40",   line: "#7c5cbf", hex: "#243e36" },
  "Account Manager":  { bg: "bg-[#3a5a40]", text: "text-white",      badge: "bg-sky-400/20 text-sky-200",         ring: "ring-sky-400/40",      line: "#59a5d8", hex: "#3a5a40" },
  "Production Manager":{ bg: "bg-[#588157]", text: "text-white",      badge: "bg-teal-400/20 text-teal-200",       ring: "ring-teal-400/40",     line: "#38a89d", hex: "#588157" },
  Supervisor:         { bg: "bg-[#344e41]", text: "text-white",      badge: "bg-indigo-400/20 text-indigo-200",   ring: "ring-indigo-400/40",   line: "#6366f1", hex: "#344e41" },
  "Crew Leader":      { bg: "bg-[#4a7c59]", text: "text-white",      badge: "bg-emerald-400/20 text-emerald-200", ring: "ring-emerald-400/40",  line: "#34d399", hex: "#4a7c59" },
  "Crew Member":      { bg: "bg-[#6b7c5e]", text: "text-white",      badge: "bg-slate-300/20 text-slate-200",     ring: "ring-slate-400/40",    line: "#94a3b8", hex: "#6b7c5e" },
};

function getTheme(role) { return LEVEL_THEMES[role] || LEVEL_THEMES["Crew Member"]; }

const INITIALS_BG = ["#243e36","#3a5a40","#588157","#5c6d64","#344e41","#4a7c59","#2d5a27","#6b7c5e"];
function getInitials(name) { return name.split(" ").filter(Boolean).map(w => w[0]).join("").toUpperCase().slice(0, 2); }
function hashIdx(name) { let h = 0; for (let i = 0; i < name.length; i++) h = name.charCodeAt(i) + ((h << 5) - h); return Math.abs(h) % INITIALS_BG.length; }

/* ─────── Avatar (hex-clipped when no image) ─────── */
function Avatar({ name, avatarUrl, size = "md", className = "" }) {
  const dim = size === "lg" ? "h-20 w-20" : size === "sm" ? "h-10 w-10" : "h-14 w-14";
  const textSz = size === "lg" ? "text-2xl" : size === "sm" ? "text-xs" : "text-base";
  const clip = { clipPath: "polygon(50% 0%,100% 25%,100% 75%,50% 100%,0% 75%,0% 25%)" };
  if (avatarUrl) {
    return <img src={avatarUrl} alt={name} style={clip} className={`${dim} shrink-0 object-cover ${className}`} />;
  }
  return (
    <div style={{ ...clip, backgroundColor: INITIALS_BG[hashIdx(name)] }} className={`${dim} ${textSz} flex shrink-0 items-center justify-center font-bold text-white ${className}`}>
      {getInitials(name)}
    </div>
  );
}

/* ─────── Org Chart Node Card ─────── */
function OrgNode({ profile, onClick, size = "md", showDivision = false }) {
  const theme = getTheme(profile.role);
  const isSm = size === "sm";
  return (
    <button
      type="button"
      onClick={() => onClick(profile)}
      className={`group relative flex items-center gap-3 rounded-[20px] ${theme.bg} ${isSm ? "px-3 py-2" : "px-4 py-3"} shadow-md ring-1 ${theme.ring} transition hover:scale-[1.02] hover:shadow-lg`}
      data-testid={`org-node-${profile.profile_id}`}
    >
      <Avatar name={profile.name} avatarUrl={profile.avatar_url} size={isSm ? "sm" : "md"} />
      <div className="min-w-0 text-left">
        <p className={`truncate font-semibold ${theme.text} ${isSm ? "text-xs" : "text-sm"}`}>{profile.name}</p>
        <Badge className={`mt-0.5 border-0 ${theme.badge} ${isSm ? "text-[9px]" : "text-[10px]"}`}>{profile.role}</Badge>
        {showDivision && profile.division && <Badge className={`ml-1 mt-0.5 border-0 bg-white/10 ${theme.text} ${isSm ? "text-[9px]" : "text-[10px]"}`}>{profile.division}</Badge>}
      </div>
    </button>
  );
}

/* ─────── Connector line (vertical + horizontal branches) ─────── */
function VLine({ height = 24, color = "#5c6d64" }) {
  return <div className="mx-auto" style={{ width: 2, height, backgroundColor: color, opacity: 0.4 }} />;
}

/* ─────── Profile Card for Grid View ─────── */
function GridProfileCard({ profile, onClick }) {
  const theme = getTheme(profile.role);
  return (
    <button
      type="button"
      onClick={() => onClick(profile)}
      className={`flex flex-col items-center gap-2 rounded-[24px] ${theme.bg} p-4 shadow-md ring-1 ${theme.ring} transition hover:scale-[1.03] hover:shadow-lg`}
      data-testid={`profile-card-${profile.profile_id}`}
    >
      <Avatar name={profile.name} avatarUrl={profile.avatar_url} />
      <div className="w-full min-w-0 text-center">
        <p className={`truncate text-sm font-semibold ${theme.text}`}>{profile.name}</p>
        {profile.age && <p className="text-xs text-white/60">Age {profile.age}</p>}
      </div>
      <Badge className={`border-0 text-[10px] ${theme.badge}`}>{profile.role}</Badge>
    </button>
  );
}

/* ─────── Profile Detail Overlay ─────── */
function ProfileDetailOverlay({ profile, onClose, onAvatarUploaded }) {
  const [detail, setDetail] = useState(null);
  const [showStats, setShowStats] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef(null);

  useEffect(() => {
    if (!profile) return;
    authGet(`/team/profiles/${profile.profile_id}`)
      .then(setDetail)
      .catch(() => setDetail(profile));
  }, [profile]);

  if (!profile) return null;
  const d = detail || profile;
  const stats = d.stats || {};
  const theme = getTheme(d.role);

  const handleAvatarUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const resp = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/team/profiles/${d.profile_id}/avatar`, {
        method: "POST",
        headers: { Authorization: `Bearer ${localStorage.getItem("auth_token")}` },
        body: fd,
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || "Upload failed");
      toast.success("Avatar uploaded!");
      if (detail) setDetail({ ...detail, avatar_url: data.avatar_url });
      if (onAvatarUploaded) onAvatarUploaded(d.profile_id, data.avatar_url);
    } catch (err) {
      toast.error(err.message || "Avatar upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4" onClick={onClose} data-testid="profile-detail-overlay">
      <motion.div
        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }}
        className="w-full max-w-sm overflow-hidden rounded-[28px] border border-border/80 bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        data-testid="profile-detail-popup"
      >
        {/* Header */}
        <div className={`relative ${theme.bg} p-6 text-center text-white`}>
          <button type="button" onClick={onClose} className="absolute right-4 top-4 flex h-8 w-8 items-center justify-center rounded-full bg-white/10 hover:bg-white/20" data-testid="profile-detail-close"><X className="h-4 w-4" /></button>
          <div className="relative mx-auto w-fit">
            <Avatar name={d.name} avatarUrl={d.avatar_url} size="lg" />
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              className="absolute -bottom-1 -right-1 flex h-7 w-7 items-center justify-center rounded-full bg-white text-[#243e36] shadow-md hover:bg-[#edf0e7]"
              data-testid="profile-avatar-upload-btn"
            >
              <Upload className="h-3.5 w-3.5" />
            </button>
            <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleAvatarUpload} data-testid="profile-avatar-file-input" />
          </div>
          {uploading && <p className="mt-2 text-xs animate-pulse">Uploading...</p>}
          <h2 className="mt-3 font-[Cabinet_Grotesk] text-2xl font-black tracking-tight">{d.name}</h2>
          {d.age && <p className="text-sm text-white/70">Age {d.age}</p>}
          <div className="mt-2 flex flex-wrap justify-center gap-1.5">
            <Badge className={`border-0 ${theme.badge}`}>{d.role}</Badge>
            {d.title && d.title !== d.role && <Badge className="border-0 bg-white/12 text-white">{d.title}</Badge>}
            {d.division && <Badge className="border-0 bg-white/12 text-white">{d.division}</Badge>}
          </div>
        </div>
        {/* Body */}
        <div className="max-h-[40vh] overflow-y-auto p-5">
          {d.parent_crew_label && <div className="mb-3 rounded-[16px] bg-[#f6f6f2] p-3"><p className="text-xs font-bold uppercase tracking-widest text-[#5f7464]">Team</p><p className="mt-1 text-sm font-semibold text-[#243e36]">{d.parent_crew_label}</p></div>}
          {d.truck_number && <div className="mb-3 rounded-[16px] bg-[#f6f6f2] p-3"><p className="text-xs font-bold uppercase tracking-widest text-[#5f7464]">Truck</p><p className="mt-1 text-sm font-semibold text-[#243e36]">{d.truck_number}</p></div>}
          <button type="button" onClick={() => setShowStats(!showStats)} className="mt-1 flex w-full items-center justify-between rounded-[16px] bg-[#edf0e7] px-4 py-3 text-left text-sm font-semibold text-[#243e36] transition hover:bg-[#e2e8db]" data-testid="profile-toggle-stats">
            Performance & Records
            <ChevronRight className={`h-4 w-4 transition-transform ${showStats ? "rotate-90" : ""}`} />
          </button>
          <AnimatePresence>
            {showStats && (
              <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                <div className="mt-3 grid grid-cols-2 gap-2" data-testid="profile-stats-grid">
                  <div className="rounded-[14px] bg-[#f6f6f2] p-3 text-center"><p className="text-xl font-black text-[#243e36]">{stats.review_count ?? "—"}</p><p className="text-[10px] font-semibold uppercase text-[#5f7464]">Reviews</p></div>
                  <div className="rounded-[14px] bg-[#f6f6f2] p-3 text-center"><p className="text-xl font-black text-[#243e36]">{stats.submission_count ?? "—"}</p><p className="text-[10px] font-semibold uppercase text-[#5f7464]">Submissions</p></div>
                  <div className="rounded-[14px] bg-[#f6f6f2] p-3 text-center"><p className="text-xl font-black text-[#243e36]">{stats.training_completed ?? 0}/{stats.training_total ?? 0}</p><p className="text-[10px] font-semibold uppercase text-[#5f7464]">Training</p></div>
                  <div className="rounded-[14px] bg-[#f6f6f2] p-3 text-center"><p className="text-xl font-black text-[#243e36]">{stats.training_total ? `${Math.round((stats.training_completed / stats.training_total) * 100)}%` : "—"}</p><p className="text-[10px] font-semibold uppercase text-[#5f7464]">Completion</p></div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );
}

/* ═══════ INDIVIDUAL VIEW — 3×5 GRID + PAGINATION ═══════ */
const PER_PAGE = 15;
function IndividualView({ profiles, onCardClick }) {
  const [page, setPage] = useState(1);
  const totalPages = Math.max(1, Math.ceil(profiles.length / PER_PAGE));
  const start = (page - 1) * PER_PAGE;
  const visible = profiles.slice(start, start + PER_PAGE);
  const rows = [];
  for (let i = 0; i < visible.length; i += 5) rows.push(visible.slice(i, i + 5));
  while (rows.length < 3) rows.push([]);

  return (
    <div className="flex h-full flex-col" data-testid="individual-view">
      <div className="flex flex-1 flex-col justify-center gap-5">
        {rows.map((row, ri) => (
          <div key={ri} className="flex justify-center gap-4" data-testid={`grid-row-${ri}`}>
            {row.map((p) => (
              <div key={p.profile_id} className="w-[170px]">
                <GridProfileCard profile={p} onClick={onCardClick} />
              </div>
            ))}
            {/* fill empty slots to keep grid alignment */}
            {Array.from({ length: 5 - row.length }).map((_, ei) => (
              <div key={`empty-${ei}`} className="w-[170px]" />
            ))}
          </div>
        ))}
      </div>
      {totalPages > 1 && (
        <div className="flex shrink-0 items-center justify-center gap-3 pt-4" data-testid="grid-pagination">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)} className="rounded-xl" data-testid="grid-prev-page"><ChevronLeft className="h-4 w-4" /></Button>
          <span className="text-sm font-semibold text-[#243e36]">{page} / {totalPages}</span>
          <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage(page + 1)} className="rounded-xl" data-testid="grid-next-page"><ChevronRight className="h-4 w-4" /></Button>
        </div>
      )}
    </div>
  );
}

/* ═══════ TEAM STRUCTURE — GRAPHIC ORG CHART ═══════ */
function TeamStructureView({ teams, onCardClick }) {
  return (
    <div className="h-full overflow-y-auto" data-testid="team-structure-view">
      <div className="flex flex-wrap justify-center gap-8 pb-4">
        {teams.map((team, i) => (
          <div key={i} className="flex flex-col items-center" data-testid={`team-card-${team.lead.profile_id}`}>
            <OrgNode profile={team.lead} onClick={onCardClick} showDivision />
            {team.members.length > 0 && (
              <>
                <VLine height={20} color={getTheme("Crew Leader").line} />
                <div className="relative flex gap-4">
                  {/* horizontal connector bar */}
                  {team.members.length > 1 && (
                    <div className="absolute left-[50px] right-[50px] top-0 h-[2px] bg-[#94a3b8]/40" />
                  )}
                  {team.members.map((m) => (
                    <div key={m.profile_id} className="flex flex-col items-center">
                      <VLine height={16} color={getTheme("Crew Member").line} />
                      <OrgNode profile={m} onClick={onCardClick} size="sm" />
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ═══════ DIVISION HIERARCHY — FULL ORG CHART ═══════ */
function HierarchyLevel({ label, profiles, onCardClick, children, lineColor = "#5c6d64" }) {
  return (
    <div className="flex flex-col items-center">
      {profiles.length > 0 && (
        <div className="flex flex-wrap justify-center gap-3">
          {profiles.map((p) => (
            <OrgNode key={p.profile_id} profile={p} onClick={onCardClick} showDivision />
          ))}
        </div>
      )}
      {profiles.length === 0 && label && (
        <div className="flex items-center gap-2 rounded-2xl bg-[#edf0e7] px-4 py-2">
          <Layers className="h-4 w-4 text-[#5f7464]" />
          <p className="text-sm font-bold text-[#243e36]">{label}</p>
        </div>
      )}
      {children && (
        <>
          <VLine height={20} color={lineColor} />
          {children}
        </>
      )}
    </div>
  );
}

function DivisionHierarchyView({ hierarchy, onCardClick }) {
  if (!hierarchy) return null;
  return (
    <div className="h-full overflow-y-auto pb-6" data-testid="hierarchy-view">
      <div className="flex flex-col items-center gap-0">
        {/* Owner */}
        <HierarchyLevel profiles={hierarchy.owners} onCardClick={onCardClick} lineColor={LEVEL_THEMES.Owner.line}>
          {/* GM */}
          <HierarchyLevel profiles={hierarchy.general_managers} onCardClick={onCardClick} lineColor={LEVEL_THEMES.GM.line}>
            {/* AM row + PM row side by side */}
            <div className="flex flex-wrap justify-center gap-12">
              {/* Account Managers column */}
              <div className="flex flex-col items-center">
                <div className="flex items-center gap-2 rounded-2xl bg-[#edf0e7] px-3 py-1.5">
                  <p className="text-xs font-bold text-[#243e36]">Account Managers</p>
                </div>
                <VLine height={12} color={LEVEL_THEMES["Account Manager"].line} />
                <div className="flex flex-wrap justify-center gap-3">
                  {hierarchy.account_managers.map((a) => <OrgNode key={a.profile_id} profile={a} onClick={onCardClick} size="sm" />)}
                </div>
              </div>
              {/* Production Managers + Supervisors + Divisions */}
              <div className="flex flex-col items-center">
                <div className="flex items-center gap-2 rounded-2xl bg-[#edf0e7] px-3 py-1.5">
                  <p className="text-xs font-bold text-[#243e36]">Production & Field</p>
                </div>
                <VLine height={12} color={LEVEL_THEMES["Production Manager"].line} />
                <div className="flex flex-wrap justify-center gap-3">
                  {hierarchy.production_managers.map((p) => <OrgNode key={p.profile_id} profile={p} onClick={onCardClick} size="sm" showDivision />)}
                </div>
                <VLine height={12} color={LEVEL_THEMES.Supervisor.line} />
                <div className="flex flex-wrap justify-center gap-3">
                  {hierarchy.supervisors.map((s) => <OrgNode key={s.profile_id} profile={s} onClick={onCardClick} size="sm" />)}
                </div>
                {/* Divisions with teams */}
                {hierarchy.divisions.map((div) => (
                  <div key={div.name} className="mt-4 flex flex-col items-center">
                    <div className="rounded-2xl bg-[#edf0e7] px-3 py-1.5">
                      <p className="text-xs font-bold text-[#243e36]">{div.name}</p>
                    </div>
                    <VLine height={12} color={LEVEL_THEMES["Crew Leader"].line} />
                    <div className="flex flex-wrap justify-center gap-6">
                      {div.teams.map((team) => (
                        <div key={team.lead.profile_id} className="flex flex-col items-center">
                          <OrgNode profile={team.lead} onClick={onCardClick} size="sm" />
                          {team.members.length > 0 && (
                            <>
                              <VLine height={12} color={LEVEL_THEMES["Crew Member"].line} />
                              <div className="flex gap-2">
                                {team.members.map((m) => (
                                  <OrgNode key={m.profile_id} profile={m} onClick={onCardClick} size="sm" />
                                ))}
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
          </HierarchyLevel>
        </HierarchyLevel>
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
  const [selectedProfile, setSelectedProfile] = useState(null);

  const reload = () => {
    if (view === "individual") authGet("/team/profiles").then((d) => setProfiles(d.profiles || [])).catch(() => {});
    else if (view === "team") authGet("/team/structure").then((d) => setTeams(d.teams || [])).catch(() => {});
    else authGet("/team/hierarchy").then(setHierarchy).catch(() => {});
  };

  useEffect(reload, [view]);

  const handleAvatarUploaded = (profileId, newUrl) => {
    setProfiles((prev) => prev.map((p) => p.profile_id === profileId ? { ...p, avatar_url: newUrl } : p));
    reload();
  };

  return (
    <div className="flex h-[calc(100vh-64px)] flex-col" data-testid="team-members-page">
      {/* Header */}
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-4 pb-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">People</p>
          <h1 className="mt-1 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[var(--foreground)] lg:text-4xl" data-testid="team-page-title">Team Members</h1>
        </div>
        <Select value={view} onValueChange={setView}>
          <SelectTrigger className="h-11 w-52 rounded-2xl border-transparent bg-[var(--accent)]" data-testid="team-view-selector">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="individual"><span className="flex items-center gap-2"><User className="h-3.5 w-3.5" /> Individual</span></SelectItem>
            <SelectItem value="team"><span className="flex items-center gap-2"><Users className="h-3.5 w-3.5" /> Team Structure</span></SelectItem>
            <SelectItem value="hierarchy"><span className="flex items-center gap-2"><Network className="h-3.5 w-3.5" /> Division Hierarchy</span></SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Content */}
      <div className="min-h-0 flex-1 overflow-hidden">
        <Card className="h-full rounded-[32px] border-border/80 bg-[var(--card)] shadow-sm">
          <CardContent className="h-full p-6">
            {view === "individual" && <IndividualView profiles={profiles} onCardClick={setSelectedProfile} />}
            {view === "team" && <TeamStructureView teams={teams} onCardClick={setSelectedProfile} />}
            {view === "hierarchy" && <DivisionHierarchyView hierarchy={hierarchy} onCardClick={setSelectedProfile} />}
          </CardContent>
        </Card>
      </div>

      {/* Profile overlay */}
      <AnimatePresence>
        {selectedProfile && <ProfileDetailOverlay profile={selectedProfile} onClose={() => setSelectedProfile(null)} onAvatarUploaded={handleAvatarUploaded} />}
      </AnimatePresence>
    </div>
  );
}
