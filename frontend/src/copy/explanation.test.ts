import { describe, it, expect } from "vitest";
import i18n from "@/i18n";
import { humanizeExplanation } from "./explanation";
import { recommendMode } from "./mapping";

describe("humanizeExplanation", () => {
  it("re-says the backend templates without internal names (en)", async () => {
    await i18n.changeLanguage("en");
    const raw = "Main risk factors: dbr=0.6005, runway_trend=-0.0559. Offsetting strengths: expense_volatility=0.1468. mutual_fund_sip was matched most strongly on liquidity_runway=1.27.";
    const out = humanizeExplanation(raw, i18n.t).join(" ");
    expect(out).toBe(
      "What raises your risk: share of income going to loans and whether your savings buffer is growing or shrinking. " +
      "What works in your favour: how much your spending swings. " +
      "Monthly SIP (mutual fund) matched you most strongly on: months of savings.",
    );
    expect(out).not.toMatch(/dbr|runway_trend|mutual_fund_sip|=/);
  });
  it("handles the no_action template (hi)", async () => {
    await i18n.changeLanguage("hi");
    const raw = "Main risk factors: runway_trend=-0.4169, dbr=0.7643. No product cleared the safety checks by enough margin to be worth acting on.";
    const out = humanizeExplanation(raw, i18n.t);
    expect(out).toHaveLength(2);
    expect(out[1]).toBe("कोई भी प्रोडक्ट सुरक्षा जाँच इतने अंतर से पास नहीं कर पाया कि उसे लेना ठीक हो।");
  });
});

describe("recommendMode", () => {
  const base = { status: "recommended", distress_state: false, simulation_summary: { p_shortfall_12m: 0 } };
  it("classifies the three modes", () => {
    expect(recommendMode({ ...base, product_type: "credit_card" })).toBe("yes");
    expect(recommendMode({ ...base, product_type: "mutual_fund_sip" })).toBe("yes");
    expect(recommendMode({ ...base, product_type: "mutual_fund_sip", simulation_summary: { p_shortfall_12m: 0.434 } })).toBe("safer");
    expect(recommendMode({ ...base, product_type: "term_insurance", distress_state: true })).toBe("safer");
    expect(recommendMode({ ...base, product_type: "credit_card", simulation_summary: { p_shortfall_12m: 0.5 } })).toBe("yes");
    expect(recommendMode({ ...base, status: "no_action", product_type: "no_action" })).toBe("none");
  });
});
