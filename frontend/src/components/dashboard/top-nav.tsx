import { cn } from "@/lib/utils";
import { PulseDot } from "./pulse-dot";
import { LiveClock } from "./live-clock";
import type { DashboardView } from "@/types/dashboard";

interface TopNavProps {
  activeView: DashboardView;
  onViewChange: (view: DashboardView) => void;
  memberCount: number;
}

const VIEW_LABELS: Record<DashboardView, string> = {
  vorstand: "Vorstand",
  schatzmeister: "Schatzmeister",
  spartenleiter: "Spartenleiter",
};

const VIEWS: DashboardView[] = ["vorstand", "schatzmeister", "spartenleiter"];

export function TopNav({ activeView, onViewChange, memberCount }: TopNavProps) {
  return (
    <div className="sticky top-0 z-50 flex h-14 items-center justify-between border-b border-border bg-card px-4">
      {/* Logo */}
      <div className="flex items-center gap-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-gradient-to-br from-[#3b82f6] to-[#a855f7] text-sm font-bold text-white">
          K
        </div>
        <span className="text-sm font-semibold text-foreground">
          klubdenker.com
        </span>
      </div>

      {/* View Switcher */}
      <div className="flex items-center rounded-lg bg-muted p-0.5">
        {VIEWS.map((view) => (
          <button
            key={view}
            onClick={() => onViewChange(view)}
            className={cn(
              "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
              activeView === view
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            {VIEW_LABELS[view]}
          </button>
        ))}
      </div>

      {/* Status */}
      <div className="flex items-center gap-3">
        <PulseDot />
        <LiveClock />
        <span className="tabular-nums text-xs text-muted-foreground">
          {memberCount} Mitglieder
        </span>
      </div>
    </div>
  );
}
