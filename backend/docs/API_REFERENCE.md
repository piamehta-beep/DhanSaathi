# DhanSaathi API Reference

Generated from the live OpenAPI document. Do not edit by hand — run
`python -m scripts.render_api_reference` after any API change.

## Essentials

- **Base URL:** `http://localhost:8010/api/v1` (OpenAPI explorer at `/docs`, raw spec at `/openapi.json`)
- **Authentication:** none. There is no API key and no login; any client can read any customer. This is a prototype constraint, not a feature.
- **Content type:** JSON in and out. All IDs are UUID strings. Dates are ISO `YYYY-MM-DD`; timestamps are ISO 8601.
- **Money:** Indian rupees as plain numbers (no currency symbol, no paise rounding guaranteed).
- **Error envelope:** every handled error is `{"detail": {"error": "<code>", ...}}` with an appropriate HTTP status. Notable codes: `customer_not_found` (404), `recommendation_not_found` (404), `session_not_found` (404), `consent_required` (403, carries `missing_scopes`), `invalid_scope` (422). Pydantic validation failures return FastAPI's standard 422 with `detail` as a list.
- **Consent gating:** endpoints marked **consent-gated** below return **403 `consent_required`** unless the customer has active consent for the listed scopes. Seeded customers already have every scope except `marketing`. Grant with `POST /consent`; revocation takes effect on the next request.
- **Warm-up:** `GET /health` reports `models.status` as `cold` -> `warming` -> `warm` (~45-50s after start). Calls made before `warm` still succeed but the first one pays the model-training cost.
- **Typed client:** `npx openapi-typescript http://localhost:8010/openapi.json -o src/api-types.ts` (run from the frontend project).

## Domain vocabulary

- **persona** — `stable_salaried | young_earner | gig_worker | near_retirement | over_leveraged | distressed`. Synthetic cohort label; useful for demo filtering, never a model input.
- **product_type** — `personal_loan | credit_card | term_insurance | mutual_fund_sip | no_action`. `no_action` is a real outcome: the system declined to recommend anything.
- **life_stage** — `early_career | mid_career | pre_retirement | retired | student`.
- **consent scope** — `transaction_analysis | product_recommendation | credit_assessment | anomaly_monitoring | marketing`.
- **constraints C1–C9** — hard safety-gate rules. A recommendation lists which passed and which failed; `veto_reason` names the first failure. C1/C2 debt-burden ceilings, C3 shortfall probability, C4 minimum runway, C5 distress state, C6 unresolved anomalies, C7 minimum history, C8 positive savings (SIP only), C9 premium affordability (insurance only).
- **dbr** — debt burden ratio, total EMI / monthly income. **liquidity_runway** — months of expenses covered by liquid savings. **p_shortfall_12m** — simulated probability of breaching the cash buffer within 12 months. **cbs_score** — Customer Benefit Score in [-1, 1]; `no_action` scores exactly 0.

## Recommended demo flow

1. `GET /customers?persona=distressed` -> pick one -> `POST /customers/{id}/recommend` -> expect `product_type: "no_action"` with a `veto_reason`.
2. `GET /customers?persona=young_earner` -> `POST .../recommend` -> `GET .../matching-products/{recommendation_id}` for the real-bank comparison.
3. Same customer -> `POST .../enquire` with `{"product_type":"personal_loan","amount":500000,"tenure_months":36}` -> expect `verdict: "declined"` with a `counter_offer`.
4. `GET .../explain/{recommendation_id}` for attributions; `GET /audit/{id}` for the decision log.

---

## Endpoints


## health

### `GET /api/v1/health`
Health
**Response 200:** `HealthResponse`

## customers

### `GET /api/v1/customers`
List Customers

| param | in | type | required | notes |
|---|---|---|---|---|
| `persona` | query | string \| null | no |  |
| `limit` | query | integer | no | default `50` |
| `offset` | query | integer | no | default `0` |
**Response 200:** `CustomerListResponse`

