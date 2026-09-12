import type { ReactNode } from "react";
import { WifiOff, Hourglass, ShieldAlert } from "lucide-react";

type Kind = "offline" | "warmup" | "consent";
const styles: Record<Kind, string> = {
  offline: "bg-care-soft text-care-ink",
  warmup: "bg-accent-soft text-accent-strong",
  consent: "bg-sand text-ink",
};
const icons: Record<Kind, ReactNode> = {
  offline: <WifiOff size={22} aria-hidden />,
  warmup: <Hourglass size={22} aria-hidden />,
  consent: <ShieldAlert size={22} aria-hidden />,
};

export function Banner({ kind, children, action }: { kind: Kind; children: ReactNode; action?: ReactNode }) {
  return (
    <div role="status" className={`flex items-center gap-3 px-4 py-3 text-sm sm:text-base ${styles[kind]}`}>
      <span className="shrink-0">{icons[kind]}</span>
      <span className="flex-1">{children}</span>
      {action}
    </div>
  );
}
