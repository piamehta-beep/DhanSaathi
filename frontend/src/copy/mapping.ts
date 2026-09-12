// Brief §10 — the single source of truth for turning API vocabulary into
// something a person can read. Nothing else in the app may re-derive these.
// Values here are i18n *keys*; the strings live in src/locales/{hi,en}.json.

export type Persona =
  | "stable_salaried" | "young_earner" | "gig_worker"
  | "near_retirement" | "over_leveraged" | "distressed";

export type ProductType =
  | "personal_loan" | "credit_card" | "term_insurance" | "mutual_fund_sip" | "no_action";

export const PERSONAS: Persona[] = [
  "stable_salaried", "young_earner", "gig_worker",
  "near_retirement", "over_leveraged", "distressed",
];

export const personaKey = (p: string) => `persona.${p}`;
export const productKey = (p: string) => `product.${p}`;
export const constraintKey = (c: string) => `constraint.${c}`;
export const vetoKey = (v: string) => `veto.${v}`;
export const vetoNextKey = (v: string) => `vetoNext.${v}`;
export const featureKey = (f: string) => `feature.${f}`;
export const confidenceKey = (c: string) => `confidence.${c}`;
export const scopeKey = (s: string) => `scope.${s}`;

export const CONSTRAINT_CODES = ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9"] as const;

export const KNOWN_VETOS = new Set([
  "post_dbr_exceeds_0.50", "new_loan_dbr_exceeds_0.40",
  "shortfall_probability_exceeds_0.15", "runway_below_3_months",
  "customer_in_distress_state", "high_anomaly_score", "insufficient_data",
  "negative_savings_rate", "insurance_premium_unaffordable",
]);

// Feature names the API can emit in shap_values / explanation strings.
// Aliases collapse onto one key so hi.json/en.json stay short.
const FEATURE_ALIASES: Record<string, string> = {
  income_cv: "income_stability",
  anomaly_count_30d: "anomaly_count",
  anomaly_count_90d: "anomaly_count",
};
export const canonicalFeature = (f: string) => FEATURE_ALIASES[f] ?? f;

export const KNOWN_FEATURES = new Set([
  "dbr", "liquidity_runway", "income_stability", "savings_rate",
  "savings_trend_slope", "expense_volatility", "category_entropy",
  "anomaly_count", "runway_trend", "txn_frequency_trend",
  "expense_trend_slope", "credit_util_trend",
]);

export const CONSENT_SCOPES = [
  "transaction_analysis", "product_recommendation",
  "credit_assessment", "anomaly_monitoring", "marketing",
] as const;
export type ConsentScope = (typeof CONSENT_SCOPES)[number];

// Which S-screens each scope unlocks (brief §6 S7: revoking must break things honestly).
export const SCOPE_UNLOCKS: Record<ConsentScope, string[]> = {
  transaction_analysis: ["home", "recommend", "enquire"],
  product_recommendation: ["recommend", "banks"],
  credit_assessment: ["home", "enquire"],
  anomaly_monitoring: ["home"],
  marketing: [],
};

// Thresholds from brief §6 S1. These classify an API number for colour; they
// never transform it.
export const runwayLight = (m: number) => (m >= 6 ? "safe" : m >= 3 ? "care" : "danger") as Light;
export const dbrLight = (d: number) => (d < 0.3 ? "safe" : d <= 0.5 ? "care" : "danger") as Light;
export const distressBand = (p: number) => (p < 0.1 ? "low" : p <= 0.3 ? "medium" : "high") as Band;
export const bandLight = (b: Band): Light => (b === "low" ? "safe" : b === "medium" ? "care" : "danger");

export type Light = "safe" | "care" | "danger";
export type Band = "low" | "medium" | "high";

// S2 mode detection (brief §6 S2).
export type RecommendMode = "yes" | "safer" | "none";
export function recommendMode(r: {
  status: string; product_type: string; distress_state: boolean;
  simulation_summary: { p_shortfall_12m: number };
}): RecommendMode {
  if (r.status !== "recommended") return "none";
  const protective = r.product_type === "term_insurance" || r.product_type === "mutual_fund_sip";
  if (protective && (r.simulation_summary.p_shortfall_12m > 0.15 || r.distress_state)) return "safer";
  return "yes";
}
