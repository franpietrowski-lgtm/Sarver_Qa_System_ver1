import { useEffect, useState } from "react";
import { ArrowRight, KeyRound, QrCode, ShieldCheck, Users } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { publicGet } from "@/lib/api";


const LOGO_URL = "https://sarverlandscape.com/wp-content/uploads/2024/10/sarver-logo.png";


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
  const [mode, setMode] = useState("admin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [crewLinks, setCrewLinks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showRecovery, setShowRecovery] = useState(false);

  useEffect(() => {
    if (authUser) navigate("/dashboard");
  }, [authUser, navigate]);

  useEffect(() => {
    publicGet("/public/crew-access").then(setCrewLinks).catch(() => setCrewLinks([]));
  }, []);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    try {
      await onLogin(email, password);
      toast.success("Welcome back — dashboard ready.");
      navigate("/dashboard");
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 overflow-hidden bg-[radial-gradient(circle_at_top_left,_rgba(216,243,220,0.85),_transparent_34%),linear-gradient(180deg,_#f5f7f5_0%,_#e8ece7_100%)]" data-testid="login-start-screen">
      <div className="flex h-full items-stretch">
        {/* Left hero panel */}
        <section className="relative hidden flex-1 overflow-hidden bg-[linear-gradient(140deg,_#204028_0%,_#2d5a27_42%,_#456b39_100%)] text-white lg:flex lg:flex-col" data-testid="login-hero-panel">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(255,255,255,0.22),_transparent_34%),radial-gradient(circle_at_70%_20%,_rgba(255,255,255,0.12),_transparent_26%)]" />
          <GrassBackdrop />
          <div className="relative flex flex-1 flex-col justify-center px-10 py-8 xl:px-14">
            <img src={LOGO_URL} alt="Sarver Landscape" className="h-10 w-auto object-contain object-left" data-testid="login-brand-logo" />
            <p className="mt-5 text-[10px] font-bold uppercase tracking-[0.32em] text-[#d8f3dc]" data-testid="login-kicker-text">Sarver quality operating system</p>
            <h1 className="mt-3 max-w-lg font-[Outfit] text-4xl font-semibold leading-tight tracking-tight xl:text-5xl" data-testid="login-page-title">Character, quality, and respect in every crew, every site.</h1>
            <p className="mt-4 max-w-md text-sm leading-relaxed text-white/70" data-testid="login-page-description">One living QA workflow for field capture, admin review, and training data.</p>
          </div>
        </section>

        {/* Right access panel */}
        <section className="flex w-full flex-col lg:w-[460px] lg:shrink-0 xl:w-[500px]">
          {/* Mobile logo bar */}
          <div className="flex items-center gap-3 px-6 pt-6 lg:hidden">
            <img src={LOGO_URL} alt="Sarver Landscape" className="h-8 w-auto" />
            <span className="text-xs font-bold uppercase tracking-widest text-[#5f7464]">Quality OS</span>
          </div>

          {/* Mode selector */}
          <div className="shrink-0 px-6 pt-6" data-testid="login-mode-selector">
            <div className="flex rounded-2xl bg-[#edf0e7] p-1">
              <button
                type="button"
                onClick={() => setMode("admin")}
                className={`flex flex-1 items-center justify-center gap-2 rounded-xl py-3 text-sm font-semibold transition ${mode === "admin" ? "bg-[#243e36] text-white shadow-sm" : "text-[#5c6d64]"}`}
                data-testid="login-mode-admin"
              >
                <ShieldCheck className="h-4 w-4" />Admin
              </button>
              <button
                type="button"
                onClick={() => setMode("crew")}
                className={`flex flex-1 items-center justify-center gap-2 rounded-xl py-3 text-sm font-semibold transition ${mode === "crew" ? "bg-[#243e36] text-white shadow-sm" : "text-[#5c6d64]"}`}
                data-testid="login-mode-crew"
              >
                <Users className="h-4 w-4" />Crew
              </button>
            </div>
          </div>

          {/* Content area */}
          <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-6 pb-6 pt-5">
            {mode === "admin" ? (
              <Card className="flex-1 rounded-[28px] border-border/80 bg-white/95 shadow-sm" data-testid="login-form-card">
                <CardContent className="flex h-full flex-col p-6 sm:p-8">
                  <div className="mb-5">
                    <p className="text-[10px] font-bold uppercase tracking-[0.28em] text-[#5f7464]" data-testid="login-form-kicker">Admin access</p>
                    <h2 className="mt-2 font-[Outfit] text-2xl font-semibold tracking-tight text-[#111815]" data-testid="login-form-title">Sign in</h2>
                    <p className="mt-1 text-xs text-[#5c6d64]">Use your assigned credentials to access the dashboard.</p>
                  </div>

                  <form onSubmit={handleSubmit} className="flex flex-1 flex-col gap-4" data-testid="login-form">
                    <div>
                      <label className="mb-1.5 block text-xs font-semibold text-[#243e36]" htmlFor="email">Email</label>
                      <Input id="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="LastFirst.Role@SLMCo.local" className="h-11 rounded-xl border-transparent bg-[#edf0e7] text-sm" data-testid="login-email-input" />
                    </div>
                    <div>
                      <div className="mb-1.5 flex items-center justify-between">
                        <label className="block text-xs font-semibold text-[#243e36]" htmlFor="password">Password</label>
                        <button type="button" onClick={() => setShowRecovery((c) => !c)} className="text-xs font-semibold text-[#2d5a27] hover:underline" data-testid="login-forgot-link">Forgot?</button>
                      </div>
                      <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="h-11 rounded-xl border-transparent bg-[#edf0e7] text-sm" data-testid="login-password-input" />
                    </div>
                    {showRecovery && (
                      <div className="rounded-xl border border-[#d3dcd0] bg-[#f5f7f5] p-3" data-testid="login-recovery-card">
                        <div className="flex items-start gap-2">
                          <KeyRound className="mt-0.5 h-3.5 w-3.5 text-[#2d5a27]" />
                          <p className="text-xs text-[#41534a]">Contact your GM or system administrator for password recovery.</p>
                        </div>
                      </div>
                    )}
                    <div className="mt-auto">
                      <Button type="submit" disabled={loading} className="h-11 w-full rounded-xl bg-[#243e36] text-sm text-white hover:bg-[#1a2c26]" data-testid="login-submit-button">
                        {loading ? "Signing in..." : "Sign in"}
                      </Button>
                    </div>
                  </form>
                </CardContent>
              </Card>
            ) : (
              <Card className="flex-1 rounded-[28px] border-border/80 bg-[#edf0e7] shadow-sm" data-testid="login-crew-access-card">
                <CardContent className="flex h-full flex-col p-6 sm:p-8">
                  <div className="mb-5 flex items-start justify-between gap-3">
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-[0.28em] text-[#5f7464]" data-testid="login-crew-access-kicker">Crew access</p>
                      <h2 className="mt-2 font-[Outfit] text-2xl font-semibold tracking-tight text-[#111815]" data-testid="login-crew-access-title">Select your crew</h2>
                      <p className="mt-1 text-xs text-[#5c6d64]">Tap your crew to open the capture portal. No password needed.</p>
                    </div>
                    <QrCode className="h-5 w-5 shrink-0 text-[#243e36]" />
                  </div>

                  <div className="flex-1 space-y-2 overflow-y-auto" data-testid="login-crew-list">
                    {crewLinks.map((link) => (
                      <button
                        key={link.id}
                        type="button"
                        className="flex w-full items-center justify-between rounded-xl border border-white/60 bg-white/80 px-4 py-3 text-left transition hover:bg-white"
                        onClick={() => navigate(`/crew/${link.code}`)}
                        data-testid={`crew-access-button-${link.code}`}
                      >
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-[#243e36]" data-testid={`crew-access-label-${link.code}`}>{link.label}</p>
                          <p className="mt-0.5 truncate text-xs text-[#5c6d64]" data-testid={`crew-access-meta-${link.code}`}>{link.truck_number} &middot; {link.division}</p>
                        </div>
                        <ArrowRight className="h-4 w-4 shrink-0 text-[#243e36]" />
                      </button>
                    ))}
                    {crewLinks.length === 0 && (
                      <div className="py-8 text-center text-sm text-[#5c6d64]">No active crew links available.</div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
