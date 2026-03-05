/**
 * AKF — Agent Knowledge Format v1.1
 *
 * Lightweight, LLM-native file format for structured knowledge exchange
 * with built-in trust, provenance, and security metadata.
 */

// Models
export type { AKFUnit, Claim, Evidence, Fidelity, ProvHop } from "./models.js";
export {
  normalizeClaim,
  normalizeProvHop,
  normalizeUnit,
  toDescriptive,
  toDescriptiveClaim,
} from "./models.js";

// Core API
export {
  create,
  createMulti,
  validate,
  toJSON,
  fromJSON,
  stripNulls,
} from "./core.js";
export type { ValidationResult } from "./core.js";

// Builder
export { AKFBuilder } from "./builder.js";

// Trust
export {
  effectiveTrust,
  AUTHORITY_WEIGHTS,
  DECAY_PRESETS,
} from "./trust.js";
export type { TrustResult, TrustDecision } from "./trust.js";

// Provenance
export {
  computeHopHash,
  computeIntegrityHash,
  validateChain,
  addHop,
  formatTree,
} from "./provenance.js";

// Security
export {
  HIERARCHY,
  labelRank,
  validateInheritance,
  canShareExternal,
  inheritLabel,
} from "./security.js";

// Transform
export { AKFTransformer } from "./transform.js";

// File I/O: read, write, stamp, embed, extract, scan
export {
  read,
  extract,
  embed,
  stampFile,
  scan,
} from "./file.js";
export type { EmbedOptions, StampOptions, ScanResult } from "./file.js";

// Streaming
export { AKFStream, stream } from "./stream.js";
export type { StreamOptions, AKFStreamLine } from "./stream.js";

// Detection classes
export {
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
} from "./detection.js";
export type { DetectionResult, DetectionReport } from "./detection.js";

// Compliance
export { audit } from "./compliance.js";
export type { AuditResult, AuditCheck } from "./compliance.js";
