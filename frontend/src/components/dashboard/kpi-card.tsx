import { type KeyboardEvent } from "react";
import { useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";
import { ArrowUp, ArrowDown } from "lucide-react";
import { SEMANTIC_COLORS } from "@/constants/design";

interface KpiCardProps {
  label: string;
  value: string;
  trend?: number;
  trendLabel?: string;
  subtitle?: string;
  accentColor?: string;
  className?: string;
  onClick?: () => void;
  href?: string;
}

export function KpiCard({
  label,
  value,
  trend,
  trendLabel,
  subtitle,
  accentColor = SEMANTIC_COLORS.info,
  className,
  onClick,
  href,
}: KpiCardProps) {
  const navigate = useNavigate();
  const isPositive = trend !== undefined && trend >= 0;
  const isInteractive = !!href || !!onClick;

  function handleClick() {
    if (!isInteractive) return;
    if (href) {
      navigate(href);
    } else if (onClick) {
      onClick();
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    if (!isInteractive) return;
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      handleClick();
    }
  }

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-xl border border-border bg-card p-4 shadow-sm",
        isInteractive &&
          "cursor-pointer hover:shadow-md hover:border-border transition-all",
        className
      )}
      onClick={isInteractive ? handleClick : undefined}
      onKeyDown={isInteractive ? handleKeyDown : undefined}
      role={isInteractive ? "button" : undefined}
      tabIndex={isInteractive ? 0 : undefined}
    >
      {/* Gradient top accent line */}
      <div
        className="absolute left-0 right-0 top-0 h-[2px]"
        style={{
          background: `linear-gradient(90deg, ${accentColor}, ${accentColor}88)`,
        }}
      />

      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 tabular-nums text-3xl font-bold leading-tight text-foreground">
        {value}
      </p>
      {subtitle && (
        <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>
      )}
      {trend !== undefined && (
        <div className="mt-1 flex items-center gap-1">
          <span
            className={cn(
              "flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-xs font-medium tabular-nums",
              isPositive
                ? "bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-400"
                : "bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-400"
            )}
          >
            {isPositive ? (
              <ArrowUp className="h-3 w-3" />
            ) : (
              <ArrowDown className="h-3 w-3" />
            )}
            {Math.abs(trend).toFixed(1)}%
          </span>
          {trendLabel && (
            <span className="text-xs text-muted-foreground">
              {trendLabel}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
