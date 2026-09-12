import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams, useSearchParams } from "react-router-dom";
import { Play, X } from "lucide-react";
import { useSimulation, useFeatures, type LoanScenario } from "@/api/queries";
import type { SimulationScenario } from "@/api/client";
import { formatINR, formatPct, formatMonths, spokenINR } from "@/lib/format";
import { paths } from "@/lib/paths";
import { Layout, StickyCta } from "@/ui/Layout";
import { ErrorState } from "@/ui/ErrorState";
import { Money } from "@/ui/Money";
import { Button, Card, CardSkeleton, ChipGroup, FanChart, type FanSeries } from "@/ui";

const AMOUNTS = [50000, 100000, 200000, 500000];
const TENURES = [12, 24, 36, 48, 60];
const RATES = [10.5, 12, 14, 18, 24];

// S8 — the Monte Carlo, month by month, with a "what if" loan overlay.
export function Future() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === "en" ? "en" : "hi";
  const { id = "" } = useParams();
  const [params] = useSearchParams();
  const preAmount = Number(params.get("amount")) || null;
  const preTenure = Number(params.get("tenure")) || 36;

  const [amount, setAmount] = useState<number | null>(preAmount ?? 200000);
  const [custom, setCustom] = useState(preAmount && !AMOUNTS.includes(preAmount) ? String(preAmount) : "");
  const [tenure, setTenure] = useState(preTenure);
  const [rate, setRate] = useState(14);
  const [loan, setLoan] = useState<LoanScenario>(preAmount ? { amount: preAmount, tenure: preTenure, rate: 14 } : null);
  const [months, setMonths] = useState(12);
  const [pathsN, setPathsN] = useState(1000);

  const features = useFeatures(id);
  const baseline = useSimulation(id, null, true, { months, paths: pathsN });
  const withLoan = useSimulation(id, loan, loan !== null, { months, paths: pathsN });
  const safety = features.data?.features.min_buffer ?? null;

  const sim = loan && withLoan.data ? withLoan.data : baseline.data;
  const series: FanSeries[] = [];
  if (sim?.scenarios.baseline) series.push({ key: "baseline", label: t("future.baseline"), scenario: sim.scenarios.baseline, tone: "accent" });
  if (loan && withLoan.data?.scenarios.take_loan) series.push({ key: "take_loan", label: t("future.takeLoan"), scenario: withLoan.data.scenarios.take_loan, tone: "care" });
  if (loan && withLoan.data?.scenarios.smaller_loan) series.push({ key: "smaller_loan", label: t("future.smallerLoan"), scenario: withLoan.data.scenarios.smaller_loan, tone: "ink" });

  const error = (baseline.isError && !baseline.data && baseline.error) || (withLoan.isError && !withLoan.data && withLoan.error);
  const method = sim?.scenarios.baseline?.parameters as { method?: string } | undefined;
  const amountLabel = (v: number) => spokenINR(v, lang) ?? formatINR(v);

  return (
    <Layout back={paths.home(id)} title={t("future.title", { n: months })}>
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-bold">{t("future.title", { n: months })}</h1>
          <p className="text-ink-soft">{t("future.lead", { paths: pathsN.toLocaleString("en-IN") })}</p>
        </div>

        {error ? (
          <ErrorState error={error} onRetry={() => { baseline.refetch(); withLoan.refetch(); }} />
        ) : series.length === 0 ? (
          <>
            <Card className="min-h-[430px]" aria-busy><CardSkeleton lines={6} /></Card>
            <div className="grid gap-3 sm:grid-cols-2"><div className="min-h-[190px]"><CardSkeleton lines={4} /></div></div>
          </>
        ) : (
          <>
            <Card className="animate-rise">
              <FanChart series={series} safetyLine={safety} />
            </Card>

            <div className="grid gap-3 sm:grid-cols-2">
              {series.map((s) => (
                <ScenarioCard key={s.key} label={s.label} scenario={s.scenario} ci={sim?.confidence_bands?.[s.key]?.p_shortfall_12m} tone={s.tone} />
              ))}
            </div>

            {method?.method && (
              <p className="text-sm text-ink-mute">
                {t("future.methodLead", {
                  method: t(method.method === "ou" ? "future.method.ou" : "future.method.bootstrap"),
                  paths: pathsN.toLocaleString("en-IN"), months,
                })}
              </p>
            )}
            <div className="grid gap-3 sm:grid-cols-2">
              <fieldset className="flex flex-col gap-2">
                <legend className="text-sm font-semibold text-ink-mute">{t("sim.months")}</legend>
                <ChipGroup name="months" label={t("sim.months")} value={months} options={[6, 12, 24].map((n) => ({ value: n, label: t("enquire.months", { n }) }))} onChange={setMonths} />
              </fieldset>
              <fieldset className="flex flex-col gap-2">
                <legend className="text-sm font-semibold text-ink-mute">{t("sim.paths")}</legend>
                <ChipGroup name="paths" label={t("sim.paths")} value={pathsN} options={[500, 1000, 2000].map((n) => ({ value: n, label: t("sim.pathsN", { n: n.toLocaleString("en-IN") }) }))} onChange={setPathsN} />
              </fieldset>
            </div>
          </>
        )}

        <Card tone="sand" className="flex flex-col gap-4" aria-labelledby="whatif-h">
          <div>
            <h2 id="whatif-h" className="text-lg font-bold">{t("future.whatIf")}</h2>
            <p className="text-sm text-ink-soft">{t("future.whatIfLead")}</p>
          </div>
          <form className="flex flex-col gap-4" onSubmit={(e) => { e.preventDefault(); if (amount && amount > 0) setLoan({ amount, tenure, rate }); }}>
            <fieldset className="flex flex-col gap-2">
              <legend className="font-semibold">{t("future.amount")}</legend>
              <ChipGroup name="amt" label={t("future.amount")} value={custom ? null : amount} options={AMOUNTS.map((v) => ({ value: v, label: amountLabel(v) }))}
                onChange={(v) => { setAmount(v); setCustom(""); }} />
              <label className="flex items-center rounded-xl border border-line bg-card focus-within:border-accent">
                <span className="pl-4 text-lg font-semibold text-ink-mute" aria-hidden>₹</span>
                <span className="sr-only">{t("enquire.customAmount")}</span>
                <input type="text" inputMode="numeric" value={custom} placeholder={t("enquire.amountPlaceholder")}
                  onChange={(e) => { const d = e.target.value.replace(/[^\d]/g, ""); setCustom(d); setAmount(d ? Number(d) : null); }}
                  className="min-h-touch w-full bg-transparent px-3 text-lg outline-none tabular" />
              </label>
            </fieldset>
            <fieldset className="flex flex-col gap-2">
              <legend className="font-semibold">{t("future.tenure")}</legend>
              <ChipGroup name="ten" label={t("future.tenure")} value={tenure} options={TENURES.map((n) => ({ value: n, label: t("enquire.months", { n }) }))} onChange={setTenure} />
            </fieldset>
            <fieldset className="flex flex-col gap-2">
              <legend className="font-semibold">{t("future.rate")}</legend>
              <ChipGroup name="rate" label={t("future.rate")} value={rate} options={RATES.map((r) => ({ value: r, label: `${r}%` }))} onChange={setRate} />
            </fieldset>
            <StickyCta>
              <div className="flex gap-2">
                <Button type="submit" variant="primary" loading={withLoan.isFetching} icon={<Play size={22} aria-hidden />} disabled={!amount}>
                  {withLoan.isFetching ? t("future.running") : t("future.run")}
                </Button>
                {loan && <Button type="button" className="shrink-0" onClick={() => setLoan(null)} icon={<X size={20} aria-hidden />}>{t("future.clear")}</Button>}
              </div>
            </StickyCta>
          </form>
        </Card>
      </div>
    </Layout>
  );
}

