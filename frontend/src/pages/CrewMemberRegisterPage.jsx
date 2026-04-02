import { useEffect, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { CheckCircle2, Copy, UserPlus } from "lucide-react";
import { useParams } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { getApiOrigin, publicGet, publicPost } from "@/lib/api";
import { toast } from "sonner";

const DIVISIONS = ["Maintenance", "Install", "Tree", "Plant Healthcare", "Winter Services"];

export default function CrewMemberRegisterPage() {
  const { parentCode } = useParams();
  const [crewLink, setCrewLink] = useState(null);
  const [name, setName] = useState("");
  const [division, setDivision] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [registered, setRegistered] = useState(null);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const link = await publicGet(`/public/crew-access/${parentCode}`);
        setCrewLink(link);
        setDivision(link.division || DIVISIONS[0]);
      } catch {
        setLoadError("This crew link is invalid or has been deactivated.");
      }
    };
    load();
  }, [parentCode]);

  const dashboardUrl = registered
    ? `${window.location.origin}/member/${registered.code}`
    : "";

  const handleRegister = async (e) => {
    e.preventDefault();
    if (!name.trim()) {
      toast.error("Please enter your name.");
      return;
    }
    setSubmitting(true);
    try {
      const result = await publicPost("/public/crew-members/register", {
        name: name.trim(),
        division,
        parent_access_code: parentCode,
      });
      setRegistered(result);
      toast.success("You're registered! Save your QR code below.");
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Registration failed");
    } finally {
      setSubmitting(false);
    }
  };

  const copyLink = () => {
    navigator.clipboard.writeText(dashboardUrl);
    toast.success("Dashboard link copied!");
  };

  if (loadError) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[linear-gradient(180deg,_#f6f6f2_0%,_#edf0e7_100%)] px-4">
        <Card className="max-w-md rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="member-register-error-card">
          <CardContent className="p-8 text-center">
            <p className="text-lg font-semibold text-[#243e36]">Link Unavailable</p>
            <p className="mt-2 text-sm text-[#5c6d64]">{loadError}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (registered) {
    return (
      <div className="min-h-screen bg-[linear-gradient(180deg,_#f6f6f2_0%,_#edf0e7_100%)] px-4 py-8">
        <div className="mx-auto max-w-md space-y-5">
          <Card className="overflow-hidden rounded-[32px] border-border/80 bg-[#243e36] text-white shadow-sm" data-testid="member-register-success-card">
            <CardContent className="p-6 text-center">
              <CheckCircle2 className="mx-auto h-12 w-12 text-[#d8f3dc]" />
              <h1 className="mt-4 font-[Cabinet_Grotesk] text-3xl font-black tracking-tight" data-testid="member-register-success-title">You're all set, {registered.name}!</h1>
              <p className="mt-2 text-sm text-white/80">Save this QR code — it's your personal dashboard pass.</p>
              <div className="mt-3 flex flex-wrap justify-center gap-2">
                <Badge className="border-0 bg-white/12 px-3 py-1 text-white">{registered.parent_crew_label}</Badge>
                <Badge className="border-0 bg-white/12 px-3 py-1 text-white">{registered.division}</Badge>
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="member-qr-card">
            <CardContent className="flex flex-col items-center p-8">
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#5f7464]">Your personal QR code</p>
              <div className="mt-5 rounded-[24px] border-2 border-[#edf0e7] bg-white p-5" data-testid="member-qr-wrapper">
                <QRCodeSVG
                  value={dashboardUrl}
                  size={220}
                  level="H"
                  bgColor="#ffffff"
                  fgColor="#243e36"
                  data-testid="member-qr-svg"
                />
              </div>
              <p className="mt-4 text-center text-sm font-semibold text-[#243e36]" data-testid="member-name-display">{registered.name}</p>
              <p className="text-xs text-[#5c6d64]">{registered.division} — {registered.parent_crew_label}</p>

              <Button
                onClick={copyLink}
                variant="outline"
                className="mt-5 h-12 w-full rounded-2xl border-[#243e36]/15 bg-white text-[#243e36] hover:bg-[#edf0e7]"
                data-testid="member-copy-link-button"
              >
                <Copy className="mr-2 h-4 w-4" /> Copy dashboard link
              </Button>

              <p className="mt-4 rounded-[16px] bg-[#f6f6f2] px-4 py-3 text-center text-xs text-[#5c6d64]" data-testid="member-save-hint">
                Screenshot this QR code or bookmark the link. You'll use it every time you open your dashboard.
              </p>
            </CardContent>
          </Card>

          <Button
            onClick={() => window.open(dashboardUrl, "_self")}
            className="h-14 w-full rounded-[22px] bg-[#243e36] text-base font-semibold text-white hover:bg-[#1a2c26]"
            data-testid="member-go-to-dashboard-button"
          >
            Open my dashboard
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,_#f6f6f2_0%,_#edf0e7_100%)] px-4 py-8">
      <div className="mx-auto max-w-md space-y-5">
        <Card className="overflow-hidden rounded-[32px] border-border/80 bg-[#243e36] text-white shadow-sm" data-testid="member-register-header-card">
          <CardContent className="p-6">
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#d8f3dc]" data-testid="member-register-kicker">Sarver Landscape</p>
            <h1 className="mt-3 font-[Cabinet_Grotesk] text-4xl font-black tracking-tight" data-testid="member-register-title">Crew Member Registration</h1>
            <p className="mt-3 text-sm text-white/80" data-testid="member-register-subtitle">
              Enter your name and division to get your personal QR code for capturing work, viewing standards, and completing training.
            </p>
            {crewLink && (
              <div className="mt-4 flex flex-wrap gap-2">
                <Badge className="border-0 bg-white/12 px-3 py-1 text-white" data-testid="member-register-crew-badge">{crewLink.label}</Badge>
                <Badge className="border-0 bg-white/12 px-3 py-1 text-white" data-testid="member-register-truck-badge">{crewLink.truck_number}</Badge>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="rounded-[32px] border-border/80 bg-white/95 shadow-sm" data-testid="member-register-form-card">
          <CardContent className="p-6">
            <form onSubmit={handleRegister} className="space-y-5" data-testid="member-register-form">
              <div className="space-y-2">
                <label className="text-sm font-semibold text-[#243e36]" htmlFor="member-name-input">Your full name</label>
                <Input
                  id="member-name-input"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. John Smith"
                  className="h-12 rounded-2xl border-transparent bg-[#edf0e7]"
                  data-testid="member-name-input"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-semibold text-[#243e36]" htmlFor="member-division-select">Division</label>
                <select
                  id="member-division-select"
                  value={division}
                  onChange={(e) => setDivision(e.target.value)}
                  className="h-12 w-full rounded-2xl border border-transparent bg-[#edf0e7] px-4 text-sm"
                  data-testid="member-division-select"
                >
                  {DIVISIONS.map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
              <Button
                type="submit"
                disabled={submitting || !name.trim()}
                className="h-14 w-full rounded-[22px] bg-[#243e36] text-base font-semibold text-white hover:bg-[#1a2c26]"
                data-testid="member-register-submit-button"
              >
                <UserPlus className="mr-2 h-5 w-5" />
                {submitting ? "Registering..." : "Register & get my QR code"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
