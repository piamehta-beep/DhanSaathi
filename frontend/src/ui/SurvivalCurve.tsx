import { useId } from "react";
import { useWidth } from "@/lib/useWidth";
import { useTranslation } from "react-i18next";
import { formatPct } from "@/lib/format";

// Survival function S(t): probability of *not* having hit distress by month t.
// Keyed by month in the API ({"1":1,"3":1,"6":0.996,"12":0.95}); we plot the
// points it gives and join them.
export function SurvivalCurve({ points }: { points: Record<string, number> }) {
  const { t } = useTranslation();
  const id = useId();
  const [ref, width] = useWidth<HTMLDivElement>();
  const pts = Object.entries(points).map(([m, v]) => [Number(m), v] as const).sort((a, b) => a[0] - b[0]);
  if (pts.length === 0) return null;
  const W = width, H = 170, padL = 50, padR = 16, padT = 12, padB = 28;
  const maxM = pts[pts.length - 1][0];
  const minV = Math.min(0.5, ...pts.map((p) => p[1]));
  const x = (m: number) => padL + (m / maxM) * (W - padL - padR);
  const y = (v: number) => padT + (1 - (v - minV) / (1 - minV || 1)) * (H - padT - padB);
  const all = [[0, 1] as const, ...pts];
  const d = all.map(([m, v], i) => `${i ? "L" : "M"}${x(m).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const area = `${d} L${x(maxM).toFixed(1)},${y(minV).toFixed(1)} L${x(0).toFixed(1)},${y(minV).toFixed(1)} Z`;
  const yTicks = [minV, (1 + minV) / 2, 1];
  return (
    <div ref={ref} className="flex flex-col gap-2">
      <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} className="block max-w-full" role="img" aria-labelledby={`${id}-t`}>
        <title id={`${id}-t`}>{t("home.survival.title")}</title>
        {yTicks.map((v) => (
          <g key={v}>
            <line x1={padL} x2={W - padR} y1={y(v)} y2={y(v)} stroke="#e4dfd5" />
            <text x={padL - 8} y={y(v) + 4} fontSize={13} textAnchor="end" fill="#6b665e">{formatPct(v)}</text>
          </g>
        ))}
        <path d={area} fill="#1a7f37" opacity={0.1} />
        <path d={d} fill="none" stroke="#1a7f37" strokeWidth={3} strokeLinejoin="round" />
        {pts.map(([m, v]) => (
          <g key={m}>
            <circle cx={x(m)} cy={y(v)} r={5} fill="#1a7f37" />
            <text x={x(m)} y={H - 8} fontSize={13} textAnchor="middle" fill="#6b665e">{m}</text>
          </g>
        ))}
      </svg>
      <ul className="flex flex-wrap gap-x-5 gap-y-1 text-sm text-ink-soft">
        {pts.map(([m, v]) => (
          <li key={m}><strong className="text-ink tabular">{formatPct(v)}</strong> {t("home.survival.atMonth", { count: m })}</li>
        ))}
      </ul>
    </div>
  );
}