### `GET /api/v1/customers/{customer_id}`
Get Customer

| param | in | type | required | notes |
|---|---|---|---|---|
| `customer_id` | path | string | yes |  |
**Response 200:** `CustomerDetail`

### `GET /api/v1/customers/{customer_id}/transactions`
Get Transactions

| param | in | type | required | notes |
|---|---|---|---|---|
| `customer_id` | path | string | yes |  |
| `start_date` | query | string \| null | no |  |
| `end_date` | query | string \| null | no |  |
| `category` | query | string \| null | no |  |
| `limit` | query | integer | no | default `100` |
| `offset` | query | integer | no | default `0` |
**Response 200:** `TransactionListResponse`

### `POST /api/v1/customers/{customer_id}/transactions`
Append a transaction.

| param | in | type | required | notes |
|---|---|---|---|---|
| `customer_id` | path | string | yes |  |

**Request body:** `NewTransaction`
**Response 201:** `TransactionCreated`

## features

### `GET /api/v1/customers/{customer_id}/features`
Get Features
**Consent-gated:** requires `transaction_analysis`.

| param | in | type | required | notes |
|---|---|---|---|---|
| `customer_id` | path | string | yes |  |
| `snapshot_date` | query | string \| null | no |  |
**Response 200:** `FeaturesResponse`

## simulation

### `POST /api/v1/customers/{customer_id}/simulate`
Simulate

| param | in | type | required | notes |
|---|---|---|---|---|
| `customer_id` | path | string | yes |  |

**Request body:** `SimulateRequest`
**Response 200:** `SimulateResponse`

## distress-risk

### `GET /api/v1/customers/{customer_id}/distress-risk`
Distress Risk
**Consent-gated:** requires `transaction_analysis`, `credit_assessment`.

| param | in | type | required | notes |
|---|---|---|---|---|
| `customer_id` | path | string | yes |  |
**Response 200:** `DistressRiskResponse`

## anomalies

### `GET /api/v1/customers/{customer_id}/anomalies`
Get Anomalies
**Consent-gated:** requires `anomaly_monitoring`.

| param | in | type | required | notes |
|---|---|---|---|---|
| `customer_id` | path | string | yes |  |
| `start_date` | query | string \| null | no |  |
| `end_date` | query | string \| null | no |  |
| `min_score` | query | number | no | default `0.5` |
| `limit` | query | integer | no | default `50` |
| `persist` | query | boolean | no | default `false` |
**Response 200:** `AnomalyListResponse`

## recommendation

### `POST /api/v1/customers/{customer_id}/recommend`
Create Recommendation
**Consent-gated:** requires `transaction_analysis`, `product_recommendation`.

| param | in | type | required | notes |
|---|---|---|---|---|
| `customer_id` | path | string | yes |  |

**Request body:** `RecommendRequest`
**Response 200:** `RecommendationResponse`

### `GET /api/v1/customers/{customer_id}/matching-products/{recommendation_id}`
Top 3 real bank products matching a recommendation (spec addendum).
**Consent-gated:** requires `transaction_analysis`, `product_recommendation`.

| param | in | type | required | notes |
|---|---|---|---|---|
| `customer_id` | path | string | yes |  |
| `recommendation_id` | path | string | yes |  |
**Response 200:** `MatchingProductsResponse`

## enquiry

### `POST /api/v1/customers/{customer_id}/enquire`
Answer "can I afford this?" for a product the customer asked about.
**Consent-gated:** requires `transaction_analysis`, `credit_assessment`.

| param | in | type | required | notes |
|---|---|---|---|---|
| `customer_id` | path | string | yes |  |

**Request body:** `EnquiryRequest`
**Response 200:** `EnquiryResponse`

## explainability

### `GET /api/v1/customers/{customer_id}/explain/{recommendation_id}`
Attributions for a recommendation, including a vetoed one.

| param | in | type | required | notes |
|---|---|---|---|---|
| `customer_id` | path | string | yes |  |
| `recommendation_id` | path | string | yes |  |
**Response 200:** `ExplainResponse`

