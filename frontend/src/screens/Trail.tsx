import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import { Sparkles, ShieldOff, ShieldCheck, ShieldAlert, ChevronDown, Fingerprint } from "lucide-react";
import { useQueries } from "@tanstack/react-query";
import { useAudit, keys, retryPolicy } from "@/api/queries";
import { api, type AuditLogItem } from "@/api/client";
import i18n from "@/i18n";
import { productKey, vetoKey, KNOWN_VETOS, scopeKey } from "@/copy/mapping";
import { formatDateTime, formatScore } from "@/lib/format";
import { paths } from "@/lib/paths";
import { Layout } from "@/ui/Layout";
import { ErrorState } from "@/ui/ErrorState";
import { Button, Card, CardSkeleton, Timeline } from "@/ui";

const PAGE = 25;

// S10 — the audit log as a timeline. Every decision, its module, and the
// SHA-256 of its inputs. Repeated hashes prove determinism, so we say so.
export function Trail() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === "en" ? "en" : "hi";
  const { id = "" } = useParams();
  const [pages, setPages] = useState(1);
  const first = useAudit(id, 0, PAGE);

  return (
    <Layout back={paths.home(id)} title={t("trail.title")}>
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-bold">{t("trail.title")}</h1>
          <p className="text-ink-soft">{t("trail.lead")}</p>
        </div>
        {first.isError && !first.data ? (
          <ErrorState error={first.error} onRetry={() => first.refetch()} />
        ) : !first.data ? (
          <><CardSkeleton /><CardSkeleton /></>
        ) : first.data.logs.length === 0 ? (
          <Card tone="sand"><p>{t("trail.empty")}</p></Card>
        ) : (
          <>
            <p className="text-sm text-ink-mute">{t("trail.total", { total: first.data.total })}</p>
            <Pages id={id} pages={pages} lang={lang} />
            {pages * PAGE < first.data.total && <Button onClick={() => setPages((p) => p + 1)} icon={<ChevronDown size={20} aria-hidden />}>{t("trail.more")}</Button>}
          </>
        )}
      </div>
    </Layout>
  );
}

// One query per page via useQueries (the count only grows). The API returns
// newest first, so the "previous" event for the determinism note is i + 1.
function Pages({ id, pages, lang }: { id: string; pages: number; lang: "hi" | "en" }) {
  const results = useQueries({
    queries: Array.from({ length: pages }, (_, i) => ({
      queryKey: [...keys.audit(id, i * PAGE), PAGE],
      queryFn: () => api.audit(id, { limit: PAGE, offset: i * PAGE }),
      retry: retryPolicy,
    })),
  });
  const logs: AuditLogItem[] = results.flatMap((r) => r.data?.logs ?? []);
  // Consecutive events with the same action and input hash are one decision
  // repeated; show it once with the count — the repeat *is* the evidence.
  const grouped: { item: AuditLogItem; times: number; last: string }[] = [];
  for (const l of logs) {
    const g = grouped[grouped.length - 1];
    if (g && g.item.action === l.action && g.item.input_hash === l.input_hash) { g.times += 1; g.last = l.timestamp; }
    else grouped.push({ item: l, times: 1, last: l.timestamp });
  }
  return <Timeline items={grouped.map((g) => toItem(g.item, g.times, g.last, lang))} />;
}

function toItem(l: AuditLogItem, times: number, last: string, lang: "hi" | "en") {
  const t = (k: string, o?: Record<string, unknown>) => (i18nT(k, o));
  const s = (l.output_summary ?? {}) as Record<string, unknown>;
  const known = ["recommendation_generated", "safety_veto", "consent_granted", "consent_revoked", "consent_denied"].includes(l.action);
  const title = t(known ? `trail.action.${l.action}` : "trail.action.unknown");
  const tone = l.action === "safety_veto" ? "care" : l.action === "consent_revoked" || l.action === "consent_denied" ? "neutral" : l.action === "consent_granted" ? "accent" : "safe";
  const icon = l.action === "safety_veto" ? <ShieldAlert size={18} /> : l.action === "consent_revoked" || l.action === "consent_denied" ? <ShieldOff size={18} /> : l.action === "consent_granted" ? <ShieldCheck size={18} /> : <Sparkles size={18} />;
  const module = i18nExists(`trail.module.${l.module}`) ? t(`trail.module.${l.module}`) : l.module;

  const bits: string[] = [];
  if (typeof s.product === "string") bits.push(t(productKey(s.product)));
  if (typeof s.cbs === "number") bits.push(t("trail.cbs", { score: formatScore(s.cbs) }));
  if (typeof s.veto_reason === "string") bits.push(t(vetoKey(KNOWN_VETOS.has(s.veto_reason) ? s.veto_reason : "unknown")));
  if (typeof s.scope === "string") bits.push(t("trail.scope", { scope: i18nExists(scopeKey(s.scope)) ? t(scopeKey(s.scope)) : s.scope }));

  return {
    key: l.id, icon, tone: tone as "safe" | "care" | "neutral" | "accent", title,
    meta: (times > 1 ? `${formatDateTime(last, lang)} – ${formatDateTime(l.timestamp, lang)} · ` : `${formatDateTime(l.timestamp, lang)} · `) + module,
    body: (
      <div className="flex flex-col gap-1">
        {bits.length > 0 && <p>{bits.join(" · ")}</p>}
        <p className="inline-flex items-center gap-1 font-mono text-xs text-ink-mute"><Fingerprint size={14} aria-hidden /> {t("trail.inputs")}: {l.input_hash.slice(0, 16)}…</p>
        {times > 1 && <p className="text-accent-strong">{t("trail.repeated", { n: times })}</p>}
      </div>
    ),
  };
}

const i18nT = (k: string, o?: Record<string, unknown>) => i18n.t(k, o) as string;
const i18nExists = (k: string) => i18n.exists(k);
