import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useParams, useSearchParams } from "react-router-dom";
import { useConsent, useConsentMutations } from "@/api/queries";
import { CONSENT_SCOPES, SCOPE_UNLOCKS, scopeKey, type ConsentScope } from "@/copy/mapping";
import { paths } from "@/lib/paths";
import { Layout } from "@/ui/Layout";
import { ErrorState } from "@/ui/ErrorState";
import { Card, CardSkeleton, Toggle } from "@/ui";

// S7 — Consent & your data. Toggles are real: revoking breaks the features.
export function Consent() {
  const { t } = useTranslation();
  const { id = "" } = useParams();
  const [params] = useSearchParams();
  const highlight = params.get("scope");
  const consent = useConsent(id);
  const { grant, revoke } = useConsentMutations(id);
  const rowRefs = useRef<Record<string, HTMLLIElement | null>>({});

  useEffect(() => {
    if (highlight && consent.data) {
      const el = rowRefs.current[highlight];
      el?.scrollIntoView({ block: "center" });
      el?.querySelector<HTMLButtonElement>("button[role=switch]")?.focus();
    }
  }, [highlight, consent.data]);

  const records = consent.data?.consent_records ?? [];
  const byScope = new Map(records.filter((r) => r.active).map((r) => [r.scope, r]));
  const busy = grant.isPending || revoke.isPending;

  const onToggle = (scope: ConsentScope, on: boolean) => {
    const active = byScope.get(scope);
    if (on && !active) {
      // Purpose text is the user-facing sentence for the scope; the backend stores it verbatim.
      grant.mutate({ scope, purpose: t(scopeKey(scope), { lng: "en" }) });
    } else if (!on && active) {
      revoke.mutate(active.id);
    }
  };

  return (
    <Layout back={paths.home(id)} title={t("consent.title")}>
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-bold">{t("consent.title")}</h1>
          <p className="text-ink-soft">{t("consent.intro")}</p>
        </div>
        {consent.isError && !consent.data ? (
          <ErrorState error={consent.error} onRetry={() => consent.refetch()} />
        ) : !consent.data ? (
          <div className="flex flex-col gap-3"><CardSkeleton /><CardSkeleton /><CardSkeleton /></div>
        ) : (
          <ul className="flex flex-col gap-3">
            {CONSENT_SCOPES.map((scope) => {
              const on = byScope.has(scope);
              const labelId = `scope-${scope}`;
              const unlocks = SCOPE_UNLOCKS[scope];
              const hl = highlight === scope;
              return (
                <li key={scope} ref={(el) => { rowRefs.current[scope] = el; }}>
                  <Card className={"flex items-start gap-4 transition-colors duration-200 " + (hl ? "ring-2 ring-accent" : "")}>
                    <div className="flex-1 flex flex-col gap-1">
                      <span id={labelId} className="font-semibold">{t(scopeKey(scope))}</span>
                      <span className="text-sm text-ink-soft">
                        {unlocks.length > 0
                          ? `${t("consent.unlocks")} ${unlocks.map((u) => t(`screen.${u}`)).join(" · ")}`
                          : t("consent.nothingUnlocks")}
                      </span>
                      {scope === "marketing" && <span className="text-sm text-ink-mute">{t("consent.marketingNote")}</span>}
                      {hl && <span className="text-sm font-semibold text-accent-strong">{t("consent.needed")}</span>}
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <Toggle checked={on} disabled={busy} labelledBy={labelId} onChange={(v) => onToggle(scope, v)} />
                      <span className="text-sm text-ink-mute">{busy ? t("consent.saving") : on ? t("consent.on") : t("consent.off")}</span>
                    </div>
                  </Card>
                </li>
              );
            })}
          </ul>
        )}
        {(grant.isError || revoke.isError) && <ErrorState error={grant.error ?? revoke.error} />}
      </div>
    </Layout>
  );
}
