import { useState } from 'react';

// ── Validate logic ──

interface CheckResult {
  rule: string;
  passed: boolean;
  detail: string;
}

function validateAKF(text: string): { valid: boolean; checks: CheckResult[]; error?: string } {
  const checks: CheckResult[] = [];

  let json: any;
  try {
    json = JSON.parse(text);
  } catch {
    return { valid: false, checks: [], error: 'Invalid JSON' };
  }

  const hasVersion = !!(json.v || json.version);
  checks.push({ rule: 'Version', passed: hasVersion, detail: hasVersion ? `v${json.v || json.version}` : 'Missing "v" or "version" field' });

  const claims = json.claims || [];
  const hasClaims = Array.isArray(claims) && claims.length > 0;
  checks.push({ rule: 'Claims present', passed: hasClaims, detail: hasClaims ? `${claims.length} claim(s)` : 'No claims array or empty' });

  const confValid = claims.every((c: any) => {
    const t = c.t ?? c.confidence;
    return typeof t === 'number' && t >= 0 && t <= 1;
  });
  checks.push({ rule: 'Confidence range', passed: confValid, detail: confValid ? 'All in [0, 1]' : 'Some confidence values out of range' });

  const tierValid = claims.every((c: any) => {
    const tier = c.tier ?? c.authority_tier;
    return tier === undefined || (typeof tier === 'number' && tier >= 1 && tier <= 5);
  });
  checks.push({ rule: 'Authority tier', passed: tierValid, detail: tierValid ? 'All tiers valid (1-5)' : 'Some tiers out of range' });

  const validLabels = ['public', 'internal', 'confidential', 'highly-confidential', 'restricted'];
  const label = json.label || json.classification;
  const labelValid = !label || validLabels.includes(label);
  checks.push({ rule: 'Classification', passed: labelValid, detail: labelValid ? (label || 'Not set') : `Invalid: "${label}"` });

  const prov = json.prov || json.provenance || [];
  const provSeq = prov.length === 0 || prov.every((h: any, i: number) => h.hop === i);
  checks.push({ rule: 'Provenance sequence', passed: provSeq, detail: provSeq ? `${prov.length} hop(s)` : 'Hop numbers not sequential' });

  const hash = json.hash || json.integrity_hash;
  const hashValid = !hash || /^(sha256|sha3-512|blake3):/.test(hash);
  checks.push({ rule: 'Hash format', passed: hashValid, detail: hashValid ? (hash ? hash.slice(0, 20) + '...' : 'Not set') : 'Invalid hash prefix' });

  const valid = checks.every(c => c.passed);
  return { valid, checks };
}

// ── Audit logic ──

interface AuditCheck {
  check: string;
  passed: boolean;
}

interface AuditResult {
  compliant: boolean;
  score: number;
  checks: AuditCheck[];
  recommendations: string[];
  error?: string;
}

function auditAKF(text: string): AuditResult {
  let json: any;
  try {
    json = JSON.parse(text);
  } catch {
    return { compliant: false, score: 0, checks: [], recommendations: [], error: 'Invalid JSON' };
  }

  const checks: AuditCheck[] = [];
  let scorePoints = 0;
  let maxPoints = 0;
  const recommendations: string[] = [];

  maxPoints++;
  const prov = json.prov || json.provenance || [];
  const hasProv = Array.isArray(prov) && prov.length > 0;
  checks.push({ check: 'Provenance present', passed: hasProv });
  if (hasProv) scorePoints++; else recommendations.push('Add provenance to track data lineage');

  maxPoints++;
  const hasHash = !!(json.hash || json.integrity_hash);
  checks.push({ check: 'Integrity hash', passed: hasHash });
  if (hasHash) scorePoints++; else recommendations.push('Compute integrity hash for tamper detection');

  maxPoints++;
  const hasClass = !!(json.label || json.classification);
  checks.push({ check: 'Classification set', passed: hasClass });
  if (hasClass) scorePoints++; else recommendations.push('Set security classification');

  maxPoints++;
  const claims = json.claims || [];
  const allSourced = claims.length === 0 || claims.every((c: any) => {
    const src = c.src || c.source;
    return src && src !== 'unspecified';
  });
  checks.push({ check: 'All claims sourced', passed: allSourced });
  if (allSourced) scorePoints++; else recommendations.push('Add source attribution to all claims');

  maxPoints++;
  const aiLabeled = claims.every((c: any) => (c.ai ?? c.ai_generated) !== undefined);
  checks.push({ check: 'AI claims labeled', passed: aiLabeled });
  if (aiLabeled) scorePoints++;

  maxPoints++;
  const riskyAi = claims.filter((c: any) => (c.ai ?? c.ai_generated) && (c.tier ?? c.authority_tier ?? 3) >= 4);
  const allRiskyDescribed = riskyAi.length === 0 || riskyAi.every((c: any) => !!c.risk);
  checks.push({ check: 'AI risk described', passed: allRiskyDescribed });
  if (allRiskyDescribed) scorePoints++; else recommendations.push('Add risk descriptions to AI-generated speculative claims');

  maxPoints++;
  const validStructure = claims.length > 0 && claims.every((c: any) => {
    const content = c.c || c.content;
    const conf = c.t ?? c.confidence;
    return content && typeof conf === 'number' && conf >= 0 && conf <= 1;
  });
  checks.push({ check: 'Valid structure', passed: validStructure });
  if (validStructure) scorePoints++;

  const score = maxPoints > 0 ? Math.round((scorePoints / maxPoints) * 100) / 100 : 0;
  return { compliant: score >= 0.7, score, checks, recommendations };
}

