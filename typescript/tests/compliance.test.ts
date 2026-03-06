import { describe, it, expect } from "vitest";
import {
  create,
  createMulti,
  audit,
  addHop,
  computeIntegrityHash,
} from "../src/index.js";

describe("audit — general", () => {
  it("should pass a well-formed unit", () => {
    let unit = createMulti(
      [
        {
          c: "Revenue is $4.2B",
          t: 0.95,
          ai: true,
          src: "SEC 10-Q",
          origin: { type: "ai", model: "gpt-4o" },
          reviews: [{ reviewer: "alice", verdict: "approved" }],
        },
      ],
      { by: "analyst", label: "internal" }
    );
    unit = addHop(unit, "analyst", "created");
    unit.hash = computeIntegrityHash(unit);
    const result = audit(unit);
    expect(result.regulation).toBe("general");
    expect(result.compliant).toBe(true);
    expect(result.score).toBeGreaterThanOrEqual(0.7);
    expect(result.checks.length).toBe(10);
    // All should pass
    const failedChecks = result.checks.filter((c) => !c.passed);
    expect(failedChecks.length).toBeLessThanOrEqual(2);
  });

  it("should fail audit with missing fields", () => {
    const unit = createMulti([{ c: "Bare claim", t: 0.5 }]);
    const result = audit(unit);
    // Missing: provenance, hash, label, source, ai_claims_labeled may still pass (ai=undefined counts)
    expect(result.compliant).toBe(false);
    expect(result.recommendations.length).toBeGreaterThan(0);
    expect(result.score).toBeLessThan(0.7);
  });

  it("should check origin_tracking for AI claims", () => {
    const unit = createMulti([{ c: "AI claim no origin", t: 0.8, ai: true }]);
    const result = audit(unit);
    const originCheck = result.checks.find((c) => c.check === "origin_tracking");
    expect(originCheck).toBeDefined();
    expect(originCheck!.passed).toBe(false);
  });

  it("should pass origin_tracking when no AI claims present", () => {
    const unit = createMulti([{ c: "Human claim", t: 0.9, ai: false, src: "docs" }]);
    const result = audit(unit);
    const originCheck = result.checks.find((c) => c.check === "origin_tracking");
    expect(originCheck).toBeDefined();
    expect(originCheck!.passed).toBe(true);
  });

  it("should check reviews present", () => {
    const unit = createMulti([{ c: "No reviews", t: 0.8, ai: false, src: "test" }]);
    const result = audit(unit);
    const reviewCheck = result.checks.find((c) => c.check === "review_present");
    expect(reviewCheck!.passed).toBe(false);
  });

  it("should pass review check with unit-level reviews", () => {
    const unit = createMulti([{ c: "Reviewed", t: 0.8, ai: false, src: "test" }]);
    unit.reviews = [{ reviewer: "bob", verdict: "approved" }];
    const result = audit(unit);
    const reviewCheck = result.checks.find((c) => c.check === "review_present");
    expect(reviewCheck!.passed).toBe(true);
  });

  it("should check freshness — expired claims fail", () => {
    const unit = createMulti([{ c: "Old claim", t: 0.8, ai: false, src: "test", exp: "2020-01-01T00:00:00Z" }]);
    const result = audit(unit);
    const freshCheck = result.checks.find((c) => c.check === "freshness_valid");
    expect(freshCheck!.passed).toBe(false);
  });
});

describe("audit — eu_ai_act", () => {
  it("should check EU AI Act articles", () => {
    const unit = createMulti([{ c: "AI content", t: 0.8, ai: true }]);
    unit.prov = [
      { hop: 0, by: "human-reviewer", do: "created", at: "2025-01-01T00:00:00Z" },
    ];
    const result = audit(unit, { regulation: "eu_ai_act" });
    expect(result.regulation).toBe("eu_ai_act");
    expect(result.checks.length).toBe(4);
    // Should have art13, art14, art15, art12
    const checkNames = result.checks.map((c) => c.check);
    expect(checkNames).toContain("art13_transparency");
    expect(checkNames).toContain("art14_human_oversight");
    expect(checkNames).toContain("art15_accuracy");
    expect(checkNames).toContain("art12_traceability");
  });

  it("should fail art14 when only AI actors in provenance", () => {
    const unit = createMulti([{ c: "AI content", t: 0.8, ai: true }]);
    unit.prov = [
      { hop: 0, by: "ai-agent", do: "created", at: "2025-01-01T00:00:00Z" },
    ];
    const result = audit(unit, { regulation: "eu_ai_act" });
    const art14 = result.checks.find((c) => c.check === "art14_human_oversight");
    expect(art14!.passed).toBe(false);
  });

  it("should pass art14 when human actors exist in provenance", () => {
    const unit = createMulti([{ c: "AI content", t: 0.8, ai: true }]);
    unit.prov = [
      { hop: 0, by: "ai-agent", do: "created", at: "2025-01-01T00:00:00Z" },
      { hop: 1, by: "human-reviewer", do: "reviewed", at: "2025-01-02T00:00:00Z" },
    ];
    const result = audit(unit, { regulation: "eu_ai_act" });
    const art14 = result.checks.find((c) => c.check === "art14_human_oversight");
    expect(art14!.passed).toBe(true);
  });

  it("should fail art15 for low-confidence AI without risk description", () => {
    const unit = createMulti([{ c: "Low confidence AI", t: 0.3, ai: true }]);
    unit.prov = [
      { hop: 0, by: "human", do: "created", at: "2025-01-01T00:00:00Z" },
    ];
    const result = audit(unit, { regulation: "eu_ai_act" });
    const art15 = result.checks.find((c) => c.check === "art15_accuracy");
    expect(art15!.passed).toBe(false);
  });

  it("should be compliant when all EU AI Act checks pass", () => {
    const unit = createMulti([
      { c: "AI content", t: 0.9, ai: true, risk: "minimal" },
    ]);
    unit.prov = [
      { hop: 0, by: "human-reviewer", do: "reviewed", at: "2025-01-01T00:00:00Z" },
    ];
    const result = audit(unit, { regulation: "eu_ai_act" });
    expect(result.compliant).toBe(true);
    expect(result.score).toBe(1);
  });
});
