import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { ArrowRight, Sparkles } from "lucide-react";
import { useQueries } from "@tanstack/react-query";
import { api } from "@/api/client";
import { keys, retryPolicy } from "@/api/queries";
import { PERSONAS, personaKey } from "@/copy/mapping";
import { paths } from "@/lib/paths";
import { Layout } from "@/ui/Layout";
import { CardSkeleton } from "@/ui";
import { ErrorState } from "@/ui/ErrorState";

// S0 — "Try DhanSaathi as…". One representative customer per persona.
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
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-2">
          <span className="text-sm font-semibold uppercase tracking-wide text-accent-strong">{t("welcome.kicker")}</span>
          <h1 className="text-2xl font-bold leading-tight">{t("app.tagline")}</h1>
          <p className="text-ink-soft">{t("welcome.subtitle")}</p>
        </div>

        {allFailed ? (
          <ErrorState error={results[0].error} onRetry={() => results.forEach((r) => r.refetch())} />
        ) : (
          <ul className="grid gap-3 sm:grid-cols-2">
            {PERSONAS.map((p, i) => {
              const r = results[i];
              const c = r.data?.customers[0];
              if (!c) return <li key={p}><CardSkeleton /></li>;
              const first = c.name.split(" ")[0];
              return (
                <li key={p} className="animate-rise">
                  <Link
                    to={paths.home(c.id)}
                    className="group flex h-full flex-col gap-3 rounded-2xl border border-line bg-card p-4 shadow-card transition-colors duration-150 hover:border-accent focus-visible:border-accent"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="text-lg font-bold">{first}</div>
                        <div className="text-sm text-ink-mute">{t("welcome.ageCity", { age: c.age, city: c.city })}</div>
                      </div>
                    </div>
                    <p className="flex-1 text-ink-soft">{t(personaKey(p))}</p>
                    <span className="inline-flex min-h-touch items-center justify-between rounded-xl bg-accent-soft px-4 font-semibold text-accent-strong group-hover:bg-accent group-hover:text-white transition-colors duration-150">
                      {t("welcome.continueAs", { name: first })}
                      <ArrowRight size={22} aria-hidden />
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}

        <Link to={paths.onboarding} className="inline-flex min-h-touch items-center gap-2 self-start rounded-xl px-1 font-semibold text-accent-strong hover:underline">
          <Sparkles size={20} aria-hidden /> {t("welcome.newLink")}
        </Link>
        <p className="text-sm text-ink-mute">{t("welcome.demoNote")}</p>
      </div>
    </Layout>
  );
}
