export function PulseDot() {
  return (
    <span className="pulse-dot-container relative flex h-3 w-3">
      <span className="pulse-dot-ring absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75" />
      <span className="relative inline-flex h-3 w-3 rounded-full bg-emerald-500" />
    </span>
  );
}
