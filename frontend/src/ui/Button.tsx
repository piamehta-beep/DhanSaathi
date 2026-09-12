import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { Loader2 } from "lucide-react";

type Variant = "primary" | "secondary" | "quiet";
const base =
  "inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition-colors duration-150 ease-out " +
  "disabled:opacity-50 disabled:cursor-not-allowed select-none min-h-touch px-5";
const variants: Record<Variant, string> = {
  primary: "bg-accent text-white hover:bg-accent-strong active:bg-accent-strong min-h-cta text-lg w-full",
  secondary: "bg-card border border-line text-ink hover:bg-sand active:bg-sand",
  quiet: "bg-transparent text-accent-strong hover:bg-accent-soft underline-offset-4",
};

type Common = { variant?: Variant; icon?: ReactNode; loading?: boolean; className?: string; children: ReactNode };

export const Button = forwardRef<HTMLButtonElement, Common & ButtonHTMLAttributes<HTMLButtonElement>>(
  function Button({ variant = "secondary", icon, loading, className = "", children, ...rest }, ref) {
    return (
      <button ref={ref} className={`${base} ${variants[variant]} ${className}`} aria-busy={loading || undefined} {...rest}>
        {loading ? <Loader2 className="animate-spin" size={22} aria-hidden /> : icon}
        <span>{children}</span>
      </button>
    );
  },
);

export function LinkButton({ to, variant = "secondary", icon, className = "", children, ...rest }:
  Common & { to: string; state?: unknown }) {
  return (
    <Link to={to} className={`${base} ${variants[variant]} ${className}`} {...rest}>
      {icon}<span>{children}</span>
    </Link>
  );
}
