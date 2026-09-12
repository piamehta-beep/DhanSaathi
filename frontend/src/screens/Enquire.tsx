import { useEffect, useRef, useState } from "react";
import { Trans, useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import { Search, ArrowRight, Check } from "lucide-react";
import { useEnquire } from "@/api/queries";
import { ApiError, type EnquiryResponse } from "@/api/client";
import { KNOWN_VETOS, vetoKey, vetoNextKey, productKey, type ProductType } from "@/copy/mapping";
import { formatINR, spokenINR, formatPct } from "@/lib/format";
import { paths } from "@/lib/paths";
import { Layout, StickyCta } from "@/ui/Layout";
import { ErrorState } from "@/ui/ErrorState";
import { Money } from "@/ui/Money";
import { Button, Card, CheckList, ChipGroup, BeforeAfter, type BARow } from "@/ui";
import { Link } from "react-router-dom";
import { TrendingUp } from "lucide-react";
import { dbrLight, runwayLight, distressBand, bandLight } from "@/copy/mapping";
import { formatMonths } from "@/lib/format";
import { BankCards } from "./BankCards";

type Askable = Exclude<ProductType, "no_action">;
// In an enquiry the debt-ceiling vetoes describe payments *with* the requested
// product, so they get their own sentence; everything else reuses veto.*.
const ENQUIRY_VETO_OVERRIDES = new Set(["post_dbr_exceeds_0.50", "new_loan_dbr_exceeds_0.40"]);
const enquiryVetoKey = (v: string) => (ENQUIRY_VETO_OVERRIDES.has(v) ? `vetoEnquire.${v}` : vetoKey(v));
const PRODUCTS: Askable[] = ["personal_loan", "credit_card", "term_insurance", "mutual_fund_sip"];
// Quick-pick grid matching the backend's candidate grid.
const AMOUNTS: Record<Askable, number[]> = {
  personal_loan: [50000, 100000, 200000, 500000],
  credit_card: [25000, 50000, 100000],
  term_insurance: [1000000, 2500000, 5000000],
  mutual_fund_sip: [500, 1000, 2500, 5000],
};
const TENURES = [12, 24, 36, 48, 60];

// S4 — "Can I afford…?" The strongest single demo moment.
export function Enquire() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === "en" ? "en" : "hi";
  const { id = "" } = useParams();
  const [product, setProduct] = useState<Askable>("personal_loan");
  const [amount, setAmount] = useState<number | null>(500000);
  const [custom, setCustom] = useState("");
  const [tenure, setTenure] = useState<number>(36);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const enquire = useEnquire(id);
  const resultRef = useRef<HTMLDivElement>(null);

  const amountLabel = (v: number) => {
    const s = spokenINR(v, lang);
    return s ?? formatINR(v);
  };

  const submit = (override?: { amount: number; tenure?: number | null }) => {
    const amt = override?.amount ?? amount;
    setFieldError(null);
    if (!amt || amt <= 0) { setFieldError(t("enquire.validation.amount")); return; }
    const ten = override?.tenure !== undefined ? override.tenure : product === "personal_loan" ? tenure : null;
    enquire.mutate(
      { product_type: product, amount: amt, tenure_months: ten },
      {
        onError: (e) => { if (e instanceof ApiError && e.isValidation) setFieldError(t("enquire.validation.server")); },
      },
    );
  };

  useEffect(() => {
    if (enquire.data) resultRef.current?.focus();
  }, [enquire.data]);

  const nonFieldError = enquire.error && !(enquire.error instanceof ApiError && enquire.error.isValidation) ? enquire.error : null;

  return (
    <Layout back={paths.suggest(id)} title={t("enquire.title")}>
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-bold">{t("enquire.title")}</h1>
          <p className="text-ink-soft">{t("enquire.subtitle")}</p>
        </div>

        <form className="flex flex-col gap-5" onSubmit={(e) => { e.preventDefault(); submit(); }} noValidate>
          <fieldset className="flex flex-col gap-2">
            <legend className="font-semibold">{t("enquire.productLabel")}</legend>
            <ChipGroup name="product" label={t("enquire.productLabel")} value={product}
              options={PRODUCTS.map((p) => ({ value: p, label: t(productKey(p)) }))}
              onChange={(p) => { setProduct(p); setAmount(AMOUNTS[p][AMOUNTS[p].length - 1]); setCustom(""); enquire.reset(); }} />
          </fieldset>

          <fieldset className="flex flex-col gap-2">
            <legend className="font-semibold">{t(`enquire.amountLabel.${product}`)}</legend>
            <ChipGroup name="amount" label={t(`enquire.amountLabel.${product}`)} value={custom ? null : amount}
              options={AMOUNTS[product].map((v) => ({ value: v, label: amountLabel(v) }))}
              onChange={(v) => { setAmount(v); setCustom(""); setFieldError(null); }} />
            <label className="mt-1 flex flex-col gap-1 text-sm text-ink-soft">
              {t("enquire.customAmount")}
              <span className="flex items-center rounded-xl border border-line bg-card focus-within:border-accent">
                <span className="pl-4 text-lg font-semibold text-ink-mute" aria-hidden>₹</span>
                <input
                  type="text" inputMode="numeric" pattern="[0-9]*" value={custom}
                  placeholder={t("enquire.amountPlaceholder")}
                  aria-invalid={!!fieldError || undefined}
                  aria-describedby={fieldError ? "amount-err" : undefined}
                  onChange={(e) => {
                    const digits = e.target.value.replace(/[^\d]/g, "");
                    setCustom(digits);
                    setAmount(digits ? Number(digits) : null);
                    setFieldError(null);
                  }}
                  className="min-h-touch w-full bg-transparent px-3 text-lg text-ink outline-none tabular"
                />
              </span>
              {custom && amount && spokenINR(amount, lang) && (
                <span className="text-ink-mute tabular">{formatINR(amount)} · {spokenINR(amount, lang)}</span>
              )}
            </label>
            {fieldError && <p id="amount-err" role="alert" className="text-sm font-semibold text-care-ink">{fieldError}</p>}
          </fieldset>

          {product === "personal_loan" && (
            <fieldset className="flex flex-col gap-2">
              <legend className="font-semibold">{t("enquire.tenureLabel")}</legend>
              <ChipGroup name="tenure" label={t("enquire.tenureLabel")} value={tenure}
                options={TENURES.map((n) => ({ value: n, label: t("enquire.months", { n }) }))}
                onChange={setTenure} />
            </fieldset>
          )}

          <StickyCta>
            <Button type="submit" variant="primary" loading={enquire.isPending} icon={<Search size={24} aria-hidden />}>
              {enquire.isPending ? t("enquire.checking") : t("enquire.check")}
            </Button>
          </StickyCta>
        </form>

        {nonFieldError && <ErrorState error={nonFieldError} onRetry={() => submit()} />}

        {enquire.data && (
          <div ref={resultRef} tabIndex={-1} className="outline-none">
            <Result r={enquire.data} onCheckAmount={(amt, ten) => { setAmount(amt); setCustom(String(amt)); if (ten) setTenure(ten); submit({ amount: amt, tenure: ten }); }} />
          </div>
        )}
      </div>
    </Layout>
  );
}

