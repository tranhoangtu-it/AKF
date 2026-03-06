/**
 * AKF v1.1 — TypeScript interfaces for Agent Knowledge Format.
 *
 * Field names use compact form (c, t, src, etc.) as the canonical wire format.
 * Descriptive aliases (content, confidence, source, etc.) are accepted on input
 * via the normalize() functions.
 */

// ---------------------------------------------------------------------------
// v1.1 New interfaces
// ---------------------------------------------------------------------------

/** Parameters used during AI generation. */
export interface GenerationParams {
  temperature?: number;
  topP?: number;
  maxTokens?: number;
  tokensInput?: number;
  tokensOutput?: number;
  tokensTotal?: number;
  costUsd?: number;
  latencyMs?: number;
  toolsUsed?: string[];
  [key: string]: unknown;
}

/** Origin tracking — who/what produced this content and how. */
export interface Origin {
  type: string;
  model?: string;
  version?: string;
  provider?: string;
  parameters?: GenerationParams;
  [key: string]: unknown;
}

/** Authorship entry. */
export interface MadeBy {
  actor: string;
  role: string;
  at?: string;
  [key: string]: unknown;
}

/** A review verdict on a claim or unit. */
export interface Review {
  reviewer: string;
  verdict: string;
  comment?: string;
  at?: string;
  [key: string]: unknown;
}

/** Detailed source information for grounded claims. */
export interface SourceDetail {
  uri: string;
  retrievedAt?: string;
  hash?: string;
  page?: number;
  section?: string;
  [key: string]: unknown;
}

/** Explainability chain for AI-generated claims. */
export interface ReasoningChain {
  steps: string[];
  conclusion?: string;
  model?: string;
  tokenCount?: number;
  [key: string]: unknown;
}

/** Free-form annotation. */
export interface Annotation {
  key: string;
  value: string;
  scope?: string;
  at?: string;
  [key: string]: unknown;
}

/** Time-sensitivity metadata. */
export interface Freshness {
  retrievedAt?: string;
  validUntil?: string;
  refreshUrl?: string;
  staleAfterHours?: number;
  [key: string]: unknown;
}

/** LLM cost tracking metadata. */
export interface CostMetadata {
  inputTokens?: number;
  outputTokens?: number;
  model?: string;
  costUsd?: number;
  [key: string]: unknown;
}

