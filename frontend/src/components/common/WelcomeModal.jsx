import { useState, useEffect } from "react";
import { ArrowRight, CheckCircle2, X } from "lucide-react";
import { Button } from "@/components/ui/button";

const ROLE_STEPS = {
  crew: [
    { title: "Capture field work", description: "Take at least 3 photos per job. GPS auto-locks for ±2m precision — wait for the green badge before submitting." },
    { title: "Report incidents or damage", description: "Use the Incident/Damage tab to log OSHA-relevant details with photos. This alerts supervisors immediately." },
    { title: "Log equipment maintenance", description: "Use the Equipment tab to submit pre/post service photos. Red-tag items trigger alerts to your PM and GM." },
    { title: "Check your standards", description: "Tap the Standards tab to review quality benchmarks for your division. These are set by management." },
  ],
  management: [
    { title: "Review crew submissions", description: "Head to the Review page to score submissions using rubric categories. Your scores feed into the calibration heatmap." },
    { title: "Launch rapid review", description: "Open the mobile swipe lane from the dashboard. Swipe right to pass, left to fail, up for exemplary. Comments are required for fail/exemplary ratings." },
    { title: "Import jobs via CSV", description: "Go to Jobs & Alignment to upload your job schedule. Required columns: job_id, job_name, service_type, truck_number. Division defaults to General if omitted." },
    { title: "Manage crew QR links", description: "Create and assign QR access codes for each crew. Each code links to a truck number and division for automatic job filtering." },
    { title: "Build standards library", description: "Create visual standards with checklists and training quizzes. Enable 'Training Mode' on any standard to include it in crew sessions." },
  ],
  owner: [
    { title: "Calibrate scores", description: "Your owner review follows management's first pass. The system tracks variance between your scores and theirs to surface calibration drift." },
    { title: "Manage rubric matrices", description: "Go to the Rubric Editor to create or tune grading factors per service type and division. Each category has a weight — weights must sum to 1.0." },
    { title: "Monitor repeat offenders", description: "The Repeat Offenders page shows crews with recurring issues across 30/90/240-day windows. Use this to trigger targeted training sessions." },
    { title: "Launch training sessions", description: "From Standards Library, assign quiz sessions to specific crews. Sessions use standards you've marked as training-enabled." },
    { title: "Export datasets", description: "Go to Exports to generate CSV or JSONL bundles. Use 'Owner Gold' to export only owner-approved training data for AI model tuning." },
    { title: "Track analytics", description: "The Analytics page shows crew score trends, submission volume, calibration heatmaps, and fail-reason frequency by period." },
  ],
};

function getStepsForUser(user) {
  if (!user) return [];
  if (user.role === "owner") return ROLE_STEPS.owner;
  if (user.title === "GM") return [...ROLE_STEPS.management, ...ROLE_STEPS.owner.slice(1, 3)];
  return ROLE_STEPS.management;
}

function getStorageKey(user) {
  return `sarver_welcome_dismissed_${user?.id || "unknown"}`;
}

export default function WelcomeModal({ user }) {
  const [visible, setVisible] = useState(false);
  const [step, setStep] = useState(0);

  const steps = getStepsForUser(user);
  const storageKey = getStorageKey(user);

  useEffect(() => {
    if (!user) return;
    const dismissed = localStorage.getItem(storageKey);
    if (!dismissed) setVisible(true);
  }, [user, storageKey]);

  const dismiss = () => {
    localStorage.setItem(storageKey, "true");
    setVisible(false);
  };

  if (!visible || !steps.length) return null;

  const current = steps[step];
  const isLast = step === steps.length - 1;
  const roleLabel = user?.role === "owner" ? "Owner" : user?.title || "Management";

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 px-4" data-testid="welcome-modal-overlay">
      <div className="w-full max-w-md overflow-hidden rounded-[28px] border border-border/80 bg-white shadow-2xl" data-testid="welcome-modal">
        <div className="relative bg-[#243e36] px-6 py-5 text-white">
          <button type="button" onClick={dismiss} className="absolute right-4 top-4 rounded-full p-1 text-white/60 transition hover:text-white" data-testid="welcome-modal-close">
            <X className="h-4 w-4" />
          </button>
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#d8f3dc]">Welcome, {user?.name || roleLabel}</p>
          <h2 className="mt-1 font-[Cabinet_Grotesk] text-2xl font-black tracking-tight">Sarver QA System</h2>
          <p className="mt-1 text-sm text-white/70">{roleLabel} workflow guide — {steps.length} steps</p>
        </div>

        <div className="px-6 py-5">
          <div className="flex items-start gap-3">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#243e36] text-xs font-bold text-white">{step + 1}</span>
            <div>
              <h3 className="font-semibold text-[#111815]">{current.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-[#5c6d64]">{current.description}</p>
            </div>
          </div>

          <div className="mt-5 flex items-center gap-1.5">
            {steps.map((_, i) => (
              <div key={i} className={`h-1.5 flex-1 rounded-full transition-colors ${i <= step ? "bg-[#243e36]" : "bg-[#dde4d6]"}`} />
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between border-t border-border/60 px-6 py-4">
          <Button type="button" variant="ghost" onClick={dismiss} className="text-sm text-[#5c6d64]" data-testid="welcome-modal-skip">
            Skip tour
          </Button>
          <div className="flex gap-2">
            {step > 0 && (
              <Button type="button" variant="outline" onClick={() => setStep(step - 1)} className="rounded-xl border-[#243e36]/15 text-sm" data-testid="welcome-modal-prev">
                Back
              </Button>
            )}
            {isLast ? (
              <Button type="button" onClick={dismiss} className="rounded-xl bg-[#243e36] text-sm hover:bg-[#1a2c26]" data-testid="welcome-modal-finish">
                <CheckCircle2 className="mr-1.5 h-4 w-4" />Get started
              </Button>
            ) : (
              <Button type="button" onClick={() => setStep(step + 1)} className="rounded-xl bg-[#243e36] text-sm hover:bg-[#1a2c26]" data-testid="welcome-modal-next">
                Next<ArrowRight className="ml-1.5 h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
