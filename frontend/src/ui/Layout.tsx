import type { ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ArrowLeft, Users, ShieldCheck, RotateCcw, ScrollText } from "lucide-react";
import { BottomNav } from "./BottomNav";
import { useQueryClient } from "@tanstack/react-query";
import { LanguageToggle } from "./LanguageToggle";
import { Banner } from "./Banner";
import { useOffline } from "@/lib/net";
import { useCustomer } from "@/api/queries";
import { ApiError } from "@/api/client";
import { ErrorState } from "./ErrorState";
import { Skeleton } from "./Skeleton";
import { paths } from "@/lib/paths";

// The frame around every screen: header with back / switch person / your data
// / language, the persistent offline banner, and a <main> landmark.
export function Layout({ children, back, title }: { children: ReactNode; back?: string | true; title?: string }) {
  const { t } = useTranslation();
  const nav = useNavigate();
  const { id } = useParams();
  const offline = useOffline();
  const qc = useQueryClient();
  // The backend checks consent before existence, so a stale customer link would
  // otherwise read as "permission needed". Resolve the customer once, here.
  const customer = useCustomer(id ?? "", !!id);
  const gone = customer.error instanceof ApiError && customer.error.isNotFound;

  return (
    <div className="min-h-dvh flex flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:m-2 focus:rounded-lg focus:bg-card focus:px-3 focus:py-2">
        {t("nav.skipToContent")}
      </a>
      <header className="sticky top-0 z-40 border-b border-line bg-paper/95 backdrop-blur">
        <nav aria-label="Main" className="mx-auto flex max-w-3xl items-center gap-2 px-4 py-2 sm:px-6">
          {back ? (
            <button
              type="button"
              onClick={() => (back === true ? nav(-1) : nav(back))}
              className="inline-flex min-h-touch min-w-[48px] items-center gap-1 rounded-xl px-2 font-semibold text-ink-soft hover:bg-sand"
            >
              <ArrowLeft size={24} aria-hidden /> <span className="sr-only sm:not-sr-only">{t("nav.back")}</span>
            </button>
          ) : (
            <Link to={paths.welcome} className="inline-flex min-h-touch items-center px-1 text-lg font-bold text-accent-strong">
              {t("app.name")}
            </Link>
          )}
          {title && back && <span className="hidden max-w-[12rem] truncate font-semibold md:inline">{title}</span>}
          <span className="flex-1" />
          {id && (
            <>
              <Link to={paths.welcome} className="inline-flex min-h-touch items-center gap-1 whitespace-nowrap rounded-xl px-2 text-sm font-semibold text-ink-soft hover:bg-sand">
                <Users size={22} aria-hidden /> <span className="hidden md:inline">{t("nav.switchPerson")}</span>
                <span className="sr-only md:hidden">{t("nav.switchPerson")}</span>
              </Link>
              <Link to={paths.trail(id)} className="inline-flex min-h-touch items-center gap-1 whitespace-nowrap rounded-xl px-2 text-sm font-semibold text-ink-soft hover:bg-sand">
                <ScrollText size={22} aria-hidden /> <span className="hidden md:inline">{t("nav.trail")}</span>
                <span className="sr-only md:hidden">{t("nav.trail")}</span>
              </Link>
              <Link to={paths.data(id)} className="inline-flex min-h-touch items-center gap-1 whitespace-nowrap rounded-xl px-2 text-sm font-semibold text-ink-soft hover:bg-sand">
                <ShieldCheck size={22} aria-hidden /> <span className="hidden md:inline">{t("nav.yourData")}</span>
                <span className="sr-only md:hidden">{t("nav.yourData")}</span>
              </Link>
            </>
          )}
          <LanguageToggle />
        </nav>
        {offline && (
          <Banner
            kind="offline"
            action={
              <button
                type="button"
                onClick={() => qc.refetchQueries({ type: "active" })}
                className="inline-flex min-h-[40px] items-center gap-1 rounded-lg bg-card px-3 text-sm font-semibold text-care-ink"
              >
                <RotateCcw size={18} aria-hidden /> {t("state.retry")}
              </button>
            }
          >
            {t("state.offline")}
          </Banner>
        )}
      </header>
      {id && !gone && <BottomNav />}
      <main id="main" className={"mx-auto flex w-full max-w-3xl flex-1 flex-col px-4 pt-5 sm:px-6 sm:pt-8 " + (id ? "pb-24 sm:pb-8" : "pb-8")}>
        {gone ? (
          <>
            <h1 className="sr-only">{t("state.notFound.title")}</h1>
            <ErrorState error={customer.error} />
          </>
        ) : children}
      </main>
    </div>
  );
}

// Bottom-anchored primary action within thumb reach on mobile (brief §8).
export function StickyCta({ children }: { children: ReactNode }) {
  return (
    <div className="sticky bottom-[72px] z-30 -mx-4 mt-6 bg-gradient-to-t from-paper via-paper to-transparent px-4 pb-2 pt-6 sm:static sm:mx-0 sm:bg-none sm:px-0 sm:pb-0 sm:pt-0">
      {children}
    </div>
  );
}

// Suspense fallback for lazy routes: a real shell with landmarks, no flash of nothing.
export function ScreenFallback() {
  const { t } = useTranslation();
  return (
    <Layout back>
      <h1 className="sr-only">{t("state.loading")}</h1>
      <div className="flex flex-col gap-3" role="status" aria-label={t("state.loading")}>
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    </Layout>
  );
}
