"""Response schemas for the public API.

These exist so the OpenAPI document describes what each endpoint *returns*,
not just what it accepts. Without them every response is an untyped object
and a client generator (openapi-typescript, orval, openapi-generator) emits
`any`, which pushes the whole API contract into the frontend's head.

Two deliberate choices:

- Envelopes and list items are typed strictly, because those are what a
  frontend iterates and destructures.
- Genuinely dynamic maps keep permissive value types. `features` holds ~30
  named metrics, `survival_function` is keyed by month, `expected_liquidity`
  by horizon. Enumerating those as fixed fields would freeze internals that
  are expected to grow, and a wrong-but-precise schema is worse than an
  honestly loose one.

FastAPI filters responses to the declared model, so every field an endpoint
actually returns must appear here or it silently disappears from the
response. The models were written against captured live responses rather
than from memory, and the test suite exercises each endpoint afterwards.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

Number = float | int | None


# --------------------------------------------------------------------------
# health
# --------------------------------------------------------------------------
class ModelWarmupStatus(BaseModel):
    status: str = Field(description="cold | warming | warm | failed | skipped_no_data")
    seconds: float | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    database: str
    model_version: str
    models: ModelWarmupStatus
    timestamp: str


# --------------------------------------------------------------------------
# customers
# --------------------------------------------------------------------------
class CustomerSummary(BaseModel):
    id: str
    persona: str
    name: str
    age: int
    city: str
    monthly_income_mean: float
    dbr: float | None
    liquidity_runway: float | None
    distress_state: bool
    life_stage: str


class CustomerListResponse(BaseModel):
    customers: list[CustomerSummary]
    total: int
    limit: int
    offset: int


class CustomerDetail(BaseModel):
    id: str
    external_id: str | None
    persona: str
    name: str
    age: int
    city: str
    state: str
    preferred_language: str
    monthly_income_mean: float
    monthly_income_std: float
    liquid_savings: float
    credit_limit: float | None
    credit_outstanding: float | None
    life_stage: str
    distress_state: bool
    distress_event_month: int | None
    distress_event_type: str | None
    created_at: str | None


# --------------------------------------------------------------------------
# transactions
# --------------------------------------------------------------------------
class TransactionItem(BaseModel):
    id: str
    txn_date: str
    txn_time: str | None
    amount: float
    type: str
    category: str
    merchant: str
    is_recurring: bool
    is_anomaly: bool


class TransactionListResponse(BaseModel):
    transactions: list[TransactionItem]
    total: int


class TransactionCreated(BaseModel):
    id: str
    customer_id: str
    txn_date: str
    txn_time: str | None
    amount: float
    type: str
    category: str
    merchant: str
    description: str | None
    is_recurring: bool


# --------------------------------------------------------------------------
# features
# --------------------------------------------------------------------------
class FeaturesResponse(BaseModel):
    customer_id: str
    snapshot_date: str
    features: dict[str, Number] = Field(
        description="Computed feature vector; see app/features for definitions."
    )
    model_version: str


# --------------------------------------------------------------------------
# distress risk
# --------------------------------------------------------------------------
class FallbackModelSummary(BaseModel):
    name: str
    distress_probability_12m: float
    concordance_index: float


class DistressRiskResponse(BaseModel):
    customer_id: str
    distress_probability_12m: float
    survival_function: dict[str, float] = Field(description="Keyed by month index")
    hazard_ratios: dict[str, float]
    median_survival_time_months: float | None
    primary_model: str
    concordance_index: float
    fallback_model: FallbackModelSummary
    model_version: str


# --------------------------------------------------------------------------
# anomalies
# --------------------------------------------------------------------------
class AnomalyItem(BaseModel):
    transaction_id: str
    txn_date: str
    amount: float
    type: str
    category: str
    merchant: str
    detection_method: str
    anomaly_score: float
    confidence: float
    features: dict[str, Number]
    injected_tag: str | None = Field(
        default=None,
        description="Ground-truth tag from the synthetic generator; validation aid only.",
    )


class AnomalyListResponse(BaseModel):
    anomalies: list[AnomalyItem]
    total: int


# --------------------------------------------------------------------------
# recommendation
# --------------------------------------------------------------------------
class CBSComponentsOut(BaseModel):
    need_match: float
    affordability_delta: float
    risk_reduction: float
    life_stage_align: float
    distress_delta: float


class SimulationSummary(BaseModel):
    p_shortfall_12m: float
    expected_runway: float
    p5_liquidity_12m: float | None
    p95_liquidity_12m: float | None


class ConfidenceInterval(BaseModel):
    cbs_low: float | None
    cbs_high: float | None
    method: str
    ci_width_ratio: float | None


class Attribution(BaseModel):
    feature: str
    value: Number | str
    shap: float
    direction: str


class RecommendationResponse(BaseModel):
    recommendation_id: str | None = None
    customer_id: str
    product_type: str
    amount: float | None
    tenure_months: int | None
    monthly_cost: float | None
    cbs_score: float
    cbs_components: CBSComponentsOut
    constraints_passed: list[str]
    constraints_failed: list[str]
    simulation_summary: SimulationSummary
    distress_probability: float
    distress_state: bool
    max_anomaly_score: float
    status: str = Field(description="recommended | no_action | vetoed")
    veto_reason: str | None
    language: str
    candidates_evaluated: int
    candidates_feasible: int
    confidence_level: str
    confidence_interval: ConfidenceInterval
    shap_values: list[Attribution]
    need_match_attribution: list[Attribution]
    explanation: str
    llm_explanation: str | None
    llm_status: str | None


# --------------------------------------------------------------------------
# bank product matching
# --------------------------------------------------------------------------
class InterestRateBand(BaseModel):
    min: float
    max: float


class BankProductMatch(BaseModel):
    bank_name: str
    product_name: str
    product_type: str
    amount: float
    tenure_months: int | None
    interest_rate_band: InterestRateBand
    monthly_cost: float
    total_interest_at_min_rate: float
    processing_fee_pct: float | None
    annual_fee: float | None
    post_dbr: float
    post_p_shortfall_12m: float
    post_runway_months: float
    passes_safety_gate: bool
    veto_reason: str | None
    constraints_failed: list[str]
    eligibility_notes: str
    source_note: str = Field(description="Provenance; these are illustrative bands, not live quotes.")
    source_url: str | None
    last_verified_date: str


class MatchingProductsResponse(BaseModel):
    customer_id: str
    recommendation_id: str
    product_type: str
    amount: float | None = None
    tenure_months: int | None = None
    matching_products: list[BankProductMatch]
    disclaimer: str | None = None
    note: str | None = None


# --------------------------------------------------------------------------
# explainability
# --------------------------------------------------------------------------
class ExplainResponse(BaseModel):
    customer_id: str
    recommendation_id: str
    product_type: str
    status: str
    shap_values: list[Attribution]
    need_match_attribution: list[Attribution]
    model_used: str
    explanation: str
    veto_reason: str | None
    constraints_failed: list[str] | None
    confidence_level: str
    confidence_interval: dict[str, Any] | None


# --------------------------------------------------------------------------
# enquiry
# --------------------------------------------------------------------------
class EnquiryRequested(BaseModel):
    product_type: str
    amount: float
    tenure_months: int | None


class EnquiryAssessment(BaseModel):
    amount: float
    tenure_months: int | None
    monthly_cost: float
    post_dbr: float
    post_p_shortfall_12m: float
    post_runway_months: float
    passes: bool
    veto_reason: str | None
    constraints_passed: list[str]
    constraints_failed: list[str]


class EnquiryBaseline(BaseModel):
    dbr: float | None
    p_shortfall_12m: float
    expected_runway: float
    liquidity_runway_months: float | None


class CounterOffer(BaseModel):
    amount: float | None = None
    tenure_months: int | None = None
    monthly_cost: float | None = None
    post_dbr: float | None = None
    post_p_shortfall_12m: float | None = None
    post_runway_months: float | None = None
    passes: bool | None = None
    veto_reason: str | None = None
    constraints_passed: list[str] | None = None
    constraints_failed: list[str] | None = None
    blocking_constraints: list[str] | None = None
    blocking_reason: str | None = None
    note: str


class EnquiryResponse(BaseModel):
    customer_id: str
    requested: EnquiryRequested
    verdict: str = Field(description="affordable | declined")
    assessment: EnquiryAssessment
    baseline: EnquiryBaseline
    distress_probability_12m: float
    counter_offer: CounterOffer | None
    matching_products: list[BankProductMatch]
    matching_products_note: str | None = None


# --------------------------------------------------------------------------
# consent and audit
# --------------------------------------------------------------------------
class ConsentRecordOut(BaseModel):
    id: str
    scope: str
    granted: bool
    granted_at: str | None
    revoked_at: str | None
    purpose: str
    active: bool


class ConsentListResponse(BaseModel):
    customer_id: str
    consent_records: list[ConsentRecordOut]


class ConsentCreated(BaseModel):
    id: str
    customer_id: str
    scope: str
    granted: bool
    granted_at: str | None
    revoked_at: str | None
    purpose: str


class ConsentRevoked(BaseModel):
    id: str
    scope: str
    granted: bool
    revoked_at: str
    active: bool


class AuditLogItem(BaseModel):
    id: str
    action: str
    module: str
    input_hash: str
    output_summary: dict[str, Any]
    timestamp: str


class AuditLogResponse(BaseModel):
    customer_id: str
    logs: list[AuditLogItem]
    total: int


# --------------------------------------------------------------------------
# simulation
# --------------------------------------------------------------------------
class SimulationScenario(BaseModel):
    p_shortfall_12m: float
    expected_liquidity: dict[str, float]
    liquidity_percentiles: dict[str, dict[str, float]]
    expected_runway: float
    parameters: dict[str, Any]


class SimulateResponse(BaseModel):
    customer_id: str
    simulation_id: str
    scenarios: dict[str, SimulationScenario]
    confidence_bands: dict[str, dict[str, dict[str, float]]]


# --------------------------------------------------------------------------
# onboarding
# --------------------------------------------------------------------------
class OnboardingStartResponse(BaseModel):
    session_id: str
    step: str
    message: str
    progress: float


class OnboardingMessageResponse(BaseModel):
    step: str
    message: str
    progress: float
    accepted: bool
    attempts: int | None = None
    review: dict[str, Any] | None = None


class OnboardingStateResponse(BaseModel):
    session_id: str
    language: str
    step: str
    progress: float
    collected: dict[str, Any]


# --------------------------------------------------------------------------
# dataset
# --------------------------------------------------------------------------
class DatasetGenerateResponse(BaseModel):
    job_id: str
    status: str
    estimated_customers: int
    estimated_transactions: int


# --------------------------------------------------------------------------
# errors
# --------------------------------------------------------------------------
class ErrorBody(BaseModel):
    error: str
    message: str | None = None
    missing_scopes: list[str] | None = None


class ErrorResponse(BaseModel):
    """Every handled error is returned as {"detail": {...}}."""

    detail: ErrorBody