## consent-and-audit

### `POST /api/v1/consent`
Grant Consent

**Request body:** `ConsentRequest`
**Response 201:** `ConsentCreated`

### `GET /api/v1/customers/{customer_id}/consent`
List Consent

| param | in | type | required | notes |
|---|---|---|---|---|
| `customer_id` | path | string | yes |  |
**Response 200:** `ConsentListResponse`

### `POST /api/v1/consent/{consent_id}/revoke`
Revoke Consent

| param | in | type | required | notes |
|---|---|---|---|---|
| `consent_id` | path | string | yes |  |
**Response 200:** `ConsentRevoked`

### `GET /api/v1/audit/{customer_id}`
Get Audit Log

| param | in | type | required | notes |
|---|---|---|---|---|
| `customer_id` | path | string | yes |  |
| `action` | query | string \| null | no |  |
| `limit` | query | integer | no | default `100` |
| `offset` | query | integer | no | default `0` |
**Response 200:** `AuditLogResponse`

## onboarding

### `POST /api/v1/onboarding/start`
Start

**Request body:** `StartRequest`
**Response 200:** `OnboardingStartResponse`

### `POST /api/v1/onboarding/{session_id}/message`
Message

| param | in | type | required | notes |
|---|---|---|---|---|
| `session_id` | path | string | yes |  |

**Request body:** `MessageRequest`
**Response 200:** `OnboardingMessageResponse`

### `GET /api/v1/onboarding/{session_id}`
Get Session

| param | in | type | required | notes |
|---|---|---|---|---|
| `session_id` | path | string | yes |  |
**Response 200:** `OnboardingStateResponse`

## dataset

### `POST /api/v1/dataset/generate`
Generate

**Request body:** `GenerateRequest`
**Response 202:** `DatasetGenerateResponse`

---

## Schemas

Every response and request body above is one of these. `T \| null` means the field may be null; `T[]` is an array; `object<string, T>` is a map with dynamic keys.

### `GenerateRequest`

| field | type | required | notes |
|---|---|---|---|
| `n_customers` | integer | no | default `1000` |
| `seed` | integer | no | default `42` |
| `clear_existing` | boolean | no | default `true` |

### `DatasetGenerateResponse`

| field | type | required | notes |
|---|---|---|---|
| `job_id` | string | yes |  |
| `status` | string | yes |  |
| `estimated_customers` | integer | yes |  |
| `estimated_transactions` | integer | yes |  |

### `CustomerListResponse`

| field | type | required | notes |
|---|---|---|---|
| `customers` | `CustomerSummary`[] | yes |  |
| `total` | integer | yes |  |
| `limit` | integer | yes |  |
| `offset` | integer | yes |  |

### `CustomerDetail`

| field | type | required | notes |
|---|---|---|---|
| `id` | string | yes |  |
| `external_id` | string \| null | yes |  |
| `persona` | string | yes |  |
| `name` | string | yes |  |
| `age` | integer | yes |  |
| `city` | string | yes |  |
| `state` | string | yes |  |
| `preferred_language` | string | yes |  |
| `monthly_income_mean` | number | yes |  |
| `monthly_income_std` | number | yes |  |
| `liquid_savings` | number | yes |  |
| `credit_limit` | number \| null | yes |  |
| `credit_outstanding` | number \| null | yes |  |
| `life_stage` | string | yes |  |
| `distress_state` | boolean | yes |  |
| `distress_event_month` | integer \| null | yes |  |
| `distress_event_type` | string \| null | yes |  |
| `created_at` | string \| null | yes |  |

### `TransactionListResponse`

| field | type | required | notes |
|---|---|---|---|
| `transactions` | `TransactionItem`[] | yes |  |
| `total` | integer | yes |  |

### `NewTransaction`

