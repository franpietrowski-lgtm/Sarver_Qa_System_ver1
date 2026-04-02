import { HelpCircle } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

export function HelpPopover({ title, children, side = "bottom", align = "start", className = "" }) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          className={`inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#243e36]/8 text-[#243e36] transition hover:bg-[#243e36]/15 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#243e36]/30 ${className}`}
          data-testid="help-popover-trigger"
          aria-label={`Help: ${title}`}
        >
          <HelpCircle className="h-3.5 w-3.5" />
        </button>
      </PopoverTrigger>
      <PopoverContent side={side} align={align} className="w-80 rounded-2xl border-border/80 bg-white p-0 shadow-xl" data-testid="help-popover-content">
        <div className="border-b border-border/60 px-4 py-3">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#5f7464]">Guide</p>
          <h4 className="mt-0.5 font-semibold text-[#111815]">{title}</h4>
        </div>
        <div className="max-h-72 overflow-y-auto px-4 py-3 text-sm leading-relaxed text-[#3a4d40]">
          {children}
        </div>
      </PopoverContent>
    </Popover>
  );
}
