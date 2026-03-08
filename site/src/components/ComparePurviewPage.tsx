export default function ComparePurviewPage() {
  const rows = [
    { feature: 'Cost', purview: 'M365 E5 license ($57/user/month)', akf: 'Free and open-source (MIT)' },
    { feature: 'Platform', purview: 'Microsoft 365 only', akf: 'Any platform, any language' },
    { feature: 'Granularity', purview: 'Document-level labels', akf: 'Claim-level trust scores' },
    { feature: 'AI-native', purview: 'Sensitivity labels for AI outputs', akf: 'Built for LLM outputs from day one' },
    { feature: 'Trust scoring', purview: 'Binary classification labels', akf: '0-1 confidence + 5 authority tiers' },
    { feature: 'Provenance', purview: 'Audit logs in compliance center', akf: 'Embedded provenance chain per file' },
    { feature: 'Agent support', purview: 'Limited (M365 Copilot)', akf: 'Any AI agent, any framework' },
    { feature: 'Lock-in', purview: 'Microsoft ecosystem', akf: 'Vendor-neutral, portable JSON' },
  ];

  return (
    <div className="pt-14">
      <div className="max-w-3xl mx-auto px-6 py-16">
        <h1 className="text-3xl font-bold text-text-primary mb-2">Microsoft Purview vs AKF</h1>
        <p className="text-xl text-text-secondary mb-4">AKF for teams not on Microsoft</p>

        <div className="p-5 rounded-lg bg-accent/10 border border-accent/20 mb-10">
          <p className="text-text-primary">
            Microsoft Purview provides enterprise data governance for M365 organizations.
            AKF provides <strong>claim-level trust metadata</strong> that works everywhere —
            no M365 license, no vendor lock-in, no per-user fees.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-border-subtle">
                <th className="py-3 pr-4 text-sm font-semibold text-text-primary">Feature</th>
                <th className="py-3 pr-4 text-sm font-semibold text-text-secondary">Purview</th>
                <th className="py-3 text-sm font-semibold text-accent">AKF</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i} className="border-b border-border-subtle/50">
                  <td className="py-3 pr-4 text-sm font-medium text-text-primary">{row.feature}</td>
                  <td className="py-3 pr-4 text-sm text-text-secondary">{row.purview}</td>
                  <td className="py-3 text-sm text-text-primary">{row.akf}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-12 p-6 rounded-lg bg-surface-raised border border-border-subtle">
          <h2 className="text-xl font-bold text-text-primary mb-3">When to use each</h2>
          <ul className="space-y-3 text-text-secondary">
            <li className="flex items-start gap-2">
              <span className="text-text-primary font-medium mt-0.5">Purview</span>
              — You're an M365 E5 shop that needs DLP, eDiscovery, and compliance across Microsoft apps.
            </li>
            <li className="flex items-start gap-2">
              <span className="text-accent font-medium mt-0.5">AKF</span>
              — You need claim-level trust metadata that works across platforms, AI agents, and file formats.
            </li>
            <li className="flex items-start gap-2">
              <span className="font-medium mt-0.5">Both</span>
              — AKF's Purview signals export (<code className="text-xs bg-surface-raised px-1 py-0.5 rounded">akf.purview_signals()</code>) maps trust scores to Purview sensitivity labels.
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
