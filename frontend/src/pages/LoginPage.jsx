import { useEffect, useState } from "react";
import { ArrowRight, BadgeCheck, KeyRound, QrCode, ShieldCheck, Truck } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { publicGet } from "@/lib/api";


const LOGO_URL = "https://sarverlandscape.com/wp-content/uploads/2024/10/sarver-logo.png";
const LAST_ROLE_KEY = "field-quality-last-role";
const ROLE_PRESETS = {
  "Production Manager": { email: "production.manager@fieldquality.local", password: "FieldQA123!" },
  Owner: { email: "owner@fieldquality.local", password: "FieldQA123!" },
  GM: { email: "gm@fieldquality.local", password: "FieldQA123!" },
};


function GrassBackdrop() {
  return (
    <svg viewBox="0 0 1200 480" className="absolute inset-x-0 bottom-0 h-[62%] w-full opacity-70 blur-[2px]" aria-hidden="true" data-testid="login-grass-backdrop">
      {[
        { x: 80, h: 210, c: "rgba(169, 209, 156, 0.38)", cls: "login-grass-blade" },
        { x: 180, h: 240, c: "rgba(143, 188, 122, 0.32)", cls: "login-grass-blade login-grass-blade--slow" },
        { x: 320, h: 220, c: "rgba(110, 160, 92, 0.3)", cls: "login-grass-blade login-grass-blade--fast" },
        { x: 470, h: 250, c: "rgba(163, 204, 152, 0.35)", cls: "login-grass-blade" },
        { x: 640, h: 215, c: "rgba(126, 181, 106, 0.33)", cls: "login-grass-blade login-grass-blade--slow" },
        { x: 810, h: 240, c: "rgba(152, 199, 134, 0.34)", cls: "login-grass-blade login-grass-blade--fast" },
        { x: 990, h: 225, c: "rgba(110, 160, 92, 0.28)", cls: "login-grass-blade" },
        { x: 1120, h: 200, c: "rgba(169, 209, 156, 0.32)", cls: "login-grass-blade login-grass-blade--slow" },
      ].map((blade, index) => (
        <path
          key={`grass-blade-${index}`}
          d={`M ${blade.x} 480 C ${blade.x - 16} ${420 - blade.h * 0.2}, ${blade.x + 18} ${340 - blade.h * 0.5}, ${blade.x - 2} ${480 - blade.h}`}
          stroke={blade.c}
          strokeWidth="18"
          strokeLinecap="round"
          fill="none"
          className={blade.cls}
        />
      ))}
    </svg>
  );
}


