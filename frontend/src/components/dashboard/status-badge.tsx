import { cn } from "@/lib/utils";
import { STATUS_COLORS, SPHERE_COLORS, PAYMENT_STATUS_COLORS } from "@/constants/design";

type StatusType = "member" | "sphere" | "payment";

interface StatusBadgeProps {
  status: string;
  type?: StatusType;
  className?: string;
}

export function StatusBadge({ status, type = "member", className }: StatusBadgeProps) {
  if (type === "payment") {
    const config = PAYMENT_STATUS_COLORS[status as keyof typeof PAYMENT_STATUS_COLORS];
    if (!config) return <span>{status}</span>;
    return (
      <span
        className={cn(
          "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
          className
        )}
        style={{
          backgroundColor: `${config.color}20`,
          color: config.color,
        }}
      >
        {config.label}
      </span>
    );
  }

  if (type === "sphere") {
    const config = SPHERE_COLORS[status as keyof typeof SPHERE_COLORS];
    if (!config) return <span>{status}</span>;
    return (
      <span
        className={cn(
          "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
          config.bg,
          config.text,
          className
        )}
      >
        {config.label}
      </span>
    );
  }

  // Default: member status
  const config = STATUS_COLORS[status as keyof typeof STATUS_COLORS];
  if (!config) return <span>{status}</span>;
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        config.bg,
        config.text,
        className
      )}
    >
      {config.label}
    </span>
  );
}
