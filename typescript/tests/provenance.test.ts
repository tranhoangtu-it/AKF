import { describe, it, expect } from "vitest";
import {
  computeHopHash,
  computeIntegrityHash,
  validateChain,
  addHop,
  modelsUsed,
  formatTree,
  create,
  createMulti,
} from "../src/index.js";
import type { AKFUnit, ProvHop } from "../src/index.js";

// ---------------------------------------------------------------------------
// computeHopHash
// ---------------------------------------------------------------------------

describe("computeHopHash", () => {
  it("should produce deterministic hashes", () => {
    const hop = { hop: 0, by: "alice", do: "created", at: "2025-01-01T00:00:00Z" };
    const h1 = computeHopHash(null, hop);
    const h2 = computeHopHash(null, hop);
    expect(h1).toBe(h2);
    expect(h1).toMatch(/^sha256:/);
  });

  it("should produce canonical hash regardless of key order", () => {
    const hop1 = { by: "alice", hop: 0, at: "2025-01-01T00:00:00Z", do: "created" };
    const hop2 = { hop: 0, do: "created", by: "alice", at: "2025-01-01T00:00:00Z" };
    const h1 = computeHopHash(null, hop1);
    const h2 = computeHopHash(null, hop2);
    expect(h1).toBe(h2);
  });

  it("should chain with previous hash", () => {
    const hop = { hop: 0, by: "alice", do: "created", at: "2025-01-01T00:00:00Z" };
    const h1 = computeHopHash(null, hop);
    const h2 = computeHopHash("sha256:abc123", hop);
    expect(h1).not.toBe(h2);
  });

  it("should handle nested objects canonically", () => {
    const hop1 = { hop: 0, by: "alice", do: "created", meta: { b: 2, a: 1 } };
    const hop2 = { hop: 0, by: "alice", do: "created", meta: { a: 1, b: 2 } };
    expect(computeHopHash(null, hop1)).toBe(computeHopHash(null, hop2));
  });
});

// ---------------------------------------------------------------------------
// computeIntegrityHash
// ---------------------------------------------------------------------------

describe("computeIntegrityHash", () => {
  it("should produce deterministic hashes", () => {
    const unit = create("Test", 0.8);
    const h1 = computeIntegrityHash(unit);
    const h2 = computeIntegrityHash(unit);
    expect(h1).toBe(h2);
    expect(h1).toMatch(/^sha256:/);
  });

  it("should exclude hash field from computation", () => {
    const unit = create("Test", 0.8);
    const h1 = computeIntegrityHash(unit);
    unit.hash = "sha256:something_else";
    const h2 = computeIntegrityHash(unit);
    expect(h1).toBe(h2);
  });

  it("should change when content changes", () => {
    const unit1 = create("Claim A", 0.8);
    const unit2 = create("Claim A", 0.8);
    // They have different IDs so hashes should differ
    const h1 = computeIntegrityHash(unit1);
    const h2 = computeIntegrityHash(unit2);
    expect(h1).not.toBe(h2);
  });
});

// ---------------------------------------------------------------------------
// validateChain
// ---------------------------------------------------------------------------

