import { useState } from "react";
import { ChevronDown, Lightbulb, X } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

const GUIDE_CONTENT = {
  management: {
    title: "Management Quick Start",
    sections: [
      { heading: "Review queue", text: "Submissions appear in Review once crews upload. Score each category using the rubric, then set a disposition (pass, pass with notes, correction required)." },
      { heading: "Rapid review (mobile)", text: "Open the swipe lane from the dashboard QR code. Swipe right = standard, left = fail, up = exemplary. You must add comments on fail/exemplary swipes." },
      { heading: "CSV job import", text: "Upload a CSV with columns: job_id, job_name, property_name, address, service_type, scheduled_date, division, truck_number. The system auto-matches submissions to jobs." },
      { heading: "Crew QR links", text: "Each crew gets a unique QR code tied to their truck and division. Scanning the code opens the mobile capture portal — no login needed." },
    ],
  },
  owner: {
    title: "Owner Quick Start",
    sections: [
      { heading: "Calibration review", text: "After management scores a submission, you provide a second score. The system calculates variance to track calibration drift over time." },
      { heading: "Rubric matrices", text: "Edit grading factors in the Rubric Editor. Each service type has weighted categories (must sum to 1.0), a pass threshold, and hard-fail conditions." },
      { heading: "Training sessions", text: "Mark standards as training-enabled, then assign quiz sessions to specific crews. Results feed into the repeat offender tracking system." },
      { heading: "Data exports", text: "Generate CSV/JSONL exports from the Exports page. 'Owner Gold' only includes owner-approved records for AI training datasets." },
      { heading: "Analytics", text: "View crew score trends, submission volume, calibration heatmaps, and fail reasons. Filter by period (weekly/monthly/quarterly/yearly)." },
    ],
  },
  gm: {
    title: "GM Quick Start",
    sections: [
      { heading: "Your dual role", text: "As GM, you have management review access plus rubric editing and equipment red-tag forwarding. You bridge field operations and owner oversight." },
      { heading: "Rubric management", text: "Create and tune rubric matrices per service type and division. Categories need weights summing to 1.0 and a pass threshold percentage." },
      { heading: "Equipment red-tags", text: "When crews flag equipment with a red-tag note, you can forward it to the Owner for final disposition from the Equipment Logs page." },
      { heading: "Repeat offenders", text: "Monitor the Repeat Offenders page to identify crews with recurring quality issues. Use this data to assign targeted training sessions." },
    ],
  },
};

function getGuideForUser(user) {
  if (!user) return null;
  if (user.role === "owner") return GUIDE_CONTENT.owner;
  if (user.title === "GM") return GUIDE_CONTENT.gm;
  return GUIDE_CONTENT.management;
}

function getStorageKey(user) {
  return `sarver_guide_hidden_${user?.role || "unknown"}_${user?.title || "default"}`;
}

export default function GettingStartedPanel({ user }) {
  const storageKey = getStorageKey(user);
  const [hidden, setHidden] = useState(() => localStorage.getItem(storageKey) === "true");
  const [expanded, setExpanded] = useState(false);

  const guide = getGuideForUser(user);
  if (!guide || hidden) return null;

  const dismiss = () => {
    localStorage.setItem(storageKey, "true");
    setHidden(true);
  };

  return (
    <div className="rounded-[24px] border shadow-sm" style={{ borderColor: 'var(--panel-border)', background: `linear-gradient(to right, var(--panel-gradient-from), var(--panel-gradient-to))` }} data-testid="getting-started-panel">
      <div className="flex items-center justify-between gap-3 px-5 py-4">
        <button type="button" onClick={() => setExpanded(!expanded)} className="flex flex-1 items-center gap-3 text-left" data-testid="getting-started-toggle">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full" style={{ backgroundColor: 'var(--btn-accent)' }}>
            <Lightbulb className="h-4 w-4 text-white" />
          </div>
          <div className="min-w-0">
            <h3 className="font-semibold text-[#111815]">{guide.title}</h3>
            <p className="text-xs text-[#5c6d64]">{expanded ? "Click to collapse" : `${guide.sections.length} tips to get you up to speed`}</p>
          </div>
        </button>
        <div className="flex items-center gap-1.5">
          <ChevronDown className={`h-4 w-4 text-[#5c6d64] transition-transform ${expanded ? "rotate-180" : ""}`} />
          <button type="button" onClick={dismiss} className="rounded-full p-1 text-[#5c6d64] transition hover:bg-[#243e36]/10 hover:text-[#243e36]" data-testid="getting-started-dismiss" aria-label="Dismiss guide">
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.25, ease: "easeInOut" }} className="overflow-hidden">
            <div className="grid gap-3 px-5 pb-5 sm:grid-cols-2">
              {guide.sections.map((section, i) => (
                <div key={i} className="rounded-2xl border border-border/60 p-4" style={{ backgroundColor: 'var(--modal-bg)' }} data-testid={`getting-started-section-${i}`}>
                  <div className="flex items-center gap-2">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold text-white" style={{ backgroundColor: 'var(--btn-accent)' }}>{i + 1}</span>
                    <h4 className="text-sm font-semibold text-[#111815]">{section.heading}</h4>
                  </div>
                  <p className="mt-2 text-xs leading-relaxed text-[#5c6d64]">{section.text}</p>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
