import { type KeyboardEvent } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, CheckCircle, Info, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { SEMANTIC_COLORS } from "@/constants/design";

interface AktionsKarteProps {
  title: string;
  description: string;
  variant: "action" | "warn" | "ok";
  onClick?: () => void;
  href?: string;
}

const VARIANT_CONFIG = {
  action: {
    color: SEMANTIC_COLORS.info,
    icon: Info,
    bg: "bg-blue-50",
    border: "border-blue-200",
  },
  warn: {
    color: SEMANTIC_COLORS.warning,
    icon: AlertTriangle,
    bg: "bg-amber-50",
    border: "border-amber-200",
  },
  ok: {
    color: SEMANTIC_COLORS.success,
    icon: CheckCircle,
    bg: "bg-emerald-50",
    border: "border-emerald-200",
  },
} as const;

export function AktionsKarte({
  title,
  description,
  variant,
  onClick,
  href,
}: AktionsKarteProps) {
  const navigate = useNavigate();
  const config = VARIANT_CONFIG[variant];
  const Icon = config.icon;
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
        "flex items-start gap-3 rounded-lg border p-3",
        config.bg,
        config.border,
        isInteractive &&
          "cursor-pointer transition-all hover:shadow-sm hover:brightness-95"
      )}
      onClick={isInteractive ? handleClick : undefined}
      onKeyDown={isInteractive ? handleKeyDown : undefined}
      role={isInteractive ? "button" : undefined}
      tabIndex={isInteractive ? 0 : undefined}
    >
      <Icon className="mt-0.5 h-4 w-4 shrink-0" style={{ color: config.color }} />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-gray-900">
          {title}
        </p>
        <p className="mt-0.5 text-xs text-gray-500">
          {description}
        </p>
      </div>
      {isInteractive && (
        <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-gray-400" />
      )}
    </div>
  );
}
