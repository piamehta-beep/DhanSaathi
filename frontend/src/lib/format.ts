// Formatting only — never arithmetic on money (brief §4). Every rupee amount on
// screen goes through formatINR.

const inGroup = (intPart: string) => {
  // Indian grouping: last three digits, then pairs. 200000 -> 2,00,000
  if (intPart.length <= 3) return intPart;
  const last3 = intPart.slice(-3);
  const rest = intPart.slice(0, -3);
  return rest.replace(/\B(?=(\d{2})+(?!\d))/g, ",") + "," + last3;
};

export function formatINR(value: number | null | undefined, opts: { decimals?: 0 | 2 } = {}): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const decimals = opts.decimals ?? 0;
  const sign = value < 0 ? "−" : "";
  const abs = Math.abs(value);
  const fixed = abs.toFixed(decimals);
  const [i, d] = fixed.split(".");
  return `${sign}₹${inGroup(i)}${d ? "." + d : ""}`;
}

// Spoken form for amounts ≥ 1 lakh: "₹2 lakh", "₹2.5 lakh", "₹1.2 crore".
// Returns null below a lakh so callers can show the plain figure alone.
export function spokenINR(value: number | null | undefined, lang: "hi" | "en"): string | null {
  if (value === null || value === undefined || Number.isNaN(value)) return null;
  const abs = Math.abs(value);
  if (abs < 100000) return null;
  const unit = abs >= 10000000 ? 10000000 : 100000;
  const n = abs / unit;
  const num = Number.isInteger(n) ? String(n) : n.toFixed(n < 10 ? 1 : 0).replace(/\.0$/, "");
  const word = unit === 10000000 ? (lang === "hi" ? "करोड़" : "crore") : (lang === "hi" ? "लाख" : "lakh");
  return `₹${num} ${word}`;
}

// Whole-number percentage unless < 1% (brief §8).
export function formatPct(ratio: number | null | undefined): string {
  if (ratio === null || ratio === undefined || Number.isNaN(ratio)) return "—";
  const pct = ratio * 100;
  if (pct > 0 && pct < 1) return `${pct.toFixed(1)}%`;
  return `${Math.round(pct)}%`;
}

export function formatRateBand(min: number, max: number): string {
  const f = (x: number) => (Number.isInteger(x) ? `${x}` : `${x.toFixed(2).replace(/0$/, "")}`);
  return `${f(min)}%–${f(max)}%`;
}

export function formatMonths(m: number | null | undefined): string {
  if (m === null || m === undefined || Number.isNaN(m)) return "—";
  return m >= 10 ? String(Math.round(m)) : m.toFixed(1).replace(/\.0$/, "");
}

// ISO date -> "15 March" style, localised.
export function formatDate(iso: string, lang: "hi" | "en"): string {
  const d = new Date(iso + "T00:00:00");
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat(lang === "hi" ? "hi-IN" : "en-IN", { day: "numeric", month: "long" }).format(d);
}

// Compact axis labels: ₹75k / ₹1.2L (en), ₹75 हज़ार / ₹1.2 लाख (hi).
export function formatINRShort(value: number, lang: "hi" | "en"): string {
  const sign = value < 0 ? "−" : "";
  const abs = Math.abs(value);
  if (abs >= 10000000) return `${sign}₹${(abs / 10000000).toFixed(1).replace(/\.0$/, "")} ${lang === "hi" ? "करोड़" : "cr"}`;
  if (abs >= 100000) return `${sign}₹${(abs / 100000).toFixed(1).replace(/\.0$/, "")} ${lang === "hi" ? "लाख" : "L"}`;
  if (abs >= 1000) return `${sign}₹${Math.round(abs / 1000)}${lang === "hi" ? " हज़ार" : "k"}`;
  return `${sign}₹${Math.round(abs)}`;
}

export function formatDateTime(iso: string, lang: "hi" | "en"): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat(lang === "hi" ? "hi-IN" : "en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" }).format(d);
}

export function formatScore(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return (v >= 0 ? "+" : "−") + Math.abs(v).toFixed(2);
}
