# DhanSaathi — Frontend Build Brief

You are a senior product designer and frontend engineer. You are building the
product UI for **DhanSaathi**, an AI-powered banking assistant for Bharat —
India's tier 2, 3 and 4 towns — for HackOut'26. The project is competing for
the **Best UI/UX** category, and this frontend is what that category will be
judged on. The backend is finished, validated, and off-limits to you.

Read this entire brief before writing any code. The API reference is in
`backend/docs/API_REFERENCE.md`; treat it as the exact contract.

---

## 1. What this product is, in one paragraph

DhanSaathi looks at a customer's transaction history and answers one honest
question: *what, if anything, should this person do with their money right
now?* Sometimes the answer is a mutual fund SIP or term insurance. Sometimes
it's a small credit card. And for roughly one customer in five — every
customer who is already in financial distress — the answer is **nothing**,
stated plainly, with the reason. The system is *bank-adverse by design*: it
would rather decline than sell. Every number it shows comes from a Monte
Carlo simulation, a survival model and a hard safety gate that no AI can
override, and every decision can explain itself. **Your job is to make that
honesty feel like trust instead of rejection.** That is the whole design
problem.

---

## 2. Who you are designing for

Design for the *user*, not for the judge — but make sure the judge can see
that you did.

**The person:** 24–55, in a town like Jaipur, Lucknow, Kolhapur or Guntur.
Earns ₹25,000–₹80,000 a month as a salaried worker, gig driver, small trader
or teacher. Hindi (or their regional language) first; reads English slowly
and distrusts it in financial contexts. Has used PhonePe, Google Pay and
WhatsApp; has probably never used a "wealth" or "credit" app. Has been burned
or knows someone burned by a loan app. Their default emotional state opening
a finance app is **wariness**.

**The device:** an entry-level or mid-range Android — ₹8,000–₹15,000, 360–412
px wide, 2–4 GB RAM, often 2+ years old, often a shared family phone. Network
is patchy 4G that drops to 3G or nothing. Data is metered. Battery is
precious.

**The hard numbers driving every choice below** (from the research this
brief is built on):

- 74% of new digital-payment users in India now come from non-metro regions,
  and **40% of them abandon an app within 90 days if it feels complicated**
  (Kantar–NPCI 2025).
- Google's Next Billion Users research: many users are unfamiliar with common
  design patterns and icons, prefer minimal typing, need the offline
  experience to be as usable as online, and respond to universally
  understood icons **paired with text**, never icons alone.
- 73% of semi-urban users trust an app more when it shows *who stands behind
  the numbers* (NPCI User Behaviour Report 2025). We cannot claim RBI or bank
  backing — we are a prototype — so our trust signal is **radical
  transparency**: show the source, show the reason, show the uncertainty.

---

## 3. What actually wins a UI/UX category

Hackathon UI/UX judging consistently rewards the same four things. Build
toward all four.

1. **A judge can use it unaided within 30 seconds.** No tutorial, no
   explanation from you. If they have to ask "what do I click", you've lost.
2. **One clear story, demoable in 90 seconds.** Not a feature tour. A
   narrative with a beginning, middle and end. Ours is: *the system says yes
   to one person, counter-offers a second, and refuses a third — and every
   time, it shows its reasoning.* Every screen either advances that story or
   is cut.
3. **Polish where it matters, restraint everywhere else.** Judges notice
   loading states, empty states, error states, and the *transition* between
   states more than they notice gradients. One accent colour. One type
   family. Generous whitespace. No decorative animation — only animation that
   communicates a state change.
4. **Evidence that you designed for the real audience.** Vernacular that
   reads naturally, not machine-translated. Numbers in lakhs. Touch targets
   sized for a thumb on a cheap screen. It should be obvious within seconds
   that this was made for a person in Lucknow, not a person in a design
   studio.

The projects that lose this category are the ones that are *beautiful but
generic* — a dark-mode dashboard with cards and charts that could be any
fintech. Don't build that.