| field | type | required | notes |
|---|---|---|---|
| `txn_date` | string | yes |  |
| `txn_time` | string \| null | no |  |
| `amount` | number | yes | Always positive; direction is carried by `type` |
| `type` | `credit` \| `debit` | yes |  |
| `category` | string | yes |  |
| `merchant` | string | yes |  |
| `description` | string \| null | no |  |
| `is_recurring` | boolean | no | default `false` |

### `TransactionCreated`

| field | type | required | notes |
|---|---|---|---|
| `id` | string | yes |  |
| `customer_id` | string | yes |  |
| `txn_date` | string | yes |  |
| `txn_time` | string \| null | yes |  |
| `amount` | number | yes |  |
| `type` | string | yes |  |
| `category` | string | yes |  |
| `merchant` | string | yes |  |
| `description` | string \| null | yes |  |
| `is_recurring` | boolean | yes |  |

### `FeaturesResponse`

| field | type | required | notes |
|---|---|---|---|
| `customer_id` | string | yes |  |
| `snapshot_date` | string | yes |  |
| `features` | object<string, number \| integer \| null> | yes | Computed feature vector; see app/features for definitions. |
| `model_version` | string | yes |  |

### `SimulateRequest`

| field | type | required | notes |
|---|---|---|---|
| `scenarios` | string[] | no | default `["baseline"]` |
| `loan_amount` | number \| null | no |  |
| `loan_tenure_months` | integer \| null | no |  |
| `loan_interest_rate` | number \| null | no |  |
| `n_paths` | integer | no | default `1000` |
| `months_projected` | integer | no | default `12` |
| `method` | string | no | default `"auto"` |

### `SimulateResponse`

| field | type | required | notes |
|---|---|---|---|
| `customer_id` | string | yes |  |
| `simulation_id` | string | yes |  |
| `scenarios` | object<string, `SimulationScenario`> | yes |  |
| `confidence_bands` | object<string, object<string, object<string, number>>> | yes |  |

### `DistressRiskResponse`

| field | type | required | notes |
|---|---|---|---|
| `customer_id` | string | yes |  |
| `distress_probability_12m` | number | yes |  |
| `survival_function` | object<string, number> | yes | Keyed by month index |
| `hazard_ratios` | object<string, number> | yes |  |
| `median_survival_time_months` | number \| null | yes |  |
| `primary_model` | string | yes |  |
| `concordance_index` | number | yes |  |
| `fallback_model` | `FallbackModelSummary` | yes |  |
| `model_version` | string | yes |  |

### `AnomalyListResponse`

| field | type | required | notes |
|---|---|---|---|
| `anomalies` | `AnomalyItem`[] | yes |  |
| `total` | integer | yes |  |

### `RecommendRequest`

| field | type | required | notes |
|---|---|---|---|
| `language` | string | no | default `"hi"` |
| `include_llm_explanation` | boolean | no | default `false` |

### `RecommendationResponse`

| field | type | required | notes |
|---|---|---|---|
| `recommendation_id` | string \| null | no |  |
| `customer_id` | string | yes |  |
| `product_type` | string | yes |  |
| `amount` | number \| null | yes |  |
| `tenure_months` | integer \| null | yes |  |
| `monthly_cost` | number \| null | yes |  |
| `cbs_score` | number | yes |  |
| `cbs_components` | `CBSComponentsOut` | yes |  |
| `constraints_passed` | string[] | yes |  |
| `constraints_failed` | string[] | yes |  |
| `simulation_summary` | `SimulationSummary` | yes |  |
| `distress_probability` | number | yes |  |
| `distress_state` | boolean | yes |  |
| `max_anomaly_score` | number | yes |  |
| `status` | string | yes | recommended \| no_action \| vetoed |
| `veto_reason` | string \| null | yes |  |
| `language` | string | yes |  |
| `candidates_evaluated` | integer | yes |  |
| `candidates_feasible` | integer | yes |  |
| `confidence_level` | string | yes |  |
| `confidence_interval` | `ConfidenceInterval` | yes |  |
| `shap_values` | `Attribution`[] | yes |  |
| `need_match_attribution` | `Attribution`[] | yes |  |
| `explanation` | string | yes |  |
| `llm_explanation` | string \| null | yes |  |
| `llm_status` | string \| null | yes |  |

