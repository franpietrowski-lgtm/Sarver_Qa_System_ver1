import { useEffect, useState } from "react";
import { ArrowRight, QrCode, ShieldCheck, Truck } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { publicGet } from "@/lib/api";


const HERO_IMAGE = "https://images.unsplash.com/photo-1772816037169-4daa98b83098?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85";


export default function LoginPage({ onLogin, authUser }) {
  const navigate = useNavigate();
  const [email, setEmail] = useState("management@fieldquality.local");
  const [password, setPassword] = useState("FieldQA123!");
  const [crewLinks, setCrewLinks] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (authUser) {
      navigate("/dashboard");
    }
  }, [authUser, navigate]);

  useEffect(() => {
    publicGet("/public/crew-access")
      .then(setCrewLinks)
      .catch(() => setCrewLinks([]));
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
    <div className="min-h-screen bg-[#f6f6f2] px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-[1.05fr_0.95fr]">
        <section className="relative overflow-hidden rounded-[36px] border border-border bg-[#243e36] p-8 text-white shadow-sm sm:p-10" data-testid="login-hero-panel">
          <img src={HERO_IMAGE} alt="Grass background" className="absolute inset-0 h-full w-full object-cover opacity-25" data-testid="login-hero-image" />
          <div className="absolute inset-0 bg-[linear-gradient(135deg,_rgba(17,24,21,0.86),_rgba(36,62,54,0.58))]" />
          <div className="relative space-y-8">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.32em] text-[#d8f3dc]" data-testid="login-kicker-text">Landscaping QA Pipeline</p>
              <h1 className="mt-4 max-w-xl font-[Cabinet_Grotesk] text-5xl font-black tracking-tight text-white sm:text-6xl" data-testid="login-page-title">Capture field proof fast. Review it with training-grade structure.</h1>
              <p className="mt-4 max-w-2xl text-sm leading-6 text-white/80 sm:text-base" data-testid="login-page-description">Crews submit from unique QR links, management scores against versioned rubrics, and owner calibration prepares clean datasets for future AI inspection models.</p>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              {[
                { icon: Truck, label: "Crew capture", value: "30 sec target" },
                { icon: ShieldCheck, label: "Review control", value: "Role-based QA" },
                { icon: QrCode, label: "Access model", value: "Unique QR crews" },
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
                <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]" data-testid="login-form-kicker">Admin access</p>
                <h2 className="mt-3 font-[Cabinet_Grotesk] text-4xl font-black tracking-tight text-[#111815]" data-testid="login-form-title">Management & owner sign-in</h2>
                <p className="mt-3 text-sm text-[#5c6d64]" data-testid="login-form-description">Demo credentials are preloaded so you can review the full system immediately.</p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4" data-testid="login-form">
                <div>
                  <label className="mb-2 block text-sm font-semibold text-[#243e36]" htmlFor="email">Email</label>
                  <Input id="email" value={email} onChange={(event) => setEmail(event.target.value)} className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="login-email-input" />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-semibold text-[#243e36]" htmlFor="password">Password</label>
                  <Input id="password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} className="h-12 rounded-2xl border-transparent bg-[#edf0e7]" data-testid="login-password-input" />
                </div>
                <Button type="submit" disabled={loading} className="h-12 w-full rounded-2xl bg-[#243e36] text-white hover:bg-[#1a2c26]" data-testid="login-submit-button">
                  {loading ? "Signing in..." : "Open operations workspace"}
                </Button>
              </form>
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