function ScenarioCard({ label, scenario, ci, tone }: { label: string; scenario: SimulationScenario; ci?: { p10?: number; p90?: number } | Record<string, number>; tone: "accent" | "care" | "ink" }) {
  const { t } = useTranslation();
  const p = scenario.p_shortfall_12m;
  const light = p < 0.1 ? "safe" : p <= 0.3 ? "care" : "danger";
  const emi = (scenario.parameters as { loan_emi?: number }).loan_emi;
  const c = ci as { p10?: number; p90?: number } | undefined;
  const lastMonth = Math.max(...Object.keys(scenario.expected_liquidity).map(Number));
  return (
    <Card tone={tone === "accent" ? "accent" : "card"} className="flex flex-col gap-2">
      <div className="font-semibold">{label}</div>
      {emi != null && <div className="text-sm text-ink-soft">{t("future.emi", { amount: formatINR(emi) })}</div>}
      <div>
        <div className="text-sm text-ink-mute">{t("future.shortfall")}</div>
        <div className="flex flex-wrap items-baseline gap-2">
          <span className={"text-2xl font-bold tabular " + (light === "safe" ? "text-safe-ink" : light === "care" ? "text-care-ink" : "text-danger-ink")}>{formatPct(p)}</span>
          {c?.p10 != null && c?.p90 != null && <span className="text-sm text-ink-mute tabular">{t("future.shortfallCI", { lo: formatPct(c.p10), hi: formatPct(c.p90) })}</span>}
        </div>
      </div>
      <div>
        <div className="text-sm text-ink-mute">{t("future.runway")}</div>
        <div className="font-semibold tabular">{t("future.runwayMonths", { months: formatMonths(scenario.expected_runway) })}</div>
      </div>
      <div className="text-sm text-ink-soft tabular">
        {t("future.atMonth", { n: lastMonth })}: <Money value={scenario.expected_liquidity[String(lastMonth)]} />
      </div>
    </Card>
  );
}