---

## 4. Non-negotiable product principles

These come from how the backend is built. Violating any of them breaks the
product's integrity, and a judge who reads the backend README will notice.

- **The frontend never computes a financial number.** No EMI arithmetic, no
  ratios, no percentages derived client-side. Every figure on screen is a
  field from an API response, formatted but not transformed. If you need a
  number the API doesn't return, the answer is to not show it.
- **`no_action` is a first-class, dignified outcome.** It is never an error
  state, never a grey empty screen, never hidden behind "no recommendations
  found". It is the product working correctly and it gets the same design
  investment as a "yes".
- **Every decline explains itself and offers a next step.** The API always
  returns a `veto_reason`, and for enquiries either a `counter_offer` amount
  or the named `blocking_constraints`. Surface both. Never leave a person
  with "no" and nothing else.
- **Bank rates are illustrative.** Every bank product carries a
  `source_note` saying its rates are representative bands, not live quotes.
  That note must be visible wherever a rate is shown — not in a tooltip, not
  behind an info icon. Honesty about provenance *is* the trust signal.
- **The structured explanation is always shown.** The optional LLM
  vernacular text (`llm_explanation`) is disabled by default and will be
  `null`; the `explanation` string and `shap_values` are always present.
  Design for the structured data; treat the LLM text as a bonus if present.
- **Consent is real.** Endpoints return **403** without it. The consent
  screen is not decoration — revoking a scope genuinely breaks the features
  that need it, and the UI should show that honestly.

---

## 5. Repository and stack

**Layout — this is fixed:**

```
DhanSaathi/
├── backend/          finished. Do not modify anything here.
├── frontend/         you build this. Start empty.
├── docker-compose.yml
└── README.md
```

Work only inside `frontend/`. The backend runs at `http://localhost:8010`;
the API is under `/api/v1`. Never edit, move or "fix" anything in
`backend/`. If the API seems wrong, it isn't — re-read the reference.

**Stack (chosen for small bundles and fast iteration):**

- React 18 + TypeScript + Vite
- Tailwind CSS (utility-first; no component library — you will write a small
  design system yourself, section 8)
- TanStack Query for all data fetching (caching, loading/error states, retry)
- react-router for the handful of routes
- react-i18next for Hindi/English (see section 9 — Hindi is the default)
- Lucide icons (always paired with a text label)
- No chart library unless truly needed; simple SVG or CSS bars for the one
  or two visualisations. Recharts is acceptable if you do need axes.
- Vite PWA plugin so it installs to the home screen and shows a proper
  offline page

**Generate the API types from the live spec — do not hand-write them:**

```bash
cd frontend
npx openapi-typescript http://localhost:8010/openapi.json -o src/api/types.ts
```

Build a thin typed client in `src/api/client.ts` around `fetch` using those
types. Read the base URL from `VITE_API_BASE` (default
`http://localhost:8010`) and add a Vite dev proxy for `/api` so the dev
server is same-origin.

**Performance budget:** initial JS under 200 KB gzipped, first meaningful
paint under 2 s on a throttled "Slow 4G" profile, no image over 30 KB, no
web fonts heavier than one family in two weights (prefer a system stack with
a good Devanagari fallback — Noto Sans Devanagari if you must load one).

---

## 6. Information architecture

Seven screens. Five carry the story; two are supporting. Mobile-first at
360 px; must also look intentional at 1280 px because the judge will
probably project a laptop.

### S0 — Welcome / "Try DhanSaathi as…"

There is no login. The demo lets a judge step into a customer's shoes.
Frame it exactly that way — warm, not a settings screen.

