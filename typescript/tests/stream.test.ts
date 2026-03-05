import { describe, it, expect, afterEach } from "vitest";
import { existsSync, unlinkSync, readFileSync } from "node:fs";
import { stream, AKFStream } from "../src/index.js";

const TMP_FILE = "/tmp/test-akf-stream.md";
const TMP_AKFL = "/tmp/test-akf-stream.md.akfl";

function cleanup() {
  for (const f of [TMP_FILE, TMP_AKFL]) {
    if (existsSync(f)) unlinkSync(f);
  }
}

afterEach(cleanup);

describe("AKFStream", () => {
  it("creates a stream and writes chunks", async () => {
    const s = stream(TMP_FILE, { model: "gpt-4o" });
    s.write("Hello ");
    s.write("world");
    const unit = await s.close();

    expect(unit.claims.length).toBeGreaterThan(0);
    expect(unit.model).toBe("gpt-4o");
  });

  it("creates .akfl log file", async () => {
    const s = stream(TMP_FILE, { model: "test-model" });
    s.write("chunk 1");
    s.write("chunk 2");
    await s.close();

    expect(existsSync(TMP_AKFL)).toBe(true);
    const lines = readFileSync(TMP_AKFL, "utf-8").trim().split("\n");
    expect(lines.length).toBe(4); // start + 2 chunks + end

    const start = JSON.parse(lines[0]);
    expect(start.type).toBe("start");
    expect(start.model).toBe("test-model");

    const end = JSON.parse(lines[lines.length - 1]);
    expect(end.type).toBe("end");
    expect(end.totalChunks).toBe(2);
  });

  it("supports explicit claims", async () => {
    const s = new AKFStream(TMP_FILE, { model: "gpt-4o" });
    s.write("Revenue grew 12%");
    s.addClaim("Revenue grew 12%", 0.95, { src: "SEC filing" });
    const unit = await s.close();

    expect(unit.claims.length).toBe(1);
    expect(unit.claims[0].t).toBe(0.95);
  });

  it("throws when writing to closed stream", async () => {
    const s = stream(TMP_FILE);
    await s.close();
    expect(() => s.write("too late")).toThrow("already closed");
  });

  it("uses custom trust score", async () => {
    const s = stream(TMP_FILE, { trustScore: 0.9 });
    s.write("content");
    const unit = await s.close();
    expect(unit.claims[0].t).toBe(0.9);
  });
});
