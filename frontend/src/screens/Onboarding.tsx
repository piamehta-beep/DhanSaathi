import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Send, RotateCcw, Home, Check } from "lucide-react";
import { api, type OnboardingMessageResponse } from "@/api/client";
import { NetworkError } from "@/api/client";
import { formatINR, formatPct } from "@/lib/format";
import { paths } from "@/lib/paths";
import { Layout } from "@/ui/Layout";
import { ErrorState } from "@/ui/ErrorState";
import { Button, Card, ChatBubble, LinkButton } from "@/ui";

type Msg = { from: "app" | "me"; text: string; tone?: "care" };
type Step = "pan" | "aadhaar" | "address" | "income" | "review" | "complete";

// Keyboard type per step: numeric where the answer is a number (brief §6 S6).
const inputFor: Record<Step, { inputMode: "text" | "numeric" | "decimal"; autoCapitalize?: string; maxLength?: number }> = {
  pan: { inputMode: "text", autoCapitalize: "characters", maxLength: 10 },
  aadhaar: { inputMode: "numeric", maxLength: 14 },
  address: { inputMode: "numeric", maxLength: 6 },
  income: { inputMode: "numeric" },
  review: { inputMode: "text" },
  complete: { inputMode: "text" },
};

// S6 — conversational onboarding, one question at a time.
export function Onboarding() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === "en" ? "en" : "hi";
  const [session, setSession] = useState<string | null>(null);
  const [step, setStep] = useState<Step>("pan");
  const [progress, setProgress] = useState(0);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [review, setReview] = useState<Record<string, unknown> | null>(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const endRef = useRef<HTMLDivElement>(null);

  const start = async () => {
    setError(null); setMsgs([]); setReview(null); setStep("pan"); setProgress(0); setText("");
    try {
      const s = await api.onboardingStart(lang);
      setSession(s.session_id); setStep(s.step as Step); setProgress(s.progress);
      setMsgs([{ from: "app", text: s.message }]);
    } catch (e) { setError(e as Error); }
  };
  // Session language is fixed at start; restart if the toggle flips.
  useEffect(() => { start(); /* eslint-disable-line react-hooks/exhaustive-deps */ }, [lang]);
  useEffect(() => { endRef.current?.scrollIntoView({ block: "nearest" }); }, [msgs]);

  const send = async (override?: string) => {
    const raw = override ?? text;
    if (!session || !raw.trim() || busy) return;
    const mine = raw.trim();
    setText(""); setBusy(true); setError(null);
    // Identifiers are masked in the transcript too — this is often a shared phone.
    const shown = step === "pan" || step === "aadhaar" ? mine.replace(/[\s-]/g, "").replace(/.(?=.{4})/g, "*") : mine;
    setMsgs((m) => [...m, { from: "me", text: shown }]);
    try {
      const r: OnboardingMessageResponse = await api.onboardingMessage(session, mine);
      setStep(r.step as Step); setProgress(r.progress);
      if (r.review) setReview(r.review as Record<string, unknown>);
      setMsgs((m) => [...m, { from: "app", text: r.message, tone: r.accepted ? undefined : "care" }]);
    } catch (e) {
      setError(e as Error);
      if (!(e instanceof NetworkError)) setText(mine);
    } finally {
      setBusy(false);
      inputRef.current?.focus();
    }
  };

  const done = step === "complete";
  const io = inputFor[step];

  return (
    <Layout back={paths.welcome} title={t("onboarding.title")}>
      <div className="flex flex-1 flex-col gap-4">
        <div>
          <h1 className="text-2xl font-bold">{t("onboarding.title")}</h1>
          <p className="text-ink-soft">{t("onboarding.intro")}</p>
        </div>
        <div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-sand" role="progressbar" aria-valuemin={0} aria-valuemax={100}
            aria-valuenow={Math.round(progress * 100)} aria-label={t("onboarding.progress", { pct: formatPct(progress) })}>
            <div className="h-full bg-accent transition-[width] duration-200 ease-out" style={{ width: `${progress * 100}%` }} />
          </div>
          <p className="mt-1 text-sm text-ink-mute">{t("onboarding.progress", { pct: formatPct(progress) })}</p>
        </div>

        <div className="flex flex-1 flex-col justify-end gap-3" aria-live="polite">
          {msgs.map((m, i) => <ChatBubble key={i} from={m.from} tone={m.tone}>{m.text}</ChatBubble>)}
          {review && step === "review" && <ReviewCard review={review} />}
          {done && (
            <Card tone="safe" className="flex flex-col gap-2 animate-rise">
              <p className="font-semibold text-safe-ink">{t("onboarding.done")}</p>
              {review && <ReviewCard review={review} bare />}
              <p className="text-sm text-ink-soft">{t("onboarding.maskedNote")}</p>
            </Card>
          )}
          {error !== null && <ErrorState error={error} onRetry={session ? () => { setError(null); inputRef.current?.focus(); } : start} />}
          <div ref={endRef} />
        </div>

        {!done ? (
          <form className="flex flex-col gap-2 pt-2 safe-bottom" onSubmit={(e) => { e.preventDefault(); void send(); }}>
            <div className="flex gap-2">
              <input
                ref={inputRef}
                autoFocus
                aria-label={t("onboarding.placeholder")}
                placeholder={t("onboarding.placeholder")}
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void send(); } }}
                disabled={!session || busy}
                inputMode={io.inputMode}
                autoCapitalize={io.autoCapitalize}
                maxLength={io.maxLength}
                autoComplete="off"
                className="min-h-cta min-w-0 flex-1 rounded-xl border border-line bg-card px-4 text-lg outline-none focus:border-accent tabular"
              />
              <Button type="submit" variant="primary" className="!w-auto shrink-0 px-4" loading={busy} disabled={!text.trim()} icon={<Send size={22} aria-hidden />}>
                {t("onboarding.send")}
              </Button>
            </div>
            {step === "review" ? (
              <Button type="button" variant="primary" onClick={() => send("yes")} loading={busy} icon={<Check size={22} aria-hidden />}>
                {t("onboarding.confirm")}
              </Button>
            ) : (
              <p className="text-sm text-ink-mute">{t("onboarding.demoHint")}</p>
            )}
          </form>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            <Button onClick={start} icon={<RotateCcw size={22} aria-hidden />}>{t("onboarding.startOver")}</Button>
            <LinkButton to={paths.welcome} variant="primary" icon={<Home size={22} aria-hidden />}>{t("onboarding.goHome")}</LinkButton>
          </div>
        )}
      </div>
    </Layout>
  );
}

function ReviewCard({ review, bare }: { review: Record<string, unknown>; bare?: boolean }) {
  const { t } = useTranslation();
  const rows: [string, string][] = [];
  for (const k of ["pan", "aadhaar", "address", "income"] as const) {
    const v = review[k];
    if (v === undefined || v === null) continue;
    rows.push([t(`onboarding.review.${k}`), k === "income" && typeof v === "number" ? formatINR(v) : String(v)]);
  }
  const body = (
    <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
      {rows.map(([k, v]) => (<div key={k} className="contents"><dt className="text-ink-mute">{k}</dt><dd className="font-semibold tabular">{v}</dd></div>))}
    </dl>
  );
  return bare ? body : <Card className="animate-rise">{body}</Card>;
}