- Language toggle top-right: **हिंदी / English**. Hindi selected by default.
- Headline in plain words: what DhanSaathi does, one sentence, no jargon.
- Six persona cards from `GET /customers?persona=…&limit=1` — or let the
  user pick a specific customer from a short list. Each card: a first name,
  age, city, one plain-language line ("Salaried, saves regularly" / "Gig
  driver, income up and down" / "Already carrying too much loan"). No
  numbers on the cards yet. The persona names in the API are internal —
  translate them to human descriptions.
- A single primary button per card: **"Continue as Sunita"** (or "सुनीता के
  रूप में देखें").
- This is the *only* screen with any hint that the data is synthetic — one
  quiet line at the bottom: "Demo data. No real customers."

### S1 — Home: "How am I doing?"

The financial health snapshot. **At most three numbers.** Each one is a
plain-language statement first and the figure second.

Source: `GET /customers/{id}` and `GET /customers/{id}/features` and
`GET /customers/{id}/distress-risk`.

Show:

1. **Runway** — `liquidity_runway`. "Your savings would cover about **8
   months** of expenses." Traffic-light: ≥6 green, 3–6 amber, <3 red.
2. **Loan load** — `dbr`. "**25%** of your income goes to loan payments."
   Green <0.30, amber 0.30–0.50, red >0.50. Never show the word "DBR".
3. **Risk of running short** — `distress_probability_12m`. "Chance of a cash
   crunch in the next year: **low**." Show the word (low / medium / high)
   large and the percentage small. Thresholds: <0.10 low, 0.10–0.30
   medium, >0.30 high.

Then one clear primary action: **"What should I do?"** → S2.

Below the fold, optional: "Recent unusual activity" from
`GET /customers/{id}/anomalies?min_score=0.7&limit=3` — only if any exist,
each as a plain sentence ("A ₹45,000 payment to a new shop on 15 March"),
never a table. This is an early-warning feature; treat it gently.

### S2 — The recommendation: "What DhanSaathi suggests"

This is the screen that wins or loses the category. `POST
/customers/{id}/recommend` returns one of three outcomes and the screen has
**three distinct visual modes**. Do not use one template with the text
swapped.

**Mode A — "Yes"** (`status: "recommended"`, a product):
- Product name in plain words ("A monthly SIP of ₹2,500" / "Term insurance
  for ₹25 lakh cover" / "A credit card with a ₹25,000 limit").
- What it costs per month (`monthly_cost`) as the single most prominent
  number.
- One sentence on why, from `explanation`.
- A confidence chip from `confidence_level`: high / medium / low, with a
  one-line plain meaning ("We are fairly sure about this").
- Two actions: **"Compare banks"** → S3 (credit/insurance only) and **"Why
  this?"** → S5.

**Mode B — "Something safer instead"**: technically the same status as A,
but when a customer is over-leveraged or borderline the product will be
insurance or a small SIP rather than credit. Detect this by `product_type ∈
{term_insurance, mutual_fund_sip}` together with `simulation_summary.
p_shortfall_12m > 0.15` or `distress_state: true`. Frame it as protection:
"Right now, protecting what you have matters more than borrowing." Then the
same product card as Mode A.

**Mode C — "Not right now"** (`status: "no_action"`):
- This screen must feel **calm and respectful**, not like a failure. Warm
  neutral colour, no red, no warning icons.
- Headline: "Right now, the best move is no new product." (Hindi: "अभी कोई
  नया प्रोडक्ट लेना सही नहीं है।")
- The reason, from `veto_reason`, translated to a human sentence (mapping in
  section 10). E.g. `customer_in_distress_state` → "Your finances are under
  strain at the moment, and adding anything would make that worse."
- What would change it: one line derived from the veto (e.g. for a debt
  ceiling: "Once your loan payments come down, we'll look again").
- Two actions: **"Why?"** → S5 and **"Check a specific product"** → S4.
- Show `candidates_evaluated` and `candidates_feasible` quietly at the
  bottom: "We checked 41 options. None was safe enough." This is a powerful
  trust line — it proves the "no" was earned.

All three modes share one element at the very bottom: a small, always
visible **"How we decided"** link → S5.

### S3 — Compare banks

`GET /customers/{id}/matching-products/{recommendation_id}`. Up to three
`matching_products`, cheapest first.

- One card per bank: bank name, product name, **monthly cost** large, the
  rate band ("10.85%–16.65%"), tenure, any fee.
- `passes_safety_gate` as a clear pass/fail chip with plain text: "Safe for
  you" / "Would stretch you too far". A bank that fails is shown, greyed,
  with the `veto_reason` in words — the comparison is more honest *with*
  the unsafe option visible.
- **The `source_note` is shown in full, in body text, once, above the
  cards.** Not a footnote. This is the screen where a judge will look for
  whether we're faking rates.
- If `matching_products` is empty and `note` is present, show the note as a
  gentle message, not an empty state illustration.

### S4 — "Can I afford…?"

`POST /customers/{id}/enquire`. The customer asks; the system answers.

- Product type as large tappable chips (loan / card / insurance / SIP), not
  a dropdown.
- Amount: quick-pick chips at the values in the API grid (₹50,000 /
  ₹1 lakh / ₹2 lakh / ₹5 lakh for loans) **plus** a numeric field. No
  slider — sliders are imprecise on cheap touchscreens.
- Tenure chips for loans (12 / 24 / 36 / 48 / 60 months).
- One primary button: **"Check"**.
- The result has two visual modes:
  - **Affordable** (`verdict: "affordable"`): green, monthly cost large,
    `post_dbr` as "after this, X% of income goes to loans", then the bank
    comparison inline (same cards as S3).
  - **Declined** (`verdict: "declined"`): amber (not red), the reason in
    words from `assessment.constraints_failed` (section 10), and then the
    most important element on the screen — the **counter-offer**. If
    `counter_offer.amount` exists: "You *could* safely borrow up to
    **₹20,000**" with its monthly cost, as an offer, with a button to check
    *that* amount. If `counter_offer.amount` is null: the
    `blocking_reason` in words and what would need to change. If
    `matching_products_note` is present (affordable amount below every
    lender's minimum), show it plainly.

This screen is the strongest single demo moment. A judge types ₹5,00,000,
gets a calm "no, but here's ₹20,000 you could manage", and understands the
entire product in one interaction. Make it feel like talking to a fair
person, not a rejection letter.

### S5 — "Why?" (explainability)

`GET /customers/{id}/explain/{recommendation_id}`. Two parts, in this order:

1. **The safety checklist.** Render constraints C1–C9 as a vertical list of
   ticks and crosses with the *human* label from section 10 — never the
   codes. Passed items green tick, failed items amber cross, items that
   didn't apply to this product omitted. This turns the safety gate into
   something a person can read in five seconds.
2. **What drove the decision.** `shap_values` (top 5) as horizontal bars: a
   plain-language feature name (section 10), the bar length by `|shap|`,
   coloured by `direction` (raises risk / lowers risk). Then the
   `explanation` sentence.

Keep this screen scannable. It exists to make the judge think "this thing
can defend every decision", not to impress them with a chart.

### S6 — Onboarding (showcase)

`POST /onboarding/start` then `POST /onboarding/{session_id}/message`. A
conversational, WhatsApp-style flow in Hindi: PAN → Aadhaar → PIN code →
income → review → done.

- Chat bubbles, one question at a time, the keyboard type matching the
  field (numeric for Aadhaar and PIN).
- Progress as a thin bar from `progress`.
- A rejected input (`accepted: false`) shows the API's message in a bubble;
  the input stays focused. Never a modal, never an alert.
- On completion show the masked values exactly as the API returns them
  (`******234F`) with a one-line note that nothing is stored unmasked.
- Reach this from a small "New to DhanSaathi?" link on S0. It is not on the
  main path; it exists to show the judge that vernacular onboarding was
  thought through.

### S7 — Consent & your data

`GET /customers/{id}/consent`, `POST /consent`, `POST /consent/{id}/revoke`.

- One toggle per scope with a plain-language purpose ("Look at my
  transactions to understand my income and spending"). `marketing` is off
  by default and stays off unless the person turns it on.
- Turning a scope off should be *possible and honest*: after revoking
  `transaction_analysis`, navigating to S1 will get a 403 — show the
  consent-required state (section 11) with a one-tap way back here to
  re-grant. Do not fake this by hiding the toggle.
- Reach it from a small "Your data" link in the header.

---

## 7. The 90-second judge walkthrough

Design the whole app so this script is smooth and requires no narration.
Practise it.

1. **S0.** Language is already Hindi. Tap the salaried persona ("Continue as
   Rajesh").
2. **S1.** Three green numbers. Tap "What should I do?".
3. **S2 Mode A.** A ₹2,500 SIP. Tap "Why this?" → **S5**, glance at the tick
   list, back.
4. Header: switch to the **over-leveraged** persona.
5. **S1.** Amber/red. **S2 Mode B or C.** "Not right now — we checked 41
   options."
6. **S4.** Type ₹5,00,000 loan. Get "declined, but ₹20,000 is safe". Tap
   the counter-offer → bank cards with the provenance note.
7. Switch to **distressed** persona. **S2 Mode C.** Calm screen. "Your
   finances are under strain."
8. Toggle to English on any screen — everything switches, numbers stay in
   lakhs.

If any step needs the presenter to explain what's happening, redesign that
step.

---

## 8. Design system

Write it as tokens in `tailwind.config` and a handful of components in
`src/ui/`. Keep it small enough to hold in your head.

**Colour.** Warm neutral base (off-white background, near-black text — not
pure white/black; cheap screens crush pure black). One brand accent, used
sparingly for the single primary action per screen — a deep saffron or
teal, chosen once. Three semantic colours that mean the same thing
everywhere: **green** = safe/yes, **amber** = caution/counter-offer/declined,
**red** = only for genuine danger (high distress risk on S1, an error). Red
is *never* used for `no_action`. All text ≥ 4.5:1 contrast on its
background; check it.

**Type.** One family. System stack (`system-ui`, `-apple-system`, `Segoe
UI`, `Roboto`, `Noto Sans`, `Noto Sans Devanagari`, `sans-serif`) so
Devanagari renders natively on Android without a download. Base 16 px;
never below 14 px for anything a person must read. Scale: 14 / 16 / 20 / 24
/ 32. Body line-height 1.5. Devanagari needs ~10% more line-height than
Latin — set 1.6 when the language is Hindi.

**Numbers.** Always Indian grouping: `₹2,00,000`, never `₹200,000`. For
amounts ≥ ₹1,00,000 also show the spoken form: "₹2 lakh". Write a single
`formatINR()` used everywhere; test it. Percentages as whole numbers unless
< 1%.

**Spacing.** 8-pt grid. Screen padding 16 px on mobile, 24 px+ on desktop.
Cards 16 px internal. Sections separated by 24–32 px, not by lines.

**Touch.** Every tappable element ≥ 48 × 48 px hit area, ≥ 8 px between
adjacent targets. Primary button full-width on mobile, 56 px tall, at the
bottom of the screen within thumb reach — not at the top.

**Icons.** Lucide, 24 px, always with a visible text label. An icon alone
is never the only way to understand a control.

**Motion.** Only for state changes: a result appearing, a mode switching, a
toggle flipping. 150–250 ms, ease-out. Respect
`prefers-reduced-motion` — under it, all motion becomes an instant change.
No looping animations, no parallax, no skeleton shimmer longer than the
content takes (use a single subtle pulse).

**Components to build:** `Button` (primary / secondary / quiet), `Card`,
`StatCard` (statement + number + traffic-light), `Chip` (selectable and
status variants), `Toggle`, `CheckList` (the C1–C9 list), `BarRow` (the
SHAP bars), `Banner` (offline / warm-up / consent), `ChatBubble`
(onboarding), `LanguageToggle`. That's the whole kit.

---

## 9. Language and microcopy

Hindi is the default; English is a toggle. Both must read as if written by a
person, not translated by a machine.

- Use **conversational, second-person, present tense**. "Your savings would
  cover 8 months" not "Liquidity runway: 8.0".
- **Never show an internal name.** No `dbr`, no `no_action`, no
  `p_shortfall_12m`, no `C3`, no persona codes. Section 10 has the full
  mapping — use it as the single source of truth.
- **Hindi register:** everyday spoken Hindi, आप form, short sentences, common
  loanwords where they are what people actually say (लोन, ईएमआई, बैंक,
  सेविंग्स are all fine — nobody says "ऋण" in a bank app). Avoid Sanskritised
  formal Hindi.
- **Every decline says what happens next.** Not "Declined." but "Not right
  now — once X changes, we'll look again."
- **Uncertainty is stated, never hidden.** "We are fairly sure" / "We are
  not sure yet — we need a few more months of data" maps directly to
  `confidence_level`.
- Keep the i18n files (`src/locales/hi.json`, `en.json`) flat and readable.
  Every string in the UI goes through them; no hard-coded text in
  components.

---

## 10. Vocabulary mapping — the single source of truth

Put this in `src/copy/mapping.ts` and import it everywhere. Never
re-derive it.

**Personas → human descriptions**

| API value | English | Hindi |
|---|---|---|
| `stable_salaried` | Salaried, saves regularly | नौकरी वाले, नियमित बचत |
| `young_earner` | Just started earning | अभी कमाना शुरू किया |
| `gig_worker` | Gig work, income goes up and down | गिग काम, आमदनी ऊपर-नीचे |
| `near_retirement` | Close to retirement | रिटायरमेंट के करीब |
| `over_leveraged` | Carrying a lot of loans | बहुत सारे लोन चल रहे हैं |
| `distressed` | Finances under strain right now | अभी पैसों की तंगी है |

**Products**

| API value | English | Hindi |
|---|---|---|
| `personal_loan` | Personal loan | पर्सनल लोन |
| `credit_card` | Credit card | क्रेडिट कार्ड |
| `term_insurance` | Term insurance (life cover) | टर्म इंश्योरेंस (लाइफ कवर) |
| `mutual_fund_sip` | Monthly SIP (mutual fund) | मासिक SIP (म्यूचुअल फंड) |
| `no_action` | No new product right now | अभी कोई नया प्रोडक्ट नहीं |

**Safety checks (C1–C9) → human labels.** Use these in the S5 checklist
and wherever `constraints_failed` is shown.

| Code | Plain English | Hindi |
|---|---|---|
| C1 | Loan payments would stay within half your income | लोन की किस्तें आमदनी के आधे से कम रहेंगी |
| C2 | A new loan keeps payments under 40% of income | नया लोन लेने पर किस्तें आमदनी के 40% से कम रहेंगी |
| C3 | Low chance of running short of cash this year | इस साल पैसे कम पड़ने का खतरा कम है |
| C4 | At least 3 months of savings would remain | कम से कम 3 महीने की बचत बची रहेगी |
| C5 | Finances are not under strain right now | अभी पैसों की तंगी नहीं है |
| C6 | No unusual account activity recently | हाल में खाते में कोई अजीब गतिविधि नहीं |
| C7 | We have enough history to judge (3+ months) | हमारे पास फैसले के लिए काफी जानकारी है |
| C8 | You are saving money each month | आप हर महीने कुछ बचा रहे हैं |
| C9 | The insurance premium is affordable | इंश्योरेंस का प्रीमियम आपके बजट में है |

**Veto reasons → sentences** (`veto_reason` / `blocking_reason`)

| API value | English |
|---|---|
| `post_dbr_exceeds_0.50` | Your loan payments are already more than half your income. |
| `new_loan_dbr_exceeds_0.40` | A new loan would push your payments past 40% of your income. |
| `shortfall_probability_exceeds_0.15` | There's a real chance you'd run short of cash this year. |
| `runway_below_3_months` | It would leave you with less than 3 months of savings. |
| `customer_in_distress_state` | Your finances are under strain at the moment. |
| `high_anomaly_score` | There's been unusual activity on your account recently. |
| `insufficient_data` | We don't have enough of your history yet — check back in a few months. |
| `negative_savings_rate` | You're spending more than you earn right now, so investing isn't safe yet. |
| `insurance_premium_unaffordable` | The premium would stretch your budget too far. |

Provide Hindi equivalents for each in `hi.json`, written naturally.

**Feature names → plain language** (for the S5 bars; `shap_values[].feature`)

| Feature | English |
|---|---|
| `dbr` | Share of income going to loans |
| `liquidity_runway` | Months of savings |
| `income_cv` / `income_stability` | How steady your income is |
| `savings_rate` | How much you save each month |
| `savings_trend_slope` | Whether your savings are growing |
| `expense_volatility` | How much your spending swings |
| `category_entropy` | How spread-out your spending is |
| `anomaly_count_30d` / `anomaly_count_90d` | Recent unusual activity |
| `runway_trend` | Whether your savings buffer is growing or shrinking |
| `txn_frequency_trend` | How your activity is changing |
| `expense_trend_slope` | Whether your spending is rising |
| `credit_util_trend` | Credit card usage trend |

**Confidence**

| API value | English |
|---|---|
| `high` | We're fairly sure about this |
| `medium` | We're reasonably sure |
| `low` | We're not very sure — treat this as a starting point |
| `insufficient_data` | We need a few more months of your history first |
| `insufficient_confidence` | We can't tell yet whether this would help |

---

## 11. States — design every one of these before you design the happy path

Judges click things that aren't on the script. Each of these must look
intentional.

- **Model warm-up.** On app load, poll `GET /health` until
  `models.status === "warm"` (up to ~60 s after backend start). Until then,
  S0 is usable but S1's primary button shows a calm banner: "Getting things
  ready — about a minute." with a progress hint from `models.seconds` if
  present. Never block the whole app.
- **Loading.** Skeleton shapes that match the final layout, single soft
  pulse, and the request's real latency is short (most calls < 400 ms) so
  don't over-invest — but `POST /recommend` can take ~1 s cold: show
  "Checking 41 options…" as the loading text. That line is *content*.
- **Offline / network error.** A persistent top banner "You're offline —
  showing what we last saw" when fetch fails; the last successful responses
  stay visible from the Query cache. Retry button. Never a full-screen
  error for a transient failure.
- **403 consent required.** A specific, friendly state: "To do this,
  DhanSaathi needs your permission to look at your transactions." with a
  single button to S7 pre-scrolled to the missing scope
  (`detail.missing_scopes`).
- **404 customer / recommendation.** Only reachable via a stale link: "That
  page has moved on" and a button back to S0.
- **Empty.** Anomalies list empty → *don't render the section at all*.
  Matching products empty → the API's `note` as a sentence. Consent list
  empty cannot happen for seeded customers; handle it anyway with the grant
  buttons.
- **Validation (422).** Inline, under the field, in words. Never a toast for
  a field error.
- **Reduced motion** and **large system font** (users on cheap phones
  frequently set 120–130% font scale): the layout must not break at 130%.
  Test it.

---

## 12. Accessibility

Treat WCAG 2.1 AA as the floor, because the target user *is* the
accessibility case: low literacy, small screen, bright sunlight, one hand.

- Contrast ≥ 4.5:1 for text, ≥ 3:1 for large text and UI chrome.
- Every interactive element reachable and operable by keyboard, with a
  visible focus ring (not the browser default; a 2 px accent ring).
- Semantic HTML: real `<button>`, real `<label>`, landmarks (`<main>`,
  `<nav>`). Chips that select are radio groups with `aria-checked`.
- Language attribute switches with the toggle (`<html lang="hi">`) so
  screen readers pick the right voice.
- Traffic-light meaning is never conveyed by colour alone — always a word
  or icon too.
- Run axe (`@axe-core/react` in dev) and fix everything it reports before
  calling the app done.

---

## 13. Definition of done

You are done when *all* of these are true:

- [ ] The 90-second walkthrough in section 7 runs end to end without the
      presenter touching the keyboard except on S4 and S6.
- [ ] Every screen has been checked at 360 px, 412 px and 1280 px wide.
- [ ] Every screen has been checked in Hindi *and* English, at 100% and
      130% system font scale.
- [ ] Every state in section 11 has been triggered deliberately and looks
      intentional (kill the backend to test offline; revoke consent to test
      403).
- [ ] `no_action` (S2 Mode C) has had *at least as much* design time as
      Mode A.
- [ ] The provenance `source_note` is visible in body text on S3 and on the
      S4 affordable result.
- [ ] No internal identifier (`dbr`, `no_action`, `C3`, a persona code) is
      visible anywhere in the UI. Grep the built output for them.
- [ ] `formatINR` has unit tests and every rupee amount on screen goes
      through it.
- [ ] Lighthouse mobile: Performance ≥ 90, Accessibility 100, Best
      Practices ≥ 95. Bundle under budget.
- [ ] axe reports zero violations.
- [ ] `frontend/README.md` exists with: how to run, the env vars, the
      walkthrough script, and a short "design decisions" section that
      explains the three-mode recommendation screen and why `no_action`
      isn't red. Judges read READMEs.
- [ ] Nothing in `backend/` was touched.

---

## 14. Do not

- Do not compute any financial number in the frontend.
- Do not hide, soften, or reframe `no_action` as anything other than a
  legitimate recommendation.
- Do not show a bank rate without its `source_note`.
- Do not invent data the API didn't return — no fake "12 people near you
  chose this", no fake ratings, no fake "RBI approved".
- Do not use red for a decline or a `no_action`. Red is for danger only.
- Do not add a dark mode, a settings screen, notifications, a chatbot, or
  any feature not in section 6. Scope discipline is part of what wins.
- Do not use a component library. The kit in section 8 is deliberately
  small so the app has one voice.
- Do not use icons without labels, sliders for money, dropdowns where four
  chips would do, modals for errors, toasts for anything a person needs to
  read twice, or infinite scroll anywhere.
- Do not machine-translate. If you cannot write natural Hindi for a string,
  write it in simple English and mark it `TODO(hi)` so a human can fix it —
  that is more honest than bad Hindi.
- Do not touch `backend/`.

---

## 15. API quick map

Full contract: `backend/docs/API_REFERENCE.md` — paste it after this brief.
The calls you'll actually make, in story order:

| Screen | Call |
|---|---|
| boot | `GET /health` (poll until `models.status === "warm"`) |
| S0 | `GET /customers?persona={p}&limit=6` |
| S1 | `GET /customers/{id}`, `GET /customers/{id}/features`, `GET /customers/{id}/distress-risk`, `GET /customers/{id}/anomalies?min_score=0.7&limit=3` |
| S2 | `POST /customers/{id}/recommend` body `{"language": "hi"}` → keep `recommendation_id` |
| S3 | `GET /customers/{id}/matching-products/{recommendation_id}` |
| S4 | `POST /customers/{id}/enquire` body `{"product_type", "amount", "tenure_months"}` |
| S5 | `GET /customers/{id}/explain/{recommendation_id}` |
| S6 | `POST /onboarding/start` → `POST /onboarding/{session_id}/message` |
| S7 | `GET /customers/{id}/consent`, `POST /consent`, `POST /consent/{id}/revoke` |

Every error is `{"detail": {"error": "<code>", ...}}`. `consent_required`
carries `missing_scopes`. All money fields are plain numbers in rupees.
All IDs are UUID strings.

Build it so a person in Lucknow trusts it, and a judge in the room can tell
that you built it for her.
