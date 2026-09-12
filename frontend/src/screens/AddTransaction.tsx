import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { PlusCircle, AlertTriangle, Check, ArrowRight, RotateCcw } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useAddTransaction, useFeatures, useAllAnomalies, keys } from "@/api/queries";
import { ApiError, type FeaturesResponse } from "@/api/client";
import { formatINR, formatDate, formatMonths, formatPct, spokenINR } from "@/lib/format";
import { paths } from "@/lib/paths";
import { Button, Card, ChipGroup, BeforeAfter, type BARow } from "@/ui";
import { ErrorState } from "@/ui/ErrorState";
import { runwayLight, dbrLight } from "@/copy/mapping";

const AMOUNTS = [500, 5000, 45000, 150000];
const CATS_OUT = ["shopping", "groceries", "dining", "transport", "medical", "utilities", "entertainment", "emi", "rent"];
const CATS_IN = ["salary", "transfer", "gig_income", "business_income"];

// Demo write path: POST a transaction, then show what the anomaly detector
// made of it and how the customer's own numbers moved. Every value shown
// is read back from the API after the append.
export function AddTransaction({ customerId, snapshotDate }: { customerId: string; snapshotDate: string }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === "en" ? "en" : "hi";
  const qc = useQueryClient();
  const add = useAddTransaction(customerId);
  const [type, setType] = useState<"debit" | "credit">("debit");
  const [amount, setAmount] = useState<number | null>(45000);
  const [custom, setCustom] = useState("");
  const [category, setCategory] = useState("shopping");
  const [merchant, setMerchant] = useState("");
  const [date, setDate] = useState(snapshotDate);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [before, setBefore] = useState<FeaturesResponse["features"] | null>(null);
  const [createdId, setCreatedId] = useState<string | null>(null);

  const features = useFeatures(customerId);
  const anomalies = useAllAnomalies(customerId);
  const catLabel = (c: string) => (i18n.exists(`cat.${c}`) ? t(`cat.${c}`) : c.replace(/_/g, " "));
  const amountLabel = (v: number) => spokenINR(v, lang) ?? formatINR(v);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (!amount || amount <= 0) errs.amount = t("add.validation.amount");
    if (!merchant.trim()) errs.merchant = t("add.validation.merchant");
    if (!date || date > snapshotDate) errs.date = t("add.validation.date", { date: formatDate(snapshotDate, lang) });
    setErrors(errs);
    if (Object.keys(errs).length) return;
    // Keep the pre-append numbers from the cache to show the movement.
    setBefore(qc.getQueryData<FeaturesResponse>(keys.features(customerId))?.features ?? null);
    add.mutate(
      { txn_date: date, amount: amount!, type, category, merchant: merchant.trim().toUpperCase(), is_recurring: false, txn_time: null, description: null },
      { onSuccess: (r) => setCreatedId(r.id) },
    );
  };

  const reset = () => { add.reset(); setCreatedId(null); setBefore(null); setMerchant(""); };
  const flagged = createdId ? anomalies.data?.anomalies.find((a) => a.transaction_id === createdId) : undefined;
  const after = createdId ? features.data?.features : undefined;
  const waiting = !!createdId && (anomalies.isFetching || features.isFetching);

  if (createdId && add.data) {
    const rows: BARow[] = after && before ? [
      { label: t("enquire.ba.runway"), before: formatMonths(before.liquidity_runway), after: formatMonths(after.liquidity_runway), light: runwayLight(after.liquidity_runway ?? 0) },
      { label: t("enquire.ba.dbr"), before: formatPct(before.dbr), after: formatPct(after.dbr), light: dbrLight(after.dbr ?? 0) },
      { label: t("home.glance.expenses"), before: formatINR(before.monthly_expenses_mean), after: formatINR(after.monthly_expenses_mean), light: (after.monthly_expenses_mean ?? 0) > (before.monthly_expenses_mean ?? 0) ? "care" : "safe" },
      { label: t("feature.anomaly_count"), before: String(before.anomaly_count_30d ?? 0), after: String(after.anomaly_count_30d ?? 0), light: (after.anomaly_count_30d ?? 0) > (before.anomaly_count_30d ?? 0) ? "care" : "safe" },
    ] : [];
    return (
      <Card tone={flagged ? "care" : "safe"} className="flex flex-col gap-4 animate-rise" aria-live="polite">
        <div>
          <h2 className={"flex items-center gap-2 text-xl font-bold " + (flagged ? "text-care-ink" : "text-safe-ink")}>
            {flagged ? <AlertTriangle size={24} aria-hidden /> : <Check size={24} aria-hidden strokeWidth={3} />}
            {waiting ? t("add.checking") : flagged ? t("add.flagged") : t("add.normal")}
          </h2>
          <p className="text-ink-soft">
            {t(add.data.type === "credit" ? "home.anomalies.credit" : "home.anomalies.debit", { amount: formatINR(add.data.amount), merchant: add.data.merchant, date: formatDate(add.data.txn_date, lang) })}
          </p>
        </div>
        {!waiting && (
          <p>{flagged ? t("add.flaggedLead", { score: flagged.anomaly_score.toFixed(2) }) : t("add.normalLead")}</p>
        )}
        {flagged && (
          <ul className="grid gap-1 text-sm sm:grid-cols-3">
            {Object.entries(flagged.features ?? {}).filter(([, v]) => v != null && Number(v) !== 0).sort((x, y) => Math.abs(Number(y[1])) - Math.abs(Number(x[1]))).slice(0, 3).map(([k, v]) => (
              <li key={k} className="flex justify-between gap-2 rounded-lg bg-card px-2 py-1">
                <span>{i18n.exists(`money.why.${k}`) ? t(`money.why.${k}`) : k.replace(/_/g, " ")}</span><span className="font-semibold tabular">{Number(v).toFixed(2)}</span>
              </li>
            ))}
          </ul>
        )}
        {rows.length > 0 && (
          <div className="rounded-xl bg-card p-3">
            <h3 className="mb-2 font-semibold">{t("add.effect")}</h3>
            <BeforeAfter rows={rows} beforeLabel={t("enquire.ba.now")} afterLabel={t("enquire.ba.after")} />
            <p className="mt-2 text-sm text-ink-mute">{t("add.rerun")}</p>
          </div>
        )}
        <div className="grid gap-2 sm:grid-cols-2">
          <Link to={paths.suggest(customerId)} className="inline-flex min-h-touch items-center justify-center gap-2 rounded-xl bg-accent px-4 font-semibold text-white hover:bg-accent-strong">
            {t("add.seeSuggest")} <ArrowRight size={20} aria-hidden />
          </Link>
          <Button onClick={reset} icon={<RotateCcw size={20} aria-hidden />}>{t("add.again")}</Button>
        </div>
      </Card>
    );
  }

  return (
    <Card tone="sand" className="flex flex-col gap-4" aria-labelledby="add-h">
      <div>
        <h2 id="add-h" className="flex items-center gap-2 text-lg font-bold"><PlusCircle size={22} aria-hidden /> {t("add.title")}</h2>
        <p className="text-sm text-ink-soft">{t("add.lead")}</p>
      </div>
      <form className="flex flex-col gap-4" onSubmit={submit} noValidate>
        <fieldset className="flex flex-col gap-2">
          <legend className="font-semibold">{t("add.type")}</legend>
          <ChipGroup name="type" label={t("add.type")} value={type}
            options={[{ value: "debit" as const, label: t("add.spent") }, { value: "credit" as const, label: t("add.received") }]}
            onChange={(v) => { setType(v); setCategory(v === "debit" ? "shopping" : "salary"); }} />
        </fieldset>
        <fieldset className="flex flex-col gap-2">
          <legend className="font-semibold">{t("add.amount")}</legend>
          <ChipGroup name="amount" label={t("add.amount")} value={custom ? null : amount} options={AMOUNTS.map((v) => ({ value: v, label: amountLabel(v) }))} onChange={(v) => { setAmount(v); setCustom(""); }} />
          <label className="flex items-center rounded-xl border border-line bg-card focus-within:border-accent">
            <span className="pl-4 text-lg font-semibold text-ink-mute" aria-hidden>₹</span>
            <span className="sr-only">{t("enquire.customAmount")}</span>
            <input type="text" inputMode="numeric" value={custom} placeholder={t("enquire.amountPlaceholder")} aria-invalid={!!errors.amount || undefined}
              onChange={(e) => { const d = e.target.value.replace(/[^\d]/g, ""); setCustom(d); setAmount(d ? Number(d) : null); }}
              className="min-h-touch w-full bg-transparent px-3 text-lg outline-none tabular" />
          </label>
          {errors.amount && <p role="alert" className="text-sm font-semibold text-care-ink">{errors.amount}</p>}
        </fieldset>
        <fieldset className="flex flex-col gap-2">
          <legend className="font-semibold">{t("add.category")}</legend>
          <ChipGroup name="cat" label={t("add.category")} value={category} options={(type === "debit" ? CATS_OUT : CATS_IN).map((c) => ({ value: c, label: catLabel(c) }))} onChange={setCategory} />
        </fieldset>
        <label className="flex flex-col gap-1">
          <span className="font-semibold">{t("add.merchant")}</span>
          <input value={merchant} onChange={(e) => setMerchant(e.target.value)} placeholder={t("add.merchantPlaceholder")} aria-invalid={!!errors.merchant || undefined}
            className="min-h-touch rounded-xl border border-line bg-card px-4 outline-none focus:border-accent" />
          {errors.merchant && <p role="alert" className="text-sm font-semibold text-care-ink">{errors.merchant}</p>}
        </label>
        <label className="flex flex-col gap-1">
          <span className="font-semibold">{t("add.date")}</span>
          <input type="date" value={date} max={snapshotDate} onChange={(e) => setDate(e.target.value)} aria-invalid={!!errors.date || undefined}
            className="min-h-touch rounded-xl border border-line bg-card px-4 outline-none focus:border-accent tabular" />
          <span className="text-sm text-ink-mute">{t("add.dateHint", { date: formatDate(snapshotDate, lang) })}</span>
          {errors.date && <p role="alert" className="text-sm font-semibold text-care-ink">{errors.date}</p>}
        </label>
        {add.isError && !(add.error instanceof ApiError && add.error.isValidation) && <ErrorState error={add.error} />}
        <Button type="submit" variant="primary" loading={add.isPending} icon={<PlusCircle size={22} aria-hidden />}>
          {add.isPending ? t("add.submitting") : t("add.submit")}
        </Button>
      </form>
    </Card>
  );
}
