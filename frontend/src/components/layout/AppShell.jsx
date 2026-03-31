import { motion } from "framer-motion";
import { ChartColumn, ClipboardCheck, FileOutput, FolderInput, LayoutDashboard, MoonStar, Settings, ShieldCheck, SunMedium, Zap } from "lucide-react";
import { NavLink } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import NotificationCenter from "@/components/common/NotificationCenter";
import { useTheme } from "@/components/theme/ThemeProvider";


const navigationByRole = {
  management: [
    { to: "/dashboard", label: "Overview", icon: LayoutDashboard },
    { to: "/jobs", label: "Alignment & QR", icon: FolderInput },
    { to: "/review", label: "Review Queue", icon: ClipboardCheck },
    { to: "/rapid-review", label: "Rapid Review", icon: Zap },
    { to: "/settings", label: "Settings", icon: Settings },
  ],
  owner: [
    { to: "/dashboard", label: "Overview", icon: LayoutDashboard },
    { to: "/owner", label: "Owner Review", icon: ShieldCheck },
    { to: "/rapid-review", label: "Rapid Review", icon: Zap },
    { to: "/analytics", label: "Calibration", icon: ChartColumn },
    { to: "/exports", label: "Exports", icon: FileOutput },
    { to: "/settings", label: "Settings", icon: Settings },
  ],
};


export default function AppShell({ user, onLogout, children }) {
  const navItems = navigationByRole[user?.role] || navigationByRole.management;
  const logoUrl = "https://sarverlandscape.com/wp-content/uploads/2024/10/sarver-logo.png";
  const { isDark, toggleTheme } = useTheme();

  return (
    <div className={`workspace-shell min-h-screen text-foreground ${isDark ? "theme-dark" : "theme-default bg-[radial-gradient(circle_at_top_left,_rgba(124,169,130,0.18),_transparent_28%),linear-gradient(180deg,_#f6f6f2_0%,_#edf0e7_100%)]"}`} data-testid="workspace-shell">
      <div className="grid min-h-screen lg:grid-cols-[280px_1fr]">
        <aside className="border-b border-border/80 bg-white/85 px-6 py-8 backdrop-blur-xl lg:border-b-0 lg:border-r">
          <div className="space-y-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]" data-testid="shell-kicker-text">Field Quality</p>
              <img src={logoUrl} alt="Sarver Landscape" className="mt-3 h-10 w-auto object-contain" data-testid="shell-brand-logo" />
              <h1 className="mt-3 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]" data-testid="shell-app-title">Quality Review</h1>
              <p className="mt-2 text-sm text-[#41534a]" data-testid="shell-app-subtitle">Character, quality, and respect across crew capture, review, and automation readiness.</p>
            </div>

            <div className="rounded-3xl border border-border bg-[#243e36] p-5 text-white shadow-sm" data-testid="shell-user-card">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm text-white/70">Signed in as</p>
                  <p className="text-lg font-semibold" data-testid="shell-user-name">{user?.name}</p>
                  {user?.title && <p className="text-sm text-white/70" data-testid="shell-user-title">{user.title}</p>}
                </div>
                <Badge className="border-0 bg-[#7ca982] px-3 py-1 text-[#10261d]" data-testid="shell-user-role-badge">{user?.role}</Badge>
              </div>
            </div>

            <NotificationCenter user={user} />

            <div className="rounded-3xl border border-border bg-white/75 p-4" data-testid="shell-theme-card">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.24em] text-[#5f7464]">Workspace theme</p>
                  <p className="mt-1 text-sm text-[#41534a]" data-testid="shell-theme-state">{isDark ? "Dark mode active" : "Default mode active"}</p>
                </div>
                <Button onClick={toggleTheme} type="button" variant="outline" className="rounded-full border-[#243e36]/10 bg-white text-[#243e36] hover:bg-[#edf0e7]" data-testid="shell-theme-toggle-button">
                  {isDark ? <SunMedium className="mr-2 h-4 w-4" /> : <MoonStar className="mr-2 h-4 w-4" />}
                  {isDark ? "Default" : "Dark"}
                </Button>
              </div>
            </div>
          </div>

          <nav className="mt-8 space-y-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  data-testid={`nav-link-${item.label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
                  className={({ isActive }) => `flex items-center gap-3 rounded-2xl border px-4 py-3 text-sm font-semibold transition-all ${isActive ? "border-[#243e36] bg-white text-[#111815] shadow-sm" : "border-transparent bg-[#f0f1ea] text-[#41534a] hover:-translate-y-0.5 hover:border-border hover:bg-white"}`}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </NavLink>
              );
            })}
          </nav>

          <Button
            onClick={onLogout}
            variant="outline"
            className="mt-8 h-12 w-full rounded-2xl border-[#243e36]/15 bg-white text-[#243e36] hover:bg-[#edf0e7]"
            data-testid="shell-logout-button"
          >
            Sign out
          </Button>
        </aside>

        <div className="px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className="space-y-6"
          >
            {children}
          </motion.div>
        </div>
      </div>
    </div>
  );
}