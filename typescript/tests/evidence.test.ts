import { describe, it, expect } from "vitest";
import { effectiveTrust } from "../src/index.js";
import type { AKFUnit, Claim, Evidence } from "../src/index.js";

function makeClaim(overrides: Partial<Claim>): Claim {
  return { c: "test", t: 0.5, ...overrides };
}

describe("Evidence and kind on Claim", () => {
  it("should accept kind field on claim", () => {
    const claim = makeClaim({ kind: "code_change" });
    expect(claim.kind).toBe("code_change");
  });

  it("should accept evidence array on claim", () => {
    const ev: Evidence = { type: "test_pass", detail: "42/42 passed" };
    const claim = makeClaim({ evidence: [ev] });
    expect(claim.evidence).toHaveLength(1);
    expect(claim.evidence![0].type).toBe("test_pass");
  });

  it("should accept evidence with all fields", () => {
    const ev: Evidence = {
      type: "type_check",
      detail: "mypy: 0 errors",
      at: "2025-01-01T00:00:00Z",
      tool: "mypy",
    };
    const claim = makeClaim({ evidence: [ev] });
    expect(claim.evidence![0].tool).toBe("mypy");
    expect(claim.evidence![0].at).toBe("2025-01-01T00:00:00Z");
  });
});

describe("Trust grounding", () => {
  it("should report ungrounded when no evidence", () => {
    const claim = makeClaim({ t: 0.9 });
    const result = effectiveTrust(claim);
    expect(result.grounded).toBe(false);
    expect(result.evidenceCount).toBe(0);
  });

  it("should report grounded when evidence present", () => {
    const ev: Evidence = { type: "test_pass", detail: "ok" };
    const claim = makeClaim({ t: 0.9, evidence: [ev] });
    const result = effectiveTrust(claim);
    expect(result.grounded).toBe(true);
    expect(result.evidenceCount).toBe(1);
  });

  it("should count multiple evidence items", () => {
    const evs: Evidence[] = [
      { type: "test_pass", detail: "ok" },
      { type: "lint_clean", detail: "clean" },
      { type: "type_check", detail: "0 errors" },
    ];
    const claim = makeClaim({ t: 0.9, evidence: evs });
    const result = effectiveTrust(claim);
    expect(result.evidenceCount).toBe(3);
  });

  it("should not change score based on evidence", () => {
    const c1 = makeClaim({ t: 0.9, tier: 1 });
    const c2 = makeClaim({
      t: 0.9,
      tier: 1,
      evidence: [{ type: "test_pass", detail: "ok" }],
    });
    const r1 = effectiveTrust(c1);
    const r2 = effectiveTrust(c2);
    expect(r1.score).toBe(r2.score);
  });
});

describe("AKFUnit new fields", () => {
  it("should accept model, tools, session on unit", () => {
    const unit: AKFUnit = {
      v: "1.0",
      claims: [makeClaim({ t: 0.8 })],
      model: "claude-sonnet-4-20250514",
      tools: ["bash", "edit"],
      session: "sess-123",
    };
    expect(unit.model).toBe("claude-sonnet-4-20250514");
    expect(unit.tools).toEqual(["bash", "edit"]);
    expect(unit.session).toBe("sess-123");
  });

  it("should work without new fields (backward compat)", () => {
    const unit: AKFUnit = {
      v: "1.0",
      claims: [makeClaim({ t: 0.8 })],
    };
    expect(unit.model).toBeUndefined();
    expect(unit.tools).toBeUndefined();
    expect(unit.session).toBeUndefined();
  });
});
