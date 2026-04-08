import { useEffect, useState } from "react";
import { GitBranch, HardDrive, Network, Shapes } from "lucide-react";

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
  const [storageStatus, setStorageStatus] = useState(null);
  const [blueprint, setBlueprint] = useState(null);
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
    const [storageResponse, blueprintResponse, usersResponse] = await Promise.all([
      authGet("/integrations/storage/status"),
      authGet("/system/blueprint"),
      authGet("/users"),
    ]);
    setStorageStatus(storageResponse);
    setBlueprint(blueprintResponse);
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

  if (!storageStatus || !blueprint) {
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

      <div className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
        <Card className="rounded-[32px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="settings-drive-card">
          <CardContent className="p-8">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Supabase storage</p>
                <h2 className="mt-2 font-[Cabinet_Grotesk] text-4xl font-black tracking-tight text-[var(--foreground)]">Backend-managed image storage for every proof set</h2>
              </div>
              <HardDrive className="h-6 w-6 text-[var(--foreground)]" />
            </div>

            <div className="mt-6 flex flex-wrap gap-2">
              <Badge className="border-0 bg-[var(--accent)] px-3 py-1 text-[var(--foreground)]" data-testid="settings-drive-configured-badge">Configured: {storageStatus.configured ? "Yes" : "No"}</Badge>
              <Badge className="border-0 bg-[var(--accent)] px-3 py-1 text-[var(--foreground)]" data-testid="settings-drive-connected-badge">Ready for uploads: {storageStatus.connected ? "Yes" : "No"}</Badge>
            </div>

            <div className="mt-6 rounded-[28px] border border-border bg-[var(--accent)] p-5" data-testid="settings-drive-path-card">
              <p className="text-sm font-semibold text-[var(--foreground)]">Storage path structure</p>
              <p className="mt-2 text-sm text-[var(--muted-foreground)]" data-testid="settings-drive-folder-structure">{storageStatus.bucket || "qa-images"}/sarver-landscape/submissions/{'{SubmissionID}'}/{'{captures|issues}'}/{'{file}'}</p>
              <p className="mt-4 text-sm text-[var(--muted-foreground)]">Project URL: {storageStatus.project_url || "Not configured"}</p>
              <p className="mt-2 text-sm text-[var(--muted-foreground)]">Required env values: {storageStatus.required_env.join(", ")}</p>
            </div>

            <div className="mt-6 rounded-[28px] border border-border bg-[var(--accent)] p-5" data-testid="settings-drive-connect-button">
              <p className="text-sm font-semibold text-[var(--foreground)]">Storage mode</p>
              <p className="mt-2 text-sm text-[var(--muted-foreground)]">Uploads are handled only by the backend service role. Crew, admin, and owner screens keep using stable review-friendly image routes.</p>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-[32px] border-border/80 bg-[#243e36] text-white shadow-sm" data-testid="settings-tech-stack-card">
          <CardContent className="p-8">
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#d8f3dc]">Suggested stack</p>
            <h2 className="mt-2 font-[Cabinet_Grotesk] text-4xl font-black tracking-tight">Implementation blueprint</h2>
            <div className="mt-6 grid gap-4 sm:grid-cols-3">
              {[
                { icon: Shapes, label: "Frontend", value: blueprint.suggested_stack.frontend },
                { icon: Network, label: "Backend", value: blueprint.suggested_stack.backend },
                { icon: GitBranch, label: "Database", value: blueprint.suggested_stack.database },
              ].map((item) => {
                const Icon = item.icon;
                return (
                  <div key={item.label} className="rounded-[28px] border border-white/10 bg-white/10 p-5" data-testid={`settings-stack-card-${item.label.toLowerCase()}`}>
                    <Icon className="h-5 w-5 text-[#d8f3dc]" />
                    <p className="mt-4 text-sm text-white/70">{item.label}</p>
                    <p className="mt-2 text-sm font-semibold text-white">{item.value}</p>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card className="rounded-[32px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="settings-architecture-card">
          <CardContent className="p-8">
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Application architecture</p>
            <div className="mt-5 space-y-5">
              {Object.entries(blueprint.architecture).map(([key, items]) => (
                <div key={key} data-testid={`settings-architecture-section-${key}`}>
                  <h3 className="font-[Cabinet_Grotesk] text-2xl font-black tracking-tight text-[var(--foreground)]">{key}</h3>
                  <ul className="mt-3 space-y-2 text-sm text-[var(--muted-foreground)]">
                    {items.map((item) => <li key={item}>• {item}</li>)}
                  </ul>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-[32px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="settings-schema-card">
          <CardContent className="p-8">
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Schema, screens, workflow</p>
            <div className="mt-5 grid gap-5">
              <div data-testid="settings-schema-list">
                <h3 className="font-[Cabinet_Grotesk] text-2xl font-black tracking-tight text-[var(--foreground)]">Collections</h3>
                <div className="mt-3 flex flex-wrap gap-2">
                  {blueprint.database_schema.map((item) => <Badge key={item} className="border-0 bg-[var(--accent)] px-3 py-1 text-[var(--foreground)]">{item}</Badge>)}
                </div>
              </div>
              <div data-testid="settings-ui-screen-list">
                <h3 className="font-[Cabinet_Grotesk] text-2xl font-black tracking-tight text-[var(--foreground)]">UI screens</h3>
                <ul className="mt-3 space-y-2 text-sm text-[var(--muted-foreground)]">
                  {blueprint.ui_screens.map((item) => <li key={item}>• {item}</li>)}
                </ul>
              </div>
              <div data-testid="settings-workflow-list">
                <h3 className="font-[Cabinet_Grotesk] text-2xl font-black tracking-tight text-[var(--foreground)]">Workflow diagram</h3>
                <div className="mt-3 flex flex-wrap gap-2">
                  {blueprint.workflow_diagram.map((item, index) => <Badge key={item} className="border-0 bg-[#243e36] px-3 py-1 text-white">{index + 1}. {item}</Badge>)}
                </div>
              </div>
              <div data-testid="settings-plan-list">
                <h3 className="font-[Cabinet_Grotesk] text-2xl font-black tracking-tight text-[var(--foreground)]">Implementation plan</h3>
                <ul className="mt-3 space-y-2 text-sm text-[var(--muted-foreground)]">
                  {blueprint.implementation_plan.map((item) => <li key={item}>• {item}</li>)}
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-[32px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="settings-learning-roadmap-card">
        <CardContent className="p-8">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Learning roadmap</p>
          <h3 className="mt-2 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[var(--foreground)]">How this system can grow into automated quality checks</h3>
          <div className="mt-5 grid gap-4 md:grid-cols-3">
            {[
              'Phase 1: humans review photo batches and store rubric labels, comments, and variance data.',
              'Phase 2: AI suggests likely scores and issues from the labeled image archive.',
              'Phase 3: AI handles most grading while humans supervise edge cases and drift.',
            ].map((step, index) => (
              <div key={step} className="rounded-[24px] border border-border bg-[var(--accent)] p-4 text-sm text-[var(--muted-foreground)]" data-testid={`settings-learning-roadmap-step-${index + 1}`}>{step}</div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Change My Password */}
      <Card className="rounded-[32px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="settings-change-password-card">
        <CardContent className="p-8">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Account security</p>
          <h3 className="mt-2 font-[Cabinet_Grotesk] text-xl font-bold tracking-tight text-[var(--foreground)]">Change my password</h3>
          <form className="mt-4 grid gap-3 max-w-md" onSubmit={changeMyPassword} data-testid="settings-change-password-form">
            <Input type="password" value={changePassForm.current} onChange={(e) => setChangePassForm((c) => ({ ...c, current: e.target.value }))} placeholder="Current password" className="h-11 rounded-2xl border-transparent bg-[var(--accent)]" data-testid="settings-current-password-input" required />
            <Input type="password" value={changePassForm.next} onChange={(e) => setChangePassForm((c) => ({ ...c, next: e.target.value }))} placeholder="New password (min 6 characters)" className="h-11 rounded-2xl border-transparent bg-[var(--accent)]" data-testid="settings-new-password-input" required />
            <Button type="submit" disabled={changingPass} className="h-11 w-fit rounded-2xl bg-[#243e36] hover:bg-[#1a2c26]" data-testid="settings-change-password-button">{changingPass ? "Updating..." : "Update password"}</Button>
          </form>
        </CardContent>
      </Card>

      <Card className="rounded-[32px] border-border/80 bg-[var(--card)] shadow-sm" data-testid="settings-staff-management-card">
        <CardContent className="p-8">
          <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Sarver staff access</p>
              <h3 className="mt-2 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[var(--foreground)]">Create and authorize implementation accounts</h3>
              <form className="mt-6 grid gap-4" onSubmit={createUser} data-testid="settings-create-user-form">
                <Input value={newUser.name} onChange={(event) => setNewUser((current) => ({ ...current, name: event.target.value }))} placeholder="Staff name" className="h-12 rounded-2xl border-transparent bg-[var(--accent)]" data-testid="settings-user-name-input" />
                <Input value={newUser.email} onChange={(event) => setNewUser((current) => ({ ...current, email: event.target.value }))} placeholder="Email" className="h-12 rounded-2xl border-transparent bg-[var(--accent)]" data-testid="settings-user-email-input" />
                <Input value={newUser.password} onChange={(event) => setNewUser((current) => ({ ...current, password: event.target.value }))} placeholder="Temporary password" className="h-12 rounded-2xl border-transparent bg-[var(--accent)]" data-testid="settings-user-password-input" />
                <div className="grid gap-4 md:grid-cols-2">
                  <select value={newUser.role} onChange={(event) => setNewUser((current) => ({ ...current, role: event.target.value, title: event.target.value === "owner" ? "Owner" : current.title }))} className="glass-dropdown h-12 rounded-2xl border border-transparent bg-[var(--accent)] px-4 text-sm text-[var(--foreground)]" data-testid="settings-user-role-select">
                    <option value="management">Admin</option>
                    <option value="owner">Owner</option>
                  </select>
                  <select value={newUser.title} onChange={(event) => setNewUser((current) => ({ ...current, title: event.target.value }))} className="glass-dropdown h-12 rounded-2xl border border-transparent bg-[var(--accent)] px-4 text-sm text-[var(--foreground)]" data-testid="settings-user-title-select">
                    {STAFF_TITLES.filter((title) => newUser.role === "owner" ? title === "Owner" : title !== "Owner").map((title) => <option key={title} value={title}>{title}</option>)}
                  </select>
                </div>
                <label className="flex items-center gap-3 rounded-2xl bg-[var(--accent)] px-4 py-3 text-sm text-[var(--foreground)]" data-testid="settings-user-active-toggle">
                  <input type="checkbox" checked={newUser.is_active} onChange={(event) => setNewUser((current) => ({ ...current, is_active: event.target.checked }))} />
                  Authorize immediately
                </label>
                <Button type="submit" disabled={creatingUser} className="h-12 rounded-2xl bg-[#243e36] hover:bg-[#1a2c26]" data-testid="settings-create-user-button">{creatingUser ? "Creating account..." : "Create staff account"}</Button>
              </form>
            </div>

            <div>
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-[var(--muted-foreground)]">Current staff access</p>
              <div className="mt-6 space-y-3">
                {users.map((user) => (
                  <div key={user.id} className="rounded-[24px] border border-border bg-[var(--accent)] p-4" data-testid={`settings-user-row-${user.id}`}>
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-[var(--foreground)]">{user.name}</p>
                        <p className="mt-1 text-sm text-[var(--muted-foreground)]">{user.email} · {user.title}</p>
                      </div>
                      <Badge className={`border-0 px-3 py-1 ${user.is_active ? "bg-emerald-500/15 text-emerald-600" : "bg-red-500/15 text-red-500"}`}>{user.is_active ? "authorized" : "inactive"}</Badge>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <Button type="button" variant="outline" onClick={() => toggleUserStatus(user.id, !user.is_active)} className="h-10 rounded-2xl border-border bg-[var(--card)] text-[var(--foreground)] hover:bg-[var(--accent)]" data-testid={`settings-user-status-button-${user.id}`}>{user.is_active ? "Deactivate" : "Authorize"}</Button>
                      <Button type="button" variant="outline" onClick={() => resetUserPassword(user.id, user.name)} className="h-10 rounded-2xl border-border bg-[var(--card)] text-[var(--foreground)] hover:bg-[var(--accent)]" data-testid={`settings-user-reset-pw-${user.id}`}>Reset password</Button>
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