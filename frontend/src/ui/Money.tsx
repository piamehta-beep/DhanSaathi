import { useTranslation } from "react-i18next";
import { formatINR, spokenINR } from "@/lib/format";

// Every rupee amount goes through here: figure in Indian grouping, plus the
// spoken form for ≥ ₹1 lakh (brief §8).
export function Money({ value, big = false, decimals = 0 }: { value: number | null | undefined; big?: boolean; decimals?: 0 | 2 }) {
  const { i18n } = useTranslation();
  const lang = i18n.language === "en" ? "en" : "hi";
  const spoken = spokenINR(value, lang);
  return (
    <span className="tabular">
      <span className={big ? "text-3xl font-bold leading-none" : "font-semibold"}>{formatINR(value, { decimals })}</span>
      {spoken && <span className={"text-ink-mute " + (big ? "ml-2 text-lg" : "ml-1 text-sm")}>({spoken})</span>}
    </span>
  );
}
