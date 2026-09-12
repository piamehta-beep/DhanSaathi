# DhanSaathi — frontend

The product UI for DhanSaathi: an AI banking assistant for Bharat that would
rather decline than sell. Hindi first, built for a ₹10,000 Android on patchy
4G, and designed so that a **"no"** feels like trust rather than rejection.

React 18 · TypeScript · Vite · Tailwind · TanStack Query · react-i18next ·
Lucide · Vite PWA. No component library — the kit in `src/ui/` is the whole
design system.

---

## Run it

The backend must be up at `http://localhost:8010` (see the root README).
Wait for `GET /api/v1/health` to report `models.status: "warm"` before demoing.

```bash
cd frontend && npm install
```

```bash
cd frontend && npm run dev
```

Open <http://localhost:5173>. The dev server proxies `/api` to the backend so
the app is same-origin.

Other commands:

```bash
cd frontend && npm run build && npm run preview
```

```bash
cd frontend && npm test
```

```bash
cd frontend && npm run check:vocab
```

```bash
cd frontend && npm run gen:types
```

`gen:types` regenerates `src/api/types.ts` from the live OpenAPI spec. Types
are never hand-written.

### Environment

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_BASE` | `http://localhost:8010` | Backend origin. In dev the Vite proxy forwards `/api` there; in a build it's prefixed to every request. Leave empty when a reverse proxy serves the app and API from one origin. |

Copy `.env.example` to `.env` to override.

---

## The 90-second walkthrough

Nothing here needs narration. Language is Hindi by default.

1. **Welcome.** Tap the salaried persona ("Suresh के रूप में देखें").
2. **Home.** Three green statements. Tap **"मुझे क्या करना चाहिए?"**
3. **Suggestion (mode A).** A monthly SIP. Tap **"यह क्यों?"** → the safety
   checklist and the five bars. Back.
4. Header → **switch person** → pick the over-leveraged persona (Rohit).
5. **Home** is amber/red. **Suggestion (mode B):** "Right now, protecting
   what you have matters more than borrowing" — a small SIP, not credit.
6. Switch to **Pooja** (just started earning). Tap the suggestion's
   **"कोई खास प्रोडक्ट जाँचें"** → **Can I afford…?** Personal loan, ₹5 lakh,
   36 months, **जाँचें**. Result: "अभी नहीं" — and then **"लेकिन इतना आप
   सुरक्षित तरीके से ले सकते हैं: ₹20,000 तक"**. Tap the counter-offer → "हाँ,
   यह आपके बस में है". (Amit, the other young earner, gets ₹2.85 lakh and
   three bank cards with the provenance note.)
7. Switch to **Sunita** (distressed). **Suggestion (mode C):** a calm, warm
   screen. "अभी कोई नया प्रोडक्ट लेना सही नहीं है।" The reason, what would change
   it, and "हमने 41 विकल्प जाँचे।"
8. Toggle **English** on any screen. Everything switches; amounts stay in
   lakhs.

Then the depth, in any order:

9. **Future** tab → the Monte Carlo fan chart (1,000 paths, p5–p95 band,
   safety line). Add a ₹2 lakh loan → three scenarios overlaid, shortfall
   probability with its bootstrap interval, EMI, month-by-month table.
10. **Money** tab → every transaction with anomaly flags; "N flagged" opens
    the detector's own reasons and scores.
11. Header **Decision trail** → the audit log: every decision, its module,
    the input fingerprint; repeated decisions collapse into "N times, same
    inputs, same decision".
12. Home, below the fold → survival curve, hazard-ratio drivers with the
    model's C-index, and the raw feature vector.
13. Suggest, below the fold → benefit score on its −1…+1 axis with the
    confidence interval, the five score components, "your next 12 months if
    you take this", need-match attribution.
14. Ask → the **before → after → with counter-offer** table for the three
    gate numbers, and a link into Future pre-filled with that loan.
