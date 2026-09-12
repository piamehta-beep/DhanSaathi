import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import { useRecommendation, useExplain, useDistress } from "@/api/queries";
import { Link } from "react-router-dom";
import { ScrollText } from "lucide-react";
import { canonicalFeature, KNOWN_FEATURES, featureKey } from "@/copy/mapping";
import { formatScore } from "@/lib/format";
import { confidenceKey, productKey, vetoKey, KNOWN_VETOS } from "@/copy/mapping";
import { humanizeExplanation } from "@/copy/explanation";
import { paths } from "@/lib/paths";
import { Layout } from "@/ui/Layout";
import { ErrorState } from "@/ui/ErrorState";
import { Card, CardSkeleton, CheckList, BarRow } from "@/ui";

// S5 — "Why?" The safety checklist first, then what drove the decision.
export function Why() {
  const { t, i18n } = useTranslation();
  const { id = "" } = useParams();
  const rec = useRecommendation(id, i18n.language === "en" ? "en" : "hi");
  const explain = useExplain(id, rec.data?.recommendation_id ?? undefined);
  const error = (rec.isError && !rec.data && rec.error) || (explain.isError && !explain.data && explain.error);

  const r = rec.data;
  const x = explain.data;
  const shap = (x?.shap_values ?? r?.shap_values ?? []).slice(0, 5);
  const max = Math.max(0, ...shap.map((s) => Math.abs(s.shap)));
  const passed = r?.constraints_passed ?? [];
  const failed = x?.constraints_failed ?? r?.constraints_failed ?? [];
  const veto = x?.veto_reason ?? r?.veto_reason ?? null;
  const level = x?.confidence_level ?? r?.confidence_level;
  const known = level && ["high", "medium", "low", "insufficient_data", "insufficient_confidence"].includes(level);
  const explanation = x?.explanation ?? r?.explanation;
  const distress = useDistress(id);
  const nm = (x?.need_match_attribution ?? r?.need_match_attribution ?? []).slice(0, 5);
  const nmMax = Math.max(0, ...nm.map((s) => Math.abs(s.shap)));
  const models = (x?.model_used ?? "").split("+").map((m) => m.trim()).filter(Boolean);
  const ci = (x?.confidence_interval ?? r?.confidence_interval) as { cbs_low?: number | null; cbs_high?: number | null } | null | undefined;
  const hazards = Object.entries(distress.data?.hazard_ratios ?? {})
    .map(([k, v]) => ({ key: canonicalFeature(k), raw: k, v }))
    .filter((h) => KNOWN_FEATURES.has(h.key))
    .sort((a, b) => Math.abs(Math.log(b.v)) - Math.abs(Math.log(a.v)));

  return (
    <Layout back={paths.suggest(id)} title={t("why.title")}>
      <div className="flex flex-col gap-8">
        <div>
          <h1 className="text-2xl font-bold">{t("why.title")}</h1>
          {r && (
            <p className="text-ink-soft">
              {t("why.decision")}: <strong>{t(productKey(r.product_type))}</strong>
            </p>
          )}
        </div>

        {error ? (
          <ErrorState error={error} onRetry={() => { rec.refetch(); explain.refetch(); }} />
        ) : !r ? (
          <div className="flex flex-col gap-3"><CardSkeleton lines={4} /><CardSkeleton lines={4} /></div>
        ) : (
          <>
            <section className="flex flex-col gap-3" aria-labelledby="chk-h">
              <div>
                <h2 id="chk-h" className="text-lg font-bold">{t("why.checklist")}</h2>
                <p className="text-sm text-ink-soft">{t("why.checklistIntro")}</p>
              </div>
              {passed.length + failed.length > 0 ? (
                <CheckList passed={passed} failed={failed} />
              ) : veto ? (
                <Card tone="sand"><p>{t(vetoKey(KNOWN_VETOS.has(veto) ? veto : "unknown"))}</p></Card>
              ) : null}
              {veto && passed.length + failed.length > 0 && (
                <p className="text-care-ink">{t(vetoKey(KNOWN_VETOS.has(veto) ? veto : "unknown"))}</p>
              )}
            </section>

            <section className="flex flex-col gap-3" aria-labelledby="drv-h">
              <div>
                <h2 id="drv-h" className="text-lg font-bold">{t("why.drivers")}</h2>
                <p className="text-sm text-ink-soft">{t("why.driversIntro")}</p>
              </div>
              {shap.length === 0 ? (
                <Card tone="sand"><p>{t("why.noAttribution")}</p></Card>
              ) : (
                <Card className="animate-rise">
                  <ul className="flex flex-col gap-4">
                    {shap.map((s) => <BarRow key={s.feature} feature={s.feature} shap={s.shap} direction={s.direction} max={max} />)}
                  </ul>
                </Card>
              )}
              {explanation && (
                <div>
                  <h3 className="text-sm font-semibold text-ink-mute">{t("why.summary")}</h3>
                  <p>{humanizeExplanation(explanation, t).join(" ")}</p>
                </div>
              )}
              {level && (
                <div>
                  <h3 className="text-sm font-semibold text-ink-mute">{t("why.confidence")}</h3>
                  <p>{known ? t(confidenceKey(level)) : t("confidence.low")}</p>
                  {ci?.cbs_low != null && ci?.cbs_high != null && <p className="text-sm text-ink-mute tabular">{t("why.ci", { lo: formatScore(ci.cbs_low), hi: formatScore(ci.cbs_high) })}</p>}
                </div>
              )}
            </section>

            {nm.length > 0 && r.product_type !== "no_action" && (
              <section className="flex flex-col gap-3" aria-labelledby="nm-h">
                <div>
                  <h2 id="nm-h" className="text-lg font-bold">{t("why.needMatch")}</h2>
                  <p className="text-sm text-ink-soft">{t("why.needMatchIntro")}</p>
                </div>
                <Card>
                  <ul className="flex flex-col gap-4">
                    {nm.map((s) => <BarRow key={s.feature} feature={s.feature} shap={s.shap} direction={s.direction} max={nmMax} words={{ up: t("rec.needMatch.up"), down: t("rec.needMatch.down") }} />)}
                  </ul>
                </Card>
              </section>
            )}

            {hazards.length > 0 && (
              <section className="flex flex-col gap-3" aria-labelledby="hz-h">
                <div>
                  <h2 id="hz-h" className="text-lg font-bold">{t("why.hazard")}</h2>
                  <p className="text-sm text-ink-soft">{t("why.hazardIntro")}</p>
                </div>
                <Card>
                  <ul className="grid gap-2 sm:grid-cols-2">
                    {hazards.map((h) => (
                      <li key={h.raw} className="flex items-center justify-between gap-2 rounded-xl bg-sand px-3 py-2 text-sm">
                        <span>{t(featureKey(h.key))}</span>
                        <span className={"shrink-0 font-semibold tabular " + (h.v > 1 ? "text-care-ink" : "text-safe-ink")}>{t("why.hazardX", { x: h.v.toFixed(2) })}</span>
                      </li>
                    ))}
                  </ul>
                  {distress.data && <p className="mt-3 text-sm text-ink-mute">{t("why.modelQuality", { c: distress.data.concordance_index.toFixed(2) })}</p>}
                </Card>
              </section>
            )}

            {models.length > 0 && (
              <section className="flex flex-col gap-2" aria-labelledby="md-h">
                <h2 id="md-h" className="text-sm font-semibold text-ink-mute">{t("why.models")}</h2>
                <ul className="flex flex-wrap gap-2">
                  {models.map((m) => <li key={m} className="rounded-full bg-sand px-3 py-1 text-sm">{i18n.exists(`why.model.${m}`) ? t(`why.model.${m}`) : m.replace(/_/g, " ")}</li>)}
                  {distress.data?.fallback_model && <li className="rounded-full bg-sand px-3 py-1 text-sm">{t("why.model.discrete_time_hazard")}</li>}
                </ul>
              </section>
            )}

            <Link to={paths.trail(id)} className="inline-flex min-h-touch items-center gap-2 self-start text-sm font-semibold text-ink-soft underline-offset-4 hover:underline">
              <ScrollText size={18} aria-hidden /> {t("why.trail")}
            </Link>
          </>
        )}
      </div>
    </Layout>
  );
}