describe("validateChain", () => {
  it("should validate a valid chain", () => {
    const prov: ProvHop[] = [
      { hop: 0, by: "alice", do: "created", at: "2025-01-01T00:00:00Z" },
      { hop: 1, by: "bob", do: "enriched", at: "2025-01-02T00:00:00Z" },
      { hop: 2, by: "carol", do: "reviewed", at: "2025-01-03T00:00:00Z" },
    ];
    expect(validateChain(prov)).toBe(true);
  });

  it("should reject a broken chain", () => {
    const prov: ProvHop[] = [
      { hop: 0, by: "alice", do: "created", at: "2025-01-01T00:00:00Z" },
      { hop: 5, by: "bob", do: "enriched", at: "2025-01-02T00:00:00Z" },
    ];
    expect(validateChain(prov)).toBe(false);
  });

  it("should reject missing first hop", () => {
    const prov: ProvHop[] = [
      { hop: 1, by: "alice", do: "created", at: "2025-01-01T00:00:00Z" },
    ];
    expect(validateChain(prov)).toBe(false);
  });

  it("should validate empty chain", () => {
    expect(validateChain([])).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// addHop
// ---------------------------------------------------------------------------

describe("addHop", () => {
  it("should add first hop to unit without provenance", () => {
    const unit = create("Test", 0.8);
    const updated = addHop(unit, "alice", "created");
    expect(updated.prov).toBeDefined();
    expect(updated.prov!.length).toBe(1);
    expect(updated.prov![0].hop).toBe(0);
    expect(updated.prov![0].by).toBe("alice");
    expect(updated.prov![0].do).toBe("created");
    expect(updated.prov![0].h).toMatch(/^sha256:/);
    expect(updated.hash).toMatch(/^sha256:/);
  });

  it("should chain hops sequentially", () => {
    let unit = create("Test", 0.8);
    unit = addHop(unit, "alice", "created");
    unit = addHop(unit, "bob", "enriched");
    expect(unit.prov!.length).toBe(2);
    expect(unit.prov![0].hop).toBe(0);
    expect(unit.prov![1].hop).toBe(1);
    expect(unit.prov![1].by).toBe("bob");
  });

  it("should include model when provided", () => {
    const unit = create("Test", 0.8);
    const updated = addHop(unit, "ai-agent", "created", { model: "gpt-4o" });
    expect(updated.prov![0].model).toBe("gpt-4o");
  });

  it("should include adds and drops", () => {
    const unit = create("Test", 0.8);
    const updated = addHop(unit, "bob", "enriched", {
      adds: ["claim-1", "claim-2"],
      drops: ["claim-3"],
    });
    expect(updated.prov![0].adds).toEqual(["claim-1", "claim-2"]);
    expect(updated.prov![0].drops).toEqual(["claim-3"]);
  });

  it("should include penalty", () => {
    const unit = create("Test", 0.8);
    const updated = addHop(unit, "transform", "transformed", { penalty: -0.1 });
    expect(updated.prov![0].pen).toBe(-0.1);
  });

  it("should not mutate the original unit", () => {
    const unit = create("Test", 0.8);
    const updated = addHop(unit, "alice", "created");
    expect(unit.prov).toBeUndefined();
    expect(updated.prov).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// modelsUsed
// ---------------------------------------------------------------------------

describe("modelsUsed", () => {
  it("should collect unit-level model", () => {
    const unit = create("Test", 0.8);
    unit.model = "gpt-4o";
    const models = modelsUsed(unit);
    expect(models).toContain("gpt-4o");
  });

  it("should collect claim origin models", () => {
    const unit = createMulti([
      { c: "AI claim", t: 0.8, ai: true, origin: { type: "ai", model: "claude-3" } },
    ]);
    const models = modelsUsed(unit);
    expect(models).toContain("claude-3");
  });

  it("should collect provenance hop models", () => {
    let unit = create("Test", 0.8);
    unit = addHop(unit, "agent", "created", { model: "gemini-pro" });
    const models = modelsUsed(unit);
    expect(models).toContain("gemini-pro");
  });

  it("should deduplicate models", () => {
    const unit = createMulti([
      { c: "Claim 1", t: 0.8, ai: true, origin: { type: "ai", model: "gpt-4o" } },
      { c: "Claim 2", t: 0.7, ai: true, origin: { type: "ai", model: "gpt-4o" } },
    ]);
    unit.model = "gpt-4o";
    const models = modelsUsed(unit);
    expect(models.filter((m) => m === "gpt-4o").length).toBe(1);
  });

  it("should return empty array when no models", () => {
    const unit = create("Test", 0.8);
    const models = modelsUsed(unit);
    expect(models).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// formatTree
// ---------------------------------------------------------------------------

describe("formatTree", () => {
  it("should return '(no provenance)' for unit without prov", () => {
    const unit = create("Test", 0.8);
    expect(formatTree(unit)).toBe("(no provenance)");
  });

  it("should format single hop", () => {
    let unit = create("Test", 0.8);
    unit = addHop(unit, "alice", "created");
    const tree = formatTree(unit);
    expect(tree).toContain("alice");
    expect(tree).toContain("created");
  });

  it("should format multi-hop tree with indentation", () => {
    let unit = create("Test", 0.8);
    unit = addHop(unit, "alice", "created");
    unit = addHop(unit, "bob", "enriched", { adds: ["c1", "c2"] });
    unit = addHop(unit, "carol", "reviewed", { drops: ["c3"] });
    const tree = formatTree(unit);
    const lines = tree.split("\n");
    expect(lines.length).toBe(3);
    // First line has no indent prefix
    expect(lines[0]).toContain("alice");
    // Second line is indented
    expect(lines[1]).toContain("bob");
    expect(lines[1]).toContain("+2 claims");
    // Third line
    expect(lines[2]).toContain("carol");
    expect(lines[2]).toContain("-1 rejected");
  });
});
