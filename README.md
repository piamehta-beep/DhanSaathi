# DhanSaathi

AI-powered hyper-personalized banking for Bharat — HackOut'26 backend prototype.

The differentiator is mathematical rigour, not UI polish. Recommendations come
out of a constrained optimizer whose hard constraints a model cannot override,
and the system is **bank-adverse by design**: it declines roughly a fifth of all
customers, and every distressed customer, because doing nothing is a real
competitor in the objective rather than a fallback.

It also doesn't stop at "personal loan, ₹2 lakh". Each decision is matched
against real bank products with real published rate bands, so the customer sees
an actual comparison — cheapest EMI first, each option independently re-checked
against the safety gate — rather than an abstract score.

---

## Architecture

```
 [A] DATA                  [B] FEATURES              [C] MODELS
 ┌──────────────┐        ┌──────────────────┐     ┌────────────────────────┐
 │ Synthetic    │        │ income           │     │ Monte Carlo cash-flow  │
 │ generator    │──────▶ │ obligations      │───▶ │   (OU / bootstrap)     │
 │ 1000 customers        │ liquidity        │     │ Cox PH survival        │
 │ 6 personas   │        │ trends           │     │   (+ discrete-time     │
 │ 652k txns    │        │ entropy          │     │    hazard fallback)    │
 └──────┬───────┘        │ credit           │     │ Anomaly: rules + iForest│
        │                │ behavioral       │     │ XGBoost need-match     │
        ▼                └──────────────────┘     │ SHAP attribution       │
 ┌──────────────┐                                 │ Bootstrap confidence   │
 │ PostgreSQL   │                                 └───────────┬────────────┘
 │ 12 tables    │                                             │ scores, probabilities
 └──────┬───────┘                                             ▼
        │                     ┌───────────────────────────────────────────┐
        │                     │ [D] DECISION LAYER                        │
        │                     │                                           │
        │                     │  Constrained optimizer                    │
        │                     │  x* = argmax CBS(x) s.t. constraints      │
        │                     │  over ~41 candidates + no_action          │
        │                     │              │                            │
        │                     │              ▼                            │
        │                     │  ╔═══════════════════════════════════╗    │
        │                     │  ║ SAFETY GATE  (C1..C9)             ║    │
        │                     │  ║ pure deterministic, zero ML       ║    │
        │                     │  ║ can veto anything, always         ║    │
        │                     │  ╚═══════════════════════════════════╝    │
        │                     │              │                            │
        │                     │              ▼                            │
        │                     │  Bank-product matching (per-product       │
        │                     │  EMI + independent gate re-check)         │
        │                     └───────────────┬───────────────────────────┘
        │                                     ▼
        │                     ┌───────────────────────────────┐
        └────────────────────▶│ [E] FastAPI + audit logging   │
                              └───────────────┬───────────────┘
                                              ▼
                              ┌───────────────────────────────┐
                              │ [F] /ui review surface        │
                              │     plain HTML, raw JSON      │
                              └───────────────────────────────┘
```

The ordering is the point. Models produce probabilities; they never produce the
final decision. The optimizer proposes; the safety gate disposes. The LLM layer,
if enabled, only rephrases numbers that are already frozen — it never computes
one.

Both isolation properties are enforced mechanically rather than by convention,
via AST inspection that fails the build:

- `tests/test_safety_isolation.py` — `app/safety/` must import no ML or LLM
  library, so no model output can reach the gate.
- `tests/test_llm_isolation.py` — `app/llm/` must import nothing from
  `app.models`, `app.safety`, `app.services` or `app.features`, so no feedback
  loop can form from language generation back into the decision.

---

## Running it

Requires Python 3.11+ (3.12 recommended) and Docker.

```bash
docker compose up -d
```

```bash
python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

```bash
cp .env.example .env && alembic upgrade head
```

Seed the data (~7 minutes for the full 1,000 customers):

```bash
python -m app.synthetic_data.seed --n 1000 --seed 42 \
  && python -m app.synthetic_data.seed_bank_products \
  && python -m app.synthetic_data.seed_consent
