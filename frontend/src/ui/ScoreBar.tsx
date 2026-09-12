import { useTranslation } from "react-i18next";
import { formatScore } from "@/lib/format";

// The Customer Benefit Score on its [-1, 1] axis with its bootstrap interval
// and the no_action baseline at 0. Everything here is an API number.
export function ScoreBar({ score, low, high }: { score: number; low: number | null; high: number | null }) {
  const { t } = useTranslation();
  const pos = (v: number) => `${((Math.max(-1, Math.min(1, v)) + 1) / 2) * 100}%`;
  const positive = score >= 0;
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between">
        <span className={"text-3xl font-bold tabular " + (positive ? "text-safe-ink" : "text-care-ink")}>{formatScore(score)}</span>
        {low != null && high != null && <span className="text-sm text-ink-mute tabular">{t("rec.score.range", { lo: formatScore(low), hi: formatScore(high) })}</span>}
      </div>
      <div className="relative h-4 rounded-full bg-sand" aria-hidden>
        {low != null && high != null && (
          <div className="absolute top-0 h-4 rounded-full bg-safe/30" style={{ left: pos(Math.min(low, high)), width: `calc(${pos(Math.max(low, high))} - ${pos(Math.min(low, high))})` }} />
        )}
        <div className="absolute top-0 h-4 w-0.5 bg-ink" style={{ left: pos(0) }} />
        <div className={"absolute top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-card " + (positive ? "bg-safe" : "bg-care")} style={{ left: pos(score) }} />
      </div>
      <div className="flex justify-between text-sm text-ink-mute">
        <span>−1</span><span>{t("rec.score.noAction")} 0</span><span>+1</span>
      </div>
    </div>
  );
}

// Small signed bars for the five CBS components.
export function ComponentBars({ items }: { items: { label: string; value: number }[] }) {
  const max = Math.max(0.01, ...items.map((i) => Math.abs(i.value)));
  return (
    <ul className="flex flex-col gap-2">
      {items.map((i) => {
        const w = Math.max(3, Math.round((Math.abs(i.value) / max) * 50));
        const pos = i.value >= 0;
        return (
          <li key={i.label} className="grid grid-cols-[1fr_auto] items-center gap-3 text-sm">
            <span className="flex flex-col gap-1">
              <span>{i.label}</span>
              <span className="relative h-2 w-full rounded-full bg-sand" aria-hidden>
                <span className="absolute left-1/2 top-0 h-2 w-px bg-line" />
                <span className={"absolute top-0 h-2 rounded-full " + (pos ? "bg-safe" : "bg-care")} style={pos ? { left: "50%", width: `${w}%` } : { right: "50%", width: `${w}%` }} />
              </span>
            </span>
            <span className={"font-semibold tabular " + (pos ? "text-safe-ink" : "text-care-ink")}>{formatScore(i.value)}</span>
          </li>
        );
      })}
    </ul>
  );
}
