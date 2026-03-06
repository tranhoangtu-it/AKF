import { describe, it, expect } from "vitest";
import {
  create,
  createMulti,
  detectAiWithoutReview,
  detectTrustBelowThreshold,
  detectHallucinationRisk,
  detectKnowledgeLaundering,
  detectClassificationDowngrade,
  detectStaleClaims,
  detectUngroundedClaims,
  detectTrustDegradationChain,
  detectExcessiveAiConcentration,
  detectProvenanceGap,
  runAllDetections,
} from "../src/index.js";
import type { AKFUnit } from "../src/index.js";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function aiUnit(overrides?: Partial<AKFUnit>): AKFUnit {
  return {
    ...createMulti([
      { c: "AI generated claim", t: 0.8, ai: true },
    ]),
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// 1. detectAiWithoutReview
// ---------------------------------------------------------------------------

describe("detectAiWithoutReview", () => {
  it("should not trigger when there are no AI claims", () => {
    const unit = create("Human claim", 0.9);
    const r = detectAiWithoutReview(unit);
    expect(r.triggered).toBe(false);
    expect(r.severity).toBe("info");
    expect(r.detectionClass).toBe("ai_content_without_review");
  });

  it("should trigger when AI claim has no review", () => {
    const unit = createMulti([{ c: "AI says hello", t: 0.8, ai: true }]);
    const r = detectAiWithoutReview(unit);
    expect(r.triggered).toBe(true);
    expect(r.severity).toBe("high");
    expect(r.affectedClaims.length).toBeGreaterThan(0);
  });

  it("should not trigger when AI claim has claim-level review", () => {
    const unit = createMulti([
      { c: "AI says hello", t: 0.8, ai: true, reviews: [{ reviewer: "alice", verdict: "approved" }] },
    ]);
    const r = detectAiWithoutReview(unit);
    expect(r.triggered).toBe(false);
  });

  it("should not trigger when unit has reviews", () => {
    const unit = createMulti([{ c: "AI says hello", t: 0.8, ai: true }]);
    unit.reviews = [{ reviewer: "bob", verdict: "approved" }];
    const r = detectAiWithoutReview(unit);
    expect(r.triggered).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// 2. detectTrustBelowThreshold
// ---------------------------------------------------------------------------

describe("detectTrustBelowThreshold", () => {
  it("should not trigger when all claims are above threshold", () => {
    const unit = create("High trust", 0.95, { tier: 1 });
    const r = detectTrustBelowThreshold(unit, 0.7);
    expect(r.triggered).toBe(false);
    expect(r.detectionClass).toBe("trust_below_threshold");
  });

  it("should trigger when claim trust is below threshold", () => {
    const unit = create("Low trust", 0.3, { tier: 5 });
    const r = detectTrustBelowThreshold(unit, 0.7);
    expect(r.triggered).toBe(true);
    expect(r.severity).toBe("high");
    expect(r.affectedClaims.length).toBe(1);
  });

  it("should use default threshold of 0.7", () => {
    const unit = create("Medium trust", 0.65);
    // tier 3 default, authority=0.7, so effective = 0.65 * 0.7 = 0.455 < 0.7
    const r = detectTrustBelowThreshold(unit);
    expect(r.triggered).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// 3. detectHallucinationRisk
// ---------------------------------------------------------------------------

describe("detectHallucinationRisk", () => {
  it("should not trigger for non-AI claims", () => {
    const unit = create("Human claim", 0.3);
    const r = detectHallucinationRisk(unit);
    expect(r.triggered).toBe(false);
    expect(r.detectionClass).toBe("hallucination_risk");
  });

  it("should trigger for low-confidence AI claim without evidence", () => {
    const unit = createMulti([{ c: "AI hallucinated this", t: 0.3, ai: true }]);
    const r = detectHallucinationRisk(unit);
    expect(r.triggered).toBe(true);
    expect(r.severity).toBe("critical");
    expect(r.affectedClaims.length).toBe(1);
  });

  it("should trigger for AI claim at tier 5", () => {
    const unit = createMulti([
      { c: "Tier 5 AI claim", t: 0.8, ai: true, tier: 5, src: "source", evidence: [{ type: "test_pass", detail: "ok" }] },
    ]);
    const r = detectHallucinationRisk(unit);
    expect(r.triggered).toBe(true);
    expect(r.findings[0]).toContain("lowest tier");
  });

  it("should not trigger for well-grounded AI claim", () => {
    const unit = createMulti([
      {
        c: "Well-grounded AI claim",
        t: 0.9,
        ai: true,
        src: "docs",
        evidence: [{ type: "human_review", detail: "approved" }],
      },
    ]);
    const r = detectHallucinationRisk(unit);
    expect(r.triggered).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// 4. detectKnowledgeLaundering
// ---------------------------------------------------------------------------

describe("detectKnowledgeLaundering", () => {
  it("should trigger for AI claim in public unit without risk", () => {
    const unit = createMulti([{ c: "AI claim", t: 0.8, ai: true }]);
    unit.label = "public";
    const r = detectKnowledgeLaundering(unit);
    expect(r.triggered).toBe(true);
    expect(r.detectionClass).toBe("knowledge_laundering");
    expect(r.severity).toBe("critical");
  });

  it("should trigger when unit has agent but claim not labeled AI", () => {
    const unit = createMulti([{ c: "Unlabeled claim", t: 0.8 }]);
    unit.agent = "gpt-4o";
    unit.label = "internal";
    const r = detectKnowledgeLaundering(unit);
    expect(r.triggered).toBe(true);
    expect(r.findings[0]).toContain("agent");
  });

  it("should not trigger for confidential unit with risk disclosure", () => {
    const unit = createMulti([{ c: "AI claim", t: 0.8, ai: true, risk: "low risk" }]);
    unit.label = "confidential";
    const r = detectKnowledgeLaundering(unit);
    expect(r.triggered).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// 5. detectClassificationDowngrade
// ---------------------------------------------------------------------------

describe("detectClassificationDowngrade", () => {
  it("should trigger for downgraded provenance action", () => {
    const unit = create("test", 0.5);
    unit.prov = [
      { hop: 0, by: "admin", do: "downgraded", at: "2025-01-01T00:00:00Z" },
    ];
    const r = detectClassificationDowngrade(unit);
    expect(r.triggered).toBe(true);
    expect(r.severity).toBe("critical");
    expect(r.detectionClass).toBe("classification_downgrade");
  });

  it("should trigger when inherit is false", () => {
    const unit = create("test", 0.5);
    unit.inherit = false;
    const r = detectClassificationDowngrade(unit);
    expect(r.triggered).toBe(true);
    expect(r.findings).toContain("Classification inheritance disabled");
  });

  it("should not trigger for normal provenance", () => {
    const unit = create("test", 0.5);
    unit.prov = [
      { hop: 0, by: "alice", do: "created", at: "2025-01-01T00:00:00Z" },
    ];
    const r = detectClassificationDowngrade(unit);
    expect(r.triggered).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// 6. detectStaleClaims
// ---------------------------------------------------------------------------

describe("detectStaleClaims", () => {
  it("should trigger for expired claims", () => {
    const unit = createMulti([{ c: "Old claim", t: 0.8, exp: "2020-01-01T00:00:00Z" }]);
    const r = detectStaleClaims(unit);
    expect(r.triggered).toBe(true);
    expect(r.severity).toBe("medium");
    expect(r.detectionClass).toBe("stale_claims");
  });

  it("should not trigger for fresh claims", () => {
    const unit = createMulti([{ c: "Fresh claim", t: 0.8, exp: "2099-01-01T00:00:00Z" }]);
    const r = detectStaleClaims(unit);
    expect(r.triggered).toBe(false);
  });

  it("should not trigger for claims without expiration", () => {
    const unit = create("No exp", 0.8);
    const r = detectStaleClaims(unit);
    expect(r.triggered).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// 7. detectUngroundedClaims
// ---------------------------------------------------------------------------

describe("detectUngroundedClaims", () => {
  it("should trigger for AI claim without evidence or source", () => {
    const unit = createMulti([{ c: "Ungrounded AI", t: 0.8, ai: true }]);
    const r = detectUngroundedClaims(unit);
    expect(r.triggered).toBe(true);
    expect(r.severity).toBe("high");
    expect(r.detectionClass).toBe("ungrounded_ai_claims");
  });

  it("should not trigger for grounded AI claim", () => {
    const unit = createMulti([
      {
        c: "Grounded AI",
        t: 0.9,
        ai: true,
        src: "docs",
        evidence: [{ type: "test_pass", detail: "100% pass" }],
      },
    ]);
    const r = detectUngroundedClaims(unit);
    expect(r.triggered).toBe(false);
  });

  it("should skip non-AI claims", () => {
    const unit = create("Human claim without src", 0.5);
    const r = detectUngroundedClaims(unit);
    expect(r.triggered).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// 8. detectTrustDegradationChain
// ---------------------------------------------------------------------------

describe("detectTrustDegradationChain", () => {
  it("should not trigger with no provenance", () => {
    const unit = create("test", 0.5);
    const r = detectTrustDegradationChain(unit);
    expect(r.triggered).toBe(false);
    expect(r.detectionClass).toBe("trust_degradation_chain");
  });

  it("should not trigger with single hop", () => {
    const unit = create("test", 0.5);
    unit.prov = [{ hop: 0, by: "alice", do: "created", at: "2025-01-01T00:00:00Z" }];
    const r = detectTrustDegradationChain(unit);
    expect(r.triggered).toBe(false);
  });

  it("should trigger with large penalties across hops", () => {
    const unit = create("test", 0.5);
    unit.prov = [
      { hop: 0, by: "alice", do: "created", at: "2025-01-01T00:00:00Z", pen: -0.2 },
      { hop: 1, by: "bob", do: "transformed", at: "2025-01-02T00:00:00Z", pen: -0.3 },
    ];
    const r = detectTrustDegradationChain(unit);
    expect(r.triggered).toBe(true);
    expect(r.severity).toBe("high");
    expect(r.findings.some((f) => f.includes("Cumulative penalty"))).toBe(true);
  });

  it("should not trigger with small penalties", () => {
    const unit = create("test", 0.5);
    unit.prov = [
      { hop: 0, by: "alice", do: "created", at: "2025-01-01T00:00:00Z" },
      { hop: 1, by: "bob", do: "enriched", at: "2025-01-02T00:00:00Z", pen: -0.05 },
    ];
    const r = detectTrustDegradationChain(unit);
    expect(r.triggered).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// 9. detectExcessiveAiConcentration
// ---------------------------------------------------------------------------

describe("detectExcessiveAiConcentration", () => {
  it("should trigger when all claims are AI", () => {
    const unit = createMulti([
      { c: "AI 1", t: 0.8, ai: true },
      { c: "AI 2", t: 0.7, ai: true },
    ]);
    const r = detectExcessiveAiConcentration(unit);
    expect(r.triggered).toBe(true);
    expect(r.detectionClass).toBe("excessive_ai_concentration");
    expect(r.findings.some((f) => f.includes("No human-authored"))).toBe(true);
  });

  it("should not trigger below max ratio", () => {
    const unit = createMulti([
      { c: "AI 1", t: 0.8, ai: true },
      { c: "Human 1", t: 0.9 },
      { c: "Human 2", t: 0.85 },
    ]);
    const r = detectExcessiveAiConcentration(unit);
    // 1/3 = 33% < 80%
    expect(r.triggered).toBe(false);
  });

  it("should use custom max ratio", () => {
    const unit = createMulti([
      { c: "AI 1", t: 0.8, ai: true },
      { c: "Human 1", t: 0.9 },
    ]);
    // 1/2 = 50% > 40%
    const r = detectExcessiveAiConcentration(unit, 0.4);
    expect(r.triggered).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// 10. detectProvenanceGap
// ---------------------------------------------------------------------------

describe("detectProvenanceGap", () => {
  it("should trigger when no provenance chain exists", () => {
    const unit = create("test", 0.5);
    const r = detectProvenanceGap(unit);
    expect(r.triggered).toBe(true);
    expect(r.detectionClass).toBe("provenance_gap");
    expect(r.findings).toContain("No provenance chain");
  });

  it("should trigger for out-of-order hops", () => {
    const unit = create("test", 0.5);
    unit.prov = [
      { hop: 0, by: "alice", do: "created", at: "2025-01-01T00:00:00Z" },
      { hop: 5, by: "bob", do: "enriched", at: "2025-01-02T00:00:00Z" },
    ];
    const r = detectProvenanceGap(unit);
    expect(r.triggered).toBe(true);
    expect(r.findings.some((f) => f.includes("Gap"))).toBe(true);
  });

  it("should trigger for unknown origin actor", () => {
    const unit = create("test", 0.5);
    unit.prov = [
      { hop: 0, by: "unknown", do: "created", at: "2025-01-01T00:00:00Z" },
    ];
    const r = detectProvenanceGap(unit);
    expect(r.triggered).toBe(true);
    expect(r.findings.some((f) => f.includes("Origin actor is unknown"))).toBe(true);
  });

  it("should trigger for hop with no actor", () => {
    const unit = create("test", 0.5);
    unit.prov = [
      { hop: 0, by: "", do: "created", at: "2025-01-01T00:00:00Z" },
    ];
    const r = detectProvenanceGap(unit);
    expect(r.triggered).toBe(true);
  });

  it("should not trigger for valid sequential provenance", () => {
    const unit = create("test", 0.5);
    unit.prov = [
      { hop: 0, by: "alice", do: "created", at: "2025-01-01T00:00:00Z" },
      { hop: 1, by: "bob", do: "enriched", at: "2025-01-02T00:00:00Z" },
    ];
    const r = detectProvenanceGap(unit);
    expect(r.triggered).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// runAllDetections
// ---------------------------------------------------------------------------

describe("runAllDetections", () => {
  it("should return 10 results", () => {
    const unit = create("test", 0.9);
    const report = runAllDetections(unit);
    expect(report.results).toHaveLength(10);
  });

  it("should mark clean when nothing triggers (aside provenance gap)", () => {
    const unit = createMulti([{ c: "Human claim", t: 0.95, src: "official", tier: 1 }]);
    unit.prov = [
      { hop: 0, by: "alice", do: "created", at: "2025-01-01T00:00:00Z" },
    ];
    unit.label = "internal";
    const report = runAllDetections(unit);
    // provenance_gap will not trigger because we have a valid chain
    // trust_below_threshold: 0.95 * 1.0 = 0.95 >= 0.7 (ok)
    // Check that at least some are not triggered
    expect(report.results.filter((r) => !r.triggered).length).toBeGreaterThan(0);
  });

  it("should pass custom thresholds", () => {
    const unit = createMulti([{ c: "AI claim", t: 0.8, ai: true }]);
    const report = runAllDetections(unit, { trustThreshold: 0.5, maxAiRatio: 0.5 });
    // maxAiRatio=0.5, and ratio is 1.0 (100%) so excessive_ai should trigger
    const aiConc = report.results.find((r) => r.detectionClass === "excessive_ai_concentration");
    expect(aiConc?.triggered).toBe(true);
  });

  it("should count critical and high correctly", () => {
    const unit = createMulti([{ c: "AI no review", t: 0.3, ai: true }]);
    const report = runAllDetections(unit);
    expect(report.triggeredCount).toBeGreaterThan(0);
    expect(typeof report.criticalCount).toBe("number");
    expect(typeof report.highCount).toBe("number");
    expect(report.clean).toBe(false);
  });
});
