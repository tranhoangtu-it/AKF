/**
 * AKF v1.0 — Streaming: attach trust metadata to streaming AI output.
 *
 * Uses .akfl (JSON Lines) format for incremental trust metadata.
 */

import { createWriteStream, type WriteStream } from "node:fs";
import type { AKFUnit, Claim } from "./models.js";
import { createMulti, toJSON } from "./core.js";

function nowISO(): string {
  return new Date().toISOString();
}

export interface StreamOptions {
  model?: string;
  agent?: string;
  classification?: string;
  trustScore?: number;
}

export interface AKFStreamLine {
  type: "start" | "chunk" | "claim" | "end";
  [key: string]: unknown;
}

/**
 * AKFStream — context-manager-style streaming that attaches trust metadata
 * alongside AI-generated content.
 *
 * Usage:
 * ```ts
 * const s = stream('output.md', { model: 'gpt-4o' });
 * s.write('Hello world');
 * s.write('More content');
 * const unit = await s.close();
 * ```
 */
export class AKFStream {
  private filepath: string;
  private options: StreamOptions;
  private contentChunks: string[] = [];
  private claims: Partial<Claim>[] = [];
  private logStream: WriteStream;
  private chunkIdx = 0;
  private startTime: string;
  private closed = false;

  constructor(filepath: string, options: StreamOptions = {}) {
    this.filepath = filepath;
    this.options = options;
    this.startTime = nowISO();

    // Create .akfl log file alongside the content file
    this.logStream = createWriteStream(filepath.replace(/(\.\w+)$/, "$1.akfl"));

    // Write start line
    this.writeLine({
      type: "start",
      model: options.model,
      agent: options.agent,
      ts: this.startTime,
    });
  }

  /** Write a content chunk. */
  write(chunk: string): void {
    if (this.closed) throw new Error("Stream is already closed");
    this.contentChunks.push(chunk);
    this.writeLine({
      type: "chunk",
      content: chunk,
      idx: this.chunkIdx++,
    });
  }

  /** Add a trust claim to the stream. */
  addClaim(content: string, trust: number, opts?: Partial<Claim>): void {
    if (this.closed) throw new Error("Stream is already closed");
    const claim: Partial<Claim> = { c: content, t: trust, ai: true, ...opts };
    this.claims.push(claim);
    this.writeLine({
      type: "claim",
      content,
      trust,
      idx: this.chunkIdx,
    });
  }

  /** Close the stream and finalize AKF metadata. Returns the AKF unit. */
  async close(): Promise<AKFUnit> {
    if (this.closed) throw new Error("Stream is already closed");
    this.closed = true;

    // If no explicit claims, create one from the full content
    if (this.claims.length === 0) {
      const fullContent = this.contentChunks.join("");
      const preview =
        fullContent.length > 100
          ? fullContent.slice(0, 100) + "..."
          : fullContent;
      this.claims.push({
        c: preview,
        t: this.options.trustScore ?? 0.7,
        ai: true,
      });
    }

    const unit = createMulti(this.claims, {
      model: this.options.model,
      agent: this.options.agent,
      label: this.options.classification,
      at: this.startTime,
    });

    // Write end line
    this.writeLine({
      type: "end",
      claims: this.claims.map((c) => ({ c: c.c, t: c.t })),
      ts: nowISO(),
      totalChunks: this.chunkIdx,
    });

    // Close log stream
    await new Promise<void>((resolve) => this.logStream.end(resolve));

    return unit;
  }

  private writeLine(data: AKFStreamLine): void {
    this.logStream.write(JSON.stringify(data) + "\n");
  }
}

/**
 * Create a new AKF stream for a file.
 *
 * Usage:
 * ```ts
 * const s = stream('output.md', { model: 'gpt-4o' });
 * for await (const chunk of llm.generate()) {
 *   s.write(chunk);
 * }
 * const unit = await s.close();
 * ```
 */
export function stream(filepath: string, options: StreamOptions = {}): AKFStream {
  return new AKFStream(filepath, options);
}
