import { useId, useState } from "react";
import { useWidth } from "@/lib/useWidth";
import { useTranslation } from "react-i18next";
import type { SimulationScenario } from "@/api/client";
import { formatINR, formatINRShort } from "@/lib/format";

// Monte Carlo liquidity fan: expected line + p5–p95 band per scenario, a
// safety line (min_buffer) and zero. Pure SVG, scales with its container.
// Values are plotted exactly as returned; only the pixel mapping is ours.
export type FanSeries = { key: string; label: string; scenario: SimulationScenario; tone: "accent" | "care" | "ink" };

const tones = {
  accent: { line: "#0f766e", fill: "#0f766e" },
  care: { line: "#b45309", fill: "#b45309" },
  ink: { line: "#5a5650", fill: "#5a5650" },
};

export function FanChart({ series, safetyLine, compact = false }: { series: FanSeries[]; safetyLine?: number | null; compact?: boolean }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === "en" ? "en" : "hi";
  const id = useId();
  const [ref, width] = useWidth<HTMLDivElement>();
  const months = Object.keys(series[0]?.scenario.expected_liquidity ?? {}).map(Number).sort((a, b) => a - b);
  const [picked, setPicked] = useState<number>(months[months.length - 1] ?? 12);
  if (months.length === 0) return null;

  const W = width, H = compact ? 200 : 280, padL = 62, padR = 12, padT = 12, padB = 28;
  const allVals: number[] = [0];
  for (const s of series) {
    for (const m of months) {
      const p = s.scenario.liquidity_percentiles[String(m)];
      allVals.push(s.scenario.expected_liquidity[String(m)], p?.p5 ?? 0, p?.p95 ?? 0);
    }
  }
  if (safetyLine != null) allVals.push(safetyLine);
  const yMin = Math.min(...allVals), yMax = Math.max(...allVals);
  const span = yMax - yMin || 1;
  const x = (m: number) => padL + ((m - months[0]) / ((months[months.length - 1] - months[0]) || 1)) * (W - padL - padR);
  const y = (v: number) => padT + (1 - (v - yMin) / span) * (H - padT - padB);

  const path = (get: (m: number) => number) => months.map((m, i) => `${i ? "L" : "M"}${x(m).toFixed(1)},${y(get(m)).toFixed(1)}`).join(" ");
  const band = (s: SimulationScenario) => {
    const top = months.map((m, i) => `${i ? "L" : "M"}${x(m).toFixed(1)},${y(s.liquidity_percentiles[String(m)].p95).toFixed(1)}`).join(" ");
    const bottom = [...months].reverse().map((m) => `L${x(m).toFixed(1)},${y(s.liquidity_percentiles[String(m)].p5).toFixed(1)}`).join(" ");
    return `${top} ${bottom} Z`;
  };
  const ticks = 4;
  const yTicks = Array.from({ length: ticks + 1 }, (_, i) => yMin + (span * i) / ticks);

  return (
    <div ref={ref} className="flex flex-col gap-3">
      <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} className="block max-w-full" role="img" aria-labelledby={`${id}-t`}>
        <title id={`${id}-t`}>{series.map((s) => s.label).join(" · ")}</title>
        {yTicks.map((v) => (
          <g key={v}>
            <line x1={padL} x2={W - padR} y1={y(v)} y2={y(v)} stroke="#e4dfd5" strokeWidth={1} />
            <text x={padL - 8} y={y(v) + 4} fontSize={13} textAnchor="end" fill="#6b665e">{formatINRShort(v, lang)}</text>
          </g>
        ))}
        {yMin < 0 && <line x1={padL} x2={W - padR} y1={y(0)} y2={y(0)} stroke="#1f1d1a" strokeWidth={1} strokeDasharray="2 4" />}
        {safetyLine != null && (
          <line x1={padL} x2={W - padR} y1={y(safetyLine)} y2={y(safetyLine)} stroke="#b91c1c" strokeWidth={1.5} strokeDasharray="6 4" />
        )}
        {series.map((s) => (
          <path key={s.key + "b"} d={band(s.scenario)} fill={tones[s.tone].fill} opacity={0.12} />
        ))}
        {series.map((s) => (
          <path key={s.key + "l"} d={path((m) => s.scenario.expected_liquidity[String(m)])} fill="none" stroke={tones[s.tone].line} strokeWidth={3} strokeLinejoin="round" strokeLinecap="round" />
        ))}
        <line x1={x(picked)} x2={x(picked)} y1={padT} y2={H - padB} stroke="#1f1d1a" strokeWidth={1} opacity={0.35} />
        {months.map((m) => (
          <text key={m} x={x(m)} y={H - 8} fontSize={13} textAnchor="middle" fill={m === picked ? "#1f1d1a" : "#6b665e"} fontWeight={m === picked ? 700 : 400}>{m}</text>
        ))}
      </svg>

      <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
        {series.map((s) => (
          <span key={s.key} className="inline-flex items-center gap-2">
            <span aria-hidden className="inline-block h-1 w-5 rounded" style={{ background: tones[s.tone].line }} /> {s.label}
          </span>
        ))}
        {safetyLine != null && (
          <span className="inline-flex items-center gap-2 text-danger-ink">
            <span aria-hidden className="inline-block h-0 w-5 border-t-2 border-dashed border-danger" /> {t("future.safetyLine")}
          </span>
        )}
      </div>

      {!compact && (
        <div className="flex flex-col gap-2">
          <div role="radiogroup" aria-label={t("future.pickMonth")} className="flex flex-wrap gap-1">
            {months.map((m) => (
              <button key={m} type="button" role="radio" aria-checked={picked === m} onClick={() => setPicked(m)}
                className={"min-h-[40px] min-w-[40px] rounded-lg px-2 text-sm font-semibold " + (picked === m ? "bg-ink text-paper" : "bg-sand text-ink-soft hover:bg-line")}>
                {m}
              </button>
            ))}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm tabular">
              <caption className="sr-only">{t("future.month", { n: picked })}</caption>
              <thead>
                <tr className="text-left text-ink-mute">
                  <th className="py-1 pr-3 font-semibold">{t("future.month", { n: picked })}</th>
                  <th className="py-1 pr-3 font-semibold">{t("future.expected")}</th>
                  <th className="py-1 font-semibold">{t("future.band")}</th>
                </tr>
              </thead>
              <tbody>
                {series.map((s) => {
                  const p = s.scenario.liquidity_percentiles[String(picked)];
                  return (
                    <tr key={s.key} className="border-t border-line">
                      <td className="py-1.5 pr-3 font-semibold">{s.label}</td>
                      <td className="py-1.5 pr-3">{formatINR(s.scenario.expected_liquidity[String(picked)])}</td>
                      <td className="py-1.5">{formatINR(p?.p5)} – {formatINR(p?.p95)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
