import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import { ArrowDownLeft, ArrowUpRight, AlertTriangle, Repeat, ChevronDown } from "lucide-react";
import { useTransactions, useAllAnomalies, useFeatures } from "@/api/queries";
import type { TransactionItem, AnomalyItem } from "@/api/client";
import { formatINR, formatDate, formatPct, formatMonths } from "@/lib/format";
import { paths } from "@/lib/paths";
import { Layout } from "@/ui/Layout";
import { ErrorState } from "@/ui/ErrorState";
import { Money as Rs } from "@/ui/Money";
import { Button, Card, CardSkeleton, ChipGroup } from "@/ui";

const CATEGORIES = ["all", "salary", "rent", "emi", "groceries", "dining", "transport", "shopping", "utilities", "entertainment", "education", "medical", "insurance_premium"];
const PAGE = 40;

// S9 — the raw material: every transaction, with anomaly flags and the
// anomaly detector's own reasons.
export function Money() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === "en" ? "en" : "hi";
  const { id = "" } = useParams();
  const [category, setCategory] = useState("all");
  const [pages, setPages] = useState(1);
  const [showFlags, setShowFlags] = useState(false);
  const features = useFeatures(id);
  const anomalies = useAllAnomalies(id);
  const anomalyById = new Map((anomalies.data?.anomalies ?? []).map((a) => [a.transaction_id, a]));

  const f = features.data?.features;
  const catLabel = (c: string) => (c === "all" ? t("money.all") : i18n.exists(`cat.${c}`) ? t(`cat.${c}`) : c.replace(/_/g, " "));

  return (
    <Layout back={paths.home(id)} title={t("money.title")}>
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-bold">{t("money.title")}</h1>
          <p className="text-ink-soft">{t("money.lead")}</p>
        </div>

        {!f && !features.isError && <div className="min-h-[190px] sm:min-h-[120px]"><CardSkeleton lines={4} /></div>}
        {f && (
          <Card className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm sm:grid-cols-4" aria-label={t("home.glance.title")}>
            <Stat label={t("home.glance.income")} value={<Rs value={f.monthly_income_mean} />} />
            <Stat label={t("home.glance.expenses")} value={<Rs value={f.monthly_expenses_mean} />} />
            <Stat label={t("home.glance.emi")} value={<Rs value={f.total_emi} />} sub={f.obligation_count != null ? t("home.glance.obligations", { n: f.obligation_count }) : undefined} />
            <Stat label={t("home.glance.savingsRate")} value={formatPct(f.savings_rate)} />
            <Stat label={t("home.glance.stability")} value={formatPct(f.income_stability)} />
            <Stat label={t("home.glance.volatility")} value={formatPct(f.expense_volatility)} />
            {f.credit_utilization != null && <Stat label={t("home.glance.creditUtil")} value={formatPct(f.credit_utilization)} />}
            <Stat label={t("home.glance.savings")} value={<Rs value={f.liquid_savings} />} sub={t("home.glance.months", { n: formatMonths(f.data_months) })} />
          </Card>
        )}

        {/* Flagged transactions are summarised in one fixed-height row; expanding is user-initiated so it never shifts on load. */}
        <Card tone="sand" className="flex min-h-[64px] flex-col gap-3" aria-labelledby="anom-h">
          <div className="flex items-center justify-between gap-3">
            <h2 id="anom-h" className="flex items-center gap-2 font-bold"><AlertTriangle size={20} aria-hidden /> {t("money.unusualTitle")}</h2>
            {(anomalies.data?.anomalies.length ?? 0) > 0 && (
              <button type="button" onClick={() => setShowFlags((v) => !v)} aria-expanded={showFlags}
                className="inline-flex min-h-touch items-center gap-1 whitespace-nowrap rounded-xl px-2 text-sm font-semibold text-accent-strong hover:bg-accent-soft">
                {showFlags ? t("common.hide") : t("money.flagged", { n: dedupe(anomalies.data!.anomalies).length })} <ChevronDown size={16} aria-hidden className={showFlags ? "rotate-180" : ""} />
              </button>
            )}
          </div>
          {showFlags && (
            <>
              <p className="text-sm text-ink-soft">{t("money.unusualLead")}</p>
              <ul className="flex flex-col gap-2">
                {dedupe(anomalies.data!.anomalies).slice(0, 8).map((a) => <AnomalyRow key={a.transaction_id} a={a} lang={lang} />)}
              </ul>
            </>
          )}
        </Card>

        <div className="flex flex-col gap-2">
          <span className="font-semibold">{t("money.filter")}</span>
          <ChipGroup name="cat" label={t("money.filter")} value={category}
            options={CATEGORIES.map((c) => ({ value: c, label: catLabel(c) }))}
            onChange={(c) => { setCategory(c); setPages(1); }} />
        </div>

        <TxnPages id={id} category={category} pages={pages} anomalyById={anomalyById} lang={lang} catLabel={catLabel} onMore={() => setPages((p) => p + 1)} />
      </div>
    </Layout>
  );
}

function Stat({ label, value, sub }: { label: string; value: React.ReactNode; sub?: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-ink-mute">{label}</span>
      <span className="text-base font-semibold tabular">{value}</span>
      {sub && <span className="text-ink-mute">{sub}</span>}
    </div>
  );
}

function dedupe(items: AnomalyItem[]) {
  const seen = new Set<string>();
  return items.filter((a) => { const k = `${a.txn_date}|${a.merchant}|${a.amount}`; if (seen.has(k)) return false; seen.add(k); return true; });
}

