import { describe, it, expect } from "vitest";
import { formatINR, spokenINR, formatPct, formatRateBand, formatMonths, formatINRShort, formatScore } from "./format";

describe("formatINR", () => {
  it("uses Indian grouping", () => {
    expect(formatINR(200000)).toBe("₹2,00,000");
    expect(formatINR(500000)).toBe("₹5,00,000");
    expect(formatINR(2500)).toBe("₹2,500");
    expect(formatINR(999)).toBe("₹999");
    expect(formatINR(1000)).toBe("₹1,000");
    expect(formatINR(12345678)).toBe("₹1,23,45,678");
    expect(formatINR(100000)).toBe("₹1,00,000");
  });
  it("rounds to whole rupees by default", () => {
    expect(formatINR(776.13)).toBe("₹776");
    expect(formatINR(4754.18)).toBe("₹4,754");
    expect(formatINR(16846.98)).toBe("₹16,847");
  });
  it("can keep paise", () => {
    expect(formatINR(776.13, { decimals: 2 })).toBe("₹776.13");
  });
  it("handles null and negatives", () => {
    expect(formatINR(null)).toBe("—");
    expect(formatINR(undefined)).toBe("—");
    expect(formatINR(-93604.64)).toBe("−₹93,605");
    expect(formatINR(0)).toBe("₹0");
  });
});

describe("spokenINR", () => {
  it("is null below a lakh", () => {
    expect(spokenINR(99999, "en")).toBeNull();
    expect(spokenINR(25000, "hi")).toBeNull();
  });
  it("speaks lakhs and crores", () => {
    expect(spokenINR(100000, "en")).toBe("₹1 lakh");
    expect(spokenINR(200000, "en")).toBe("₹2 lakh");
    expect(spokenINR(250000, "en")).toBe("₹2.5 lakh");
    expect(spokenINR(285000, "en")).toBe("₹2.9 lakh");
    expect(spokenINR(500000, "hi")).toBe("₹5 लाख");
    expect(spokenINR(12000000, "en")).toBe("₹1.2 crore");
    expect(spokenINR(12000000, "hi")).toBe("₹1.2 करोड़");
  });
});

describe("formatPct", () => {
  it("rounds to whole numbers, keeps one decimal under 1%", () => {
    expect(formatPct(0.289)).toBe("29%");
    expect(formatPct(0.6005)).toBe("60%");
    expect(formatPct(0.028)).toBe("3%");
    expect(formatPct(0.005)).toBe("0.5%");
    expect(formatPct(0)).toBe("0%");
    expect(formatPct(1)).toBe("100%");
    expect(formatPct(null)).toBe("—");
  });
});

describe("misc", () => {
  it("rate band", () => {
    expect(formatRateBand(10.85, 16.65)).toBe("10.85%–16.65%");
    expect(formatRateBand(36, 43)).toBe("36%–43%");
    expect(formatRateBand(10.5, 21)).toBe("10.5%–21%");
  });
  it("months", () => {
    expect(formatMonths(10.48)).toBe("10");
    expect(formatMonths(2.62)).toBe("2.6");
    expect(formatMonths(6)).toBe("6");
    expect(formatMonths(1.27)).toBe("1.3");
  });
});

describe("compact", () => {
  it("short rupees", () => {
    expect(formatINRShort(75000, "en")).toBe("₹75k");
    expect(formatINRShort(120000, "en")).toBe("₹1.2 L");
    expect(formatINRShort(-18754, "en")).toBe("−₹19k");
    expect(formatINRShort(500, "en")).toBe("₹500");
    expect(formatINRShort(200000, "hi")).toBe("₹2 लाख");
    expect(formatINRShort(75000, "hi")).toBe("₹75 हज़ार");
  });
  it("signed scores", () => {
    expect(formatScore(0.3893)).toBe("+0.39");
    expect(formatScore(-0.0327)).toBe("−0.03");
    expect(formatScore(0)).toBe("+0.00");
  });
});