// Baseline → assessment (→ counter-offer) for the three gate numbers.
function BeforeAfterCard({ r, counterLabel }: { r: EnquiryResponse; counterLabel?: string }) {
  const { t } = useTranslation();
  const a = r.assessment, b = r.baseline, co = r.counter_offer;
  const hasCo = !!co && co.amount != null && co.post_dbr != null;
  const shortLight = (p: number) => bandLight(distressBand(p));
  const rows: BARow[] = [
    { label: t("enquire.ba.dbr"), before: formatPct(b.dbr), after: formatPct(a.post_dbr), light: dbrLight(a.post_dbr),
      extra: hasCo ? { label: counterLabel ?? "", value: formatPct(co!.post_dbr), light: dbrLight(co!.post_dbr!) } : undefined },
    { label: t("enquire.ba.runway"), before: formatMonths(b.liquidity_runway_months ?? b.expected_runway), after: formatMonths(a.post_runway_months), light: runwayLight(a.post_runway_months),
      extra: hasCo && co!.post_runway_months != null ? { label: counterLabel ?? "", value: formatMonths(co!.post_runway_months), light: runwayLight(co!.post_runway_months) } : undefined },
    { label: t("enquire.ba.shortfall"), before: formatPct(b.p_shortfall_12m), after: formatPct(a.post_p_shortfall_12m), light: shortLight(a.post_p_shortfall_12m),
      extra: hasCo && co!.post_p_shortfall_12m != null ? { label: counterLabel ?? "", value: formatPct(co!.post_p_shortfall_12m), light: shortLight(co!.post_p_shortfall_12m) } : undefined },
  ];
  return (
    <Card className="flex flex-col gap-3">
      <h2 className="font-bold">{t("enquire.beforeAfter")}</h2>
      <BeforeAfter rows={rows} beforeLabel={t("enquire.ba.now")} afterLabel={t("enquire.ba.after")} />
      <p className="text-sm text-ink-mute">{t("enquire.distress", { pct: formatPct(r.distress_probability_12m) })}</p>
      {r.requested.product_type === "personal_loan" && (
        <Link to={paths.future(r.customer_id, { amount: r.requested.amount, tenure: r.requested.tenure_months ?? 36 })}
          className="inline-flex min-h-touch items-center gap-1 font-semibold text-accent-strong hover:underline"><TrendingUp size={18} aria-hidden /> {t("enquire.seeFuture")}</Link>
      )}
    </Card>
  );
}

