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
          <span className="text-gray-700">{label}</span>
          <span className="tabular-nums text-gray-500">
            {Math.round(percent)}%
          </span>
        </div>
      )}
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-100">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${percent}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}
