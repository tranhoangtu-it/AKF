/**
 * AKF v1.1 — File I/O: read, write, stamp, embed, extract AKF metadata.
 *
 * Supports:
 * - .akf (native JSON)
 * - .json (_akf key)
 * - .md (YAML frontmatter)
 * - .html (JSON-LD script tag)
 * - Everything else via sidecar .akf.json
 */

import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { extname, basename, dirname, join } from "node:path";
import type { AKFUnit, Claim } from "./models.js";
import { normalizeUnit } from "./models.js";
import { create, createMulti, toJSON, fromJSON, stripNulls, validate } from "./core.js";
import type { ValidationResult } from "./core.js";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function sidecarPath(filepath: string): string {
  const dir = dirname(filepath);
  const base = basename(filepath);
  return join(dir, `${base}.akf.json`);
}

function nowISO(): string {
  return new Date().toISOString();
}

// ---------------------------------------------------------------------------
// Read / Extract
// ---------------------------------------------------------------------------

/**
 * Read AKF metadata from any file.
 * Checks native format first, then sidecar.
 */
export function read(filepath: string): AKFUnit {
  const ext = extname(filepath).toLowerCase();

  if (ext === ".akf") {
    const content = readFileSync(filepath, "utf-8");
    return fromJSON(content);
  }

  if (ext === ".json") {
    const content = readFileSync(filepath, "utf-8");
    const data = JSON.parse(content);
    if (data._akf) {
      return normalizeUnit(data._akf);
    }
    // Maybe the whole file is an AKF unit
    if (data.v && data.claims) {
      return normalizeUnit(data);
    }
    throw new Error(`No AKF metadata found in ${filepath}`);
  }

  if (ext === ".md") {
    const content = readFileSync(filepath, "utf-8");
    const match = content.match(/^---\n([\s\S]*?)\n---/);
    if (match) {
      // Simple YAML frontmatter parsing for akf key
      const fmLines = match[1].split("\n");
      const akfIdx = fmLines.findIndex((l) => l.startsWith("akf:"));
      if (akfIdx >= 0) {
        // Extract indented block after akf:
        const jsonStr = fmLines[akfIdx].replace("akf:", "").trim();
        if (jsonStr) {
          return fromJSON(jsonStr);
        }
      }
    }
    // Fall through to sidecar
  }

  if (ext === ".html" || ext === ".htm") {
    const content = readFileSync(filepath, "utf-8");
    const match = content.match(
      /<script\s+type=["']application\/akf\+json["'][^>]*>([\s\S]*?)<\/script>/i
    );
    if (match) {
      return fromJSON(match[1].trim());
    }
    // Fall through to sidecar
  }

  // Sidecar fallback
  const sidecar = sidecarPath(filepath);
  if (existsSync(sidecar)) {
    const content = readFileSync(sidecar, "utf-8");
    return fromJSON(content);
  }

  throw new Error(`No AKF metadata found for ${filepath}`);
}

/** Alias for read — extract AKF metadata from any file. */
export const extract = read;

// ---------------------------------------------------------------------------
// Write / Embed
// ---------------------------------------------------------------------------

export interface EmbedOptions {
  claims?: Array<Partial<Claim>>;
  classification?: string;
  author?: string;
  agent?: string;
  model?: string;
}

/**
 * Embed AKF metadata into a file.
 * Uses native embedding for supported formats, sidecar for others.
 */
export function embed(filepath: string, unit: AKFUnit): void;
export function embed(filepath: string, options: EmbedOptions): void;
export function embed(filepath: string, unitOrOpts: AKFUnit | EmbedOptions): void {
  let unit: AKFUnit;

  if ("v" in unitOrOpts && "claims" in unitOrOpts && Array.isArray(unitOrOpts.claims)) {
    unit = unitOrOpts as AKFUnit;
  } else {
    const opts = unitOrOpts as EmbedOptions;
    const claims = (opts.claims || []).map((c) => ({
      c: c.c || (c as Record<string, unknown>).content as string || "",
      t: c.t ?? (c as Record<string, unknown>).confidence as number ?? 0.7,
      ...c,
    })) as Claim[];

    unit = createMulti(claims, {
      by: opts.author,
      agent: opts.agent,
      model: opts.model,
      label: opts.classification,
    });
  }

  const ext = extname(filepath).toLowerCase();
  const jsonStr = toJSON(unit, 2);

  if (ext === ".akf") {
    writeFileSync(filepath, jsonStr, "utf-8");
    return;
  }

  if (ext === ".json") {
    let data: Record<string, unknown> = {};
    if (existsSync(filepath)) {
      data = JSON.parse(readFileSync(filepath, "utf-8"));
    }
    data._akf = JSON.parse(jsonStr);
    writeFileSync(filepath, JSON.stringify(data, null, 2), "utf-8");
    return;
  }

  if (ext === ".md") {
    let content = "";
    if (existsSync(filepath)) {
      content = readFileSync(filepath, "utf-8");
    }
    const compactJson = toJSON(unit);
    // Check if frontmatter exists
    if (content.startsWith("---\n")) {
      const endIdx = content.indexOf("\n---", 4);
      if (endIdx > 0) {
        const frontmatter = content.slice(4, endIdx);
        const rest = content.slice(endIdx + 4);
        // Replace or add akf key
        const lines = frontmatter.split("\n").filter((l) => !l.startsWith("akf:"));
        lines.push(`akf: ${compactJson}`);
        content = `---\n${lines.join("\n")}\n---${rest}`;
      }
    } else {
      content = `---\nakf: ${compactJson}\n---\n${content}`;
    }
    writeFileSync(filepath, content, "utf-8");
    return;
  }

  if (ext === ".html" || ext === ".htm") {
    let content = "";
    if (existsSync(filepath)) {
      content = readFileSync(filepath, "utf-8");
    }
    const scriptTag = `<script type="application/akf+json">\n${jsonStr}\n</script>`;
    // Remove existing AKF script if present
    content = content.replace(
      /<script\s+type=["']application\/akf\+json["'][^>]*>[\s\S]*?<\/script>/gi,
      ""
    );
    // Insert before </head> or append
    if (content.indexOf("</head>") >= 0) {
      content = content.replace("</head>", `${scriptTag}\n</head>`);
    } else {
      content += `\n${scriptTag}`;
    }
    writeFileSync(filepath, content, "utf-8");
    return;
  }

  // Sidecar for everything else
  const sidecar = sidecarPath(filepath);
  writeFileSync(sidecar, jsonStr, "utf-8");
}

// ---------------------------------------------------------------------------
// Stamp
// ---------------------------------------------------------------------------

export interface StampOptions {
  model?: string;
  agent?: string;
  claims?: Array<string | Partial<Claim>>;
  trustScore?: number;
  classification?: string;
  evidence?: string[];
}

/**
 * Stamp a file with AKF trust metadata.
 * Creates or updates AKF metadata on the file.
 */
export function stampFile(filepath: string, options: StampOptions = {}): AKFUnit {
  const {
    model,
    agent,
    claims: rawClaims = [],
    trustScore = 0.7,
    classification,
    evidence,
  } = options;

  const claims: Partial<Claim>[] = rawClaims.map((c) => {
    const base = typeof c === "string"
      ? { c, t: trustScore, ai: true }
      : { t: trustScore, ai: true, ...c };
    if (model) {
      (base as Record<string, unknown>).origin = { type: "ai", model };
    }
    return base;
  });

  // If no claims provided, create a default stamp claim
  if (claims.length === 0) {
    claims.push({
      c: `Stamped by ${agent || model || "akf"}`,
      t: trustScore,
      ai: true,
    });
  }

  // Add evidence to claims if provided
  if (evidence && evidence.length > 0) {
    const evidenceObjs = evidence.map((e) => ({
      type: detectEvidenceType(e),
      detail: e,
      at: nowISO(),
    }));
    for (const claim of claims) {
      claim.evidence = evidenceObjs;
    }
  }

  const unit = createMulti(claims, {
    model,
    agent,
    label: classification,
    by: agent,
    at: nowISO(),
  });

  embed(filepath, unit);
  return unit;
}

/** Auto-detect evidence type from a plain string. */
function detectEvidenceType(evidence: string): string {
  const lower = evidence.toLowerCase();
  if (/\d+\/\d+\s*tests?\s*pass/i.test(lower)) return "test_pass";
  if (/mypy|type.?check/i.test(lower)) return "type_check";
  if (/lint|eslint|pylint/i.test(lower)) return "lint_clean";
  if (/ci|pipeline|build.*pass/i.test(lower)) return "ci_pass";
  if (/review|approved/i.test(lower)) return "human_review";
  return "other";
}

// ---------------------------------------------------------------------------
// Scan
// ---------------------------------------------------------------------------

export interface ScanResult {
  enriched: boolean;
  format: string;
  claimCount: number;
  classification: string | null;
  overallTrust: number;
  aiClaimCount: number;
  validation: ValidationResult | null;
}

/**
 * Scan a file for AKF metadata and return a summary report.
 */
export function scan(filepath: string): ScanResult {
  const ext = extname(filepath).toLowerCase();
  const format = ext.replace(".", "") || "unknown";

  try {
    const unit = read(filepath);
    const validation = validate(unit);

    const claims = unit.claims || [];
    const aiClaims = claims.filter((c) => c.ai);
    const totalTrust =
      claims.length > 0
        ? claims.reduce((sum, c) => sum + (c.t || 0), 0) / claims.length
        : 0;

    return {
      enriched: true,
      format,
      claimCount: claims.length,
      classification: unit.label || null,
      overallTrust: Math.round(totalTrust * 100) / 100,
      aiClaimCount: aiClaims.length,
      validation,
    };
  } catch {
    return {
      enriched: false,
      format,
      claimCount: 0,
      classification: null,
      overallTrust: 0,
      aiClaimCount: 0,
      validation: null,
    };
  }
}