export default function LoginPage({ onLogin, authUser }) {
  const navigate = useNavigate();
  const [email, setEmail] = useState(ROLE_PRESETS["Production Manager"].email);
  const [password, setPassword] = useState(ROLE_PRESETS["Production Manager"].password);
  const [selectedRole, setSelectedRole] = useState("Production Manager");
  const [crewLinks, setCrewLinks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showRecovery, setShowRecovery] = useState(false);

  useEffect(() => {
    if (authUser) {
      navigate("/dashboard");
    }
  }, [authUser, navigate]);

  useEffect(() => {
    const rememberedRole = localStorage.getItem(LAST_ROLE_KEY);
    if (rememberedRole && ROLE_PRESETS[rememberedRole]) {
      setSelectedRole(rememberedRole);
      setEmail(ROLE_PRESETS[rememberedRole].email);
      setPassword(ROLE_PRESETS[rememberedRole].password);
    }
  }, []);

  useEffect(() => {
    publicGet("/public/crew-access")
      .then(setCrewLinks)
      .catch(() => setCrewLinks([]));
  }, []);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    try {
      const result = await onLogin(email, password);
      const matchedRole = Object.entries(ROLE_PRESETS).find(([, credentials]) => credentials.email === email)?.[0] || result.user?.title || result.user?.role;
      localStorage.setItem(LAST_ROLE_KEY, matchedRole);
      toast.success("Welcome back — dashboard ready.");
      navigate("/dashboard");
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,_rgba(216,243,220,0.85),_transparent_34%),linear-gradient(180deg,_#f5f7f5_0%,_#e8ece7_100%)] px-4 py-6 sm:px-6 lg:px-8" data-testid="login-start-screen">
      <div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-[1.05fr_0.95fr]">
        <section className="relative overflow-hidden rounded-[36px] border border-[#d3dcd0] bg-[linear-gradient(140deg,_#204028_0%,_#2d5a27_42%,_#456b39_100%)] p-8 text-white shadow-sm sm:p-10" data-testid="login-hero-panel">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(255,255,255,0.22),_transparent_34%),radial-gradient(circle_at_70%_20%,_rgba(255,255,255,0.12),_transparent_26%)]" />
          <GrassBackdrop />
          <div className="relative space-y-8">
            <div>
              <img src={LOGO_URL} alt="Sarver Landscape" className="h-12 w-auto object-contain" data-testid="login-brand-logo" />
              <p className="mt-4 text-xs font-bold uppercase tracking-[0.32em] text-[#d8f3dc]" data-testid="login-kicker-text">Sarver quality operating system</p>
              <h1 className="mt-4 max-w-xl font-[Outfit] text-5xl font-semibold tracking-tight text-white sm:text-6xl" data-testid="login-page-title">Welcome crews, admins, and owners into one living QA workflow.</h1>
              <p className="mt-4 max-w-2xl text-sm leading-6 text-white/80 sm:text-base" data-testid="login-page-description">Field capture stays fast. Review stays sharp. Training data stays usable. This start screen keeps the brand grounded in landscape motion with a focused access point for every role.</p>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              {[
                { icon: Truck, label: "Crew capture", value: "Fast mobile proof" },
                { icon: ShieldCheck, label: "Review control", value: "Rapid + standard QA" },
                { icon: QrCode, label: "Access model", value: "Persistent crew identity" },
              ].map((item) => {
                const Icon = item.icon;
                return (
                  <div key={item.label} className="rounded-3xl border border-white/15 bg-white/10 p-5 backdrop-blur-sm" data-testid={`login-highlight-${item.label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
                    <Icon className="h-5 w-5 text-[#d8f3dc]" />
                    <p className="mt-4 text-sm text-white/70">{item.label}</p>
                    <p className="mt-1 text-xl font-semibold text-white">{item.value}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        <section className="space-y-6">
          <Card className="rounded-[36px] border-border/80 bg-white/95 shadow-sm" data-testid="login-form-card">
            <CardContent className="p-8 sm:p-10">
              <div className="mb-8">
                <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]" data-testid="login-form-kicker">Start screen</p>
                <h2 className="mt-3 font-[Outfit] text-4xl font-semibold tracking-tight text-[#111815]" data-testid="login-form-title">Standard sign-in</h2>
                <p className="mt-3 text-sm text-[#5c6d64]" data-testid="login-form-description">Use a standard user and password pair. The last successful role preset is remembered for the next visit.</p>
              </div>

              <div className="mb-6 flex flex-wrap gap-2" data-testid="login-role-preset-group">
                {Object.keys(ROLE_PRESETS).map((role) => (
                  <button
                    key={role}
                    type="button"
                    onClick={() => {
                      setSelectedRole(role);
                      setEmail(ROLE_PRESETS[role].email);
                      setPassword(ROLE_PRESETS[role].password);
                    }}
                    className={`rounded-full px-4 py-2 text-sm font-semibold transition-transform hover:-translate-y-0.5 ${selectedRole === role ? "bg-[#243e36] text-white" : "bg-[#edf0e7] text-[#243e36]"}`}
                    data-testid={`login-role-preset-${role.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
                  >
                    {role}
                  </button>
                ))}
              </div>

              <form onSubmit={handleSubmit} className="space-y-4" data-testid="login-form">
                <div>
                  <label className="mb-2 block text-sm font-semibold text-[#243e36]" htmlFor="email">User</label>
                  <Input id="email" value={email} onChange={(event) => setEmail(event.target.value)} className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="login-email-input" />
                </div>
                <div>
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <label className="block text-sm font-semibold text-[#243e36]" htmlFor="password">Pass</label>
                    <button type="button" onClick={() => setShowRecovery((current) => !current)} className="text-sm font-semibold text-[#2d5a27] underline-offset-4 hover:underline" data-testid="login-forgot-link">Forgot user/pass?</button>
                  </div>
                  <Input id="password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="login-password-input" />
                </div>
                {showRecovery && (
                  <div className="rounded-[24px] border border-[#d3dcd0] bg-[#f5f7f5] p-4" data-testid="login-recovery-card">
                    <div className="flex items-start gap-3">
                      <KeyRound className="mt-0.5 h-4 w-4 text-[#2d5a27]" />
                      <div className="text-sm text-[#41534a]">
                        <p className="font-semibold text-[#243e36]">Access recovery</p>
                        <p className="mt-1">For this internal preview, GM and Production Manager demo access remain available as fallback access so the team is not locked out.</p>
                      </div>
                    </div>
                  </div>
                )}
                <Button type="submit" disabled={loading} className="h-12 w-full rounded-2xl bg-[#243e36] text-white hover:bg-[#1a2c26]" data-testid="login-submit-button">
                  {loading ? "Signing in..." : "Submit"}
                </Button>
              </form>

              <div className="mt-6 flex items-center gap-2 rounded-[24px] bg-[#edf0e7] px-4 py-3 text-sm text-[#41534a]" data-testid="login-role-memory-hint">
                <BadgeCheck className="h-4 w-4 text-[#2d5a27]" />
                Last role memory: <span className="font-semibold text-[#243e36]">{selectedRole}</span>
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-[36px] border-border/80 bg-[#edf0e7] shadow-sm" data-testid="login-crew-access-card">
            <CardContent className="p-8">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]" data-testid="login-crew-access-kicker">Crew access</p>
                  <h3 className="mt-2 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight text-[#111815]" data-testid="login-crew-access-title">Jump into a QR-ready crew portal</h3>
                </div>
                <QrCode className="h-6 w-6 text-[#243e36]" />
              </div>

              <div className="mt-6 space-y-3">
                {crewLinks.map((link) => (
                  <button
                    key={link.id}
                    type="button"
                    className="flex w-full items-center justify-between rounded-3xl border border-white/60 bg-white/80 px-5 py-4 text-left transition-transform hover:-translate-y-0.5"
                    onClick={() => navigate(`/crew/${link.code}`)}
                    data-testid={`crew-access-button-${link.code}`}
                  >
                    <div>
                      <p className="text-sm font-semibold text-[#243e36]" data-testid={`crew-access-label-${link.code}`}>{link.label}</p>
                      <p className="mt-1 text-sm text-[#5c6d64]" data-testid={`crew-access-meta-${link.code}`}>{link.truck_number} · {link.division}</p>
                    </div>
                    <ArrowRight className="h-4 w-4 text-[#243e36]" />
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        </section>
      </div>
    </div>
  );
}