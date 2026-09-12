import { useTranslation } from "react-i18next";
import { setLang, type Lang } from "@/i18n";

export function LanguageToggle() {
  const { t, i18n } = useTranslation();
  const current: Lang = i18n.language === "en" ? "en" : "hi";
  const opts: Lang[] = ["hi", "en"];
  return (
    <div role="radiogroup" aria-label={t("lang.switch")} className="inline-flex rounded-xl border border-line bg-card p-1">
      {opts.map((l) => (
        <button
          key={l}
          type="button"
          role="radio"
          aria-checked={current === l}
          lang={l}
          onClick={() => setLang(l)}
          className={
            "min-h-[40px] rounded-lg px-3 text-sm font-semibold transition-colors duration-150 " +
            (current === l ? "bg-ink text-paper" : "text-ink-soft hover:bg-sand")
          }
        >
          {t(`lang.${l}`)}
        </button>
      ))}
    </div>
  );
}
