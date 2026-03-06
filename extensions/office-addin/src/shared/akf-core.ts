/**
 * AKF Core — self-contained trust scoring, audit, and metadata types.
 * Mirrors the Python SDK's trust and compliance logic.
 */

export interface AKFClaim {
  id?: string;
  content: string;
  confidence: number;
  source?: string;
  authority_tier?: number;
  verified?: boolean;
  ai_generated?: boolean;
  risk?: string;
}

export interface AKFProvHop {
  hop: number;
  actor: string;
  action: string;
  timestamp: string;
  claims_added?: string[];
  claims_removed?: string[];
}

export interface AKFMetadata {
  version?: string;
  id?: string;
  author?: string;
  classification?: string;
  claims: AKFClaim[];
  provenance?: AKFProvHop[];
  integrity_hash?: string;
}

export interface TrustResult {
  score: number;
  decision: "ACCEPT" | "LOW" | "REJECT";
}

export interface AuditCheck {
  check: string;
  passed: boolean;
}

export interface AuditResult {
  compliant: boolean;
  score: number;
  checks: AuditCheck[];
  recommendations: string[];
}

const AUTHORITY_WEIGHTS: Record<number, number> = {
  1: 1.0,
  2: 0.85,
  3: 0.7,
  4: 0.5,
  5: 0.3,
};

export function effectiveTrust(claim: AKFClaim): TrustResult {
  const tier = claim.authority_tier ?? 3;
  const authWeight = AUTHORITY_WEIGHTS[tier] ?? 0.7;
  const score = claim.confidence * authWeight;
  let decision: TrustResult["decision"];
  if (score >= 0.7) decision = "ACCEPT";
  else if (score >= 0.4) decision = "LOW";
  else decision = "REJECT";
  return { score, decision };
}

export function trustColor(confidence: number): string {
  if (confidence >= 0.8) return "#22c55e";
  if (confidence >= 0.5) return "#eab308";
  return "#ef4444";
}

export function trustLabel(confidence: number): string {
  if (confidence >= 0.8) return "High";
  if (confidence >= 0.5) return "Medium";
  return "Low";
}

export function overallTrust(claims: AKFClaim[]): number {
  if (claims.length === 0) return 0;
  const sum = claims.reduce((acc, c) => acc + c.confidence, 0);
  return sum / claims.length;
}

export function audit(meta: AKFMetadata): AuditResult {
  const checks: AuditCheck[] = [];
  let scorePoints = 0;
  let maxPoints = 0;
  const recommendations: string[] = [];

  // Check 1: Provenance present
  maxPoints++;
  const hasProv = !!meta.provenance && meta.provenance.length > 0;
  checks.push({ check: "provenance_present", passed: hasProv });
  if (hasProv) scorePoints++;
  else recommendations.push("Add provenance to track data lineage");

  // Check 2: Integrity hash
  maxPoints++;
  const hasHash = !!meta.integrity_hash;
  checks.push({ check: "integrity_hash", passed: hasHash });
  if (hasHash) scorePoints++;
  else recommendations.push("Compute integrity hash for tamper detection");

  // Check 3: Classification set
  maxPoints++;
  const hasClass = !!meta.classification;
  checks.push({ check: "classification_set", passed: hasClass });
  if (hasClass) scorePoints++;
  else recommendations.push("Set security classification");

  // Check 4: All claims sourced
  maxPoints++;
  const allSourced = meta.claims.every(
    (c) => c.source && c.source !== "unspecified"
  );
  checks.push({ check: "all_claims_sourced", passed: allSourced });
  if (allSourced) scorePoints++;
  else recommendations.push("Add source attribution to all claims");

  // Check 5: AI claims labeled
  maxPoints++;
  const aiLabeled = meta.claims.every((c) => c.ai_generated !== undefined);
  checks.push({ check: "ai_claims_labeled", passed: aiLabeled });
  if (aiLabeled) scorePoints++;

  // Check 6: High-risk AI claims have risk descriptions
  maxPoints++;
  const riskyAi = meta.claims.filter(
    (c) => c.ai_generated && (c.authority_tier ?? 3) >= 4
  );
  const allRiskyDescribed =
    riskyAi.length === 0 || riskyAi.every((c) => !!c.risk);
  checks.push({ check: "ai_risk_described", passed: allRiskyDescribed });
  if (allRiskyDescribed) scorePoints++;
  else
    recommendations.push(
      "Add risk descriptions to AI-generated speculative claims"
    );

  // Check 7: Valid structure
  maxPoints++;
  const validStructure = meta.claims.length > 0 && meta.claims.every(
    (c) => c.content && c.confidence >= 0 && c.confidence <= 1
  );
  checks.push({ check: "valid_structure", passed: validStructure });
  if (validStructure) scorePoints++;

  const score = maxPoints > 0 ? scorePoints / maxPoints : 0;

  return {
    compliant: score >= 0.7,
    score: Math.round(score * 100) / 100,
    checks,
    recommendations,
  };
}

export function createDefaultMetadata(): AKFMetadata {
  return {
    version: "1.0",
    id: crypto.randomUUID(),
    classification: "internal",
    claims: [],
    provenance: [
      {
        hop: 1,
        actor: "office-addin",
        action: "created",
        timestamp: new Date().toISOString(),
      },
    ],
  };
}
