export default function CompareWatermarkingPage() {
  const rows = [
    { feature: 'Visibility', wm: 'Hidden (imperceptible signals)', akf: 'Explicit (structured JSON metadata)' },
    { feature: 'Purpose', wm: 'Prove AI origin / detect AI content', akf: 'Prove claim trustworthiness' },
    { feature: 'Granularity', wm: 'Entire output', akf: 'Individual claims within output' },
    { feature: 'Trust scoring', wm: 'None (detection only)', akf: '0-1 confidence + authority tiers' },
    { feature: 'Provenance chain', wm: 'None (single origin stamp)', akf: 'Full transformation lineage' },
    { feature: 'Survives editing', wm: 'May degrade with paraphrasing', akf: 'Preserved through transforms' },
    { feature: 'Machine-readable', wm: 'Statistical detection', akf: 'Native JSON, LLM-parseable' },
    { feature: 'Use case', wm: '"Was this written by AI?"', akf: '"Can I trust what AI wrote?"' },
  ];

  return (
    <div className="pt-14">
      <div className="max-w-3xl mx-auto px-6 py-16">
        <h1 className="text-3xl font-bold text-text-primary mb-2">Watermarking vs AKF</h1>
        <p className="text-xl text-text-secondary mb-4">Watermarks prove origin. AKF proves trust.</p>

        <div className="p-5 rounded-lg bg-accent/10 border border-accent/20 mb-10">
          <p className="text-text-primary">
            AI watermarking embeds hidden signals to detect AI-generated content.
            AKF embeds <strong>explicit trust metadata</strong> — confidence scores, source provenance,
            and authority tiers — so consumers can evaluate the reliability of each claim.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-border-subtle">
                <th className="py-3 pr-4 text-sm font-semibold text-text-primary">Feature</th>
                <th className="py-3 pr-4 text-sm font-semibold text-text-secondary">Watermarking</th>
                <th className="py-3 text-sm font-semibold text-accent">AKF</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i} className="border-b border-border-subtle/50">
                  <td className="py-3 pr-4 text-sm font-medium text-text-primary">{row.feature}</td>
                  <td className="py-3 pr-4 text-sm text-text-secondary">{row.wm}</td>
                  <td className="py-3 text-sm text-text-primary">{row.akf}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-12 p-6 rounded-lg bg-surface-raised border border-border-subtle">
          <h2 className="text-xl font-bold text-text-primary mb-3">Different questions, complementary answers</h2>
          <p className="text-text-secondary mb-4">
            Watermarking answers: <em>"Did an AI produce this?"</em>
          </p>
          <p className="text-text-secondary mb-4">
            AKF answers: <em>"How much should I trust what the AI said, and why?"</em>
          </p>
          <p className="text-text-secondary">
            Knowing content is AI-generated is step one. Knowing which claims are backed by SEC filings
            (confidence 0.98, tier 1) versus AI speculation (confidence 0.55, tier 4) is what
            actually makes AI outputs actionable in enterprise workflows.
          </p>
        </div>
      </div>
    </div>
  );
}
