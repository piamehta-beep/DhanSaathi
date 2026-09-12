import type { ReactNode } from "react";
import { Check, X, Minus } from "lucide-react";
import type { Light } from "@/copy/mapping";

// Status chip: colour never carries meaning alone — always an icon and a word.
export function StatusChip({ light, children }: { light: Light | "neutral"; children: ReactNode }) {
  const cls = {
    safe: "bg-safe-soft text-safe-ink",
    care: "bg-care-soft text-care-ink",
    danger: "bg-danger-soft text-danger-ink",
    neutral: "bg-sand text-ink-soft",
  }[light];
  const Icon = light === "safe" ? Check : light === "danger" ? X : Minus;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-semibold ${cls}`}>
      <Icon size={16} aria-hidden strokeWidth={2.5} />
      {children}
    </span>
  );
}

// Selectable chips form a radio group (brief §12).
export function ChipGroup<T extends string | number>({ label, options, value, onChange, name }: {
  label: string; name: string; options: { value: T; label: string }[]; value: T | null; onChange: (v: T) => void;
}) {
  return (
    <div role="radiogroup" aria-label={label} className="flex flex-wrap gap-2">
      {options.map((o) => {
        const selected = o.value === value;
        return (
          <button
            key={String(o.value)}
            type="button"
            role="radio"
            aria-checked={selected}
            name={name}
            onClick={() => onChange(o.value)}
            className={
              "min-h-touch rounded-xl px-4 py-2 text-base font-semibold border transition-colors duration-150 " +
              (selected
                ? "bg-accent text-white border-accent"
                : "bg-card text-ink border-line hover:bg-sand")
            }
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
