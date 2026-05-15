type ProgressBarProps = {
  value: number;
  active?: boolean;
};

export function ProgressBar({ value, active = false }: ProgressBarProps) {
  const safeValue = Math.min(1, Math.max(0, value));

  return (
    <div
      className="h-1 overflow-hidden rounded-full bg-white/10"
      role="progressbar"
      aria-label="Audio progress"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(safeValue * 100)}
    >
      <div
        className={`h-full rounded-full transition-[width] duration-150 ${
          active ? "bg-cyan-200" : "bg-white/25"
        }`}
        style={{ width: `${safeValue * 100}%` }}
      />
    </div>
  );
}
