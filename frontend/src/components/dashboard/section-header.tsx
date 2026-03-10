interface SectionHeaderProps {
  label: string;
  action?: string;
  onAction?: () => void;
}

export function SectionHeader({ label, action, onAction }: SectionHeaderProps) {
  return (
    <div className="flex items-center justify-between">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-700">
        {label}
      </h3>
      {action && (
        <button
          onClick={onAction}
          className="text-xs text-gray-400 hover:text-gray-600 hover:underline"
        >
          {action}
        </button>
      )}
    </div>
  );
}
