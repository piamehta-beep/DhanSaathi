import type { ReactNode } from "react";

export function Timeline({ items }: { items: { key: string; icon: ReactNode; tone: "safe" | "care" | "neutral" | "accent"; title: string; body: ReactNode; meta: ReactNode }[] }) {
  const dot = { safe: "bg-safe-soft text-safe-ink", care: "bg-care-soft text-care-ink", neutral: "bg-sand text-ink-soft", accent: "bg-accent-soft text-accent-strong" };
  return (
    <ol className="relative flex flex-col gap-4 border-l-2 border-line pl-6">
      {items.map((it) => (
        <li key={it.key} className="relative animate-rise">
          <span aria-hidden className={`absolute -left-[31px] top-0 inline-flex h-8 w-8 items-center justify-center rounded-full ${dot[it.tone]}`}>{it.icon}</span>
          <div className="flex flex-col gap-1 rounded-2xl border border-line bg-card p-3 shadow-card">
            <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
              <span className="font-semibold">{it.title}</span>
              <span className="text-sm text-ink-mute">{it.meta}</span>
            </div>
            <div className="text-sm text-ink-soft">{it.body}</div>
          </div>
        </li>
      ))}
    </ol>
  );
}
