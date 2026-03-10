import { cn } from "@/lib/utils";
import { MAHNSTUFEN_COLORS } from "@/constants/design";

interface MahnstufenBadgeProps {
  stufe: 0 | 1 | 2 | 3;
}

export function MahnstufenBadge({ stufe }: MahnstufenBadgeProps) {
  const config = MAHNSTUFEN_COLORS[stufe];
  return (
    <span
      className={cn(
        "inline-flex items-center rounded px-1.5 py-0.5 text-xs font-bold tabular-nums",
        config.bg,
        config.text
      )}
      aria-label={`Mahnstufe ${stufe}`}
    >
      {config.label}
    </span>
  );
}