/** Profile of an AI agent in the provenance chain. */
export interface AgentProfile {
  id: string;
  name?: string;
  version?: string;
  capabilities?: string[];
  trustCeiling?: number;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Core interfaces
// ---------------------------------------------------------------------------

/** Multi-resolution fidelity for a claim. */
export interface Fidelity {
  /** Headline (~5 tokens) */
  h?: string;
  /** Summary (~50 tokens) */
  s?: string;
  /** Full detail (~2000 tokens) */
  f?: string;
}

/** A piece of evidence supporting a claim. */
export interface Evidence {
  /** Evidence type (test_pass, type_check, lint_clean, ci_pass, human_review, other) */
  type: string;
  /** Description of the evidence */
  detail: string;
  /** ISO-8601 timestamp */
  at?: string;
  /** Tool that produced the evidence */
  tool?: string;
  /** Extensible: unknown fields */
  [key: string]: unknown;
}

/** A single knowledge claim with trust metadata. */
export interface Claim {
  /** Content (required) */
  c: string;
  /** Trust score 0.0-1.0 (required) */
  t: number;
  /** Claim identifier */
  id?: string;
  /** Source attribution */
  src?: string;
  /** URI reference */
  uri?: string;
  /** Authority tier 1-5 */
  tier?: number;
  /** Verified flag */
  ver?: boolean;
  /** Verified by */
  ver_by?: string;
  /** AI-generated flag */
  ai?: boolean;
  /** Risk description */
  risk?: string;
  /** Temporal decay half-life in days */
  decay?: number;
  /** Expiration timestamp */
  exp?: string;
  /** Tags */
  tags?: string[];
  /** Contradicting claim reference */
  contra?: string;
  /** Multi-resolution fidelity */
  fidelity?: Fidelity;
  /** Kind of claim (claim, code_change, decision, suggestion, review, test_result, diagnosis) */
  kind?: string;
  /** Evidence supporting the claim */
  evidence?: Evidence[];
  // v1.1 fields
  /** Origin tracking */
  origin?: Origin;
  /** Review verdicts */
  reviews?: Review[];
  /** Detailed source info */
  sourceDetail?: SourceDetail;
  /** Reasoning chain */
  reasoning?: ReasoningChain;
  /** Freshness metadata */
  freshness?: Freshness;
  /** Annotations */
  annotations?: Annotation[];
  /** Cost metadata */
  cost?: CostMetadata;
  /** ID of claim this supersedes */
  supersedes?: string;
  /** Hard expiry timestamp */
  expiresAt?: string;
  /** Verification timestamp */
  verifiedAt?: string;
  /** Claim IDs this depends on */
  dependsOn?: string[];
  /** Relationship type */
  relationship?: string;
  /** Extensible: unknown fields */
  [key: string]: unknown;
}

/** A single hop in the provenance chain. */
export interface ProvHop {
  /** Hop number (sequential from 0) */
  hop: number;
  /** Actor who performed the action */
  by: string;
  /** Action: created|enriched|reviewed|consumed|transformed */
  do: string;
  /** ISO-8601 timestamp */
  at: string;
  /** Chained hash of this hop */
  h?: string;
  /** Penalty applied (must be negative) */
  pen?: number;
  /** Claim IDs added */
  adds?: string[];
  /** Claim IDs dropped/rejected */
  drops?: string[];
  // v1.1 fields
  /** Model used for this hop */
  model?: string;
  /** Hash of the input */
  inputHash?: string;
  /** Hash of the output */
  outputHash?: string;
  /** Agent profile */
  agentProfile?: AgentProfile;
  /** Duration in milliseconds */
  durationMs?: number;
  /** Tool calls made */
  toolCalls?: string[];
  /** Extensible: unknown fields */
  [key: string]: unknown;
}

/** Root AKF envelope — the top-level knowledge unit. */
export interface AKFUnit {
  /** Version (required) */
  v: string;
  /** Non-empty array of claims (required) */
  claims: Claim[];
  /** Unit identifier */
  id?: string;
  /** Author */
  by?: string;
  /** AI agent identifier */
  agent?: string;
  /** Model identifier */
  model?: string;
  /** Tools used */
  tools?: string[];
  /** Session identifier */
  session?: string;
  /** ISO-8601 creation timestamp */
  at?: string;
  /** Security classification */
  label?: string;
  /** Whether children inherit classification */
  inherit?: boolean;
  /** Whether external sharing is allowed */
  ext?: boolean;
  /** Retention period in days */
  ttl?: number;
  /** Provenance chain */
  prov?: ProvHop[];
  /** Integrity hash (algorithm-prefixed) */
  hash?: string;
  /** Free-form metadata */
  meta?: Record<string, unknown>;
  // v1.1 fields
  /** Authorship chain */
  madeBy?: MadeBy[];
  /** Review verdicts */
  reviews?: Review[];
  /** Security metadata */
  security?: Record<string, unknown>;
  /** Compliance metadata */
  compliance?: Record<string, unknown>;
  /** Cost metadata */
  cost?: CostMetadata;
  /** Annotations */
  annotations?: Annotation[];
  /** Schema version */
  schemaVersion?: string;
  /** Parent unit ID */
  parentId?: string;
  /** Extensible: unknown fields */
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Descriptive name normalization
// ---------------------------------------------------------------------------

/** Maps descriptive claim field names to compact names. */
const CLAIM_ALIASES: Record<string, string> = {
  content: "c",
  confidence: "t",
  source: "src",
  authority_tier: "tier",
  verified: "ver",
  verified_by: "ver_by",
  ai_generated: "ai",
  decay_half_life: "decay",
  expires: "exp",
  contradicts: "contra",
  // v1.1
  source_detail: "sourceDetail",
  expires_at: "expiresAt",
  verified_at: "verifiedAt",
  depends_on: "dependsOn",
  supersedes_id: "supersedes",
};

/** Maps descriptive ProvHop field names to compact names. */
const PROVHOP_ALIASES: Record<string, string> = {
  actor: "by",
  action: "do",
  timestamp: "at",
  hash: "h",
  penalty: "pen",
  claims_added: "adds",
  claims_removed: "drops",
  // v1.1
  input_hash: "inputHash",
  output_hash: "outputHash",
  agent_profile: "agentProfile",
  duration_ms: "durationMs",
  tool_calls: "toolCalls",
};

/** Maps descriptive AKFUnit field names to compact names. */
const UNIT_ALIASES: Record<string, string> = {
  version: "v",
  author: "by",
  created: "at",
  classification: "label",
  inherit_classification: "inherit",
  allow_external: "ext",
  integrity_hash: "hash",
  provenance: "prov",
  // v1.1
  made_by: "madeBy",
  schema_version: "schemaVersion",
  parent_id: "parentId",
};

/** Remap keys in an object using an alias map. Unknown keys pass through. */
function remapKeys(obj: Record<string, unknown>, aliases: Record<string, string>): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(obj)) {
    const mappedKey = aliases[key] || key;
    result[mappedKey] = value;
  }
  return result;
}

