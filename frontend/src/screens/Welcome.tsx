import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { ArrowRight, Sparkles, ChevronDown, Search, Info } from "lucide-react";
import { useQueries } from "@tanstack/react-query";
import { api } from "@/api/client";
import { keys, retryPolicy, useCustomerPage } from "@/api/queries";
import { PERSONAS, personaKey, runwayLight, dbrLight } from "@/copy/mapping";
import { formatMonths, formatPct, formatINR } from "@/lib/format";
import { paths } from "@/lib/paths";
import { Layout } from "@/ui/Layout";
import { CardSkeleton, ChipGroup, StatusChip, Button } from "@/ui";
import { ErrorState } from "@/ui/ErrorState";

const PAGE = 12;

// S0 — "Try DhanSaathi as…": six quick-start personas, then the full
// 1,000-customer browser with persona filter and name search.
export function Welcome() {
  const { t } = useTranslation();
  const results = useQueries({
    queries: PERSONAS.map((p) => ({
      queryKey: [...keys.customers(p), 1],
      queryFn: () => api.customers({ persona: p, limit: 1 }),
      retry: retryPolicy,
      staleTime: 10 * 60_000,
    })),
  });
  const allFailed = results.every((r) => r.isError);

  return (
    <Layout>
      <div className="flex flex-col gap-8">
        <div className="flex flex-col gap-2">
          <span className="text-sm font-semibold uppercase tracking-wide text-accent-strong">{t("welcome.kicker")}</span>
          <h1 className="text-2xl font-bold leading-tight">{t("app.tagline")}</h1>
          <p className="text-ink-soft">{t("welcome.subtitle")}</p>
        </div>

        <section className="flex flex-col gap-3" aria-labelledby="quick-h">
          <h2 id="quick-h" className="text-lg font-bold">{t("welcome.quick")}</h2>
          {allFailed ? (
            <ErrorState error={results[0].error} onRetry={() => results.forEach((r) => r.refetch())} />
          ) : (
            <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {PERSONAS.map((p, i) => {
                const c = results[i].data?.customers[0];
                if (!c) return <li key={p}><CardSkeleton /></li>;
                const first = c.name.split(" ")[0];
                return (
                  <li key={p} className="animate-rise">
                    <Link to={paths.home(c.id)} className="group flex h-full flex-col gap-3 rounded-2xl border border-line bg-card p-4 shadow-card transition-colors duration-150 hover:border-accent focus-visible:border-accent">
                      <div>
                        <div className="text-lg font-bold">{first}</div>
                        <div className="text-sm text-ink-mute">{t("welcome.ageCity", { age: c.age, city: c.city })}</div>
                      </div>
                      <p className="flex-1 text-ink-soft">{t(personaKey(p))}</p>
                      <span className="inline-flex min-h-touch items-center justify-between rounded-xl bg-accent-soft px-4 font-semibold text-accent-strong transition-colors duration-150 group-hover:bg-accent group-hover:text-white">
                        {t("welcome.continueAs", { name: first })} <ArrowRight size={22} aria-hidden />
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        <Browser />

        <div className="flex flex-wrap gap-x-6 gap-y-1">
          <Link to={paths.onboarding} className="inline-flex min-h-touch items-center gap-2 rounded-xl px-1 font-semibold text-accent-strong hover:underline">
            <Sparkles size={20} aria-hidden /> {t("welcome.newLink")}
          </Link>
          <Link to={paths.about} className="inline-flex min-h-touch items-center gap-2 rounded-xl px-1 font-semibold text-accent-strong hover:underline">
            <Info size={20} aria-hidden /> {t("about.link")}
          </Link>
        </div>
        <p className="text-sm text-ink-mute">{t("welcome.demoNote")}</p>
      </div>
    </Layout>
  );
}

function Browser() {
  const { t } = useTranslation();
  const [persona, setPersona] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [pages, setPages] = useState(1);
  const first = useCustomerPage(persona === "all" ? undefined : persona, 0, PAGE);
  const total = first.data?.total ?? 0;
  const q = search.trim().toLowerCase();

  return (
    <section className="flex flex-col gap-3" aria-labelledby="browse-h">
      <div>
        <h2 id="browse-h" className="text-lg font-bold">{t("welcome.browse")}</h2>
        <p className="text-sm text-ink-soft">{t("welcome.browseHint")}</p>
      </div>
      <ChipGroup name="persona" label={t("welcome.all")} value={persona}
        options={[{ value: "all", label: t("welcome.all") }, ...PERSONAS.map((p) => ({ value: p, label: t(personaKey(p)) }))]}
        onChange={(p) => { setPersona(p); setPages(1); }} />
      <label className="flex items-center gap-2 rounded-xl border border-line bg-card px-3 focus-within:border-accent">
        <Search size={20} aria-hidden className="text-ink-mute" />
        <span className="sr-only">{t("welcome.search")}</span>
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder={t("welcome.searchPlaceholder")} className="min-h-touch w-full bg-transparent outline-none" />
      </label>
      {first.isError && !first.data ? (
        <ErrorState error={first.error} onRetry={() => first.refetch()} />
      ) : !first.data ? (
        <CardSkeleton lines={4} />
      ) : (
        <>
          <p className="text-sm text-ink-mute">{t("welcome.showing", { count: Math.min(pages * PAGE, total), total })}</p>
          <ul className="divide-y divide-line rounded-2xl border border-line bg-card">
            {Array.from({ length: pages }, (_, i) => <PageRows key={i} persona={persona} offset={i * PAGE} q={q} />)}
          </ul>
          {pages * PAGE < total && <Button onClick={() => setPages((p) => p + 1)} icon={<ChevronDown size={20} aria-hidden />}>{t("welcome.more")}</Button>}
        </>
      )}
    </section>
  );
}

function PageRows({ persona, offset, q }: { persona: string; offset: number; q: string }) {
  const { t } = useTranslation();
  const page = useCustomerPage(persona === "all" ? undefined : persona, offset, PAGE);
  if (!page.data) return <li className="px-4 py-3 text-sm text-ink-mute">…</li>;
  const rows = page.data.customers.filter((c) => !q || c.name.toLowerCase().includes(q) || c.city.toLowerCase().includes(q));
  if (rows.length === 0 && offset === 0 && q) return <li className="px-4 py-3 text-sm text-ink-mute">{t("welcome.noMatch")}</li>;
  return (
    <>
      {rows.map((c) => (
        <li key={c.id}>
          <Link to={paths.home(c.id)} className="flex items-center gap-3 px-4 py-3 hover:bg-sand">
            <span className="flex min-w-0 flex-1 flex-col">
              <span className="truncate font-semibold">{c.name} <span className="font-normal text-ink-mute">· {t("welcome.ageCity", { age: c.age, city: c.city })}</span></span>
              <span className="flex flex-wrap gap-x-3 text-sm text-ink-soft">
                <span>{t(personaKey(c.persona))}</span>
                <span className="tabular">{formatINR(c.monthly_income_mean)}{t("unit.perMonth")}</span>
              </span>
            </span>
            <span className="hidden gap-1 sm:flex">
              {c.liquidity_runway != null && <StatusChip light={runwayLight(c.liquidity_runway)}>{formatMonths(c.liquidity_runway)} {t("unit.months")}</StatusChip>}
              {c.dbr != null && <StatusChip light={dbrLight(c.dbr)}>{formatPct(c.dbr)}</StatusChip>}
            </span>
            <ArrowRight size={20} aria-hidden className="shrink-0 text-ink-mute" />
          </Link>
        </li>
      ))}
    </>
  );
}
