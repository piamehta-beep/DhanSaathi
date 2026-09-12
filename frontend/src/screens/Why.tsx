import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import { useRecommendation, useExplain } from "@/api/queries";
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
                </div>
              )}
            </section>
          </>
        )}
      </div>
    </Layout>
  );
}