### `MatchingProductsResponse`

| field | type | required | notes |
|---|---|---|---|
| `customer_id` | string | yes |  |
| `recommendation_id` | string | yes |  |
| `product_type` | string | yes |  |
| `amount` | number \| null | no |  |
| `tenure_months` | integer \| null | no |  |
| `matching_products` | `BankProductMatch`[] | yes |  |
| `disclaimer` | string \| null | no |  |
| `note` | string \| null | no |  |

### `ExplainResponse`

| field | type | required | notes |
|---|---|---|---|
| `customer_id` | string | yes |  |
| `recommendation_id` | string | yes |  |
| `product_type` | string | yes |  |
| `status` | string | yes |  |
| `shap_values` | `Attribution`[] | yes |  |
| `need_match_attribution` | `Attribution`[] | yes |  |
| `model_used` | string | yes |  |
| `explanation` | string | yes |  |
| `veto_reason` | string \| null | yes |  |
| `constraints_failed` | string[] \| null | yes |  |
| `confidence_level` | string | yes |  |
| `confidence_interval` | object \| null | yes |  |

### `ConsentRequest`

| field | type | required | notes |
|---|---|---|---|
| `customer_id` | string | yes |  |
| `scope` | string | yes |  |
| `granted` | boolean | yes |  |
| `purpose` | string | yes |  |

### `ConsentCreated`

| field | type | required | notes |
|---|---|---|---|
| `id` | string | yes |  |
| `customer_id` | string | yes |  |
| `scope` | string | yes |  |
| `granted` | boolean | yes |  |
| `granted_at` | string \| null | yes |  |
| `revoked_at` | string \| null | yes |  |
| `purpose` | string | yes |  |

### `ConsentListResponse`

| field | type | required | notes |
|---|---|---|---|
| `customer_id` | string | yes |  |
| `consent_records` | `ConsentRecordOut`[] | yes |  |

### `ConsentRevoked`

| field | type | required | notes |
|---|---|---|---|
| `id` | string | yes |  |
| `scope` | string | yes |  |
| `granted` | boolean | yes |  |
| `revoked_at` | string | yes |  |
| `active` | boolean | yes |  |

### `AuditLogResponse`

| field | type | required | notes |
|---|---|---|---|
| `customer_id` | string | yes |  |
| `logs` | `AuditLogItem`[] | yes |  |
| `total` | integer | yes |  |

### `StartRequest`

| field | type | required | notes |
|---|---|---|---|
| `language` | string | no | default `"hi"` |
| `customer_name` | string \| null | no |  |

### `OnboardingStartResponse`

| field | type | required | notes |
|---|---|---|---|
| `session_id` | string | yes |  |
| `step` | string | yes |  |
| `message` | string | yes |  |
| `progress` | number | yes |  |

### `MessageRequest`

| field | type | required | notes |
|---|---|---|---|
| `message` | string | yes |  |

### `OnboardingMessageResponse`

| field | type | required | notes |
|---|---|---|---|
| `step` | string | yes |  |
| `message` | string | yes |  |
| `progress` | number | yes |  |
| `accepted` | boolean | yes |  |
| `attempts` | integer \| null | no |  |
| `review` | object \| null | no |  |

### `OnboardingStateResponse`

| field | type | required | notes |
|---|---|---|---|
| `session_id` | string | yes |  |
| `language` | string | yes |  |
| `step` | string | yes |  |
| `progress` | number | yes |  |
| `collected` | object | yes |  |

### `EnquiryRequest`

| field | type | required | notes |
|---|---|---|---|
| `product_type` | string | yes |  |
| `amount` | number | yes |  |
| `tenure_months` | integer \| null | no |  |

### `EnquiryResponse`

