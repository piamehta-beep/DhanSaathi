import { useTranslation } from "react-i18next";
import { canonicalFeature, KNOWN_FEATURES, featureKey } from "@/copy/mapping";

// One horizontal attribution bar. Length is |shap| relative to the largest in
// the set (a pure scale for display); colour and a word carry direction.
export function BarRow({ feature, shap, direction, max, words }: {
  feature: string; shap: number; direction: string; max: number; words?: { up: string; down: string };
}) {
  const { t } = useTranslation();
  const c = canonicalFeature(feature);
  const label = KNOWN_FEATURES.has(c) ? t(featureKey(c)) : feature.replace(/_/g, " ");
  const raises = direction.startsWith("increases");
  const good = words ? raises : !raises; // need-match up = good; distress up = bad
  const width = max > 0 ? Math.max(6, Math.round((Math.abs(shap) / max) * 100)) : 0;
  return (
    <li className="flex flex-col gap-1">
      <div className="flex items-baseline justify-between gap-3">
        <span>{label}</span>
        <span className={"shrink-0 text-sm font-semibold " + (good ? "text-safe-ink" : "text-care-ink")}>
          {raises ? (words?.up ?? t("why.raises")) : (words?.down ?? t("why.lowers"))}
        </span>
      </div>
      <div className="h-3 w-full rounded-full bg-sand" aria-hidden>
        <div
          className={"h-3 rounded-full transition-[width] duration-200 ease-out " + (good ? "bg-safe" : "bg-care")}
          style={{ width: `${width}%` }}
        />
      </div>
    </li>
  );
}
