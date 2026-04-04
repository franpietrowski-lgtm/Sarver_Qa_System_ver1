import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronLeft, ChevronRight, Layers, Network, User, Users, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { authGet, authPatch } from "@/lib/api";
import { toast } from "sonner";


/* ─────── Colour helpers ─────── */
const ROLE_COLORS = {
  Owner: "bg-amber-100 text-amber-800",
  GM: "bg-violet-100 text-violet-800",
  "Account Manager": "bg-sky-100 text-sky-800",
  "Production Manager": "bg-teal-100 text-teal-800",
  Supervisor: "bg-indigo-100 text-indigo-800",
  "Crew Leader": "bg-emerald-100 text-emerald-800",
  "Crew Member": "bg-slate-100 text-slate-700",
};

const INITIALS_BG = [
  "bg-[#243e36]", "bg-[#3a5a40]", "bg-[#588157]", "bg-[#5c6d64]",
  "bg-[#344e41]", "bg-[#4a7c59]", "bg-[#2d5a27]", "bg-[#6b7c5e]",
];

function getInitials(name) {
  return name.split(" ").filter(Boolean).map(w => w[0]).join("").toUpperCase().slice(0, 2);
}
function hashColor(name) {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = name.charCodeAt(i) + ((h << 5) - h);
  return INITIALS_BG[Math.abs(h) % INITIALS_BG.length];
}


/* ─────── Avatar ─────── */
function Avatar({ name, avatarUrl, size = "md" }) {
  const sizeClass = size === "lg" ? "h-20 w-20 text-2xl" : size === "sm" ? "h-10 w-10 text-xs" : "h-14 w-14 text-base";
  if (avatarUrl) {
    return <img src={avatarUrl} alt={name} className={`${sizeClass} shrink-0 rounded-full object-cover ring-2 ring-white`} />;
  }
  return (
    <div className={`${sizeClass} ${hashColor(name)} flex shrink-0 items-center justify-center rounded-full font-bold text-white ring-2 ring-white`}>
      {getInitials(name)}
    </div>
  );
}


/* ─────── Profile Card ─────── */
function ProfileCard({ profile, onClick }) {
  const roleBadge = ROLE_COLORS[profile.role] || "bg-gray-100 text-gray-700";
  return (
    <button
      type="button"
      onClick={() => onClick(profile)}
      className="flex w-[170px] shrink-0 flex-col items-center gap-2.5 rounded-[24px] border border-border bg-white/90 p-4 text-center shadow-sm transition hover:border-[#243e36]/30 hover:shadow-md"
      data-testid={`profile-card-${profile.profile_id}`}
    >
      <Avatar name={profile.name} avatarUrl={profile.avatar_url} />
      <div className="w-full min-w-0">
        <p className="truncate text-sm font-semibold text-[#111815]">{profile.name}</p>
        {profile.age && <p className="text-xs text-[#5c6d64]">Age {profile.age}</p>}
      </div>
      <Badge className={`border-0 text-[10px] ${roleBadge}`}>{profile.role}</Badge>
    </button>
  );
}


/* ─────── Carousel Row ─────── */
function CarouselRow({ items, onCardClick }) {
  const scrollRef = useRef(null);
  const scroll = (dir) => {
    if (!scrollRef.current) return;
    scrollRef.current.scrollBy({ left: dir * 200, behavior: "smooth" });
  };
  if (!items.length) return null;
  return (
    <div className="relative" data-testid="carousel-row">
      <button type="button" onClick={() => scroll(-1)} className="absolute -left-3 top-1/2 z-10 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full border border-border bg-white shadow-sm hover:bg-[#edf0e7]" data-testid="carousel-prev"><ChevronLeft className="h-4 w-4" /></button>
      <div ref={scrollRef} className="flex gap-3 overflow-x-auto scroll-smooth px-6 py-2 scrollbar-hide" style={{ scrollSnapType: "x mandatory" }}>
        {items.map((p) => (
          <div key={p.profile_id} style={{ scrollSnapAlign: "start" }}>
            <ProfileCard profile={p} onClick={onCardClick} />
          </div>
        ))}
      </div>
      <button type="button" onClick={() => scroll(1)} className="absolute -right-3 top-1/2 z-10 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full border border-border bg-white shadow-sm hover:bg-[#edf0e7]" data-testid="carousel-next"><ChevronRight className="h-4 w-4" /></button>
    </div>
  );
}