```

The consent step matters: endpoints that read customer data are consent-gated
and return **403** without it. Set `ENFORCE_CONSENT=false` in `.env` to bypass
that while debugging.

Run the API:

```bash
uvicorn app.main:app --reload --port 8010
```

Then open **http://localhost:8010/ui/** for the review surface, or
**http://localhost:8010/docs** for the OpenAPI explorer.

### Integrating a frontend

Every endpoint declares a typed response schema, so a client can be generated
straight from the spec:

```bash
npx openapi-typescript http://localhost:8010/openapi.json -o src/api-types.ts
```

Notes for whoever builds the UI:

- **Consent gates most endpoints.** Anything reading customer data returns
  **403** with `{"detail": {"error": "consent_required", "missing_scopes": [...]}}`
  unless consent is seeded or granted. Every handled error uses that
  `{"detail": {...}}` shape.
- **Wait for warm.** `GET /api/v1/health` reports `models.status`; calls made
  before it reads `warm` pay the one-off training cost.
- **Run a single worker.** Onboarding sessions and the trained-model cache are
  per-process, so `--workers 2` would give intermittent session 404s and train
  the models once per worker.
- **There is no authentication.** Any client can read any customer. That is
  acceptable for a prototype and must not reach a real deployment.
- Typical warm latencies: features 41ms, distress-risk 28ms, recommend 369ms,
  simulate 73ms, enquire 249ms, customers 72ms.

The server is ready immediately and trains the Cox and XGBoost models in a
background thread (~45s). `GET /api/v1/health` reports `models.status` as
`warming` then `warm`; wait for `warm` before demoing, or the first request
pays the training cost. Disable with `WARM_MODELS_ON_STARTUP=false`.

> **Apple Silicon note.** XGBoost needs the OpenMP runtime. If `import xgboost`
> fails with `Library not loaded: @rpath/libomp.dylib`, install it with the
> **arm64** Homebrew (`/opt/homebrew/bin/brew install libomp`). An x86_64 libomp
> from a Rosetta Homebrew under `/usr/local` will not load into an arm64 Python.

### Validation

```bash
pytest tests/ -q
```

The full Section 9.3 sweep across all 1,000 customers is slower and lives
outside the test loop:

```bash
python -m scripts.full_sweep
```

---

## Validation results

Measured on the seeded dataset (seed 42), all targets from spec Section 9.

| Module | Metric | Result | Target |
|---|---|---|---|
| Survival (Cox PH) | C-index (held-out) | **0.890** | > 0.70 |
| Survival | significant covariates with expected sign | **4/4** | all |
| Survival | Schoenfeld PH violations | **0** | none |
| Simulation | actual liquidity inside [p5,p95] | **85.6%** | > 80% |
| Anomaly | precision / recall / F1 | **0.832 / 0.978 / 0.899** | 0.70 / 0.60 / 0.65 |
| Anomaly | false positive rate | **0.0043** | < 0.05 |
| Optimizer | hard-constraint violations (all 1,000) | **0** | 0 |
| Optimizer | no_action rate | **21.7%** | > 20% |
| Optimizer | distressed customers declined | **96–100%** | > 80% |
| Fairness | non-financial attributes in model features | **0** | none |
| Consent | revocation blocks access immediately | **403** | enforced |

Predicted 12-month distress probability separates the personas cleanly, which is
the property the safety gate actually depends on:

| persona | P(distress within 12m) |
|---|---|
| near_retirement | 0.017 |
| gig_worker | 0.020 |
| young_earner | 0.020 |
| stable_salaried | 0.023 |
| over_leveraged | 0.122 |
| **distressed** | **0.556** |

---

## Demo walkthrough

Pick one customer from each of three personas in the `/ui` surface and walk the
same four buttons. The story tells itself.

**1. Stable salaried — the system says yes.**
DBR around 0.25, 8–11 months of runway, savings rate ~+0.20. `distress-risk`
returns roughly 0.02. `recommend` returns a **mutual fund SIP**: it is the
product their life stage and cash flow actually support, and the optimizer
found ~36 of 41 candidates feasible. Note it recommends the *smallest* SIP that
clears the benefit margin, not the largest they could afford.

**2. Over-leveraged — the system counter-offers.**
DBR 0.53–0.60, runway around 1.3 months. `simulate` with a ₹200,000 loan and
watch `p_shortfall_12m` jump against the baseline. `recommend` returns
**term insurance or no_action, never credit** — constraints C1–C4 fire on every
loan and card candidate. Roughly a quarter to a half of this persona is declined
outright.

**3. Distressed — the system refuses.**
DBR above 0.70, runway under 1 month, `distress-risk` around 0.56. `recommend`
returns **no_action** with a `veto_reason`, and only 1 of 41 candidates is
feasible. Then press `explain`: the refusal is attributed to specific features
with real SHAP-style values, not a templated apology. This is the case the whole
architecture exists for — the bank makes no money here, and the system says so
anyway.

Finish on **matching bank products** for customer 1 or 2 to show the grounding
layer: three named banks, their published APR bands, computed monthly cost
cheapest-first, per-bank post-DBR, and a per-product safety-gate result.

**The strongest single moment: let a customer ask for too much.** Use section 5
of the review UI to request a Rs 5,00,000 personal loan.

- A *young earner* is declined (post-DBR 0.63, C1/C2/C3 fail) and immediately
  counter-offered the largest amount that does clear every check — plus an
  honest note when that amount falls below every listed lender's minimum ticket
  size.
- An *over-leveraged* customer is declined with `no amount works`, naming the
  blocking constraint: their existing debt burden already exceeds the ceiling,
  so the problem is not the size of the request.
- A customer with recent unresolved anomalous activity is blocked on C6, which
  tells them the issue is their account activity, not their affordability.

Declining without saying what *is* affordable leaves a customer to guess, and
guessing usually means asking a lender with fewer scruples.

---

## API

All under `/api/v1`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness + DB check |
| POST | `/dataset/generate` | regenerate synthetic data |
| GET | `/customers` | list, filterable by persona |
| GET | `/customers/{id}` | full customer record |
| GET | `/customers/{id}/transactions` | transaction history |
| POST | `/customers/{id}/transactions` | append a transaction |
| GET | `/customers/{id}/features` | full computed feature vector |
| POST | `/customers/{id}/simulate` | Monte Carlo scenarios + confidence bands |
| GET | `/customers/{id}/distress-risk` | survival model output |
| GET | `/customers/{id}/anomalies` | scored anomalies |
| POST | `/customers/{id}/recommend` | full pipeline → decision |
| POST | `/customers/{id}/enquire` | "can I afford X?" + counter-offer |
| GET | `/customers/{id}/matching-products/{rec_id}` | real bank products |
| GET | `/customers/{id}/explain/{rec_id}` | attributions, incl. for vetoes |
| POST | `/consent`, `GET /customers/{id}/consent`, `POST /consent/{id}/revoke` | DPDP consent |
| GET | `/audit/{customer_id}` | append-only decision log |
| POST | `/onboarding/start` | begin vernacular onboarding |
| POST | `/onboarding/{session_id}/message` | advance the onboarding state machine |
| GET | `/onboarding/{session_id}` | current onboarding state |

---

## Honest notes

Things a judge might reasonably poke at, stated up front.

- **Bank rate bands are illustrative, not scraped.** They are representative
  figures for each product category, stored as ranges rather than false-precision
  point values. Every row carries a `source_note` saying so, and `source_url` is
  left blank rather than filled with a page that was never actually verified. A
  fabricated citation would be worse than an honest label.
- **Personal loans are never *proactively* recommended.** A borrowing need comes
  from an expressed funding requirement, and the synthetic dataset contains no
  such signal, so the need-match model has nothing honest to learn for that
  class. Rather than invent a label, the system covers the direction borrowing
  need actually comes from: `POST /customers/{id}/enquire` lets the customer ask,
  and answers with the full safety-gate verdict plus real bank products. The gate
  is identical either way — asking for credit does not buy a weaker check than
  being offered it, which a test asserts directly.
- **Need-match labels encode a designer's prior**, not observed outcomes. The
  dataset has no take-up or satisfaction data. In production these labels would
  be replaced by realised outcomes; the model is deliberately only one weighted
  term of five, and can never override the gate.
- **Constraint C6's window is a judgement call.** The spec fixes the 0.80 anomaly
  threshold but not the window it applies over. Measured over all 18 months, 98%
  of customers breach it and C6 silently becomes a blanket ban on credit. It is
  scoped here to 30 days, matching the `anomaly_count_30d` feature and C6's intent
  of *unresolved* activity. The threshold itself is unchanged.
- **Anomaly detection is a hybrid, and the forest is the junior partner.** A pure
  Isolation Forest scored 0.05 precision here, because the dominant injected
  anomaly shape is a burst of near-identical transactions — a *dense* cluster,
  which isolation-based scoring cannot see by construction. Deterministic robust
  rules carry the detection; the forest ranks and triages.
- **Within-persona C-index is near chance** (~0.5–0.6) even though population
  C-index is 0.89. Personas are generated from identical parameters, so there is
  little real signal left to rank *within* one, and the subgroup event counts are
  small. Across the population, which is what the gate consumes, discrimination is
  strong.
- **Section 10.5's literal fairness rule is not applied as written.** It asks
  that no persona fall below a 20% recommendation rate, which directly
  contradicts Sections 9.5 and 10.6 requiring distressed customers to be
  declined at least 80% of the time. Declining them is the anti-predatory
  feature, not a bias defect. The audit instead reports per-persona rates for
  transparency and tests the question that matters — whether a *non-financial*
  attribute predicts the outcome. `city`, `state`, `age`, and `name` are never
  model features, and a test asserts that.
- **The LLM vernacular layer ships disabled, by policy.** `DATA_LOCALITY=strict`
  is the default and switches it off outright, because Section 10.4 requires
  customer data to stay in-region and a hosted model endpoint cannot be assumed
  to satisfy that. Set `DATA_LOCALITY=regional` plus `OPENAI_API_KEY` only when
  the configured endpoint genuinely is. With it off, the structured explanation
  is still returned — the vernacular text is an addition on top, never a
  replacement. Verified: recommendations are numerically identical with the
  layer on and off.
- **Onboarding does no real KYC.** The state machine validates *formats* only —
  PAN pattern, Aadhaar's published Verhoeff checksum, PIN code shape. Nothing
  contacts UIDAI or the Income Tax Department and no identifier is checked
  against a real record. Collected identifiers are stored masked and the raw
  value is discarded, since a prototype has no legitimate reason to retain a
  government identifier.
