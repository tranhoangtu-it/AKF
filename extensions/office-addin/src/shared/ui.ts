/**
 * DOM rendering helpers for the AKF taskpane.
 */

import {
  AKFMetadata,
  AKFClaim,
  AuditResult,
  trustColor,
  trustLabel,
  overallTrust,
} from "./akf-core";

export function renderHeader(
  container: HTMLElement,
  meta: AKFMetadata
): void {
  const trust = overallTrust(meta.claims);
  const color = trustColor(trust);

  container.innerHTML = `
    <div style="margin-bottom:16px">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
        <span style="font-size:14px;font-weight:600">AKF Trust Metadata</span>
        ${
          meta.classification
            ? `<span style="background:#334155;color:#94a3b8;padding:2px 8px;border-radius:4px;font-size:11px;text-transform:uppercase">${meta.classification}</span>`
            : ""
        }
      </div>
      <div style="display:flex;align-items:center;gap:8px">
        <span style="width:10px;height:10px;border-radius:50%;background:${color};display:inline-block"></span>
        <span style="font-size:13px;color:#cbd5e1">Trust: ${trust.toFixed(2)} (${trustLabel(trust)})</span>
      </div>
      <div style="font-size:12px;color:#64748b;margin-top:4px">${meta.claims.length} claim(s)</div>
    </div>
  `;
}

export function renderClaims(
  container: HTMLElement,
  claims: AKFClaim[]
): void {
  if (claims.length === 0) {
    container.innerHTML = `<div style="color:#64748b;font-size:13px;padding:12px 0">No claims found.</div>`;
    return;
  }

  const items = claims
    .map((c) => {
      const color = trustColor(c.confidence);
      const badges: string[] = [];
      if (c.source) badges.push(`<span style="color:#94a3b8;font-size:11px">${c.source}</span>`);
      if (c.verified) badges.push(`<span style="color:#22c55e;font-size:11px">verified</span>`);
      if (c.ai_generated) badges.push(`<span style="color:#eab308;font-size:11px">AI</span>`);

      return `
        <div style="padding:8px 0;border-bottom:1px solid #1e293b">
          <div style="display:flex;align-items:flex-start;gap:8px">
            <span style="width:8px;height:8px;border-radius:50%;background:${color};display:inline-block;margin-top:5px;flex-shrink:0"></span>
            <div>
              <div style="font-size:13px;color:#e2e8f0">${c.content}</div>
              <div style="display:flex;gap:8px;margin-top:4px;align-items:center">
                <span style="color:${color};font-size:11px;font-weight:600">${c.confidence.toFixed(2)}</span>
                ${badges.join("")}
              </div>
              ${c.risk ? `<div style="color:#ef4444;font-size:11px;margin-top:2px">Risk: ${c.risk}</div>` : ""}
            </div>
          </div>
        </div>
      `;
    })
    .join("");

  container.innerHTML = `<div>${items}</div>`;
}

export function renderProvenance(
  container: HTMLElement,
  meta: AKFMetadata
): void {
  const prov = meta.provenance;
  if (!prov || prov.length === 0) {
    container.innerHTML = `<div style="color:#64748b;font-size:13px;padding:12px 0">No provenance recorded.</div>`;
    return;
  }

  const items = prov
    .map(
      (hop) => `
      <div style="display:flex;gap:8px;padding:6px 0;border-left:2px solid #334155;padding-left:12px;margin-left:4px">
        <div>
          <div style="font-size:13px;color:#e2e8f0"><strong>${hop.actor}</strong> &mdash; ${hop.action}</div>
          <div style="font-size:11px;color:#64748b">${hop.timestamp}</div>
        </div>
      </div>
    `
    )
    .join("");

  container.innerHTML = `
    <div style="margin-top:8px">
      <div style="font-size:13px;font-weight:600;color:#94a3b8;margin-bottom:8px">Provenance</div>
      ${items}
    </div>
  `;
}

export function renderAudit(
  container: HTMLElement,
  result: AuditResult
): void {
  const statusColor = result.compliant ? "#22c55e" : "#ef4444";
  const statusText = result.compliant ? "COMPLIANT" : "NON-COMPLIANT";

  const checkItems = result.checks
    .map(
      (c) =>
        `<div style="padding:4px 0;font-size:13px">
          ${c.passed ? "\u2705" : "\u274c"} ${c.check.replace(/_/g, " ")}
        </div>`
    )
    .join("");

  const recs = result.recommendations.length > 0
    ? `<div style="margin-top:12px">
        <div style="font-size:12px;font-weight:600;color:#94a3b8;margin-bottom:4px">Recommendations</div>
        ${result.recommendations.map((r) => `<div style="font-size:12px;color:#cbd5e1;padding:2px 0">\u2022 ${r}</div>`).join("")}
      </div>`
    : "";

  container.innerHTML = `
    <div>
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
        <span style="color:${statusColor};font-weight:600;font-size:14px">${statusText}</span>
        <span style="color:#64748b;font-size:13px">(score: ${result.score.toFixed(2)})</span>
      </div>
      ${checkItems}
      ${recs}
    </div>
  `;
}

export function renderEmpty(container: HTMLElement): void {
  container.innerHTML = `
    <div style="text-align:center;padding:40px 20px">
      <div style="font-size:14px;color:#94a3b8;margin-bottom:12px">No AKF metadata found</div>
      <div style="font-size:13px;color:#64748b;margin-bottom:20px">
        This document doesn't have trust metadata yet.
      </div>
      <button id="embed-cta" style="
        background:#3b82f6;color:white;border:none;padding:10px 24px;
        border-radius:6px;font-size:13px;cursor:pointer;font-weight:500
      ">Embed Metadata</button>
    </div>
  `;
}
