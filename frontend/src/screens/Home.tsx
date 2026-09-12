import { Trans, useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import { ArrowRight, Bell } from "lucide-react";
import { useCustomer, useFeatures, useDistress, useAnomalies, useHealth } from "@/api/queries";
import { ApiError, type AnomalyItem } from "@/api/client";
import { runwayLight, dbrLight, distressBand, bandLight } from "@/copy/mapping";
import { formatPct, formatMonths, formatINR, formatDate } from "@/lib/format";
import { paths } from "@/lib/paths";
import { Layout, StickyCta } from "@/ui/Layout";
import { ErrorState } from "@/ui/ErrorState";
import { StatCard, Card, Banner, LinkButton, CardSkeleton } from "@/ui";

// S1 — "How am I doing?" At most three numbers, each a sentence first.
export function Home() {
  const { t, i18n } = useTranslation();
  const { id = "" } = useParams();
  const lang = i18n.language === "en" ? "en" : "hi";
  const customer = useCustomer(id);
  const features = useFeatures(id);
  const distress = useDistress(id);
  const anomalies = useAnomalies(id);
  const health = useHealth();
  const warming = health.data ? health.data.models.status !== "warm" && health.data.models.status !== "failed" : false;

  // A 404 on the customer or a 403 on features/distress replaces the page.
  const blocking = [customer, features, distress].find(
    (q) => q.error instanceof ApiError && (q.error.isConsent || q.error.isNotFound) && !q.data,
  );
  const nothingLoaded = !customer.data && !features.data && !distress.data;
  const firstError = [customer, features, distress].find((q) => q.isError && !q.data);

  const first = customer.data?.name.split(" ")[0];
  const f = features.data?.features;
  const runway = f?.liquidity_runway ?? null;
  const dbr = f?.dbr ?? null;
  const p = distress.data?.distress_probability_12m ?? null;
  const band = p === null ? null : distressBand(p);
  // A same-day frequency spike arrives as N identical rows; say it once, with a count.
  const anomalyRows = (() => {
    const seen = new Map<string, AnomalyItem & { times: number }>();
    for (const a of anomalies.data?.anomalies ?? []) {
      const k = `${a.txn_date}|${a.merchant}|${a.amount}|${a.type}`;
      const cur = seen.get(k);
      if (cur) cur.times += 1; else seen.set(k, { ...a, times: 1 });
    }
    return [...seen.values()];
  })();

  return (
    <Layout back={paths.welcome}>
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-1">
          {first ? (
            <p className="text-ink-soft">{t("home.greeting", { name: first })}</p>
          ) : (
            <CardSkeleton lines={1} />
          )}
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
                <StatCard
                  light={runwayLight(runway)}
                  statement={<Trans i18nKey="home.runway" values={{ months: formatMonths(runway) }} components={{ 1: <strong className="text-xl" /> }} />}
                />
              )}
              {dbr === null ? <CardSkeleton lines={3} /> : (
                <StatCard
                  light={dbrLight(dbr)}
                  statement={<Trans i18nKey="home.loan" values={{ pct: formatPct(dbr) }} components={{ 1: <strong className="text-xl" /> }} />}
                />
              )}
              {p === null || band === null ? <CardSkeleton lines={3} /> : (
                <StatCard
                  light={bandLight(band)}
                  statement={
                    <span className="flex flex-col gap-1">
                      <span>{t("home.risk")}</span>
                      <strong className="text-2xl capitalize">{t(`band.${band}`)}</strong>
                    </span>
                  }
                  aside={t("home.riskPct", { pct: formatPct(p) })}
                />
              )}
            </div>

            {anomalyRows.length > 0 && (
              <Card tone="sand" className="flex flex-col gap-2" aria-labelledby="anom-h">
                <h2 id="anom-h" className="flex items-center gap-2 font-semibold"><Bell size={20} aria-hidden /> {t("home.anomalies.title")}</h2>
                <ul className="flex flex-col gap-1 text-ink-soft">
                  {anomalyRows.map((a) => (
                    <li key={a.transaction_id}>
                      {t(a.type === "credit" ? "home.anomalies.credit" : "home.anomalies.debit", {
                        amount: formatINR(a.amount), merchant: a.merchant, date: formatDate(a.txn_date, lang),
                      })}
                      {a.times > 1 && <span className="text-ink-mute"> · {t("home.anomalies.times", { n: a.times })}</span>}
                    </li>
                  ))}
                </ul>
                <p className="text-sm text-ink-mute">{t("home.anomalies.note")}</p>
              </Card>
            )}

            <StickyCta>
              {warming && (
                <div className="mb-3 overflow-hidden rounded-xl">
                  <Banner kind="warmup">
                    {t("state.warming")}
                    {health.data?.models.seconds != null && (
                      <span className="ml-2 text-sm opacity-80">{t("state.warmingHint", { seconds: Math.round(health.data.models.seconds) })}</span>
                    )}
                  </Banner>
                </div>
              )}
              <LinkButton to={paths.suggest(id)} variant="primary" icon={<ArrowRight size={24} aria-hidden />}
                aria-disabled={warming || undefined} className={warming ? "pointer-events-none opacity-60" : ""}>
                {t("home.cta")}
              </LinkButton>
            </StickyCta>
          </>
        )}
      </div>
    </Layout>
  );
}
