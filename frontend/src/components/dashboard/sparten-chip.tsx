import { SPARTEN_COLORS } from "@/constants/design";

interface SpartenChipProps {
  name: string;
}

export function SpartenChip({ name }: SpartenChipProps) {
  const color = SPARTEN_COLORS[name] || "#6b7280";
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium"
      style={{
        backgroundColor: `${color}20`,
        color: color,
      }}
      aria-label={name}
    >
      <span
        className="inline-block h-1.5 w-1.5 rounded-full"
        style={{ backgroundColor: color }}
      />
      {name}
    </span>
  );
}
