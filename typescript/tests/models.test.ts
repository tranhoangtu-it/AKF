import { describe, it, expect } from "vitest";
import {
  normalizeClaim,
  normalizeProvHop,
  normalizeUnit,
  toDescriptiveClaim,
  toDescriptive,
} from "../src/index.js";

// ---------------------------------------------------------------------------
// normalizeClaim
// ---------------------------------------------------------------------------

describe("normalizeClaim", () => {
  it("should convert descriptive names to compact", () => {
    const claim = normalizeClaim({
      content: "Revenue is $4.2B",
      confidence: 0.95,
      source: "SEC 10-Q",
      authority_tier: 1,
      verified: true,
      verified_by: "auditor",
      ai_generated: false,
      decay_half_life: 365,
      expires: "2026-01-01T00:00:00Z",
      contradicts: "claim-abc",
    });
    expect(claim.c).toBe("Revenue is $4.2B");
    expect(claim.t).toBe(0.95);
    expect(claim.src).toBe("SEC 10-Q");
    expect(claim.tier).toBe(1);
    expect(claim.ver).toBe(true);
    expect(claim.ver_by).toBe("auditor");
    expect(claim.ai).toBe(false);
    expect(claim.decay).toBe(365);
    expect(claim.exp).toBe("2026-01-01T00:00:00Z");
    expect(claim.contra).toBe("claim-abc");
  });

  it("should pass through unknown keys", () => {
    const claim = normalizeClaim({
      content: "Test",
      confidence: 0.5,
      future_field: "value",
    });
    expect(claim.c).toBe("Test");
    expect((claim as Record<string, unknown>).future_field).toBe("value");
  });

  it("should pass through already-compact keys", () => {
    const claim = normalizeClaim({ c: "Test", t: 0.5, src: "docs" });
    expect(claim.c).toBe("Test");
    expect(claim.t).toBe(0.5);
    expect(claim.src).toBe("docs");
  });

  it("should handle v1.1 field aliases", () => {
    const claim = normalizeClaim({
      content: "Test",
      confidence: 0.8,
      source_detail: { uri: "https://example.com" },
      expires_at: "2026-06-01T00:00:00Z",
      verified_at: "2025-06-01T00:00:00Z",
      depends_on: ["claim-1"],
      supersedes_id: "old-claim",
    });
    expect(claim.sourceDetail).toEqual({ uri: "https://example.com" });
    expect(claim.expiresAt).toBe("2026-06-01T00:00:00Z");
    expect(claim.verifiedAt).toBe("2025-06-01T00:00:00Z");
    expect(claim.dependsOn).toEqual(["claim-1"]);
    expect(claim.supersedes).toBe("old-claim");
  });
});

// ---------------------------------------------------------------------------
// normalizeProvHop
// ---------------------------------------------------------------------------

describe("normalizeProvHop", () => {
  it("should convert descriptive names to compact", () => {
    const hop = normalizeProvHop({
      hop: 0,
      actor: "alice",
      action: "created",
      timestamp: "2025-01-01T00:00:00Z",
      hash: "sha256:abc",
      penalty: -0.1,
      claims_added: ["c1"],
      claims_removed: ["c2"],
    });
    expect(hop.by).toBe("alice");
    expect(hop.do).toBe("created");
    expect(hop.at).toBe("2025-01-01T00:00:00Z");
    expect(hop.h).toBe("sha256:abc");
    expect(hop.pen).toBe(-0.1);
    expect(hop.adds).toEqual(["c1"]);
    expect(hop.drops).toEqual(["c2"]);
  });

  it("should handle v1.1 ProvHop aliases", () => {
    const hop = normalizeProvHop({
      hop: 0,
      actor: "bot",
      action: "enriched",
      timestamp: "2025-01-01T00:00:00Z",
      input_hash: "sha256:in",
      output_hash: "sha256:out",
      agent_profile: { id: "agent-1" },
      duration_ms: 1500,
      tool_calls: ["search", "summarize"],
    });
    expect(hop.inputHash).toBe("sha256:in");
    expect(hop.outputHash).toBe("sha256:out");
    expect(hop.agentProfile).toEqual({ id: "agent-1" });
    expect(hop.durationMs).toBe(1500);
    expect(hop.toolCalls).toEqual(["search", "summarize"]);
  });
});

