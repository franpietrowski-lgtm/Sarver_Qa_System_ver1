import { useEffect, useState } from "react";
import { BookOpen, ChevronDown, ChevronRight, Download, Lock, Users as UsersIcon } from "lucide-react";

import { useTheme, THEMES, THEME_SWATCHES, FONT_PACKAGES } from "@/components/theme/ThemeProvider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { authGet, authPatch, authPost } from "@/lib/api";
import { toast } from "sonner";


const STAFF_TITLES = ["GM", "Account Manager", "Production Manager", "Supervisor", "Owner"];


export default function SettingsPage() {
  const { theme: currentTheme, setTheme, fontPkg, setFontPkg } = useTheme();
  const [users, setUsers] = useState([]);
  const [creatingUser, setCreatingUser] = useState(false);
  const [newUser, setNewUser] = useState({
    name: "",
    email: "",
    role: "management",
    title: "Production Manager",
    password: "",
    is_active: true,
  });

  const loadSettings = async () => {
    const usersResponse = await authGet("/users");
    setUsers(usersResponse);
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const createUser = async (event) => {
    event.preventDefault();
    setCreatingUser(true);
    try {
      await authPost("/users", newUser);
      toast.success("Staff account created.");
      setNewUser({ name: "", email: "", role: "management", title: "Production Manager", password: "", is_active: true });
      await loadSettings();
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Unable to create user");
    } finally {
      setCreatingUser(false);
    }
  };

  const [tempPassword, setTempPassword] = useState(null);

  const toggleUserStatus = async (userId, isActive) => {
    try {
      await authPatch(`/users/${userId}/status`, { is_active: isActive });
      toast.success(isActive ? "Account authorized." : "Account deactivated.");
      await loadSettings();
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Unable to update user status");
    }
  };

  const resetUserPassword = async (userId, userName) => {
    if (!window.confirm(`Reset password for ${userName}? This will generate a temporary password.`)) return;
    try {
      const result = await authPost(`/users/${userId}/reset-password`);
      setTempPassword(result);
      toast.success(`Password reset for ${userName}. Share the temp password below.`);
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Unable to reset password");
    }
  };

  const [changePassForm, setChangePassForm] = useState({ current: "", next: "" });
  const [changingPass, setChangingPass] = useState(false);

  const changeMyPassword = async (event) => {
    event.preventDefault();
    if (changePassForm.next.length < 6) {
      toast.error("New password must be at least 6 characters");
      return;
    }
    setChangingPass(true);
    try {
      await authPost("/auth/change-password", { current_password: changePassForm.current, new_password: changePassForm.next });
      toast.success("Your password has been updated.");
      setChangePassForm({ current: "", next: "" });
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Unable to change password");
    } finally {
      setChangingPass(false);
    }
  };

  if (!users) {
    return <div className="rounded-[28px] border border-border bg-[var(--card)] p-10 text-center text-[var(--foreground)]" data-testid="settings-loading-state">Loading settings...</div>;
  }

  return (
    <div className="space-y-6" data-testid="settings-page">
      <Card className="rounded-[24px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="settings-theme-card">
        <CardContent className="p-4 sm:p-5">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Workspace theme</p>
          <p className="mt-1 mb-3 text-sm text-[var(--muted-foreground)]" data-testid="settings-theme-state">Active: {THEMES.find((t) => t.id === currentTheme)?.label || "Default"}</p>
          <div className="grid grid-cols-4 gap-2 sm:grid-cols-4 lg:grid-cols-8">
            {THEMES.map((t) => {
              const swatches = THEME_SWATCHES[t.id];
              const isActive = currentTheme === t.id;
              return (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => { setTheme(t.id); toast.success(`Theme switched to ${t.label}`); }}
                  className={`group relative flex flex-col items-center gap-1 rounded-xl border-2 p-2 transition-all ${isActive ? "border-[var(--foreground)] shadow-md ring-2 ring-[var(--foreground)]/20" : "border-border/60 hover:border-[var(--foreground)]/40 hover:shadow-sm"}`}
                  data-testid={`settings-theme-option-${t.id}`}
                >
                  <div className="flex h-6 w-full overflow-hidden rounded-lg">
                    {swatches.map((color, i) => (
                      <div key={i} className="flex-1" style={{ backgroundColor: color }} />
                    ))}
                  </div>
                  <span className="text-[10px] font-semibold text-[var(--foreground)]">{t.label}</span>
                  {isActive && <div className="absolute -top-1 -right-1 h-3 w-3 rounded-full border-2 border-[var(--card)] bg-[var(--foreground)]" />}
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Font package picker */}
      <Card className="rounded-[24px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="settings-font-card">
        <CardContent className="p-4 sm:p-5">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Font package</p>
          <p className="mt-1 mb-3 text-sm text-[var(--muted-foreground)]" data-testid="settings-font-state">Active: {FONT_PACKAGES.find((f) => f.id === fontPkg)?.label || "Brand"}</p>
          <div className="grid grid-cols-4 gap-2 sm:grid-cols-4">
            {FONT_PACKAGES.map((f) => {
              const isActive = fontPkg === f.id;
              return (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => { setFontPkg(f.id); toast.success(`Font switched to ${f.label}`); }}
                  className={`group relative flex flex-col items-center gap-1 rounded-xl border-2 p-2 transition-all ${isActive ? "border-[var(--foreground)] shadow-md ring-2 ring-[var(--foreground)]/20" : "border-border/60 hover:border-[var(--foreground)]/40 hover:shadow-sm"}`}
                  data-testid={`settings-font-option-${f.id}`}
                >
                  <span className="text-lg font-bold text-[var(--foreground)]" style={{ fontFamily: f.family }}>Aa</span>
                  <span className="text-[10px] font-semibold text-[var(--foreground)]">{f.label}</span>
                  {isActive && <div className="absolute -top-1 -right-1 h-3 w-3 rounded-full border-2 border-[var(--card)] bg-[var(--foreground)]" />}
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Workflow Guides — Expandable Cards */}
      <Card className="rounded-[24px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="settings-workflow-guides-card">
        <CardContent className="p-4 sm:p-5">
          <div className="mb-1 flex items-center justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Workflow guides</p>
              <p className="mt-1 text-sm text-[var(--muted-foreground)]">Step-by-step walkthroughs for every role and workflow in the Sarver QA system.</p>
            </div>
            <BookOpen className="h-5 w-5 text-[var(--foreground)]" />
          </div>
          <WorkflowGuides />
        </CardContent>
      </Card>

      {/* System Reference PDF Download */}
      <Card className="rounded-[24px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="settings-system-ref-card">
        <CardContent className="flex items-center justify-between gap-4 p-4 sm:p-5">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">System reference</p>
            <p className="mt-1 text-sm text-[var(--foreground)]">Architecture, storage paths, tech stack, schema, and implementation blueprint.</p>
            <p className="mt-1 text-xs text-[var(--muted-foreground)]">Downloads a document with all technical configuration and system details.</p>
          </div>
          <Button
            type="button"
            onClick={() => { const url = `${process.env.REACT_APP_BACKEND_URL}/api/exports/system-reference-pdf`; const token = localStorage.getItem("token"); window.open(`${url}?token=${token}`, "_blank"); }}
            className="h-10 shrink-0 rounded-xl bg-[var(--btn-accent)] hover:bg-[var(--btn-accent-hover)]"
            data-testid="settings-download-system-pdf"
          >
            <Download className="mr-2 h-4 w-4" />Download PDF
          </Button>
        </CardContent>
      </Card>

      {/* Account Security */}
      <Card className="rounded-[24px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="settings-change-password-card">
        <CardContent className="p-4 sm:p-5">
          <div className="flex items-center gap-2">
            <Lock className="h-4 w-4 text-[var(--foreground)]" />
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Account security</p>
          </div>
          <p className="mt-2 text-sm font-semibold text-[var(--foreground)]">Change my password</p>
          <form className="mt-3 grid gap-3 max-w-md" onSubmit={changeMyPassword} data-testid="settings-change-password-form">
            <Input type="password" value={changePassForm.current} onChange={(e) => setChangePassForm((c) => ({ ...c, current: e.target.value }))} placeholder="Current password" className="h-11 rounded-2xl border-[var(--form-card-border)] bg-[var(--chip-bg)]" data-testid="settings-current-password-input" required />
            <Input type="password" value={changePassForm.next} onChange={(e) => setChangePassForm((c) => ({ ...c, next: e.target.value }))} placeholder="New password (min 6 characters)" className="h-11 rounded-2xl border-[var(--form-card-border)] bg-[var(--chip-bg)]" data-testid="settings-new-password-input" required />
            <Button type="submit" disabled={changingPass} className="h-11 w-fit rounded-2xl bg-[var(--btn-accent)] hover:bg-[var(--btn-accent-hover)]" data-testid="settings-change-password-button">{changingPass ? "Updating..." : "Update password"}</Button>
          </form>
        </CardContent>
      </Card>

      {/* Staff Management */}
      <Card className="rounded-[24px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="settings-staff-management-card">
        <CardContent className="p-4 sm:p-5">
          <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
            <div>
              <div className="flex items-center gap-2">
                <UsersIcon className="h-4 w-4 text-[var(--foreground)]" />
                <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Staff access management</p>
              </div>
              <p className="mt-2 text-sm text-[var(--foreground)]">Create and authorize Sarver team accounts. Each account is role-locked to their dashboard view.</p>
              <form className="mt-5 grid gap-4" onSubmit={createUser} data-testid="settings-create-user-form">
                <Input value={newUser.name} onChange={(event) => setNewUser((current) => ({ ...current, name: event.target.value }))} placeholder="Staff name" className="h-12 rounded-2xl border-[var(--form-card-border)] bg-[var(--chip-bg)]" data-testid="settings-user-name-input" />
                <Input value={newUser.email} onChange={(event) => setNewUser((current) => ({ ...current, email: event.target.value }))} placeholder="Email" className="h-12 rounded-2xl border-[var(--form-card-border)] bg-[var(--chip-bg)]" data-testid="settings-user-email-input" />
                <Input value={newUser.password} onChange={(event) => setNewUser((current) => ({ ...current, password: event.target.value }))} placeholder="Temporary password" className="h-12 rounded-2xl border-[var(--form-card-border)] bg-[var(--chip-bg)]" data-testid="settings-user-password-input" />
                <div className="grid gap-4 md:grid-cols-2">
                  <select value={newUser.role} onChange={(event) => setNewUser((current) => ({ ...current, role: event.target.value, title: event.target.value === "owner" ? "Owner" : current.title }))} className="glass-dropdown h-12 rounded-2xl border border-[var(--form-card-border)] bg-[var(--chip-bg)] px-4 text-sm text-[var(--foreground)]" data-testid="settings-user-role-select">
                    <option value="management">Admin</option>
                    <option value="owner">Owner</option>
                  </select>
                  <select value={newUser.title} onChange={(event) => setNewUser((current) => ({ ...current, title: event.target.value }))} className="glass-dropdown h-12 rounded-2xl border border-[var(--form-card-border)] bg-[var(--chip-bg)] px-4 text-sm text-[var(--foreground)]" data-testid="settings-user-title-select">
                    {STAFF_TITLES.filter((title) => newUser.role === "owner" ? title === "Owner" : title !== "Owner").map((title) => <option key={title} value={title}>{title}</option>)}
                  </select>
                </div>
                <label className="flex items-center gap-3 rounded-2xl bg-[var(--chip-bg)] px-4 py-3 text-sm text-[var(--foreground)]" data-testid="settings-user-active-toggle">
                  <input type="checkbox" checked={newUser.is_active} onChange={(event) => setNewUser((current) => ({ ...current, is_active: event.target.checked }))} />
                  Authorize immediately
                </label>
                <Button type="submit" disabled={creatingUser} className="h-12 rounded-2xl bg-[var(--btn-accent)] hover:bg-[var(--btn-accent-hover)]" data-testid="settings-create-user-button">{creatingUser ? "Creating account..." : "Create staff account"}</Button>
              </form>
            </div>

            <div>
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Current staff access</p>
              <div className="mt-5 space-y-3">
                {users.map((user) => (
                  <div key={user.id} className="rounded-[20px] border border-[var(--form-card-border)] bg-[var(--form-card-bg)] p-4" data-testid={`settings-user-row-${user.id}`}>
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-[var(--foreground)]">{user.name}</p>
                        <p className="mt-1 text-sm text-[var(--muted-foreground)]">{user.email} · {user.title}</p>
                      </div>
                      <Badge className={`border-0 px-3 py-1 ${user.is_active ? "bg-emerald-500/15 text-emerald-600" : "bg-red-500/15 text-red-500"}`}>{user.is_active ? "authorized" : "inactive"}</Badge>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <Button type="button" variant="outline" onClick={() => toggleUserStatus(user.id, !user.is_active)} className="h-10 rounded-2xl border-[var(--form-card-border)] bg-[var(--card)] text-[var(--foreground)] hover:bg-[var(--chip-bg)]" data-testid={`settings-user-status-button-${user.id}`}>{user.is_active ? "Deactivate" : "Authorize"}</Button>
                      <Button type="button" variant="outline" onClick={() => resetUserPassword(user.id, user.name)} className="h-10 rounded-2xl border-[var(--form-card-border)] bg-[var(--card)] text-[var(--foreground)] hover:bg-[var(--chip-bg)]" data-testid={`settings-user-reset-pw-${user.id}`}>Reset password</Button>
                    </div>
                    {tempPassword && tempPassword.user_email === user.email && (
                      <div className="mt-3 rounded-2xl border p-3" style={{ backgroundColor: "var(--status-watch-bg)", borderColor: "var(--status-watch-border)" }} data-testid={`settings-temp-pw-${user.id}`}>
                        <p className="text-xs font-bold" style={{ color: "var(--status-watch-text)" }}>Temp password generated — share with {user.name}:</p>
                        <p className="mt-1 select-all font-mono text-sm font-bold text-[var(--foreground)]" data-testid={`settings-temp-pw-value-${user.id}`}>{tempPassword.temp_password}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Workflow Guide Cards ────────────────────────────────────────────────
const WORKFLOW_GUIDES = [
  {
    id: "onboarding",
    title: "New Staff Onboarding",
    summary: "How to create accounts, set roles, and get a new team member into the system.",
    steps: [
      { label: "Create Account", detail: "Navigate to Settings > Staff Access Management. Enter the team member's name, email, and a temporary password. Select their role (Admin or Owner) and title (GM, PM, AM, Supervisor)." },
      { label: "Authorize Access", detail: "Check 'Authorize immediately' to give instant access, or leave unchecked to activate later. The new user can log in at /login with their temp credentials." },
      { label: "Set Division", detail: "Production Managers should be assigned to a division. This controls which crew assignments and reviews they see by default." },
      { label: "First Login", detail: "The new user logs in, gets routed to their role-specific dashboard. They should change their password in Settings > Account Security immediately." },
    ],
  },
  {
    id: "job-allocation",
    title: "Job Creation & Crew Allocation",
    summary: "Account Managers create jobs, PMs assign crews via the daily assignment board.",
    steps: [
      { label: "Create Job (AM)", detail: "Account Managers navigate to QJA (Quality Job Assignments) and create a new job with property name, address, service type, division, and truck number." },
      { label: "Assign Crew (PM)", detail: "Production Managers open Crew Assignments and drag jobs onto crew columns for each day of the week. Use 'Pre-load week forecast' to auto-assign based on division and truck matching." },
      { label: "Crew Receives Work", detail: "When a crew leader opens their QR portal (/crew/{code}), they see jobs assigned to their truck number. They capture photos and submit quality proof sets." },
      { label: "Review Cycle", detail: "Submitted work enters the Review Queue for management scoring. Rapid Review (mobile swipe) handles high-volume QA. Detailed management reviews score by rubric category." },
    ],
  },
  {
    id: "rapid-review",
    title: "Rapid Review (Mobile Swipe QA)",
    summary: "Fast-track quality review from your phone using swipe gestures.",
    steps: [
      { label: "Access", detail: "Scan the QR code on the Overview dashboard or navigate to the Rapid Review link. Works best on mobile — optimized for one-handed swipe operation." },
      { label: "Swipe Right", detail: "Standard pass — the work meets quality expectations. No comment required." },
      { label: "Swipe Left", detail: "Fail — work does not meet standards. A comment is required explaining the deficiency. This triggers coaching recommendations." },
      { label: "Swipe Up", detail: "Exemplary — work exceeds expectations. A comment is required noting what was exceptional. This contributes positive data to crew performance metrics." },
      { label: "Speed Alerts", detail: "Reviews under 4 seconds are flagged as 'fast swipes.' Three or more fast swipes in a session triggers an Owner notification to ensure review integrity." },
    ],
  },
  {
    id: "incident-reporting",
    title: "Emergency Incident Reporting",
    summary: "When accidents or property damage occur, crews file an emergency report that bypasses photo requirements.",
    steps: [
      { label: "Crew Files Report", detail: "In the Crew QR app, toggle 'Emergency: Incident/Accident' on. This removes the 3-photo minimum requirement. Describe the incident in the notes field and attach any available photos." },
      { label: "Dashboard Alert", detail: "A red-flashing alert appears on the Overview dashboard for all Supervisors, PMs, GMs, and the Owner. Click to see the full incident details." },
      { label: "Acknowledge", detail: "A manager reviews the incident, takes action (client notification, crew coaching), and clicks 'Acknowledge' to clear the alert. Dismissed incidents remain in the submission history." },
    ],
  },
  {
    id: "coaching-loop",
    title: "Closed-Loop Coaching",
    summary: "Crews flagged as repeat offenders receive auto-generated training based on their weakest rubric areas.",
    steps: [
      { label: "Repeat Offender Detection", detail: "The system monitors flagged issues per crew over a rolling window. Crews exceeding thresholds (3 = Warning, 5 = Critical) are surfaced on the Repeat Offenders page." },
      { label: "Auto-Generate Coaching", detail: "Click 'Auto-generate coaching sessions' on the Repeat Offenders page. The system creates targeted training sessions loaded with division-relevant standards." },
      { label: "Crew Completes Training", detail: "Crew leaders and members access training sessions via their portal. Each session includes a quiz on the relevant standards." },
      { label: "Loop Closure", detail: "When coaching is assigned AND training is completed, the coaching loop status moves from 'Open' to 'Closed.' This is tracked on the Overview dashboard widget." },
    ],
  },
  {
    id: "client-report",
    title: "Client Quality Reports",
    summary: "Generate professional quality reports for client-facing presentations.",
    steps: [
      { label: "Navigate", detail: "Open Client Report from the sidebar. Select a job using the search dropdown — it filters as you type and shows glass-effect suggestions." },
      { label: "Set Timeframe", detail: "Choose Monthly, Quarterly, or Annual to control the reporting period. Data aggregates across all submissions for the selected job and timeframe." },
      { label: "Review Metrics", detail: "The report shows average scores, photo count, crew performance, and quality trends over the selected period." },
      { label: "Export PDF", detail: "Click 'Download PDF' to generate a professional client-ready report document with all metrics and photo references." },
    ],
  },
];

function WorkflowGuides() {
  const [expanded, setExpanded] = useState(null);

  return (
    <div className="mt-4 space-y-2" data-testid="workflow-guides-list">
      {WORKFLOW_GUIDES.map((guide) => (
        <div key={guide.id} className="rounded-[16px] border border-[var(--form-card-border)] bg-[var(--form-card-bg)] transition-shadow hover:shadow-sm" data-testid={`workflow-guide-${guide.id}`}>
          <button
            type="button"
            onClick={() => setExpanded(expanded === guide.id ? null : guide.id)}
            className="flex w-full items-center justify-between gap-3 p-4 text-left"
            data-testid={`workflow-guide-toggle-${guide.id}`}
          >
            <div className="min-w-0">
              <p className="text-sm font-semibold text-[var(--foreground)]">{guide.title}</p>
              <p className="mt-0.5 text-xs text-[var(--muted-foreground)]">{guide.summary}</p>
            </div>
            {expanded === guide.id
              ? <ChevronDown className="h-4 w-4 shrink-0 text-[var(--muted-foreground)]" />
              : <ChevronRight className="h-4 w-4 shrink-0 text-[var(--muted-foreground)]" />
            }
          </button>
          {expanded === guide.id && (
            <div className="border-t border-[var(--form-card-border)] px-4 pb-4 pt-3" data-testid={`workflow-guide-content-${guide.id}`}>
              <div className="space-y-3">
                {guide.steps.map((step, idx) => (
                  <div key={idx} className="flex gap-3">
                    <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--btn-accent)] text-[10px] font-bold text-white">{idx + 1}</div>
                    <div>
                      <p className="text-sm font-semibold text-[var(--foreground)]">{step.label}</p>
                      <p className="mt-0.5 text-xs leading-relaxed text-[var(--muted-foreground)]">{step.detail}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}