function AnomalyRow({ a, lang }: { a: AnomalyItem; lang: "hi" | "en" }) {
  const { t, i18n } = useTranslation();
  const [open, setOpen] = useState(false);
  const reasons = Object.entries(a.features ?? {}).filter(([, v]) => v != null && Number(v) !== 0)
    .sort((x, y) => Math.abs(Number(y[1])) - Math.abs(Number(x[1]))).slice(0, 3);
  return (
    <li className="rounded-xl border border-line bg-card p-3 text-sm">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <span>{t(a.type === "credit" ? "home.anomalies.credit" : "home.anomalies.debit", { amount: formatINR(a.amount), merchant: a.merchant, date: formatDate(a.txn_date, lang) })}</span>
        <span className="rounded-full bg-care-soft px-2 py-0.5 font-semibold text-care-ink tabular">{t("money.score", { score: a.anomaly_score.toFixed(2) })}</span>
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-ink-mute">
        <span>{i18n.exists(`money.method.${a.detection_method}`) ? t(`money.method.${a.detection_method}`) : a.detection_method.replace(/_/g, " ")}</span>
        <button type="button" onClick={() => setOpen((o) => !o)} className="inline-flex min-h-[32px] items-center gap-1 font-semibold text-accent-strong" aria-expanded={open}>
          {open ? t("common.hide") : t("common.showDetails")} <ChevronDown size={16} aria-hidden className={open ? "rotate-180" : ""} />
        </button>
      </div>
      {open && (
        <ul className="mt-2 grid gap-1 sm:grid-cols-3">
          {reasons.map(([k, v]) => (
            <li key={k} className="flex justify-between gap-2 rounded-lg bg-sand px-2 py-1">
              <span>{i18n.exists(`money.why.${k}`) ? t(`money.why.${k}`) : k.replace(/_/g, " ")}</span>
              <span className="font-semibold tabular">{Number(v).toFixed(2)}</span>
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

function TxnPages({ id, category, pages, anomalyById, lang, catLabel, onMore }: {
  id: string; category: string; pages: number; anomalyById: Map<string, AnomalyItem>; lang: "hi" | "en"; catLabel: (c: string) => string; onMore: () => void;
}) {
  const { t } = useTranslation();
  const first = useTransactions(id, category, 0, PAGE);
  const total = first.data?.total ?? 0;
  return (
    <div className="flex flex-col gap-3">
      {first.isError && !first.data ? (
        <ErrorState error={first.error} onRetry={() => first.refetch()} />
      ) : !first.data ? (
        <><CardSkeleton /><CardSkeleton /><CardSkeleton /></>
      ) : first.data.transactions.length === 0 ? (
        <Card tone="sand"><p>{t("money.empty")}</p></Card>
      ) : (
        <>
          <p className="text-sm text-ink-mute">{t("money.total", { total })}</p>
          <ul className="divide-y divide-line rounded-2xl border border-line bg-card">
            {first.data.transactions.map((tx) => <TxnRow key={tx.id} tx={tx} anomaly={anomalyById.get(tx.id)} lang={lang} catLabel={catLabel} />)}
            {Array.from({ length: pages - 1 }, (_, i) => <Page key={i + 1} id={id} category={category} offset={(i + 1) * PAGE} anomalyById={anomalyById} lang={lang} catLabel={catLabel} />)}
          </ul>
          {pages * PAGE < total && <Button onClick={onMore} icon={<ChevronDown size={20} aria-hidden />}>{t("money.more")}</Button>}
        </>
      )}
    </div>
  );
}

function Page({ id, category, offset, anomalyById, lang, catLabel }: { id: string; category: string; offset: number; anomalyById: Map<string, AnomalyItem>; lang: "hi" | "en"; catLabel: (c: string) => string }) {
  const q = useTransactions(id, category, offset, PAGE);
  if (!q.data) return <li className="px-4 py-3 text-sm text-ink-mute">…</li>;
  return <>{q.data.transactions.map((tx) => <TxnRow key={tx.id} tx={tx} anomaly={anomalyById.get(tx.id)} lang={lang} catLabel={catLabel} />)}</>;
}

function TxnRow({ tx, anomaly, lang, catLabel }: { tx: TransactionItem; anomaly?: AnomalyItem; lang: "hi" | "en"; catLabel: (c: string) => string }) {
  const { t } = useTranslation();
  const credit = tx.type === "credit";
  return (
    <li className={"flex items-center gap-3 px-4 py-3 " + (tx.is_anomaly ? "bg-care-soft/60" : "")}>
      <span className={"inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full " + (credit ? "bg-safe-soft text-safe-ink" : "bg-sand text-ink-soft")} aria-hidden>
        {credit ? <ArrowDownLeft size={18} /> : <ArrowUpRight size={18} />}
      </span>
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="truncate font-semibold">{tx.merchant}</span>
        <span className="flex flex-wrap gap-x-2 text-sm text-ink-mute">
          <span>{formatDate(tx.txn_date, lang)}</span>
          <span>· {catLabel(tx.category)}</span>
          {tx.is_recurring && <span className="inline-flex items-center gap-1"><Repeat size={14} aria-hidden /> {t("money.recurring")}</span>}
          {tx.is_anomaly && <span className="inline-flex items-center gap-1 font-semibold text-care-ink"><AlertTriangle size={14} aria-hidden /> {t("money.unusual")}{anomaly ? ` · ${t("money.score", { score: anomaly.anomaly_score.toFixed(2) })}` : ""}</span>}
        </span>
      </span>
      <span className={"shrink-0 font-semibold tabular " + (credit ? "text-safe-ink" : "")}>{credit ? "+" : "−"}{formatINR(tx.amount)}</span>
    </li>
  );
}