// ---------------------------------------------------------------------------
// normalizeUnit
// ---------------------------------------------------------------------------

describe("normalizeUnit", () => {
  it("should convert descriptive unit fields to compact", () => {
    const unit = normalizeUnit({
      version: "1.0",
      claims: [{ content: "Test", confidence: 0.8 }],
      author: "alice",
      created: "2025-01-01T00:00:00Z",
      classification: "internal",
      inherit_classification: true,
      allow_external: false,
      integrity_hash: "sha256:abc",
    });
    expect(unit.v).toBe("1.0");
    expect(unit.by).toBe("alice");
    expect(unit.at).toBe("2025-01-01T00:00:00Z");
    expect(unit.label).toBe("internal");
    expect(unit.inherit).toBe(true);
    expect(unit.ext).toBe(false);
    expect(unit.hash).toBe("sha256:abc");
  });

  it("should normalize nested claims", () => {
    const unit = normalizeUnit({
      version: "1.0",
      claims: [
        { content: "Claim A", confidence: 0.9, source: "docs" },
        { content: "Claim B", confidence: 0.7, ai_generated: true },
      ],
    });
    expect(unit.claims[0].c).toBe("Claim A");
    expect(unit.claims[0].src).toBe("docs");
    expect(unit.claims[1].c).toBe("Claim B");
    expect(unit.claims[1].ai).toBe(true);
  });

  it("should normalize nested provenance", () => {
    const unit = normalizeUnit({
      version: "1.0",
      claims: [{ content: "Test", confidence: 0.5 }],
      provenance: [
        { hop: 0, actor: "alice", action: "created", timestamp: "2025-01-01T00:00:00Z" },
      ],
    });
    expect(unit.prov).toBeDefined();
    expect(unit.prov![0].by).toBe("alice");
    expect(unit.prov![0].do).toBe("created");
  });

  it("should handle v1.1 unit aliases", () => {
    const unit = normalizeUnit({
      version: "1.0",
      claims: [{ content: "Test", confidence: 0.5 }],
      made_by: [{ actor: "alice", role: "author" }],
      schema_version: "1.1",
      parent_id: "parent-123",
    });
    expect(unit.madeBy).toEqual([{ actor: "alice", role: "author" }]);
    expect(unit.schemaVersion).toBe("1.1");
    expect(unit.parentId).toBe("parent-123");
  });
});

// ---------------------------------------------------------------------------
// toDescriptiveClaim
// ---------------------------------------------------------------------------

describe("toDescriptiveClaim", () => {
  it("should convert compact claim to descriptive", () => {
    const descriptive = toDescriptiveClaim({
      c: "Revenue is $4.2B",
      t: 0.95,
      src: "SEC 10-Q",
      tier: 1,
      ver: true,
      ver_by: "auditor",
      ai: false,
      decay: 365,
      exp: "2026-01-01T00:00:00Z",
      contra: "claim-abc",
    });
    expect(descriptive.content).toBe("Revenue is $4.2B");
    expect(descriptive.confidence).toBe(0.95);
    expect(descriptive.source).toBe("SEC 10-Q");
    expect(descriptive.authority_tier).toBe(1);
    expect(descriptive.verified).toBe(true);
    expect(descriptive.verified_by).toBe("auditor");
    expect(descriptive.ai_generated).toBe(false);
    expect(descriptive.decay_half_life).toBe(365);
    expect(descriptive.expires).toBe("2026-01-01T00:00:00Z");
    expect(descriptive.contradicts).toBe("claim-abc");
  });

  it("should handle v1.1 fields", () => {
    const descriptive = toDescriptiveClaim({
      c: "Test",
      t: 0.8,
      sourceDetail: { uri: "https://example.com" },
      expiresAt: "2026-06-01T00:00:00Z",
      verifiedAt: "2025-06-01T00:00:00Z",
      dependsOn: ["claim-1"],
      supersedes: "old-claim",
    });
    expect(descriptive.source_detail).toEqual({ uri: "https://example.com" });
    expect(descriptive.expires_at).toBe("2026-06-01T00:00:00Z");
    expect(descriptive.verified_at).toBe("2025-06-01T00:00:00Z");
    expect(descriptive.depends_on).toEqual(["claim-1"]);
    expect(descriptive.supersedes_id).toBe("old-claim");
  });

  it("should skip null and undefined values", () => {
    const descriptive = toDescriptiveClaim({ c: "Test", t: 0.8 });
    // Only keys with defined, non-null values should be present
    expect(Object.keys(descriptive)).toEqual(["content", "confidence"]);
  });
});

