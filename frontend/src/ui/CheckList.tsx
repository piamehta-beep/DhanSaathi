import { Check, X } from "lucide-react";
import { useTranslation } from "react-i18next";
import { CONSTRAINT_CODES, constraintKey } from "@/copy/mapping";

// The C1–C9 safety gate as ticks and crosses. Codes never reach the screen;
// checks that didn't apply to this product are omitted (brief §6 S5).
export function CheckList({ passed, failed }: { passed: string[]; failed: string[] }) {
  const { t } = useTranslation();
  const rows = CONSTRAINT_CODES
    .filter((c) => passed.includes(c) || failed.includes(c))
    .map((c) => ({ code: c, ok: passed.includes(c) && !failed.includes(c) }));
  if (rows.length === 0) return null;
  return (
    <ul className="divide-y divide-line rounded-2xl border border-line bg-card">
      {rows.map(({ code, ok }) => (
        <li key={code} className="flex items-start gap-3 px-4 py-3">
          <span
            className={
              "mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full " +
              (ok ? "bg-safe-soft text-safe-ink" : "bg-care-soft text-care-ink")
            }
            aria-hidden
          >
            {ok ? <Check size={18} strokeWidth={3} /> : <X size={18} strokeWidth={3} />}
          </span>
          <span className="flex-1">
            <span className="block">{t(constraintKey(code))}</span>
            <span className={"text-sm font-semibold " + (ok ? "text-safe-ink" : "text-care-ink")}>
              {ok ? t("why.passed") : t("why.failed")}
            </span>
          </span>
        </li>
      ))}
    </ul>
  );
}
