import { Trans, useTranslation } from "react-i18next";
import { useParams, Link } from "react-router-dom";
import { ArrowRight, Bell, TrendingUp, Receipt, HeartPulse } from "lucide-react";
import { useCustomer, useFeatures, useDistress, useAnomalies, useHealth, useSimulation } from "@/api/queries";
import { ApiError, type AnomalyItem } from "@/api/client";
import { runwayLight, dbrLight, distressBand, bandLight, canonicalFeature, KNOWN_FEATURES, featureKey } from "@/copy/mapping";
import { formatPct, formatMonths, formatINR, formatDate } from "@/lib/format";
import { paths } from "@/lib/paths";
import { Layout, StickyCta } from "@/ui/Layout";
import { ErrorState } from "@/ui/ErrorState";
import { Money } from "@/ui/Money";
import { StatCard, Card, Banner, LinkButton, CardSkeleton, FanChart, SurvivalCurve } from "@/ui";

// S1 — "How am I doing?" Three headline statements first; then the
// projection, the survival curve, what drives it, and the raw numbers.
export function Home() {
  const { t, i18n } = useTranslation();
  const { id = "" } = useParams();
  const lang = i18n.language === "en" ? "en" : "hi";
  const customer = useCustomer(id);
  const features = useFeatures(id);
  const distress = useDistress(id);
  const anomalies = useAnomalies(id);
  const sim = useSimulation(id, null);
  const health = useHealth();
  const warming = health.data ? health.data.models.status !== "warm" && health.data.models.status !== "failed" : false;

  const blocking = [customer, features, distress].find(
    (q) => q.error instanceof ApiError && (q.error.isConsent || q.error.isNotFound) && !q.data,
  );
  const nothingLoaded = !customer.data && !features.data && !distress.data;
  const firstError = [customer, features, distress].find((q) => q.isError && !q.data);

  const first = customer.data?.name.split(" ")[0];
  const f = features.data?.features;
  const runway = f?.liquidity_runway ?? null;
  const dbr = f?.dbr ?? null;
  const d = distress.data;
  const p = d?.distress_probability_12m ?? null;
  const band = p === null ? null : distressBand(p);

  const anomalyRows = (() => {
    const seen = new Map<string, AnomalyItem & { times: number }>();
    for (const a of anomalies.data?.anomalies ?? []) {
      const k = `${a.txn_date}|${a.merchant}|${a.amount}|${a.type}`;
      const cur = seen.get(k);
      if (cur) cur.times += 1; else seen.set(k, { ...a, times: 1 });
    }
    return [...seen.values()];
  })();

  // Hazard ratios: sort by distance from 1 (no effect) and take the top 4.
  const hazards = Object.entries(d?.hazard_ratios ?? {})
    .map(([k, v]) => ({ key: canonicalFeature(k), raw: k, v }))
    .filter((h) => KNOWN_FEATURES.has(h.key))
    .sort((a, b) => Math.abs(Math.log(b.v)) - Math.abs(Math.log(a.v))).slice(0, 4);
  const baseline = sim.data?.scenarios.baseline;

  return (
    <Layout back={paths.welcome}>
      <div className="flex flex-col gap-8">
        <div className="flex flex-col gap-1">
          {first ? <p className="text-ink-soft">{t("home.greeting", { name: first })}</p> : <CardSkeleton lines={1} />}
          <h1 className="text-2xl font-bold">{t("home.title")}</h1>
        </div>

        {blocking ? (
          <ErrorState error={blocking.error} onRetry={() => blocking.refetch()} />
        ) : nothingLoaded && firstError ? (
          <ErrorState error={firstError.error} onRetry={() => { customer.refetch(); features.refetch(); distress.refetch(); }} />
        ) : (
          <>
            <div className="grid gap-3 sm:grid-cols-3">
              {runway === null ? <CardSkeleton lines={3} /> : (
                <StatCard light={runwayLight(runway)} statement={<Trans i18nKey="home.runway" values={{ months: formatMonths(runway) }} components={{ 1: <strong className="text-xl" /> }} />} />
              )}
              {dbr === null ? <CardSkeleton lines={3} /> : (
                <StatCard light={dbrLight(dbr)} statement={<Trans i18nKey="home.loan" values={{ pct: formatPct(dbr) }} components={{ 1: <strong className="text-xl" /> }} />} />
              )}
              {p === null || band === null ? <CardSkeleton lines={3} /> : (
                <StatCard light={bandLight(band)}
                  statement={<span className="flex flex-col gap-1"><span>{t("home.risk")}</span><strong className="text-2xl capitalize">{t(`band.${band}`)}</strong></span>}
                  aside={t("home.riskPct", { pct: formatPct(p) })} />
              )}
            </div>

            <StickyCta>
              {warming && (
                <div className="mb-3 overflow-hidden rounded-xl">
                  <Banner kind="warmup">
                    {t("state.warming")}
                    {health.data?.models.seconds != null && <span className="ml-2 text-sm opacity-80">{t("state.warmingHint", { seconds: Math.round(health.data.models.seconds) })}</span>}
                  </Banner>
                </div>
              )}
              <LinkButton to={paths.suggest(id)} variant="primary" icon={<ArrowRight size={24} aria-hidden />}
                aria-disabled={warming || undefined} className={warming ? "pointer-events-none opacity-60" : ""}>
                {t("home.cta")}
              </LinkButton>
            </StickyCta>

            <section className="flex flex-col gap-3" aria-labelledby="fut-h">
              <div>
                <h2 id="fut-h" className="flex items-center gap-2 text-lg font-bold"><TrendingUp size={22} aria-hidden /> {t("home.future.title")}</h2>
                <p className="text-sm text-ink-soft">{t("home.future.lead")}</p>
              </div>
              {baseline ? (
                <Card className="animate-rise">
                  <FanChart compact series={[{ key: "baseline", label: t("future.baseline"), scenario: baseline, tone: "accent" }]} safetyLine={f?.min_buffer ?? null} />
                  <Link to={paths.future(id)} className="mt-3 inline-flex min-h-touch items-center gap-1 font-semibold text-accent-strong hover:underline">{t("home.future.link")} <ArrowRight size={18} aria-hidden /></Link>
                </Card>
              ) : sim.isError ? null : <div className="min-h-[330px]"><CardSkeleton lines={5} /></div>}
            </section>

            {d && (
              <section className="flex flex-col gap-3" aria-labelledby="surv-h">
                <div>
                  <h2 id="surv-h" className="flex items-center gap-2 text-lg font-bold"><HeartPulse size={22} aria-hidden /> {t("home.survival.title")}</h2>
                  <p className="text-sm text-ink-soft">{t("home.survival.lead")}</p>
                </div>
                <Card className="flex flex-col gap-4 animate-rise">
                  <SurvivalCurve points={d.survival_function} />
                  {d.median_survival_time_months != null && <p className="text-sm text-care-ink">{t("home.survival.median", { months: formatMonths(d.median_survival_time_months) })}</p>}
                  <div className="rounded-xl bg-sand px-3 py-2 text-sm">
                    <p className="font-semibold">{t("home.twoModels", { a: formatPct(d.distress_probability_12m), b: formatPct(d.fallback_model.distress_probability_12m) })}</p>
                    <p className="text-ink-soft">{t("home.twoModelsLead")}</p>
                  </div>
                  {hazards.length > 0 && (
                    <div className="flex flex-col gap-2">
                      <h3 className="text-sm font-semibold text-ink-mute">{t("home.drivers.title")}</h3>
                      <ul className="grid gap-2 sm:grid-cols-2">
                        {hazards.map((h) => (
                          <li key={h.raw} className="flex items-center justify-between gap-2 rounded-xl bg-sand px-3 py-2 text-sm">
                            <span>{t(featureKey(h.key))}</span>
                            <span className={"shrink-0 font-semibold tabular " + (h.v > 1 ? "text-care-ink" : "text-safe-ink")}>{t("why.hazardX", { x: h.v.toFixed(2) })} · {h.v > 1 ? t("why.raises") : t("why.lowers")}</span>
                          </li>
                        ))}
                      </ul>
                      <p className="text-sm text-ink-mute">{t("why.modelQuality", { c: d.concordance_index.toFixed(2) })}</p>
                    </div>
                  )}
                </Card>
              </section>
            )}

            {f && (
              <section className="flex flex-col gap-3" aria-labelledby="glance-h">
                <h2 id="glance-h" className="flex items-center gap-2 text-lg font-bold"><Receipt size={22} aria-hidden /> {t("home.glance.title")}</h2>
                <Card className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm sm:grid-cols-4">
                  <Stat label={t("home.glance.income")} value={<Money value={f.monthly_income_mean} />} />
                  <Stat label={t("home.glance.expenses")} value={<Money value={f.monthly_expenses_mean} />} />
                  <Stat label={t("home.glance.savings")} value={<Money value={f.liquid_savings} />} />
                  <Stat label={t("home.glance.savingsRate")} value={formatPct(f.savings_rate)} />
                  <Stat label={t("home.glance.emi")} value={<Money value={f.total_emi} />} sub={f.obligation_count != null ? t("home.glance.obligations", { n: f.obligation_count }) : undefined} />
                  <Stat label={t("home.glance.stability")} value={formatPct(f.income_stability)} />
                  <Stat label={t("home.glance.volatility")} value={formatPct(f.expense_volatility)} />
                  {f.credit_utilization != null ? <Stat label={t("home.glance.creditUtil")} value={formatPct(f.credit_utilization)} /> : <Stat label={t("home.glance.months", { n: formatMonths(f.data_months) })} value="" />}
                  <Link to={paths.money(id)} className="col-span-2 inline-flex min-h-touch items-center gap-1 font-semibold text-accent-strong hover:underline sm:col-span-4">{t("home.glance.link")} <ArrowRight size={18} aria-hidden /></Link>
                </Card>
              </section>
            )}

            {anomalyRows.length > 0 && (
              <Card tone="sand" className="flex flex-col gap-2" aria-labelledby="anom-h">
                <h2 id="anom-h" className="flex items-center gap-2 font-semibold"><Bell size={20} aria-hidden /> {t("home.anomalies.title")}</h2>
                <ul className="flex flex-col gap-1 text-ink-soft">
                  {anomalyRows.map((a) => (
                    <li key={a.transaction_id}>
                      {t(a.type === "credit" ? "home.anomalies.credit" : "home.anomalies.debit", { amount: formatINR(a.amount), merchant: a.merchant, date: formatDate(a.txn_date, lang) })}
                      {a.times > 1 && <span className="text-ink-mute"> · {t("home.anomalies.times", { n: a.times })}</span>}
                    </li>
                  ))}
                </ul>
                <p className="text-sm text-ink-mute">{t("home.anomalies.note")}</p>
              </Card>
            )}
          </>
        )}
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
