// The backend's `explanation` is built from four fixed templates
// (app/models/explainer.py narrate()). We parse those exact shapes and re-say
// them with human feature names. Nothing is computed; every value quoted is
// the API's own. Unknown shapes fall back to the raw text.
import type { TFunction } from "i18next";
import { canonicalFeature, KNOWN_FEATURES, featureKey, productKey } from "./mapping";

type Pair = { feature: string; value: string };

const parsePairs = (s: string): Pair[] =>
  s.split(",").map((p) => p.trim()).filter(Boolean).map((p) => {
    const [feature, value = ""] = p.split("=");
    return { feature: feature.trim(), value: value.trim() };
  });

const featureLabel = (t: TFunction, f: string) => {
  const c = canonicalFeature(f);
  return KNOWN_FEATURES.has(c) ? t(featureKey(c)) : f.replace(/_/g, " ");
};

const list = (t: TFunction, pairs: Pair[]) => {
  const names = pairs.map((p) => featureLabel(t, p.feature).toLowerCase());
  if (names.length <= 1) return names.join("");
  return `${names.slice(0, -1).join(", ")} ${t("explain.and")} ${names[names.length - 1]}`;
};

export function humanizeExplanation(raw: string, t: TFunction): string[] {
  const out: string[] = [];
  const sentences = raw.split(/\.\s+|\.$/).map((s) => s.trim()).filter(Boolean);
  for (const s of sentences) {
    let m: RegExpMatchArray | null;
    if ((m = s.match(/^Main risk factors:\s*(.+)$/))) {
      out.push(t("explain.risk", { items: list(t, parsePairs(m[1])) }));
    } else if ((m = s.match(/^Offsetting strengths:\s*(.+)$/))) {
      out.push(t("explain.strength", { items: list(t, parsePairs(m[1])) }));
    } else if ((m = s.match(/^(\w+) was matched most strongly on (.+)$/))) {
      const [{ feature }] = parsePairs(m[2]);
      out.push(t("explain.matched", { product: t(productKey(m[1])), feature: featureLabel(t, feature).toLowerCase() }));
    } else if (/^No product cleared the safety checks/.test(s)) {
      out.push(t("explain.noneCleared"));
    } else if (/^Not enough data/.test(s)) {
      out.push(t("explain.notEnough"));
    } else {
      out.push(s + ".");
    }
  }
  return out;
}
