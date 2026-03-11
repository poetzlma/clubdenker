import { cn } from "@/lib/utils";
import { SEMANTIC_COLORS } from "@/constants/design";

interface ProgressBarProps {
  value: number;
  max?: number;
  color?: string;
  label?: string;
  showLabel?: boolean;
  showPercentage?: boolean;
  className?: string;
}

export function ProgressBar({
  value,
  max = 100,
  color = SEMANTIC_COLORS.info,
  className,
  showLabel,
  showPercentage,
  label,
}: ProgressBarProps) {
  const percent = Math.min(Math.max((value / max) * 100, 0), 100);

  return (
    <div className={cn("space-y-1", className)}>
      {(showLabel || label || showPercentage) && (
        <div className="flex items-center justify-between text-xs">
          <span className="text-foreground">{label}</span>
          <span className="tabular-nums text-muted-foreground">
            {Math.round(percent)}%
          </span>
        </div>
      )}
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${percent}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}