15. Welcome → browse all 1,000 customers with persona filter and search.
16. **Money → "Add a transaction and watch"**: add a ₹45,000 payment to a
    new merchant, dated inside the data window. The anomaly detector flags
    it live (score, reasons), and the before/after strip shows the runway
    and spend moving. This is the only write path in the UI and it is
    labelled as permanent for that demo customer.
17. Future → change the horizon (6/12/24 months) and path count
    (500/1,000/2,000); Suggest → "Explain in plain words (AI)" shows the
    LLM layer's honest status (off, because data doesn't leave the server);
    Home → the primary and backup distress models side by side; Your data →
    grant/revoke history per scope; Trail → filter by event kind.
18. Welcome → **How does it work?** — the seven-step pipeline, what the
    system refuses to do, and the backend's validation results.

Things a judge might click off-script, all designed:

- **आपका डेटा** (shield icon) → turn off "transactions" → go Home → the
  honest 403 state with one button back to re-grant.
- **New to DhanSaathi?** on Welcome → the WhatsApp-style onboarding. Demo
  values are printed under the input.
- Kill the backend → the offline banner appears; the last-seen screens stay
  visible; Retry recovers.

---

## Design decisions

**Three recommendation modes, not one template.** `POST /recommend` returns
a product or `no_action`, and a product can be either a genuine "yes" or a
protective counter-move. The screen has three distinct layouts:

- *Yes* — the product in plain words as the headline, monthly cost as the
  single big number, a confidence chip with its plain meaning, "Compare
  banks" + "Why this?".
- *Something safer instead* — same product card, but the headline is the
  reframe ("protecting what you have matters more than borrowing"). Detected
  from `product_type ∈ {term_insurance, mutual_fund_sip}` together with
  `p_shortfall_12m > 0.15` or `distress_state`.
- *Not right now* — `no_action`.

**Why `no_action` isn't red.** Red means danger. A decline is the system
working correctly for a person who is already stretched — the *opposite* of
danger. Mode C is warm neutral (sand), with a leaf icon, no warning glyphs,
and gets the same three things every "yes" gets: a reason (`veto_reason` in
words), what would change it, and proof the answer was earned
("We checked 41 options. None was safe enough." from `candidates_evaluated`
/ `candidates_feasible`). Amber is reserved for counter-offers and declines
in the enquiry flow, where the person asked for something specific.

**The frontend computes no financial number.** Every figure is an API field
passed through `formatINR` / `formatPct` / `formatMonths`. Traffic lights
classify a number for colour; they never transform it. The one place we
touch text is the backend's `explanation` string, which is built from four
fixed templates — `src/copy/explanation.ts` parses those exact shapes and
re-says them with human feature names. Nothing is invented; unknown shapes
fall through verbatim.

**Vocabulary lives in one file.** `src/copy/mapping.ts` is the only place
API values (personas, products, C1–C9, veto reasons, feature names,
confidence levels, scopes) meet human words; the words themselves are in
`src/locales/{hi,en}.json`. `npm run check:vocab` greps the locale files and
the built HTML for internal identifiers.

**Hindi is written, not translated.** Everyday spoken register, आप form,
common loanwords (लोन, ईएमआई, बैंक, SIP). Gendered verb forms are avoided so
the copy works for everyone ("क्या यह मेरे बस में है?" rather than "ले सकूँगा").

**Provenance is body text.** Every bank card set is preceded by the API's
`source_note` in full — above the cards, not behind an icon.

**Consent is real.** Toggles call `POST /consent` / `POST /consent/{id}/revoke`
and invalidate every cached query for that customer, so a revoked scope
produces the real 403 on the next screen. The 403 state reads
`detail.missing_scopes` and deep-links to the exact toggle.

**Every backend endpoint is on screen.** `/simulate` (Future tab + Home +
Suggest + Ask), `/distress-risk` in full (survival function, hazard
ratios, C-index, fallback model), `/transactions` (Money tab),
`/audit` (Decision trail), `/features` in full (At a glance), the CBS
score, its components and interval, and the need-match attribution.
Charts are hand-written SVG sized to the container so text stays at a
readable size on a phone; no chart library.