| field | type | required | notes |
|---|---|---|---|
| `customer_id` | string | yes |  |
| `requested` | `EnquiryRequested` | yes |  |
| `verdict` | string | yes | affordable \| declined |
| `assessment` | `EnquiryAssessment` | yes |  |
| `baseline` | `EnquiryBaseline` | yes |  |
| `distress_probability_12m` | number | yes |  |
| `counter_offer` | `CounterOffer` \| null | yes |  |
| `matching_products` | `BankProductMatch`[] | yes |  |
| `matching_products_note` | string \| null | no |  |

### `HealthResponse`

| field | type | required | notes |
|---|---|---|---|
| `status` | string | yes |  |
| `database` | string | yes |  |
| `model_version` | string | yes |  |
| `models` | `ModelWarmupStatus` | yes |  |
| `timestamp` | string | yes |  |

### `CustomerSummary`

| field | type | required | notes |
|---|---|---|---|
| `id` | string | yes |  |
| `persona` | string | yes |  |
| `name` | string | yes |  |
| `age` | integer | yes |  |
| `city` | string | yes |  |
| `monthly_income_mean` | number | yes |  |
| `dbr` | number \| null | yes |  |
| `liquidity_runway` | number \| null | yes |  |
| `distress_state` | boolean | yes |  |
| `life_stage` | string | yes |  |

### `TransactionItem`

| field | type | required | notes |
|---|---|---|---|
| `id` | string | yes |  |
| `txn_date` | string | yes |  |
| `txn_time` | string \| null | yes |  |
| `amount` | number | yes |  |
| `type` | string | yes |  |
| `category` | string | yes |  |
| `merchant` | string | yes |  |
| `is_recurring` | boolean | yes |  |
| `is_anomaly` | boolean | yes |  |

### `SimulationScenario`

| field | type | required | notes |
|---|---|---|---|
| `p_shortfall_12m` | number | yes |  |
| `expected_liquidity` | object<string, number> | yes |  |
| `liquidity_percentiles` | object<string, object<string, number>> | yes |  |
| `expected_runway` | number | yes |  |
| `parameters` | object | yes |  |

### `FallbackModelSummary`

| field | type | required | notes |
|---|---|---|---|
| `name` | string | yes |  |
| `distress_probability_12m` | number | yes |  |
| `concordance_index` | number | yes |  |

### `AnomalyItem`

| field | type | required | notes |
|---|---|---|---|
| `transaction_id` | string | yes |  |
| `txn_date` | string | yes |  |
| `amount` | number | yes |  |
| `type` | string | yes |  |
| `category` | string | yes |  |
| `merchant` | string | yes |  |
| `detection_method` | string | yes |  |
| `anomaly_score` | number | yes |  |
| `confidence` | number | yes |  |
| `features` | object<string, number \| integer \| null> | yes |  |
| `injected_tag` | string \| null | no | Ground-truth tag from the synthetic generator; validation aid only. |

### `CBSComponentsOut`

| field | type | required | notes |
|---|---|---|---|
| `need_match` | number | yes |  |
| `affordability_delta` | number | yes |  |
| `risk_reduction` | number | yes |  |
| `life_stage_align` | number | yes |  |
| `distress_delta` | number | yes |  |

### `SimulationSummary`

| field | type | required | notes |
|---|---|---|---|
| `p_shortfall_12m` | number | yes |  |
| `expected_runway` | number | yes |  |
| `p5_liquidity_12m` | number \| null | yes |  |
| `p95_liquidity_12m` | number \| null | yes |  |

### `ConfidenceInterval`

| field | type | required | notes |
|---|---|---|---|
| `cbs_low` | number \| null | yes |  |
| `cbs_high` | number \| null | yes |  |
| `method` | string | yes |  |
| `ci_width_ratio` | number \| null | yes |  |

### `Attribution`

| field | type | required | notes |
|---|---|---|---|
| `feature` | string | yes |  |
| `value` | number \| integer \| string \| null | yes |  |
| `shap` | number | yes |  |
| `direction` | string | yes |  |

