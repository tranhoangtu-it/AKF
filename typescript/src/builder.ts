/**
 * AKF v1.1 — Fluent builder API.
 */

import { randomUUID } from "node:crypto";
import type { AKFUnit, Claim, Evidence, ProvHop } from "./models.js";
import { computeIntegrityHash } from "./provenance.js";

/** Fluent builder for constructing AKF units. */
export class AKFBuilder {
  private _claims: Claim[] = [];
  private _by: string | undefined;
  private _agentId: string | undefined;
  private _modelId: string | undefined;
  private _label: string | undefined;
  private _inherit: boolean | undefined;
  private _ext: boolean | undefined;
  private _ttl: number | undefined;
  private _tools: string[] | undefined;
  private _session: string | undefined;
  private _meta: Record<string, unknown> | undefined;

  /** Add a claim. */
  claim(
    content: string,
    trust: number,
    opts?: Partial<Omit<Claim, "c" | "t">>
  ): this {
    const claimId: string = (opts?.id as string) || randomUUID().replace(/-/g, "").slice(0, 8);
    this._claims.push({ c: content, t: trust, ...opts, id: claimId });
    return this;
  }

  /** Set author. */
  by(author: string): this {
    this._by = author;
    return this;
  }

  /** Set AI agent identifier. */
  agent(id: string): this {
    this._agentId = id;
    return this;
  }

  /** Set security classification. */
  label(classification: string): this {
    this._label = classification;
    return this;
  }

  /** Set inheritance flag. */
  inherit(value: boolean = true): this {
    this._inherit = value;
    return this;
  }

  /** Set external sharing flag. */
  ext(value: boolean = true): this {
    this._ext = value;
    return this;
  }

  /** Set retention period in days. */
  ttl(days: number): this {
    this._ttl = days;
    return this;
  }

  /** Set model identifier. */
  model(id: string): this {
    this._modelId = id;
    return this;
  }

  /** Set kind on the last claim. */
  kind(kind: string): this {
    if (this._claims.length === 0) {
      throw new Error("No claims to set kind on — add a claim first");
    }
    const last = this._claims[this._claims.length - 1];
    this._claims[this._claims.length - 1] = { ...last, kind };
    return this;
  }

  /** Add evidence to the last claim. */
  evidence(...items: Evidence[]): this {
    if (this._claims.length === 0) {
      throw new Error("No claims to add evidence to — add a claim first");
    }
    const last = this._claims[this._claims.length - 1];
    const existing = last.evidence ? [...last.evidence] : [];
    existing.push(...items);
    this._claims[this._claims.length - 1] = { ...last, evidence: existing };
    return this;
  }

  /** Set tools used. */
  tools(...names: string[]): this {
    this._tools = names;
    return this;
  }

  /** Set session identifier. */
  session(id: string): this {
    this._session = id;
    return this;
  }

  /** Add tags to the last claim. */
  tag(...tags: string[]): this {
    if (this._claims.length === 0) {
      throw new Error("No claims to tag — add a claim first");
    }
    const last = this._claims[this._claims.length - 1];
    const existing = last.tags ? [...last.tags] : [];
    existing.push(...tags);
    this._claims[this._claims.length - 1] = { ...last, tags: existing };
    return this;
  }

  /** Set free-form metadata. */
  meta(data: Record<string, unknown>): this {
    this._meta = data;
    return this;
  }

  /** Build the AKF unit. */
  build(): AKFUnit {
    if (this._claims.length === 0) {
      throw new Error("At least one claim is required");
    }

    const now = new Date().toISOString();
    const id = `akf-${randomUUID().replace(/-/g, "").slice(0, 12)}`;

    // Auto-create provenance hop 0
    let prov: ProvHop[] | undefined;
    if (this._by || this._agentId) {
      const actor = this._by || this._agentId || "unknown";
      prov = [
        {
          hop: 0,
          by: actor,
          do: "created",
          at: now,
          adds: this._claims
            .map((c) => c.id)
            .filter((id): id is string => id !== undefined),
        },
      ];
    }

    const unit: AKFUnit = {
      v: "1.0",
      id,
      claims: this._claims,
      by: this._by,
      agent: this._agentId,
      model: this._modelId,
      tools: this._tools,
      session: this._session,
      at: now,
      label: this._label,
      inherit: this._inherit,
      ext: this._ext,
      ttl: this._ttl,
      prov,
      meta: this._meta,
    };

    // Auto-compute integrity hash
    const integrity = computeIntegrityHash(unit);
    unit.hash = integrity;

    return unit;
  }
}
