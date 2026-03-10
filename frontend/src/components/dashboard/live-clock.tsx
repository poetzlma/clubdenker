import { useState, useEffect } from "react";

export function LiveClock() {
  const [time, setTime] = useState(() => new Date());

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  const formatted = time.toLocaleTimeString("de-DE", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  return (
    <span className="tabular-nums font-mono text-sm text-gray-500">
      {formatted}
    </span>
  );
}
