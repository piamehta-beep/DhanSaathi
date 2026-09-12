import { useTranslation } from "react-i18next";
import { Landmark } from "lucide-react";
import type { BankProductMatch } from "@/api/client";
import { KNOWN_VETOS, vetoKey } from "@/copy/mapping";
import { formatRateBand, formatPct, formatDate, formatINR } from "@/lib/format";
import { Money } from "@/ui/Money";
import { Card, StatusChip } from "@/ui";

// Shared by S3 and the S4 affordable result. The source_note is body text,
// shown once above the cards — never a tooltip (brief §6 S3).
export function BankCards({ products }: { products: BankProductMatch[] }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === "en" ? "en" : "hi";
  if (products.length === 0) return null;
  const sourceNote = products[0].source_note;
  return (
    <div className="flex flex-col gap-4">
      <Card tone="sand" className="flex flex-col gap-1" aria-labelledby="src-h">
        <h2 id="src-h" className="font-semibold">{t("banks.sourceHeading")}</h2>
        <p className="text-ink-soft">{t("banks.sourceLead")}</p>
        <p className="text-sm text-ink-soft" lang="en">{sourceNote}</p>
      </Card>
      <p className="text-sm font-semibold text-ink-mute">{t("banks.cheapestFirst")}</p>
      <ul className="flex flex-col gap-3">
        {products.map((p, i) => {
          const ok = p.passes_safety_gate;
          const veto = p.veto_reason && KNOWN_VETOS.has(p.veto_reason) ? p.veto_reason : p.veto_reason ? "unknown" : null;
          return (
            <li key={`${p.bank_name}-${p.product_name}-${i}`} className="animate-rise">
              <Card className={"flex flex-col gap-3 " + (ok ? "" : "opacity-80")}>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-2">
                    <Landmark size={22} aria-hidden className="mt-0.5 shrink-0 text-ink-mute" />
                    <div>
                      <div className="font-bold">{p.bank_name}</div>
                      <div className="text-sm text-ink-soft">{p.product_name}</div>
                    </div>
                  </div>
                  <StatusChip light={ok ? "safe" : "care"}>{ok ? t("banks.safe") : t("banks.unsafe")}</StatusChip>
                </div>
                <div className="flex flex-wrap items-end gap-x-6 gap-y-2">
                  <div>
                    <div className="text-sm text-ink-mute">{t("banks.monthly")}</div>
                    <Money value={p.monthly_cost} big />
                  </div>
                  <div>
                    <div className="text-sm text-ink-mute">{t("banks.rate")}</div>
                    <div className="font-semibold tabular">{formatRateBand(p.interest_rate_band.min, p.interest_rate_band.max)}</div>
                  </div>
                  {p.tenure_months != null && (
                    <div className="font-semibold">{t("banks.tenure", { months: p.tenure_months })}</div>
                  )}
                </div>
                <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-ink-soft">
                  {p.processing_fee_pct != null && <li>{t("banks.processingFee", { pct: formatPct(p.processing_fee_pct / 100) })}</li>}
                  {p.annual_fee != null && <li>{t("banks.annualFee", { amount: formatINR(p.annual_fee) })}</li>}
                </ul>
                {!ok && veto && <p className="text-care-ink">{t(vetoKey(veto))}</p>}
                <details className="text-sm text-ink-soft">
                  <summary className="cursor-pointer font-semibold min-h-[32px] inline-flex items-center">{t("banks.eligibility")}</summary>
                  <p className="mt-1" lang="en">{p.eligibility_notes}</p>
                  <p className="mt-1 text-ink-mute">{t("banks.verified", { date: formatDate(p.last_verified_date, lang) })}</p>
                </details>
              </Card>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
