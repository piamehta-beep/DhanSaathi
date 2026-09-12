import { ArrowRight } from "lucide-react";
import type { Light } from "@/copy/mapping";

// A row of "now → after" pairs. Each value is an API number, pre-formatted;
// the light classifies the *after* value for colour, never transforms it.
export type BARow = { label: string; before: string; after: string; light: Light; extra?: { label: string; value: string; light: Light } };

const chip: Record<Light, string> = {
  safe: "bg-safe-soft text-safe-ink",
  care: "bg-care-soft text-care-ink",
  danger: "bg-danger-soft text-danger-ink",
};

export function BeforeAfter({ rows, beforeLabel, afterLabel }: { rows: BARow[]; beforeLabel: string; afterLabel: string }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-ink-mute">
            <th className="py-1 pr-2 font-semibold"></th>
            <th className="py-1 pr-2 font-semibold">{beforeLabel}</th>
            <th className="py-1 pr-2 font-semibold" aria-hidden></th>
            <th className="py-1 font-semibold">{afterLabel}</th>
            {rows.some((r) => r.extra) && <th className="py-1 pl-2 font-semibold">{rows.find((r) => r.extra)?.extra?.label}</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.label} className="border-t border-line">
              <td className="py-2 pr-2">{r.label}</td>
              <td className="py-2 pr-2 font-semibold tabular">{r.before}</td>
              <td className="py-2 pr-2 text-ink-mute" aria-hidden><ArrowRight size={16} /></td>
              <td className="py-2"><span className={`rounded-full px-2 py-0.5 font-semibold tabular ${chip[r.light]}`}>{r.after}</span></td>
              {r.extra && <td className="py-2 pl-2"><span className={`rounded-full px-2 py-0.5 font-semibold tabular ${chip[r.extra.light]}`}>{r.extra.value}</span></td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
