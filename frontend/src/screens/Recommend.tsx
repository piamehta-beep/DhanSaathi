import { useTranslation } from "react-i18next";
import { useParams, Link } from "react-router-dom";
import { HelpCircle, Landmark, Search, Shield, Sparkles, Leaf } from "lucide-react";
import { useRecommendation } from "@/api/queries";
import type { RecommendationResponse } from "@/api/client";
import { recommendMode, vetoKey, vetoNextKey, KNOWN_VETOS, confidenceKey } from "@/copy/mapping";
import { paths } from "@/lib/paths";
import { humanizeExplanation } from "@/copy/explanation";
import { formatINR, spokenINR } from "@/lib/format";
import i18n from "@/i18n";
import { Layout, StickyCta } from "@/ui/Layout";
import { ErrorState } from "@/ui/ErrorState";
import { Money } from "@/ui/Money";
import { Card, LinkButton, Skeleton, StatusChip } from "@/ui";

// S2 — three distinct visual modes, not one template with the text swapped.
export function Recommend() {
  const { t, i18n } = useTranslation();
  const { id = "" } = useParams();
  const rec = useRecommendation(id, i18n.language === "en" ? "en" : "hi");

  return (
    <Layout back={paths.home(id)} title={t("rec.title")}>
      <div className="flex flex-col gap-6">
        {rec.isPending ? (
          <>
            <h1 className="sr-only">{t("rec.title")}</h1>
            <Loading />
          </>
        ) : rec.isError && !rec.data ? (
          <>
            <h1 className="text-2xl font-bold">{t("rec.title")}</h1>
            <ErrorState error={rec.error} onRetry={() => rec.refetch()} />
          </>
        ) : rec.data ? (
          <Result r={rec.data} customerId={id} />
        ) : null}
      </div>
    </Layout>
  );
}

function Loading() {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-4" role="status" aria-live="polite">
      <p className="text-lg font-semibold text-accent-strong">{t("rec.loading")}</p>
      <Skeleton className="h-8 w-2/3" />
      <div className="rounded-2xl border border-line bg-card p-4 flex flex-col gap-3">
        <Skeleton className="h-6 w-1/2" />
        <Skeleton className="h-12 w-1/3" />
        <Skeleton className="h-4 w-3/4" />
      </div>
    </div>
  );
}

function ConfidenceChip({ level }: { level: string }) {
  const { t } = useTranslation();
  const light = level === "high" ? "safe" : level === "medium" ? "safe" : level === "low" ? "care" : "neutral";
  const known = ["high", "medium", "low", "insufficient_data", "insufficient_confidence"].includes(level);
  return (
    <div className="flex flex-wrap items-center gap-2">
      <StatusChip light={light}>{known ? t(`confidence.label.${level}`) : t("confidence.label.low")}</StatusChip>
      <span className="text-sm text-ink-soft">{known ? t(confidenceKey(level)) : t("confidence.low")}</span>
    </div>
  );
}

function productLine(t: (k: string, o?: Record<string, unknown>) => string, r: RecommendationResponse, amount: string) {
  const key = `rec.product.${r.product_type}`;
  const base = t(key, { amount });
  return r.product_type === "personal_loan" && r.tenure_months ? `${base}, ${t("rec.tenure", { months: r.tenure_months })}` : base;
}