**Type scale in rem.** Cheap phones are frequently set to 120–130% system
font size; every screen was checked at 130% and 360 px.

**Motion only for state changes.** A 200 ms rise when a result appears;
toggles and bars animate their own change; nothing loops.
`prefers-reduced-motion` collapses all of it to instant.

---

## Layout

```
src/
  api/        types.ts (generated), client.ts (typed fetch), queries.ts (TanStack hooks)
  copy/       mapping.ts (API vocabulary → i18n keys), explanation.ts
  lib/        format.ts (+ tests), net.ts (offline store), paths.ts
  locales/    hi.json, en.json — flat, every UI string
  ui/         Button, Card, Chip, StatCard, Toggle, CheckList, BarRow, Banner,
              ChatBubble, LanguageToggle, Skeleton, Money, ErrorState, Layout,
              BottomNav, FanChart, SurvivalCurve, BeforeAfter, ScoreBar, Timeline
  screens/    Welcome (S0), Home (S1), Recommend (S2), Banks (S3), Enquire (S4),
              Why (S5), Onboarding (S6), Consent (S7), Future (S8), Money (S9),
              Trail (S10), About, AddTransaction, BankCards (shared)
```

Routes: `/` · `/start` · `/how-it-works` · `/c/:id` · `/c/:id/suggest` ·
`/c/:id/banks` · `/c/:id/ask` · `/c/:id/why` · `/c/:id/data` ·
`/c/:id/future` · `/c/:id/money` · `/c/:id/trail`.

### Backend coverage

| Endpoint | Where |
|---|---|
| `GET /health` | warm-up banner on Home |
| `GET /customers` | Welcome quick-start + full browser (persona filter, search, paging) |
| `GET /customers/{id}` | header, Home greeting, 404 guard |
| `GET /customers/{id}/features` | Home stats + At a glance, Money header, safety line on charts |
| `GET /customers/{id}/distress-risk` | Home (probability, survival curve, hazard ratios, C-index), Why |
| `GET /customers/{id}/anomalies` | Home (recent), Money (all, with detector reasons) |
| `GET /customers/{id}/transactions` | Money |
| `POST /customers/{id}/simulate` | Future (baseline / take_loan / smaller_loan), Home mini chart |
| `POST /customers/{id}/recommend` | Suggest (three modes, score, components, simulation summary, attributions) |
| `GET …/matching-products/{rec}` | Banks |
| `POST /customers/{id}/enquire` | Ask (verdict, counter-offer, before/after, banks) |
| `GET …/explain/{rec}` | Why (checklist, SHAP bars, need-match, models, CI) |
| `GET /audit/{id}` | Decision trail |
| consent endpoints | Your data + 403 state |
| onboarding endpoints | Get started |
| `POST /customers/{id}/transactions` | Money → "Add a transaction and watch" (demo write path) |
| `POST /recommend` with `include_llm_explanation` | Suggest → "Explain in plain words (AI)" |
| `POST /dataset/generate` | admin-only; intentionally not exposed |

---

## Verification

- `npm test` — `formatINR`, `spokenINR`, `formatPct`, explanation
  humaniser, mode detection.
- axe (dev-only, `@axe-core/react`) — zero violations on all thirteen
  routes with seeded data.
- Every state in the brief triggered deliberately: warm-up, loading,
  offline (fetch failure with cached data and without), 403, 404, empty
  anomalies, empty matching products, 422, reduced motion, 130% font.
- Checked at 360, 390, 412 and 1280 px, Hindi and English.
- Lighthouse mobile (simulated slow 4G, production build): Performance
  95–98, Accessibility 100, Best Practices 100 on Welcome, Home, Suggest,
  Ask, Future and Money; FCP 1.8–2.0 s, TBT ≤ 10 ms, CLS ≤ 0.07.
- Initial JS ≈ 119 KB gzipped (vendor 64 + app 33 + i18n 22); every
  screen off the main story path is code-split.
