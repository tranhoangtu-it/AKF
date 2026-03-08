import { useState } from 'react';

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

  // Version present
  const hasVersion = !!(json.v || json.version);
  checks.push({ rule: 'Version', passed: hasVersion, detail: hasVersion ? `v${json.v || json.version}` : 'Missing "v" or "version" field' });

  // Claims array non-empty
  const claims = json.claims || [];
  const hasClaims = Array.isArray(claims) && claims.length > 0;
  checks.push({ rule: 'Claims present', passed: hasClaims, detail: hasClaims ? `${claims.length} claim(s)` : 'No claims array or empty' });

  // Confidence 0-1
  const confValid = claims.every((c: any) => {
    const t = c.t ?? c.confidence;
    return typeof t === 'number' && t >= 0 && t <= 1;
  });
  checks.push({ rule: 'Confidence range', passed: confValid, detail: confValid ? 'All in [0, 1]' : 'Some confidence values out of range' });

  // Authority tier 1-5
  const tierValid = claims.every((c: any) => {
    const tier = c.tier ?? c.authority_tier;
    return tier === undefined || (typeof tier === 'number' && tier >= 1 && tier <= 5);
  });
  checks.push({ rule: 'Authority tier', passed: tierValid, detail: tierValid ? 'All tiers valid (1-5)' : 'Some tiers out of range' });

  // Classification label valid
  const validLabels = ['public', 'internal', 'confidential', 'highly-confidential', 'restricted'];
  const label = json.label || json.classification;
  const labelValid = !label || validLabels.includes(label);
  checks.push({ rule: 'Classification', passed: labelValid, detail: labelValid ? (label || 'Not set') : `Invalid: "${label}"` });

  // Provenance sequential
  const prov = json.prov || json.provenance || [];
  const provSeq = prov.length === 0 || prov.every((h: any, i: number) => h.hop === i);
  checks.push({ rule: 'Provenance sequence', passed: provSeq, detail: provSeq ? `${prov.length} hop(s)` : 'Hop numbers not sequential' });

  // Hash format
  const hash = json.hash || json.integrity_hash;
  const hashValid = !hash || /^(sha256|sha3-512|blake3):/.test(hash);
  checks.push({ rule: 'Hash format', passed: hashValid, detail: hashValid ? (hash ? hash.slice(0, 20) + '...' : 'Not set') : 'Invalid hash prefix' });

  const valid = checks.every(c => c.passed);
  return { valid, checks };
}

export default function ValidatePage() {
  const [input, setInput] = useState('');
  const [result, setResult] = useState<ReturnType<typeof validateAKF> | null>(null);

  const sampleAKF = JSON.stringify({
    v: '1.0',
    label: 'internal',
    claims: [
      { c: 'Q3 revenue was $4.2B', t: 0.98, src: 'SEC Filing', tier: 1, ver: true },
      { c: 'Market share grew 2%', t: 0.75, src: 'analyst report', tier: 3 }
    ],
    prov: [{ hop: 0, by: 'sarah@acme.com', do: 'created', at: '2025-07-15T09:30:00Z' }]
  }, null, 2);

  return (
    <div className="pt-14">
      <div className="max-w-3xl mx-auto px-6 py-16">
        <h1 className="text-3xl font-bold text-text-primary mb-2">Validate AKF</h1>
        <p className="text-text-secondary mb-8">
          Paste AKF JSON to check structural validity. All validation runs client-side.
        </p>

        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Paste AKF JSON here..."
          className="w-full h-64 bg-surface-raised border border-border-subtle rounded-lg p-4 font-mono text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent/50 resize-y"
        />

        <div className="flex gap-3 mt-4">
          <button
            onClick={() => setResult(validateAKF(input))}
            disabled={!input.trim()}
            className="px-6 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Validate
          </button>
          <button
            onClick={() => { setInput(sampleAKF); setResult(null); }}
            className="px-4 py-2 rounded-lg border border-border-subtle text-text-secondary hover:text-text-primary transition-colors"
          >
            Load Sample
          </button>
        </div>

        {result && (
          <div className="mt-8 space-y-4">
            <div className={`p-4 rounded-lg border ${result.valid ? 'border-green-500/30 bg-green-500/5' : 'border-red-500/30 bg-red-500/5'}`}>
              <span className={`font-semibold ${result.valid ? 'text-green-400' : 'text-red-400'}`}>
                {result.valid ? 'Valid AKF' : 'Invalid AKF'}
              </span>
              {result.error && <span className="ml-2 text-red-400">{result.error}</span>}
            </div>

            {result.checks.length > 0 && (
              <div className="space-y-2">
                {result.checks.map((check, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-surface-raised">
                    <span className="text-lg">{check.passed ? '\u2705' : '\u274c'}</span>
                    <div>
                      <span className="font-medium text-text-primary">{check.rule}</span>
                      <span className="ml-2 text-sm text-text-secondary">{check.detail}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