### `BankProductMatch`

| field | type | required | notes |
|---|---|---|---|
| `bank_name` | string | yes |  |
| `product_name` | string | yes |  |
| `product_type` | string | yes |  |
| `amount` | number | yes |  |
| `tenure_months` | integer \| null | yes |  |
| `interest_rate_band` | `InterestRateBand` | yes |  |
| `monthly_cost` | number | yes |  |
| `total_interest_at_min_rate` | number | yes |  |
| `processing_fee_pct` | number \| null | yes |  |
| `annual_fee` | number \| null | yes |  |
| `post_dbr` | number | yes |  |
| `post_p_shortfall_12m` | number | yes |  |
| `post_runway_months` | number | yes |  |
| `passes_safety_gate` | boolean | yes |  |
| `veto_reason` | string \| null | yes |  |
| `constraints_failed` | string[] | yes |  |
| `eligibility_notes` | string | yes |  |
| `source_note` | string | yes | Provenance; these are illustrative bands, not live quotes. |
| `source_url` | string \| null | yes |  |
| `last_verified_date` | string | yes |  |

### `ConsentRecordOut`

| field | type | required | notes |
|---|---|---|---|
| `id` | string | yes |  |
| `scope` | string | yes |  |
| `granted` | boolean | yes |  |
| `granted_at` | string \| null | yes |  |
| `revoked_at` | string \| null | yes |  |
| `purpose` | string | yes |  |
| `active` | boolean | yes |  |

### `AuditLogItem`

| field | type | required | notes |
|---|---|---|---|
| `id` | string | yes |  |
| `action` | string | yes |  |
| `module` | string | yes |  |
| `input_hash` | string | yes |  |
| `output_summary` | object | yes |  |
| `timestamp` | string | yes |  |

### `EnquiryRequested`

| field | type | required | notes |
|---|---|---|---|
| `product_type` | string | yes |  |
| `amount` | number | yes |  |
| `tenure_months` | integer \| null | yes |  |

### `EnquiryAssessment`

| field | type | required | notes |
|---|---|---|---|
| `amount` | number | yes |  |
| `tenure_months` | integer \| null | yes |  |
| `monthly_cost` | number | yes |  |
| `post_dbr` | number | yes |  |
| `post_p_shortfall_12m` | number | yes |  |
| `post_runway_months` | number | yes |  |
| `passes` | boolean | yes |  |
| `veto_reason` | string \| null | yes |  |
| `constraints_passed` | string[] | yes |  |
| `constraints_failed` | string[] | yes |  |

### `EnquiryBaseline`

| field | type | required | notes |
|---|---|---|---|
| `dbr` | number \| null | yes |  |
| `p_shortfall_12m` | number | yes |  |
| `expected_runway` | number | yes |  |
| `liquidity_runway_months` | number \| null | yes |  |

### `CounterOffer`

| field | type | required | notes |
|---|---|---|---|
| `amount` | number \| null | no |  |
| `tenure_months` | integer \| null | no |  |
| `monthly_cost` | number \| null | no |  |
| `post_dbr` | number \| null | no |  |
| `post_p_shortfall_12m` | number \| null | no |  |
| `post_runway_months` | number \| null | no |  |
| `passes` | boolean \| null | no |  |
| `veto_reason` | string \| null | no |  |
| `constraints_passed` | string[] \| null | no |  |
| `constraints_failed` | string[] \| null | no |  |
| `blocking_constraints` | string[] \| null | no |  |
| `blocking_reason` | string \| null | no |  |
| `note` | string | yes |  |

### `ModelWarmupStatus`

| field | type | required | notes |
|---|---|---|---|
| `status` | string | yes | cold \| warming \| warm \| failed \| skipped_no_data |
| `seconds` | number \| null | no |  |
| `error` | string \| null | no |  |

### `InterestRateBand`

| field | type | required | notes |
|---|---|---|---|
| `min` | number | yes |  |
| `max` | number | yes |  |
