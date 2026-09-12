import type { HTMLAttributes, ReactNode } from "react";

type Tone = "card" | "sand" | "safe" | "care" | "danger" | "accent";
const tones: Record<Tone, string> = {
  card: "bg-card border border-line",
  sand: "bg-sand",
  safe: "bg-safe-soft",
  care: "bg-care-soft",
  danger: "bg-danger-soft",
  accent: "bg-accent-soft",
};

export function Card({ tone = "card", className = "", children, ...rest }:
  { tone?: Tone; className?: string; children: ReactNode } & HTMLAttributes<HTMLElement>) {
  return (
    <section className={`rounded-2xl p-4 shadow-card ${tones[tone]} ${className}`} {...rest}>
      {children}
    </section>
  );
}