/* ─────── Profile Detail Overlay ─────── */
function ProfileDetailOverlay({ profile, onClose }) {
  const [detail, setDetail] = useState(null);
  const [showStats, setShowStats] = useState(false);

  useEffect(() => {
    if (!profile) return;
    authGet(`/team/profiles/${profile.profile_id}`)
      .then(setDetail)
      .catch(() => setDetail(profile));
  }, [profile]);

  if (!profile) return null;
  const d = detail || profile;
  const stats = d.stats || {};
  const roleBadge = ROLE_COLORS[d.role] || "bg-gray-100 text-gray-700";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4" onClick={onClose} data-testid="profile-detail-overlay">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="w-full max-w-sm overflow-hidden rounded-[28px] border border-border/80 bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        data-testid="profile-detail-popup"
      >
        {/* Header */}
        <div className="bg-[#243e36] p-6 text-center text-white">
          <button type="button" onClick={onClose} className="absolute right-4 top-4 flex h-8 w-8 items-center justify-center rounded-full bg-white/10 text-white hover:bg-white/20" data-testid="profile-detail-close"><X className="h-4 w-4" /></button>
          <Avatar name={d.name} avatarUrl={d.avatar_url} size="lg" />
          <h2 className="mt-3 font-[Cabinet_Grotesk] text-2xl font-black tracking-tight">{d.name}</h2>
          {d.age && <p className="text-sm text-white/70">Age {d.age}</p>}
          <div className="mt-2 flex flex-wrap justify-center gap-1.5">
            <Badge className={`border-0 ${roleBadge}`}>{d.role}</Badge>
            {d.title && d.title !== d.role && <Badge className="border-0 bg-white/12 text-white">{d.title}</Badge>}
            {d.division && <Badge className="border-0 bg-white/12 text-white">{d.division}</Badge>}
          </div>
        </div>

        {/* Body */}
        <div className="max-h-[40vh] overflow-y-auto p-5">
          {d.parent_crew_label && (
            <div className="mb-3 rounded-[16px] bg-[#f6f6f2] p-3">
              <p className="text-xs font-bold uppercase tracking-widest text-[#5f7464]">Team</p>
              <p className="mt-1 text-sm font-semibold text-[#243e36]">{d.parent_crew_label}</p>
            </div>
          )}
          {d.truck_number && (
            <div className="mb-3 rounded-[16px] bg-[#f6f6f2] p-3">
              <p className="text-xs font-bold uppercase tracking-widest text-[#5f7464]">Truck</p>
              <p className="mt-1 text-sm font-semibold text-[#243e36]">{d.truck_number}</p>
            </div>
          )}

          {/* Toggle stats */}
          <button type="button" onClick={() => setShowStats(!showStats)} className="mt-1 flex w-full items-center justify-between rounded-[16px] bg-[#edf0e7] px-4 py-3 text-left text-sm font-semibold text-[#243e36] transition hover:bg-[#e2e8db]" data-testid="profile-toggle-stats">
            Performance & Records
            <ChevronRight className={`h-4 w-4 transition-transform ${showStats ? "rotate-90" : ""}`} />
          </button>
          <AnimatePresence>
            {showStats && (
              <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                <div className="mt-3 grid grid-cols-2 gap-2" data-testid="profile-stats-grid">
                  <div className="rounded-[14px] bg-[#f6f6f2] p-3 text-center">
                    <p className="text-xl font-black text-[#243e36]">{stats.review_count ?? "—"}</p>
                    <p className="text-[10px] font-semibold uppercase text-[#5f7464]">Reviews</p>
                  </div>
                  <div className="rounded-[14px] bg-[#f6f6f2] p-3 text-center">
                    <p className="text-xl font-black text-[#243e36]">{stats.submission_count ?? "—"}</p>
                    <p className="text-[10px] font-semibold uppercase text-[#5f7464]">Submissions</p>
                  </div>
                  <div className="rounded-[14px] bg-[#f6f6f2] p-3 text-center">
                    <p className="text-xl font-black text-[#243e36]">{stats.training_completed ?? 0}/{stats.training_total ?? 0}</p>
                    <p className="text-[10px] font-semibold uppercase text-[#5f7464]">Training</p>
                  </div>
                  <div className="rounded-[14px] bg-[#f6f6f2] p-3 text-center">
                    <p className="text-xl font-black text-[#243e36]">{stats.training_total ? `${Math.round((stats.training_completed / stats.training_total) * 100)}%` : "—"}</p>
                    <p className="text-[10px] font-semibold uppercase text-[#5f7464]">Completion</p>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );
}


/* ─────── Individual View ─────── */
function IndividualView({ profiles, onCardClick }) {
  const rows = [];
  for (let i = 0; i < profiles.length; i += 5) {
    rows.push(profiles.slice(i, i + 5));
  }
  while (rows.length < 3) rows.push([]);

  return (
    <div className="flex h-full flex-col justify-center gap-4" data-testid="individual-view">
      {rows.slice(0, 3).map((row, i) => (
        <CarouselRow key={i} items={row} onCardClick={onCardClick} />
      ))}
      {rows.length > 3 && (
        <div className="flex flex-wrap justify-center gap-3 pt-2">
          {profiles.slice(15).map((p) => (
            <ProfileCard key={p.profile_id} profile={p} onClick={onCardClick} />
          ))}
        </div>
      )}
    </div>
  );
}


/* ─────── Team Structure View ─────── */
function TeamStructureView({ teams, onCardClick }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3" data-testid="team-structure-view">
      {teams.map((team, i) => (
        <Card key={i} className="rounded-[28px] border-border/80 bg-white/95 shadow-sm" data-testid={`team-card-${team.lead.profile_id}`}>
          <CardContent className="p-5">
            <button type="button" onClick={() => onCardClick(team.lead)} className="flex w-full items-center gap-3 text-left">
              <Avatar name={team.lead.name} avatarUrl={team.lead.avatar_url} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-[#111815]">{team.lead.name}</p>
                <div className="mt-1 flex flex-wrap gap-1">
                  <Badge className="border-0 bg-emerald-100 text-[10px] text-emerald-800">Crew Leader</Badge>
                  <Badge className="border-0 bg-[#edf0e7] text-[10px] text-[#243e36]">{team.division}</Badge>
                </div>
              </div>
            </button>
            {team.members.length > 0 && (
              <div className="mt-4 space-y-2 border-l-2 border-[#d8f3dc] pl-4" data-testid="team-members-list">
                {team.members.map((m) => (
                  <button key={m.profile_id} type="button" onClick={() => onCardClick(m)} className="flex w-full items-center gap-2.5 rounded-2xl p-2 text-left transition hover:bg-[#f6f6f2]" data-testid={`team-member-${m.profile_id}`}>
                    <Avatar name={m.name} avatarUrl={m.avatar_url} size="sm" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-[#243e36]">{m.name}</p>
                      <p className="text-xs text-[#5c6d64]">Crew Member</p>
                    </div>
                  </button>
                ))}
              </div>
            )}
            {team.members.length === 0 && (
              <p className="mt-3 text-xs text-[#5c6d64]">No registered members yet</p>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}


/* ─────── Division Hierarchy View ─────── */
function HierarchyNode({ profile, label, indent = 0, onCardClick, children }) {
  const roleBadge = ROLE_COLORS[profile?.role || label] || "bg-gray-100 text-gray-700";
  return (
    <div style={{ paddingLeft: `${indent * 20}px` }} data-testid={`hierarchy-node-${profile?.profile_id || label}`}>
      {profile ? (
        <button type="button" onClick={() => onCardClick(profile)} className="flex items-center gap-2.5 rounded-2xl p-2 text-left transition hover:bg-[#f6f6f2]">
          <Avatar name={profile.name} avatarUrl={profile.avatar_url} size="sm" />
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-[#111815]">{profile.name}</p>
            <Badge className={`border-0 text-[10px] ${roleBadge}`}>{profile.role || profile.title}</Badge>
          </div>
        </button>
      ) : (
        <div className="flex items-center gap-2 py-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#edf0e7] text-[#5f7464]"><Layers className="h-4 w-4" /></div>
          <p className="text-sm font-bold text-[#243e36]">{label}</p>
        </div>
      )}
      {children}
    </div>
  );
}

function DivisionHierarchyView({ hierarchy, onCardClick }) {
  if (!hierarchy) return null;
  return (
    <div className="space-y-1 overflow-y-auto" data-testid="hierarchy-view" style={{ maxHeight: "calc(100vh - 220px)" }}>
      {/* Owners */}
      <HierarchyNode label="Ownership" indent={0} onCardClick={onCardClick}>
        {hierarchy.owners.map((o) => <HierarchyNode key={o.profile_id} profile={o} indent={1} onCardClick={onCardClick} />)}
      </HierarchyNode>

      {/* GMs */}
      <HierarchyNode label="General Managers" indent={1} onCardClick={onCardClick}>
        {hierarchy.general_managers.map((g) => <HierarchyNode key={g.profile_id} profile={g} indent={2} onCardClick={onCardClick} />)}
      </HierarchyNode>

      {/* AMs */}
      <HierarchyNode label="Account Managers" indent={2} onCardClick={onCardClick}>
        {hierarchy.account_managers.map((a) => <HierarchyNode key={a.profile_id} profile={a} indent={3} onCardClick={onCardClick} />)}
      </HierarchyNode>

      {/* PMs */}
      <HierarchyNode label="Production Managers" indent={2} onCardClick={onCardClick}>
        {hierarchy.production_managers.map((p) => <HierarchyNode key={p.profile_id} profile={p} indent={3} onCardClick={onCardClick} />)}
      </HierarchyNode>

      {/* Supervisors */}
      <HierarchyNode label="Supervisors" indent={2} onCardClick={onCardClick}>
        {hierarchy.supervisors.map((s) => <HierarchyNode key={s.profile_id} profile={s} indent={3} onCardClick={onCardClick} />)}
      </HierarchyNode>

      {/* Divisions → Teams → Members */}
      {hierarchy.divisions.map((div) => (
        <HierarchyNode key={div.name} label={div.name} indent={3} onCardClick={onCardClick}>
          {div.teams.map((team, i) => (
            <HierarchyNode key={team.lead.profile_id} profile={team.lead} indent={4} onCardClick={onCardClick}>
              {team.members.map((m) => (
                <HierarchyNode key={m.profile_id} profile={m} indent={5} onCardClick={onCardClick} />
              ))}
            </HierarchyNode>
          ))}
        </HierarchyNode>
      ))}
    </div>
  );
}


/* ═══════ Main Page ═══════ */
export default function TeamMembersPage() {
  const [view, setView] = useState("individual");
  const [profiles, setProfiles] = useState([]);
  const [teams, setTeams] = useState([]);
  const [hierarchy, setHierarchy] = useState(null);
  const [selectedProfile, setSelectedProfile] = useState(null);

  useEffect(() => {
    if (view === "individual") {
      authGet("/team/profiles").then((d) => setProfiles(d.profiles || [])).catch(() => {});
    } else if (view === "team") {
      authGet("/team/structure").then((d) => setTeams(d.teams || [])).catch(() => {});
    } else {
      authGet("/team/hierarchy").then(setHierarchy).catch(() => {});
    }
  }, [view]);

  return (
    <div className="flex h-[calc(100vh-64px)] flex-col" data-testid="team-members-page">
      {/* Header bar */}
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-4 pb-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">People</p>
          <h1 className="mt-1 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815] lg:text-4xl" data-testid="team-page-title">Team Members</h1>
        </div>
        <Select value={view} onValueChange={setView}>
          <SelectTrigger className="h-11 w-52 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="team-view-selector">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="individual"><span className="flex items-center gap-2"><User className="h-3.5 w-3.5" /> Individual</span></SelectItem>
            <SelectItem value="team"><span className="flex items-center gap-2"><Users className="h-3.5 w-3.5" /> Team Structure</span></SelectItem>
            <SelectItem value="hierarchy"><span className="flex items-center gap-2"><Network className="h-3.5 w-3.5" /> Division Hierarchy</span></SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Content area (fills remaining height, no page scroll) */}
      <div className="min-h-0 flex-1 overflow-hidden">
        <Card className="h-full rounded-[32px] border-border/80 bg-white/95 shadow-sm">
          <CardContent className="h-full p-6">
            {view === "individual" && <IndividualView profiles={profiles} onCardClick={setSelectedProfile} />}
            {view === "team" && <TeamStructureView teams={teams} onCardClick={setSelectedProfile} />}
            {view === "hierarchy" && <DivisionHierarchyView hierarchy={hierarchy} onCardClick={setSelectedProfile} />}
          </CardContent>
        </Card>
      </div>

      {/* Profile overlay */}
      <AnimatePresence>
        {selectedProfile && <ProfileDetailOverlay profile={selectedProfile} onClose={() => setSelectedProfile(null)} />}
      </AnimatePresence>
    </div>
  );
}
