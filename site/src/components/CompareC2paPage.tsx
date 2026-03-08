export default function CompareC2paPage() {
  const rows = [
    { feature: 'Scope', c2pa: 'File-level media provenance', akf: 'Claim-level knowledge trust' },
    { feature: 'Granularity', c2pa: 'Entire file (image, video, document)', akf: 'Individual claims within a document' },
    { feature: 'Trust scoring', c2pa: 'Binary (signed or not)', akf: '0-1 confidence + authority tiers' },
    { feature: 'AI-native', c2pa: 'Designed for media authenticity', akf: 'Designed for LLM outputs and AI agents' },
    { feature: 'Provenance chain', c2pa: 'Media creation/editing history', akf: 'Knowledge transformation lineage' },
    { feature: 'Machine-readable', c2pa: 'JUMBF/CBOR binary manifest', akf: 'JSON (compact or descriptive)' },
    { feature: 'Open standard', c2pa: 'Yes (C2PA Coalition)', akf: 'Yes (MIT license, open spec)' },
    { feature: 'Use case', c2pa: '"Was this photo real?"', akf: '"Can I trust this claim?"' },
  ];

  return (
    <div className="pt-14">
      <div className="max-w-3xl mx-auto px-6 py-16">
        <h1 className="text-3xl font-bold text-text-primary mb-2">C2PA vs AKF</h1>
        <p className="text-xl text-text-secondary mb-4">Why you need both</p>

        <div className="p-5 rounded-lg bg-accent/10 border border-accent/20 mb-10">
          <p className="text-text-primary">
            <strong>C2PA</strong> proves a file is authentic. <strong>AKF</strong> proves the claims inside it are trustworthy.
            They complement each other — AKF operates as the claim-level trust layer inside C2PA manifests.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-border-subtle">
                <th className="py-3 pr-4 text-sm font-semibold text-text-primary">Feature</th>
                <th className="py-3 pr-4 text-sm font-semibold text-text-secondary">C2PA</th>
                <th className="py-3 text-sm font-semibold text-accent">AKF</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i} className="border-b border-border-subtle/50">
                  <td className="py-3 pr-4 text-sm font-medium text-text-primary">{row.feature}</td>
                  <td className="py-3 pr-4 text-sm text-text-secondary">{row.c2pa}</td>
                  <td className="py-3 text-sm text-text-primary">{row.akf}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-12 p-6 rounded-lg bg-surface-raised border border-border-subtle">
          <h2 className="text-xl font-bold text-text-primary mb-3">Better Together</h2>
          <p className="text-text-secondary mb-4">
            A C2PA manifest tells you "this document was created by Sarah in Adobe Acrobat."
            AKF metadata inside the document tells you "the revenue claim has 0.98 confidence
            from an SEC filing, but the growth projection is AI-generated with 0.60 confidence."
          </p>
          <p className="text-text-secondary">
            Use C2PA for <strong>file authenticity</strong>. Use AKF for <strong>claim trustworthiness</strong>.
            Together, they provide complete provenance from file origin to individual knowledge claims.
          </p>
        </div>
      </div>
    </div>
  );
}
