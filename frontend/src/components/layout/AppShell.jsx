import { motion } from "framer-motion";
import { ChartColumn, ClipboardCheck, FileOutput, FileText, FolderInput, Grid3X3, LayoutDashboard, Radar, Settings, ShieldCheck, TrendingUp, Users } from "lucide-react";
import { NavLink } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import NotificationCenter from "@/components/common/NotificationCenter";
import { useTheme } from "@/components/theme/ThemeProvider";


const navigationByRole = {
  management: [
    { to: "/dashboard", label: "Overview", icon: LayoutDashboard },
    { to: "/client-report", label: "Client Report", icon: FileText },
    { to: "/jobs", label: "QJA", icon: FolderInput },
    { to: "/team-members", label: "Team Members", icon: Users },
    { to: "/review", label: "Review Queue", icon: ClipboardCheck },
    { to: "/rubric-editor", label: "Rubric Matrices", icon: Grid3X3 },
    { to: "/standards", label: "Standards Library", icon: ShieldCheck },
    { to: "/repeat-offenders", label: "Repeat Offenders", icon: Radar },
    { to: "/settings", label: "Settings", icon: Settings },
  ],
  owner: [
    { to: "/dashboard", label: "Overview", icon: LayoutDashboard },
    { to: "/client-report", label: "Client Report", icon: FileText },
    { to: "/owner", label: "Owner Review", icon: ShieldCheck },
    { to: "/team-members", label: "Team Members", icon: Users },
    { to: "/analytics", label: "Calibration", icon: ChartColumn },
    { to: "/reviewer-performance", label: "Reviewer Perf.", icon: TrendingUp },
    { to: "/rubric-editor", label: "Rubric Matrices", icon: Grid3X3 },
    { to: "/standards", label: "Standards Library", icon: ShieldCheck },
    { to: "/repeat-offenders", label: "Repeat Offenders", icon: Radar },
    { to: "/exports", label: "Exports", icon: FileOutput },
    { to: "/settings", label: "Settings", icon: Settings },
  ],
};


export default function AppShell({ user, onLogout, children }) {
  const roleKey = (user?.role || "").trim().toLowerCase();
  const navItems = (navigationByRole[roleKey] || []).filter((item) => {
    if (item.to === "/rubric-editor" && !["GM", "Owner"].includes(user?.title) && user?.role !== "owner") return false;
    return true;
  });
  const logoUrl = "https://sarverlandscape.com/wp-content/uploads/2024/10/sarver-logo.png";
  const { theme, fontPkg } = useTheme();
  const fontClass = fontPkg !== "brand" ? `font-${fontPkg}` : "";

  return (
    <div key={roleKey || "no-role"} className={`workspace-shell min-h-screen text-foreground theme-${theme} ${fontClass} ${theme === "default" ? "bg-[radial-gradient(circle_at_top_left,_rgba(124,169,130,0.18),_transparent_28%),linear-gradient(180deg,_#f6f6f2_0%,_#edf0e7_100%)]" : ""}`} data-testid="workspace-shell">
      <div className="grid min-h-screen lg:grid-cols-[280px_1fr]">
        <aside className="border-b border-border/80 bg-white/85 px-6 py-8 backdrop-blur-xl lg:border-b-0 lg:border-r">
          <div className="space-y-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]" data-testid="shell-kicker-text">Field Quality</p>
              <img src={logoUrl} alt="Sarver Landscape" className="mt-3 h-10 w-auto object-contain" data-testid="shell-brand-logo" />
              <h1 className="mt-3 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]" data-testid="shell-app-title">Quality Review</h1>
              <p className="mt-2 text-sm text-[#41534a]" data-testid="shell-app-subtitle">Character, quality, and respect across crew capture, review, and automation readiness.</p>
            </div>

            <div className="rounded-2xl border border-border bg-[#243e36] p-4 text-white shadow-sm" data-testid="shell-user-card">
              <p className="text-lg font-semibold" data-testid="shell-user-name">{user?.name}</p>
              <p className="text-sm text-white/70" data-testid="shell-user-title">{user?.title || user?.role}</p>
            </div>

            <NotificationCenter user={user} />
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