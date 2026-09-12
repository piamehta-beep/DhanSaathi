"""Render docs/API_REFERENCE.md from the live OpenAPI document.

The reference is generated rather than hand-written so it cannot drift from
the code: every endpoint, field, type and nullability comes from the same
schemas FastAPI enforces at runtime. Regenerate after any API change with:

    python -m scripts.render_api_reference

It reads http://localhost:8010/openapi.json by default (the server must be
running) or a path given as the first argument.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "docs" / "API_REFERENCE.md"

HEADER = """# DhanSaathi API Reference

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

"""


def load_spec(source: str | None) -> dict:
    if source and not source.startswith("http"):
        return json.loads(Path(source).read_text())
    url = source or "http://localhost:8010/openapi.json"
    with urllib.request.urlopen(url) as resp:
        return json.load(resp)


class Renderer:
    def __init__(self, spec: dict) -> None:
        self.spec = spec
        self.schemas = spec.get("components", {}).get("schemas", {})
        self.rendered: set[str] = set()
        self.queue: list[str] = []

    # -- type formatting ---------------------------------------------------
    def type_of(self, schema: dict) -> str:
        if not schema:
            return "any"
        if "$ref" in schema:
            name = schema["$ref"].split("/")[-1]
            self.enqueue(name)
            return f"`{name}`"
        if "anyOf" in schema:
            parts = [self.type_of(s) for s in schema["anyOf"]]
            parts = [p for p in parts if p != "null"]
            has_null = any(s.get("type") == "null" for s in schema["anyOf"])
            joined = " \\| ".join(dict.fromkeys(parts))
            return f"{joined} \\| null" if has_null else joined
        t = schema.get("type")
        if t == "array":
            return f"{self.type_of(schema.get('items', {}))}[]"
        if t == "object":
            extra = schema.get("additionalProperties")
            if isinstance(extra, dict) and extra:
                return f"object<string, {self.type_of(extra)}>"
            if schema.get("properties"):
                return "object"
            return "object"
        if t == "null":
            return "null"
        if "enum" in schema:
            return " \\| ".join(f"`{v}`" for v in schema["enum"])
        return t or "any"

    def enqueue(self, name: str) -> None:
        if name not in self.rendered and name not in self.queue:
            self.queue.append(name)

    # -- schema tables -----------------------------------------------------
    def schema_table(self, name: str) -> str:
        schema = self.schemas.get(name, {})
        props = schema.get("properties", {})
        required = set(schema.get("required", []))
        lines = [f"### `{name}`"]
        if schema.get("description"):
            lines.append(schema["description"].strip())
        lines.append("")
        lines.append("| field | type | required | notes |")
        lines.append("|---|---|---|---|")
        for field, fs in props.items():
            note = (fs.get("description") or "").replace("\n", " ").replace("|", "\\|").strip()
            default = fs.get("default", None)
            if default is not None and "default" in fs:
                note = (note + f" default `{json.dumps(default)}`").strip()
            lines.append(
                f"| `{field}` | {self.type_of(fs)} | {'yes' if field in required else 'no'} | {note} |"
            )
        lines.append("")
        return "\n".join(lines)

    # -- endpoints ---------------------------------------------------------
    def endpoint(self, path: str, method: str, op: dict) -> str:
        lines = [f"### `{method.upper()} {path}`"]
        tags = op.get("tags") or []
        summary = (op.get("description") or op.get("summary") or "").strip()
        if summary:
            first_para = summary.split("\n\n")[0].replace("\n", " ")
            lines.append(first_para)
        deps = op.get("x-consent") or self._consent_hint(path, method)
        if deps:
            lines.append(f"**Consent-gated:** requires {deps}.")
        params = [p for p in op.get("parameters", []) if p.get("in") in ("query", "path")]
        if params:
            lines.append("")
            lines.append("| param | in | type | required | notes |")
            lines.append("|---|---|---|---|---|")
            for p in params:
                s = p.get("schema", {})
                note = (p.get("description") or "").replace("\n", " ").replace("|", "\\|")
                if "default" in s:
                    note = (note + f" default `{json.dumps(s['default'])}`").strip()
                lines.append(
                    f"| `{p['name']}` | {p['in']} | {self.type_of(s)} | "
                    f"{'yes' if p.get('required') else 'no'} | {note} |"
                )
        body = op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema")
        if body:
            lines.append("")
            lines.append(f"**Request body:** {self.type_of(body)}")
        responses = op.get("responses", {})
        for code in ("200", "201", "202"):
            r = responses.get(code)
            if not r:
                continue
            schema = r.get("content", {}).get("application/json", {}).get("schema")
            if schema:
                lines.append(f"**Response {code}:** {self.type_of(schema)}")
        lines.append("")
        return "\n".join(lines)

    def _consent_hint(self, path: str, method: str) -> str | None:
        gated = {
            ("/api/v1/customers/{customer_id}/features", "get"): "`transaction_analysis`",
            ("/api/v1/customers/{customer_id}/distress-risk", "get"): "`transaction_analysis`, `credit_assessment`",
            ("/api/v1/customers/{customer_id}/anomalies", "get"): "`anomaly_monitoring`",
            ("/api/v1/customers/{customer_id}/recommend", "post"): "`transaction_analysis`, `product_recommendation`",
            ("/api/v1/customers/{customer_id}/matching-products/{recommendation_id}", "get"): "`transaction_analysis`, `product_recommendation`",
            ("/api/v1/customers/{customer_id}/enquire", "post"): "`transaction_analysis`, `credit_assessment`",
        }
        return gated.get((path, method))

    def render(self) -> str:
        out = [HEADER]
        paths = self.spec["paths"]
        by_tag: dict[str, list[str]] = {}
        for path, ops in paths.items():
            for method, op in ops.items():
                tag = (op.get("tags") or ["other"])[0]
                by_tag.setdefault(tag, []).append(self.endpoint(path, method, op))
        order = [
            "health", "customers", "features", "simulation", "distress-risk", "anomalies",
            "recommendation", "enquiry", "explainability", "consent-and-audit",
            "onboarding", "dataset",
        ]
        for tag in order + [t for t in by_tag if t not in order]:
            if tag not in by_tag:
                continue
            out.append(f"## {tag}\n")
            out.extend(by_tag[tag])

        out.append("---\n\n## Schemas\n")
        out.append("Every response and request body above is one of these. `T \\| null` means the field may be null; `T[]` is an array; `object<string, T>` is a map with dynamic keys.\n")
        while self.queue:
            name = self.queue.pop(0)
            if name in self.rendered:
                continue
            self.rendered.add(name)
            out.append(self.schema_table(name))
        return "\n".join(out)


def main() -> None:
    source = sys.argv[1] if len(sys.argv) > 1 else None
    spec = load_spec(source)
    text = Renderer(spec).render()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(f"wrote {OUT} ({len(text.splitlines())} lines, {len(text)} chars)")


if __name__ == "__main__":
    main()