function Result({ r, customerId }: { r: RecommendationResponse; customerId: string }) {
  const { t } = useTranslation();
  const mode = recommendMode(r);
  const canCompare = r.product_type === "personal_loan" || r.product_type === "credit_card" || r.product_type === "term_insurance";

  if (mode === "none") {
    const veto = r.veto_reason && KNOWN_VETOS.has(r.veto_reason) ? r.veto_reason : "unknown";
    return (
      <div className="flex flex-col gap-6 animate-rise">
        <div className="flex flex-col gap-3">
          <span className="inline-flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-ink-mute">
            <Leaf size={18} aria-hidden /> {t("rec.none.kicker")}
          </span>
          <h1 className="text-2xl font-bold leading-tight">{t("rec.none.title")}</h1>
        </div>
        <Card tone="sand" className="flex flex-col gap-4">
          <div>
            <h2 className="text-sm font-semibold text-ink-mute">{t("rec.reason")}</h2>
            <p className="text-lg">{t(vetoKey(veto))}</p>
          </div>
          <div>
            <h2 className="text-sm font-semibold text-ink-mute">{t("rec.whatChanges")}</h2>
            <p>{t(vetoNextKey(veto))}</p>
          </div>
        </Card>
        <div className="grid gap-3 sm:grid-cols-2">
          <LinkButton to={paths.why(customerId)} icon={<HelpCircle size={22} aria-hidden />}>{t("rec.whyShort")}</LinkButton>
          <LinkButton to={paths.ask(customerId)} icon={<Search size={22} aria-hidden />}>{t("rec.checkSpecific")}</LinkButton>
        </div>
        <p className="text-sm text-ink-mute">
          {t(r.candidates_feasible === 0 ? "rec.none.checkedNone" : "rec.none.checkedSome", {
            evaluated: r.candidates_evaluated, feasible: r.candidates_feasible,
          })}
        </p>
        <HowWeDecided id={customerId} />
      </div>
    );
  }

  const amountText = formatAmountText(r.amount);
  // One sentence on why: the "matched on" line if the API produced one, else the first.
  const sentences = humanizeExplanation(r.explanation, t);
  const whySentence = sentences.find((x) => /matched|मेल/.test(x)) ?? sentences[0];

  return (
    <div className="flex flex-col gap-6 animate-rise">
      <div className="flex flex-col gap-3">
        {mode === "safer" ? (
          <>
            <span className="inline-flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-accent-strong">
              <Shield size={18} aria-hidden /> {t("rec.safer.kicker")}
            </span>
            <h1 className="text-2xl font-bold leading-tight">{t("rec.safer.lead")}</h1>
          </>
        ) : (
          <>
            <span className="inline-flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-accent-strong">
              <Sparkles size={18} aria-hidden /> {t("rec.yes.kicker")}
            </span>
            <h1 className="text-2xl font-bold leading-tight">{productLine(t, r, amountText)}</h1>
          </>
        )}
      </div>

      <Card tone={mode === "safer" ? "accent" : "card"} className="flex flex-col gap-4">
        {mode === "safer" && <p className="text-lg font-semibold">{productLine(t, r, amountText)}</p>}
        <div>
          <div className="text-sm font-semibold text-ink-mute">{t("rec.monthlyCost")}</div>
          <Money value={r.monthly_cost} big />
        </div>
        {whySentence && <p className="text-ink-soft">{whySentence}</p>}
        <ConfidenceChip level={r.confidence_level} />
        <p className="text-sm text-ink-mute">
          {t("rec.yes.checked", { evaluated: r.candidates_evaluated, feasible: r.candidates_feasible })}
        </p>
      </Card>

      <StickyCta>
        <div className="grid gap-3 sm:grid-cols-2">
          {canCompare && (
            <LinkButton to={paths.banks(customerId)} variant="primary" icon={<Landmark size={22} aria-hidden />}>{t("rec.compare")}</LinkButton>
          )}
          <LinkButton to={paths.why(customerId)} variant={canCompare ? "secondary" : "primary"} icon={<HelpCircle size={22} aria-hidden />}>
            {t("rec.why")}
          </LinkButton>
        </div>
      </StickyCta>
      <HowWeDecided id={customerId} />
    </div>
  );
}

function HowWeDecided({ id }: { id: string }) {
  const { t } = useTranslation();
  return (
    <Link to={paths.why(id)} className="inline-flex min-h-touch items-center gap-2 self-start text-sm font-semibold text-ink-soft underline-offset-4 hover:underline">
      <HelpCircle size={18} aria-hidden /> {t("rec.howDecided")}
    </Link>
  );
}

// Product headline needs the amount as a string inside a sentence.
function formatAmountText(v: number | null | undefined) {
  const lang = i18n.language === "en" ? "en" : "hi";
  const spoken = spokenINR(v, lang);
  return spoken ? `${formatINR(v)} (${spoken})` : formatINR(v);
}
