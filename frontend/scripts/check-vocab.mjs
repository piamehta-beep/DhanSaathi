// Brief §13: no internal identifier may reach the screen. This greps the
// *user-facing strings* (both locale files) and the built HTML for API
// vocabulary. Code files legitimately contain these tokens (they are the
// mapping keys), so only the strings a person can read are checked.
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

const banned = [
  /\bdbr\b/i, /\bno_action\b/, /\bp_shortfall/i, /\bC[1-9]\b/,
  /\bstable_salaried\b/, /\byoung_earner\b/, /\bgig_worker\b/, /\bnear_retirement\b/,
  /\bover_leveraged\b/, /\bdistressed\b/, /\bliquidity_runway\b/, /\bveto_reason\b/,
  /\bcbs_score\b/, /\bshap\b/i, /\bpost_dbr\b/, /_exceeds_/, /\binsufficient_confidence\b/,
];

let bad = 0;
const check = (label, text) => {
  for (const re of banned) {
    const m = text.match(re);
    if (m) { console.error(`✗ ${label}: matched ${re} ("${m[0]}")`); bad++; }
  }
};

for (const f of ["hi", "en"]) {
  const json = JSON.parse(readFileSync(new URL(`../src/locales/${f}.json`, import.meta.url), "utf8"));
  for (const [k, v] of Object.entries(json)) check(`${f}.json ${k}`, v);
}

try {
  const dist = new URL("../dist", import.meta.url).pathname;
  for (const f of readdirSync(dist)) if (f.endsWith(".html")) check(`dist/${f}`, readFileSync(join(dist, f), "utf8"));
} catch { /* no build yet */ }

if (bad) { console.error(`${bad} internal identifier(s) visible in UI strings.`); process.exit(1); }
console.log("✓ no internal identifiers in user-facing strings");
