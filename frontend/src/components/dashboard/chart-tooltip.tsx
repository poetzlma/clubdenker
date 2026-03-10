export interface ChartTooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    color: string;
  }>;
  label?: string;
  formatter?: (value: number) => string;
}

export function ChartTooltip({
  active,
  payload,
  label,
  formatter,
}: ChartTooltipProps) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2 shadow-lg">
      <p className="mb-1 text-xs font-medium text-gray-500">
        {label}
      </p>
      {payload.map((entry, i) => (
        <div key={i} className="flex items-center gap-2 text-xs">
          <span
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-gray-500">{entry.name}:</span>
          <span className="tabular-nums font-medium text-gray-900">
            {formatter ? formatter(entry.value) : entry.value.toLocaleString("de-DE")}
          </span>
        </div>
      ))}
    </div>
  );
}
