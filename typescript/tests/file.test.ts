import { describe, it, expect, afterEach } from "vitest";
import { readFileSync, writeFileSync, unlinkSync, existsSync } from "node:fs";
import { stampFile, read, extract, embed, scan, create } from "../src/index.js";

const TMP_AKF = "/tmp/test-akf-file.akf";
const TMP_JSON = "/tmp/test-akf-file.json";
const TMP_MD = "/tmp/test-akf-file.md";
const TMP_HTML = "/tmp/test-akf-file.html";
const TMP_TXT = "/tmp/test-akf-file.txt";

function cleanup(...files: string[]) {
  for (const f of files) {
    if (existsSync(f)) unlinkSync(f);
    // Also cleanup sidecar
    if (existsSync(f + ".akf.json")) unlinkSync(f + ".akf.json");
  }
}

afterEach(() => {
  cleanup(TMP_AKF, TMP_JSON, TMP_MD, TMP_HTML, TMP_TXT);
});

describe("stampFile", () => {
  it("stamps a .akf file", () => {
    const unit = stampFile(TMP_AKF, {
      model: "gpt-4o",
      claims: ["Revenue was $4.2B"],
      trustScore: 0.95,
    });
    expect(unit.claims.length).toBe(1);
    expect(unit.claims[0].t).toBe(0.95);

    // Read it back
    const loaded = read(TMP_AKF);
    expect(loaded.claims.length).toBe(1);
    expect(loaded.claims[0].c).toBe("Revenue was $4.2B");
  });

  it("stamps with evidence", () => {
    const unit = stampFile(TMP_AKF, {
      agent: "claude-code",
      claims: ["Fixed auth bug"],
      evidence: ["42/42 tests passed", "mypy: 0 errors"],
    });
    expect(unit.claims[0].evidence).toBeDefined();
    expect(unit.claims[0].evidence!.length).toBe(2);
    expect(unit.claims[0].evidence![0].type).toBe("test_pass");
    expect(unit.claims[0].evidence![1].type).toBe("type_check");
  });

  it("stamps a .json file with _akf key", () => {
    writeFileSync(TMP_JSON, JSON.stringify({ data: "hello" }), "utf-8");
    stampFile(TMP_JSON, { claims: ["Processed data"], trustScore: 0.8 });

    const content = JSON.parse(readFileSync(TMP_JSON, "utf-8"));
    expect(content.data).toBe("hello");
    expect(content._akf).toBeDefined();
    expect(content._akf.claims.length).toBe(1);
  });

  it("stamps a .md file with frontmatter", () => {
    writeFileSync(TMP_MD, "# Hello\n\nWorld\n", "utf-8");
    stampFile(TMP_MD, { claims: ["Summary accurate"], trustScore: 0.9 });

    const content = readFileSync(TMP_MD, "utf-8");
    expect(content).toMatch(/^---\n/);
    expect(content).toContain("akf:");
    expect(content).toContain("# Hello");
  });

  it("stamps a .txt file with sidecar", () => {
    writeFileSync(TMP_TXT, "plain text content", "utf-8");
    stampFile(TMP_TXT, { claims: ["Content reviewed"], trustScore: 0.85 });

    expect(existsSync(TMP_TXT + ".akf.json")).toBe(true);
    const sidecar = JSON.parse(readFileSync(TMP_TXT + ".akf.json", "utf-8"));
    expect(sidecar.claims.length).toBe(1);
  });
});

describe("read / extract", () => {
  it("reads from .akf file", () => {
    const unit = create("Test claim", 0.9);
    writeFileSync(TMP_AKF, JSON.stringify(unit), "utf-8");

    const loaded = read(TMP_AKF);
    expect(loaded.claims[0].c).toBe("Test claim");
  });

  it("extract is an alias for read", () => {
    expect(extract).toBe(read);
  });

  it("reads from sidecar", () => {
    writeFileSync(TMP_TXT, "content", "utf-8");
    const unit = create("Sidecar claim", 0.8);
    writeFileSync(TMP_TXT + ".akf.json", JSON.stringify(unit), "utf-8");

    const loaded = read(TMP_TXT);
    expect(loaded.claims[0].c).toBe("Sidecar claim");
  });

  it("throws when no metadata found", () => {
    writeFileSync(TMP_TXT, "no metadata", "utf-8");
    expect(() => read(TMP_TXT)).toThrow("No AKF metadata found");
  });
});

describe("embed", () => {
  it("embeds into HTML with script tag", () => {
    writeFileSync(TMP_HTML, "<html><head></head><body></body></html>", "utf-8");
    const unit = create("HTML claim", 0.85);
    embed(TMP_HTML, unit);

    const content = readFileSync(TMP_HTML, "utf-8");
    expect(content).toContain('application/akf+json');
    expect(content).toContain("HTML claim");

    // Read it back
    const loaded = read(TMP_HTML);
    expect(loaded.claims[0].c).toBe("HTML claim");
  });

  it("embeds with options shorthand", () => {
    embed(TMP_AKF, {
      claims: [{ c: "Option claim", t: 0.9 }],
      classification: "internal",
    });
    const loaded = read(TMP_AKF);
    expect(loaded.claims[0].c).toBe("Option claim");
    expect(loaded.label).toBe("internal");
  });
});

describe("scan", () => {
  it("scans a file with metadata", () => {
    stampFile(TMP_AKF, {
      claims: ["Claim 1", "Claim 2"],
      trustScore: 0.8,
      classification: "internal",
    });
    const result = scan(TMP_AKF);
    expect(result.enriched).toBe(true);
    expect(result.claimCount).toBe(2);
    expect(result.classification).toBe("internal");
    expect(result.overallTrust).toBeGreaterThan(0);
  });

  it("scans a file without metadata", () => {
    writeFileSync(TMP_TXT, "no metadata", "utf-8");
    const result = scan(TMP_TXT);
    expect(result.enriched).toBe(false);
    expect(result.claimCount).toBe(0);
  });
});