// ---------------------------------------------------------------------------
// toDescriptive (full unit)
// ---------------------------------------------------------------------------

describe("toDescriptive", () => {
  it("should convert compact unit to descriptive", () => {
    const descriptive = toDescriptive({
      v: "1.0",
      claims: [{ c: "Test", t: 0.8, src: "docs" }],
      by: "alice",
      at: "2025-01-01T00:00:00Z",
      label: "internal",
      inherit: true,
      ext: false,
      hash: "sha256:abc",
    });
    expect(descriptive.version).toBe("1.0");
    expect(descriptive.author).toBe("alice");
    expect(descriptive.created).toBe("2025-01-01T00:00:00Z");
    expect(descriptive.classification).toBe("internal");
    expect(descriptive.inherit_classification).toBe(true);
    expect(descriptive.allow_external).toBe(false);
    expect(descriptive.integrity_hash).toBe("sha256:abc");
  });

  it("should convert nested claims to descriptive", () => {
    const descriptive = toDescriptive({
      v: "1.0",
      claims: [{ c: "Test", t: 0.8, src: "docs", ai: true }],
    });
    const claims = descriptive.claims as Record<string, unknown>[];
    expect(claims[0].content).toBe("Test");
    expect(claims[0].source).toBe("docs");
    expect(claims[0].ai_generated).toBe(true);
  });

  it("should convert provenance hops to descriptive", () => {
    const descriptive = toDescriptive({
      v: "1.0",
      claims: [{ c: "Test", t: 0.8 }],
      prov: [
        { hop: 0, by: "alice", do: "created", at: "2025-01-01T00:00:00Z", h: "sha256:abc", pen: -0.1, adds: ["c1"], drops: ["c2"] },
      ],
    });
    const provenance = descriptive.provenance as Record<string, unknown>[];
    expect(provenance).toBeDefined();
    expect(provenance[0].actor).toBe("alice");
    expect(provenance[0].action).toBe("created");
    expect(provenance[0].hash).toBe("sha256:abc");
    expect(provenance[0].penalty).toBe(-0.1);
    expect(provenance[0].claims_added).toEqual(["c1"]);
    expect(provenance[0].claims_removed).toEqual(["c2"]);
  });

  it("should handle unit with no optional fields", () => {
    const descriptive = toDescriptive({
      v: "1.0",
      claims: [{ c: "Bare", t: 0.5 }],
    });
    expect(descriptive.version).toBe("1.0");
    expect(descriptive.claims).toBeDefined();
    expect(descriptive.author).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// Edge cases
// ---------------------------------------------------------------------------

describe("edge cases", () => {
  it("should handle empty claims array in normalizeUnit", () => {
    const unit = normalizeUnit({ version: "1.0", claims: [] });
    expect(unit.v).toBe("1.0");
    expect(unit.claims).toEqual([]);
  });

  it("should handle missing claims in normalizeUnit", () => {
    const unit = normalizeUnit({ version: "1.0" });
    expect(unit.v).toBe("1.0");
    // claims should be undefined since it wasn't provided
    expect(unit.claims).toBeUndefined();
  });

  it("should handle claim with only required fields", () => {
    const claim = normalizeClaim({ content: "X", confidence: 0.1 });
    expect(claim.c).toBe("X");
    expect(claim.t).toBe(0.1);
  });

  it("should round-trip: normalize then toDescriptive", () => {
    const original = {
      content: "Revenue",
      confidence: 0.9,
      source: "SEC",
      ai_generated: true,
    };
    const compact = normalizeClaim(original);
    const back = toDescriptiveClaim(compact);
    expect(back.content).toBe("Revenue");
    expect(back.confidence).toBe(0.9);
    expect(back.source).toBe("SEC");
    expect(back.ai_generated).toBe(true);
  });
});