function Result({ r, onCheckAmount }: { r: EnquiryResponse; onCheckAmount: (amount: number, tenure: number | null) => void }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === "en" ? "en" : "hi";
  const a = r.assessment;
  const amountText = (v: number) => { const s = spokenINR(v, lang); return s ? `${formatINR(v)} (${s})` : formatINR(v); };

  if (r.verdict === "affordable") {
    return (
      <div className="flex flex-col gap-4 animate-rise">
        <Card tone="safe" className="flex flex-col gap-3">
          <h2 className="flex items-center gap-2 text-xl font-bold text-safe-ink"><Check size={26} aria-hidden strokeWidth={3} /> {t("enquire.affordable.title")}</h2>
          <p className="text-ink-soft">{t("enquire.affordable.lead", { product: t(productKey(r.requested.product_type)), amount: amountText(r.requested.amount) })}</p>
          <div>
            <div className="text-sm text-ink-mute">{t("enquire.affordable.monthly")}</div>
            <Money value={a.monthly_cost} big />
          </div>
          <p><Trans i18nKey="enquire.affordable.postDbr" values={{ pct: formatPct(a.post_dbr) }} components={{ 1: <strong /> }} /></p>
        </Card>
        <BeforeAfterCard r={r} />
        {r.matching_products.length > 0 ? (
          <>
            <h2 className="text-lg font-bold">{t("enquire.banksForThis")}</h2>
            <BankCards products={r.matching_products} />
          </>
        ) : r.matching_products_note ? (
          <Card tone="sand"><p>{lang === "hi" ? t("enquire.noLender.hi") : r.matching_products_note}</p>{lang === "hi" && <p className="mt-1 text-sm text-ink-mute" lang="en">{r.matching_products_note}</p>}</Card>
        ) : null}
      </div>
    );
  }

  const veto = a.veto_reason && KNOWN_VETOS.has(a.veto_reason) ? a.veto_reason : "unknown";
  const co = r.counter_offer;
  const hasOffer = !!co && co.amount != null && co.amount > 0;
  const blockReason = co?.blocking_reason && KNOWN_VETOS.has(co.blocking_reason) ? co.blocking_reason : veto;

  return (
    <div className="flex flex-col gap-4 animate-rise">
      <Card tone="care" className="flex flex-col gap-3">
        <h2 className="text-xl font-bold text-care-ink">{t("enquire.declined.title")}</h2>
        <p className="text-lg">{t("enquire.declined.lead", { amount: amountText(r.requested.amount) })}</p>
        <p className="text-ink-soft">{t(enquiryVetoKey(veto))}</p>
        <p className="text-sm text-ink-soft">
          <Trans i18nKey="enquire.declined.postDbr" values={{ pct: formatPct(a.post_dbr) }} components={{ 1: <strong /> }} />
        </p>
        {a.constraints_failed.length > 0 && (
          <details className="text-sm">
            <summary className="min-h-[32px] inline-flex cursor-pointer items-center font-semibold text-care-ink">{t("enquire.declined.checks")}</summary>
            <div className="mt-2"><CheckList passed={a.constraints_passed} failed={a.constraints_failed} /></div>
          </details>
        )}
      </Card>

      {hasOffer && co ? (
        <Card tone="safe" className="flex flex-col gap-3">
          <h2 className="font-semibold text-safe-ink">{t("enquire.counter.title")}</h2>
          <div className="text-3xl font-bold leading-none tabular">{t("enquire.counter.upTo", { amount: formatINR(co.amount!) })}</div>
          {spokenINR(co.amount!, lang) && <div className="text-lg text-ink-soft">{spokenINR(co.amount!, lang)}</div>}
          <p className="text-ink-soft">
            {t("enquire.counter.monthly", { amount: formatINR(co.monthly_cost ?? null) })}
            {co.tenure_months ? `, ${t("enquire.counter.tenure", { months: co.tenure_months })}` : ""}
          </p>
          {r.matching_products_note && (
            <p className="text-sm text-ink-soft">{lang === "hi" ? t("enquire.noLender.hi") : r.matching_products_note}</p>
          )}
          <Button variant="primary" onClick={() => onCheckAmount(co.amount!, co.tenure_months ?? null)} icon={<ArrowRight size={24} aria-hidden />}>
            {t("enquire.counter.check", { amount: formatINR(co.amount!) })}
          </Button>
        </Card>
      ) : (
        <Card tone="sand" className="flex flex-col gap-2">
          <h2 className="font-semibold">{t("enquire.blocked.title")}</h2>
          <p className="text-sm text-ink-mute">{t("enquire.blocked.lead")}</p>
          <p className="text-lg">{t(enquiryVetoKey(blockReason))}</p>
          <p className="text-ink-soft">{t(vetoNextKey(blockReason))}</p>
        </Card>
      )}
      <BeforeAfterCard r={r} counterLabel={hasOffer && co ? t("enquire.ba.counter", { amount: formatINR(co.amount!) }) : undefined} />
    </div>
  );
}
