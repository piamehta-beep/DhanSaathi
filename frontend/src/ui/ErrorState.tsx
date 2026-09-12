import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import { ShieldCheck, RotateCcw, Compass } from "lucide-react";
import { ApiError, NetworkError } from "@/api/client";
import { scopeKey } from "@/copy/mapping";
import { paths } from "@/lib/paths";
import { Button, LinkButton } from "./Button";
import { Card } from "./Card";

// One component for every non-happy path (brief §11). Each state is specific,
// says what happened in words, and offers exactly one way forward.
export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const { t } = useTranslation();
  const { id } = useParams();

  if (error instanceof ApiError && error.isConsent) {
    const scopes = error.missingScopes;
    return (
      <Card tone="sand" className="flex flex-col gap-4 animate-rise" role="alert">
        <div className="flex items-center gap-2 text-lg font-semibold">
          <ShieldCheck size={24} aria-hidden /> {t("state.consent.title")}
        </div>
        <p>{t("state.consent.body")}</p>
        <ul className="list-disc pl-5 flex flex-col gap-1">
          {scopes.map((s) => <li key={s}>{t(scopeKey(s))}</li>)}
        </ul>
        {id && (
          <LinkButton to={paths.data(id, scopes[0])} variant="primary" icon={<ShieldCheck size={22} aria-hidden />}>
            {t("state.consent.cta")}
          </LinkButton>
        )}
      </Card>
    );
  }

  if (error instanceof ApiError && error.isNotFound) {
    return (
      <Card tone="sand" className="flex flex-col gap-4 animate-rise" role="alert">
        <div className="flex items-center gap-2 text-lg font-semibold">
          <Compass size={24} aria-hidden /> {t("state.notFound.title")}
        </div>
        <p>{t("state.notFound.body")}</p>
        <LinkButton to={paths.welcome} variant="primary">{t("state.notFound.cta")}</LinkButton>
      </Card>
    );
  }

  const offline = error instanceof NetworkError;
  return (
    <Card tone="sand" className="flex flex-col gap-4 animate-rise" role="alert">
      <p>{offline ? t("state.offlineNoData") : t("state.error")}</p>
      {onRetry && (
        <Button onClick={onRetry} icon={<RotateCcw size={20} aria-hidden />}>{t("state.retry")}</Button>
      )}
    </Card>
  );
}