/** Normalize a claim object, converting descriptive names to compact. */
export function normalizeClaim(raw: Record<string, unknown>): Claim {
  return remapKeys(raw, CLAIM_ALIASES) as unknown as Claim;
}

/** Normalize a ProvHop object, converting descriptive names to compact. */
export function normalizeProvHop(raw: Record<string, unknown>): ProvHop {
  return remapKeys(raw, PROVHOP_ALIASES) as unknown as ProvHop;
}

/** Normalize an AKFUnit object, converting descriptive names to compact. */
export function normalizeUnit(raw: Record<string, unknown>): AKFUnit {
  const mapped = remapKeys(raw, UNIT_ALIASES);

  // Also normalize nested claims
  if (Array.isArray(mapped.claims)) {
    mapped.claims = (mapped.claims as Record<string, unknown>[]).map(
      (c) => normalizeClaim(c)
    );
  }

  // Also normalize nested provenance
  if (Array.isArray(mapped.prov)) {
    mapped.prov = (mapped.prov as Record<string, unknown>[]).map(
      (p) => normalizeProvHop(p)
    );
  }

  return mapped as unknown as AKFUnit;
}

/** Convert a compact claim to descriptive field names (for human display). */
export function toDescriptiveClaim(claim: Claim): Record<string, unknown> {
  const reverseMap: Record<string, string> = {
    c: "content",
    t: "confidence",
    src: "source",
    tier: "authority_tier",
    ver: "verified",
    ver_by: "verified_by",
    ai: "ai_generated",
    decay: "decay_half_life",
    exp: "expires",
    contra: "contradicts",
    // v1.1
    sourceDetail: "source_detail",
    expiresAt: "expires_at",
    verifiedAt: "verified_at",
    dependsOn: "depends_on",
    supersedes: "supersedes_id",
  };
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(claim)) {
    if (value !== undefined && value !== null) {
      result[reverseMap[key] || key] = value;
    }
  }
  return result;
}

/** Convert a compact ProvHop to descriptive field names (for human display). */
function toDescriptiveHop(hop: ProvHop): Record<string, unknown> {
  const reverseMap: Record<string, string> = {
    by: "actor",
    do: "action",
    at: "timestamp",
    h: "hash",
    pen: "penalty",
    adds: "claims_added",
    drops: "claims_removed",
    // v1.1
    inputHash: "input_hash",
    outputHash: "output_hash",
    agentProfile: "agent_profile",
    durationMs: "duration_ms",
    toolCalls: "tool_calls",
  };
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(hop)) {
    if (value !== undefined && value !== null) {
      result[reverseMap[key] || key] = value;
    }
  }
  return result;
}

/** Convert a compact AKFUnit to descriptive field names (for human display). */
export function toDescriptive(unit: AKFUnit): Record<string, unknown> {
  const reverseMap: Record<string, string> = {
    v: "version",
    by: "author",
    at: "created",
    label: "classification",
    inherit: "inherit_classification",
    ext: "allow_external",
    hash: "integrity_hash",
    prov: "provenance",
    // v1.1
    madeBy: "made_by",
    schemaVersion: "schema_version",
    parentId: "parent_id",
  };
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(unit)) {
    if (value !== undefined && value !== null) {
      if (key === "claims") {
        result["claims"] = (value as Claim[]).map(toDescriptiveClaim);
      } else if (key === "prov") {
        result["provenance"] = (value as ProvHop[]).map(toDescriptiveHop);
      } else {
        result[reverseMap[key] || key] = value;
      }
    }
  }
  return result;
}
