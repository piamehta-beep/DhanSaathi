import type { ReactNode } from "react";

export function ChatBubble({ from, children, tone = "normal" }: {
  from: "app" | "me"; children: ReactNode; tone?: "normal" | "care";
}) {
  const mine = from === "me";
  return (
    <div className={`flex ${mine ? "justify-end" : "justify-start"} animate-rise`}>
      <div
        className={
          "max-w-[85%] rounded-2xl px-4 py-3 text-base leading-relaxed " +
          (mine
            ? "bg-accent text-white rounded-br-md"
            : tone === "care"
              ? "bg-care-soft text-care-ink rounded-bl-md"
              : "bg-card border border-line rounded-bl-md")
        }
      >
        {children}
      </div>
    </div>
  );
}
