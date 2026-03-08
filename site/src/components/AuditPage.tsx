import { useState } from 'react';

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

  // 1. Provenance present
  maxPoints++;
  const prov = json.prov || json.provenance || [];
  const hasProv = Array.isArray(prov) && prov.length > 0;
  checks.push({ check: 'Provenance present', passed: hasProv });
  if (hasProv) scorePoints++; else recommendations.push('Add provenance to track data lineage');

  // 2. Integrity hash
  maxPoints++;
  const hasHash = !!(json.hash || json.integrity_hash);
  checks.push({ check: 'Integrity hash', passed: hasHash });
  if (hasHash) scorePoints++; else recommendations.push('Compute integrity hash for tamper detection');

  // 3. Classification set
  maxPoints++;
  const hasClass = !!(json.label || json.classification);
  checks.push({ check: 'Classification set', passed: hasClass });
  if (hasClass) scorePoints++; else recommendations.push('Set security classification');

  // 4. All claims sourced
  maxPoints++;
  const claims = json.claims || [];
  const allSourced = claims.length === 0 || claims.every((c: any) => {
    const src = c.src || c.source;
    return src && src !== 'unspecified';
  });
  checks.push({ check: 'All claims sourced', passed: allSourced });
  if (allSourced) scorePoints++; else recommendations.push('Add source attribution to all claims');

  // 5. AI claims labeled
  maxPoints++;
  const aiLabeled = claims.every((c: any) => (c.ai ?? c.ai_generated) !== undefined);
  checks.push({ check: 'AI claims labeled', passed: aiLabeled });
  if (aiLabeled) scorePoints++;

  // 6. AI risk described
  maxPoints++;
  const riskyAi = claims.filter((c: any) => (c.ai ?? c.ai_generated) && (c.tier ?? c.authority_tier ?? 3) >= 4);
  const allRiskyDescribed = riskyAi.length === 0 || riskyAi.every((c: any) => !!c.risk);
  checks.push({ check: 'AI risk described', passed: allRiskyDescribed });
  if (allRiskyDescribed) scorePoints++; else recommendations.push('Add risk descriptions to AI-generated speculative claims');

  // 7. Valid structure
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

export default function AuditPage() {
  const [input, setInput] = useState('');
  const [result, setResult] = useState<AuditResult | null>(null);

  const sampleAKF = JSON.stringify({
    v: '1.0',
    label: 'confidential',
    hash: 'sha256:abc123',
    claims: [
      { c: 'Q3 revenue $4.2B', t: 0.98, src: 'SEC 10-Q', ai: false },
      { c: 'Market share 23%', t: 0.85, src: 'Gartner', ai: false }
    ],
    prov: [{ hop: 0, by: 'sarah@acme.com', do: 'created', at: '2025-07-15T09:30:00Z' }]
  }, null, 2);

  return (
    <div className="pt-14">
      <div className="max-w-3xl mx-auto px-6 py-16">
        <h1 className="text-3xl font-bold text-text-primary mb-2">Compliance Audit</h1>
        <p className="text-text-secondary mb-8">
          Run the 7-check AKF compliance audit on any AKF JSON. All checks run client-side.
        </p>

        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Paste AKF JSON here..."
          className="w-full h-64 bg-surface-raised border border-border-subtle rounded-lg p-4 font-mono text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent/50 resize-y"
        />

        <div className="flex gap-3 mt-4">
          <button
            onClick={() => setResult(auditAKF(input))}
            disabled={!input.trim()}
            className="px-6 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Run Audit
          </button>
          <button
            onClick={() => { setInput(sampleAKF); setResult(null); }}
            className="px-4 py-2 rounded-lg border border-border-subtle text-text-secondary hover:text-text-primary transition-colors"
          >
            Load Sample
          </button>
        </div>

        {result && (
          <div className="mt-8 space-y-6">
            {/* Score banner */}
            <div className={`p-6 rounded-lg border ${result.compliant ? 'border-green-500/30 bg-green-500/5' : 'border-red-500/30 bg-red-500/5'}`}>
              <div className="flex items-center justify-between">
                <div>
                  <span className={`text-2xl font-bold ${result.compliant ? 'text-green-400' : 'text-red-400'}`}>
                    {result.compliant ? 'COMPLIANT' : 'NON-COMPLIANT'}
                  </span>
                  {result.error && <p className="text-red-400 mt-1">{result.error}</p>}
                </div>
                <div className="text-right">
                  <div className="text-3xl font-mono font-bold text-text-primary">{(result.score * 100).toFixed(0)}%</div>
                  <div className="text-sm text-text-secondary">audit score</div>
                </div>
              </div>
            </div>

            {/* Check grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {result.checks.map((check, i) => (
                <div key={i} className={`p-4 rounded-lg border ${check.passed ? 'border-green-500/20 bg-green-500/5' : 'border-red-500/20 bg-red-500/5'}`}>
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{check.passed ? '\u2705' : '\u274c'}</span>
                    <span className="font-medium text-text-primary">{check.check}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Recommendations */}
            {result.recommendations.length > 0 && (
              <div className="p-4 rounded-lg bg-surface-raised border border-border-subtle">
                <h3 className="font-semibold text-text-primary mb-3">Recommendations</h3>
                <ul className="space-y-2">
                  {result.recommendations.map((rec, i) => (
                    <li key={i} className="flex items-start gap-2 text-text-secondary">
                      <span className="text-accent mt-0.5">&bull;</span>
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
