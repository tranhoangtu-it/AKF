/**
 * AKF metadata storage and audit logic for Google Workspace.
 *
 * Storage: PropertiesService.getDocumentProperties().getProperty('akf_metadata')
 *
 * Note: Document Properties don't survive export-to-DOCX. They persist only
 * within the Google Workspace ecosystem. For DOCX interop, use the Python CLI
 * to re-embed after export.
 */

var AKF_PROPERTY_KEY = 'akf_metadata';

function getAKFMetadata() {
  var props = PropertiesService.getDocumentProperties();
  var raw = props.getProperty(AKF_PROPERTY_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch (e) {
    return null;
  }
}

function setAKFMetadata(meta) {
  var props = PropertiesService.getDocumentProperties();
  props.setProperty(AKF_PROPERTY_KEY, JSON.stringify(meta));
}

function embedMetadata() {
  var existing = getAKFMetadata();
  if (existing) return existing;

  var email = Session.getActiveUser().getEmail();
  var meta = {
    version: '1.0',
    id: Utilities.getUuid(),
    author: email,
    classification: 'internal',
    claims: [],
    provenance: [
      {
        hop: 1,
        actor: email,
        action: 'created',
        timestamp: new Date().toISOString()
      }
    ]
  };

  setAKFMetadata(meta);
  return meta;
}

function auditMetadata(meta) {
  if (!meta) meta = getAKFMetadata();
  if (!meta) return { compliant: false, score: 0, checks: [], recommendations: ['No metadata found'] };

  var checks = [];
  var scorePoints = 0;
  var maxPoints = 0;
  var recommendations = [];

  // Check 1: Provenance present
  maxPoints++;
  var hasProv = meta.provenance && meta.provenance.length > 0;
  checks.push({ check: 'provenance_present', passed: !!hasProv });
  if (hasProv) scorePoints++;
  else recommendations.push('Add provenance to track data lineage');

  // Check 2: Integrity hash
  maxPoints++;
  var hasHash = !!meta.integrity_hash;
  checks.push({ check: 'integrity_hash', passed: hasHash });
  if (hasHash) scorePoints++;
  else recommendations.push('Compute integrity hash for tamper detection');

  // Check 3: Classification set
  maxPoints++;
  var hasClass = !!meta.classification;
  checks.push({ check: 'classification_set', passed: hasClass });
  if (hasClass) scorePoints++;
  else recommendations.push('Set security classification');

  // Check 4: All claims sourced
  maxPoints++;
  var claims = meta.claims || [];
  var allSourced = claims.length === 0 || claims.every(function(c) {
    return c.source && c.source !== 'unspecified';
  });
  checks.push({ check: 'all_claims_sourced', passed: allSourced });
  if (allSourced) scorePoints++;
  else recommendations.push('Add source attribution to all claims');

  // Check 5: AI claims labeled
  maxPoints++;
  var aiLabeled = claims.every(function(c) {
    return c.ai_generated !== undefined;
  });
  checks.push({ check: 'ai_claims_labeled', passed: aiLabeled });
  if (aiLabeled) scorePoints++;

  // Check 6: High-risk AI claims have risk descriptions
  maxPoints++;
  var riskyAi = claims.filter(function(c) {
    return c.ai_generated && (c.authority_tier || 3) >= 4;
  });
  var allRiskyDescribed = riskyAi.length === 0 || riskyAi.every(function(c) { return !!c.risk; });
  checks.push({ check: 'ai_risk_described', passed: allRiskyDescribed });
  if (allRiskyDescribed) scorePoints++;
  else recommendations.push('Add risk descriptions to AI-generated speculative claims');

  // Check 7: Valid structure
  maxPoints++;
  var validStructure = claims.length > 0 && claims.every(function(c) {
    return c.content && c.confidence >= 0 && c.confidence <= 1;
  });
  checks.push({ check: 'valid_structure', passed: validStructure });
  if (validStructure) scorePoints++;

  var score = maxPoints > 0 ? scorePoints / maxPoints : 0;

  return {
    compliant: score >= 0.7,
    score: Math.round(score * 100) / 100,
    checks: checks,
    recommendations: recommendations
  };
}

function getMetadataForSidebar() {
  var meta = getAKFMetadata();
  if (!meta) return { found: false };
  var auditResult = auditMetadata(meta);
  return {
    found: true,
    metadata: meta,
    audit: auditResult
  };
}
