interface VuMeterProps {
  level: number;
}

export function VuMeter({ level }: VuMeterProps) {
  const clamped = Math.min(1, Math.max(0, level));
  const widths = [
    "w-0",
    "w-[10%]",
    "w-[20%]",
    "w-[30%]",
    "w-[40%]",
    "w-[50%]",
    "w-[60%]",
    "w-[70%]",
    "w-[80%]",
    "w-[90%]",
    "w-full"
  ] as const;
  const index = Math.min(widths.length - 1, Math.round(clamped * (widths.length - 1)));

  return (
    <div className="h-2 w-full rounded-full bg-slate-800">
      <div className={`h-full rounded-full bg-emerald-500 transition-all duration-75 ${widths[index]}`} />
    </div>
  );
}