// ── Combined page ──

type Tab = 'validate' | 'audit';

export default function ValidatePage() {
  const [tab, setTab] = useState<Tab>('validate');
  const [input, setInput] = useState('');
  const [valResult, setValResult] = useState<ReturnType<typeof validateAKF> | null>(null);
  const [auditResult, setAuditResult] = useState<AuditResult | null>(null);

  const sampleAKF = JSON.stringify({
    v: '1.0',
    label: 'confidential',
    hash: 'sha256:abc123',
    claims: [
      { c: 'Q3 revenue $4.2B', t: 0.98, src: 'SEC 10-Q', tier: 1, ai: false },
      { c: 'Market share 23%', t: 0.85, src: 'Gartner', ai: false }
    ],
    prov: [{ hop: 0, by: 'sarah@acme.com', do: 'created', at: '2025-07-15T09:30:00Z' }]
  }, null, 2);

  const runAction = () => {
    if (tab === 'validate') setValResult(validateAKF(input));
    else setAuditResult(auditAKF(input));
  };

  return (
    <div className="pt-14 min-h-screen bg-gradient-to-b from-surface to-surface-raised/30">
      <div className="max-w-4xl mx-auto px-6 py-16">
        {/* Header */}
        <div className="text-center mb-10">
          <p className="text-xs font-mono text-accent tracking-widest uppercase mb-2">Online Tools</p>
          <h1 className="text-4xl font-extrabold tracking-tight text-text-primary">Validate & Audit</h1>
          <p className="mt-3 text-text-secondary max-w-lg mx-auto">
            Check structural validity or run a 7-point compliance audit on any AKF JSON. Everything runs client-side — your data never leaves the browser.
          </p>
        </div>

        {/* Main card */}
        <div className="rounded-2xl border border-border-subtle bg-surface shadow-lg overflow-hidden">
          {/* Tab bar */}
          <div className="flex border-b border-border-subtle">
            <button
              onClick={() => setTab('validate')}
              className={`flex-1 py-3.5 text-sm font-semibold transition-colors relative ${
                tab === 'validate'
                  ? 'text-accent'
                  : 'text-text-tertiary hover:text-text-secondary'
              }`}
            >
              Schema Validate
              {tab === 'validate' && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent" />
              )}
            </button>
            <button
              onClick={() => setTab('audit')}
              className={`flex-1 py-3.5 text-sm font-semibold transition-colors relative ${
                tab === 'audit'
                  ? 'text-accent'
                  : 'text-text-tertiary hover:text-text-secondary'
              }`}
            >
              Compliance Audit
              {tab === 'audit' && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent" />
              )}
            </button>
          </div>

          {/* Input area */}
          <div className="p-6">
            <div className="relative">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={`{\n  "v": "1.0",\n  "claims": [\n    { "c": "Your claim here", "t": 0.95 }\n  ]\n}`}
                className="w-full h-48 bg-surface-raised/50 border border-border-subtle rounded-xl p-4 font-mono text-sm text-text-primary placeholder:text-text-tertiary/50 focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent/40 resize-none"
                spellCheck={false}
              />
              <span className="absolute top-3 right-3 text-[10px] font-mono text-text-tertiary/40 uppercase tracking-wider">
                JSON
              </span>
            </div>

            <div className="flex items-center gap-3 mt-4">
              <button
                onClick={runAction}
                disabled={!input.trim()}
                className="px-6 py-2.5 rounded-xl bg-accent hover:bg-accent-hover text-white text-sm font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-sm hover:shadow-md"
              >
                {tab === 'validate' ? 'Run Validation' : 'Run Audit'}
              </button>
              <button
                onClick={() => { setInput(sampleAKF); setValResult(null); setAuditResult(null); }}
                className="px-5 py-2.5 rounded-xl border border-border-subtle text-sm text-text-secondary hover:text-text-primary hover:border-accent/30 transition-all"
              >
                Load Sample
              </button>
              {input && (
                <button
                  onClick={() => { setInput(''); setValResult(null); setAuditResult(null); }}
                  className="ml-auto text-xs text-text-tertiary hover:text-text-secondary transition-colors"
                >
                  Clear
                </button>
              )}
            </div>
          </div>

          {/* Validate results */}
          {tab === 'validate' && valResult && (
            <div className="border-t border-border-subtle">
              <div className={`px-6 py-4 flex items-center gap-3 ${valResult.valid ? 'bg-emerald-500/5' : 'bg-red-500/5'}`}>
                <span className="text-2xl">{valResult.valid ? '\u2705' : '\u274c'}</span>
                <div>
                  <span className={`font-bold text-lg ${valResult.valid ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                    {valResult.valid ? 'Valid AKF' : 'Invalid AKF'}
                  </span>
                  {valResult.error && <span className="ml-2 text-sm text-red-500">&mdash; {valResult.error}</span>}
                </div>
                <span className="ml-auto text-sm text-text-tertiary font-mono">
                  {valResult.checks.filter(c => c.passed).length}/{valResult.checks.length} checks
                </span>
              </div>
              <div className="px-6 pb-5 pt-2 space-y-1.5">
                {valResult.checks.map((check, i) => (
                  <div key={i} className="flex items-center gap-3 py-2 px-3 rounded-lg hover:bg-surface-raised/50 transition-colors">
                    <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${check.passed ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' : 'bg-red-500/10 text-red-600 dark:text-red-400'}`}>
                      {check.passed ? '\u2713' : '\u2717'}
                    </span>
                    <span className="font-medium text-sm text-text-primary">{check.rule}</span>
                    <span className="text-xs text-text-tertiary ml-auto">{check.detail}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Audit results */}
          {tab === 'audit' && auditResult && (
            <div className="border-t border-border-subtle">
              {/* Score banner */}
              <div className={`px-6 py-5 flex items-center justify-between ${auditResult.compliant ? 'bg-emerald-500/5' : 'bg-red-500/5'}`}>
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{auditResult.compliant ? '\u2705' : '\u274c'}</span>
                  <div>
                    <span className={`font-bold text-lg ${auditResult.compliant ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                      {auditResult.compliant ? 'COMPLIANT' : 'NON-COMPLIANT'}
                    </span>
                    {auditResult.error && <p className="text-sm text-red-500">{auditResult.error}</p>}
                  </div>
                </div>
                <div className="text-right">
                  <div className={`text-3xl font-mono font-bold ${auditResult.compliant ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                    {(auditResult.score * 100).toFixed(0)}%
                  </div>
                  <div className="text-[10px] uppercase tracking-wider text-text-tertiary">score</div>
                </div>
              </div>

              {/* Check grid */}
              <div className="px-6 py-4 grid grid-cols-2 gap-2">
                {auditResult.checks.map((check, i) => (
                  <div key={i} className={`flex items-center gap-2.5 py-2.5 px-3 rounded-lg border ${check.passed ? 'border-emerald-500/20 bg-emerald-500/5' : 'border-red-500/20 bg-red-500/5'}`}>
                    <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${check.passed ? 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400' : 'bg-red-500/20 text-red-600 dark:text-red-400'}`}>
                      {check.passed ? '\u2713' : '\u2717'}
                    </span>
                    <span className="text-sm font-medium text-text-primary">{check.check}</span>
                  </div>
                ))}
              </div>

              {/* Recommendations */}
              {auditResult.recommendations.length > 0 && (
                <div className="px-6 pb-5">
                  <div className="p-4 rounded-xl bg-amber-500/5 border border-amber-500/20">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-400 mb-2.5">Recommendations</h3>
                    <ul className="space-y-1.5">
                      {auditResult.recommendations.map((rec, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-text-secondary">
                          <span className="text-amber-500 mt-0.5 text-xs">&#9656;</span>
                          {rec}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
