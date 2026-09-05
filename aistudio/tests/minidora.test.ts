import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";
import { MinidoraCore } from "../src/core/minidora.js";
import { StrictLanguageModel } from "../src/core/language-model.js";
import { ExactRational } from "../src/core/exact-rational.js";
import type { SearchProvider, SearchResult } from "../src/types.js";

const req = (text: string, sessionId = "test") => ({ id: `req_${Math.random()}`, text, timestamp: Date.now(), sessionId });

class TestSearchProvider implements SearchProvider {
  readonly id = "search.test";
  isConfigured() { return true; }
  async search(query: string): Promise<SearchResult[]> {
    return [
      { title: `${query}資料A`, url: "https://unit.invalid/a", snippet: `${query}の第一資料。重要事項A。`, provider: this.id, fetchedAt: 1 },
      { title: `${query}資料B`, url: "https://unit.invalid/b", snippet: `${query}の第二資料。重要事項B。`, provider: this.id, fetchedAt: 2 },
    ];
  }
}

describe("MINIDORA core nuclei", () => {
  it("strict language model keeps each conditional distribution exactly normalized", () => {
    const model = StrictLanguageModel.train(["abc", "abd"], 3, 1);
    const audit = model.audit();
    expect(audit.ok).toBe(true);
    expect(audit.minimumEndProbability.compare(ExactRational.zero())).toBeGreaterThan(0);
  });

  it("strict language model state is deterministic across document order", () => {
    const a = StrictLanguageModel.train(["alpha", "beta"], 3, 1);
    const b = StrictLanguageModel.train(["beta", "alpha"], 3, 1);
    expect(a.stateHash()).toBe(b.stateHash());
  });

  it("strict language model survives serialize / restore", () => {
    const model = StrictLanguageModel.train(["abc", "abd"], 3, 1);
    const restored = StrictLanguageModel.restore(model.serialize());
    expect(restored.stateHash()).toBe(model.stateHash());
    expect(restored.sequenceProbability("abc").toJSON()).toEqual(model.sequenceProbability("abc").toJSON());
  });

  it("calculation uses exact parser", async () => {
    const core = new MinidoraCore();
    expect((await core.process(req("2+3"))).text).toBe("5");
    expect((await core.process(req("(4+6)/2"))).text).toBe("5");
    expect((await core.process(req("0.1+0.2"))).text).toBe("0.3");
  });

  it("calculation rejects code-like input instead of evaluating it", async () => {
    const core = new MinidoraCore();
    const response = await core.process(req("process.exit(1)+2"));
    expect(response.status).not.toBe("ok");
  });

  it("summarization preserves source-derived sentences and actually compresses", async () => {
    const core = new MinidoraCore();
    const source = "第一文は背景です。第二文は補足です。第三文は重要事項です。第四文も重要事項を説明します。";
    const response = await core.process(req(`要約して: ${source}`));
    expect(response.status).toBe("ok");
    expect(response.text.length).toBeLessThan(source.length);
    expect(source).toContain(response.text.split(" ")[0]);
  });

  it("extracts observed email/url/date without invention", async () => {
    const core = new MinidoraCore();
    const response = await core.process(req("日付とメールとURLを抽出して: 2026-09-05 連絡 a@b.jp https://openai.com/"));
    expect(response.text).toContain("2026-09-05");
    expect(response.text).toContain("a@b.jp");
    expect(response.text).toContain("https://openai.com/");
  });

  it("keeps Instruction P free of concrete Data values", async () => {
    const core = new MinidoraCore();
    const response = await core.process(req("日付を抜いてJSONにして: 会議は2026-09-05です。"));
    const trace = core.traceManager.getTrace(response.traceId)!;
    expect(JSON.stringify(trace.operationPlan?.steps[0].instructionP)).not.toContain("2026-09-05");
    expect(JSON.stringify(trace.moduleInputs["step_01"])).toContain("2026-09-05");
  });

  it("compares explicit numeric Data deterministically", async () => {
    const core = new MinidoraCore();
    const response = await core.process(req("10と7を比較して"));
    expect(response.status).toBe("ok");
    expect(response.text).toContain("10 > 7");
  });

  it("chains extraction -> transformation and trace matches actual order", async () => {
    const core = new MinidoraCore();
    const response = await core.process(req("日付を抜いてJSONにして: 会議は2026-09-05です。"));
    expect(response.status).toBe("ok");
    expect(JSON.parse(response.text).dates).toEqual(["2026-09-05"]);
    const trace = core.traceManager.getTrace(response.traceId)!;
    expect(trace.modulesExecuted).toEqual(["extraction", "transformation"]);
    expect(trace.operationPlan?.steps.map(step => step.moduleId)).toEqual(trace.modulesExecuted);
  });

  it("follow-up transformation consumes structured session result", async () => {
    const core = new MinidoraCore();
    await core.process(req("日付を抽出して: 会議は2026-09-05です。", "follow"));
    const response = await core.process(req("それをJSONにして", "follow"));
    expect(JSON.parse(response.text).dates).toEqual(["2026-09-05"]);
  });

  it("search is explicitly held when provider is not configured", async () => {
    const core = new MinidoraCore();
    const response = await core.process(req("OpenAIを検索して"));
    expect(response.status).toBe("held");
    expect(response.text).toBe("検索Providerが設定されていません");
    expect(response.sources).toEqual([]);
  });

  it("search provider can be connected without changing Core", async () => {
    const core = new MinidoraCore({ searchProvider: new TestSearchProvider() });
    const response = await core.process(req("OpenAIを検索して"));
    expect(response.status).toBe("ok");
    expect(response.sources).toHaveLength(2);
    const trace = core.traceManager.getTrace(response.traceId)!;
    expect(trace.externalDataAccess).toEqual(["search:search.test:OpenAI"]);
  });

  it("search -> summarization is a real multi-module plan", async () => {
    const core = new MinidoraCore({ searchProvider: new TestSearchProvider() });
    const response = await core.process(req("OpenAIを検索して2行でまとめて"));
    expect(response.status).toBe("ok");
    const trace = core.traceManager.getTrace(response.traceId)!;
    expect(trace.modulesExecuted).toEqual(["search", "summarization"]);
    expect(response.sources).toHaveLength(2);
  });

  it("unknown world knowledge request does not invent an answer", async () => {
    const core = new MinidoraCore();
    const response = await core.process(req("OpenAIについて教えて"));
    expect(response.status).toBe("held");
    expect(response.text).toBe("外部Data Providerが設定されていません");
  });

  it("conversation identity is handled without external knowledge", async () => {
    const core = new MinidoraCore();
    const response = await core.process(req("あなたは誰"));
    expect(response.status).toBe("ok");
    expect(response.text).toContain("MINIDORA");
    const trace = core.traceManager.getTrace(response.traceId)!;
    expect(trace.modulesExecuted).toEqual(["conversation"]);
  });

  it("conversation can recall actual prior turn only within the session", async () => {
    const core = new MinidoraCore();
    await core.process(req("こんにちは", "memory"));
    const response = await core.process(req("さっき何言った？", "memory"));
    expect(response.text).toContain("こんにちは");
  });

  it("trace contains semantic IR, plan, capability-model evaluation and language-model choice", async () => {
    const core = new MinidoraCore();
    const response = await core.process(req("2+3"));
    const trace = core.traceManager.getTrace(response.traceId)!;
    expect(trace.semanticIR?.schema).toBe("minidora.hds-semantic-ir.ts.v1");
    expect(trace.operationPlan?.schema).toBe("minidora.operation-plan.ts.v1");
    expect(trace.modelEvaluation).not.toBeNull();
    expect(trace.languageModel?.stateHash).toBeTruthy();
    expect(trace.stages.map(stage => stage.stage)).toContain("FINAL_VALIDATION");
  });

  it("health is derived from actual nuclei and registry", () => {
    const core = new MinidoraCore();
    const health = core.health();
    expect(health.ok).toBe(true);
    expect(health.strictLanguageModel.ready).toBe(true);
    expect(health.capabilities).toBeGreaterThanOrEqual(8);
    expect(health.searchProvider).toBe(false);
  });
});

describe("forbidden fallback audit", () => {
  it("MINIDORA source path contains no eval/new Function/MockSearchProvider", () => {
    const root = path.resolve("src");
    const files = walk(root).filter(file => /\.(ts|tsx)$/.test(file) && !file.endsWith("routes.ts"));
    const source = files.map(file => fs.readFileSync(file, "utf8")).join("\n");
    expect(source).not.toMatch(/\beval\s*\(/);
    expect(source).not.toContain("new Function");
    expect(source).not.toContain("MockSearchProvider");
    expect(source).not.toContain("example.com");
  });

  it("Gemini generateContent exists only in isolated API comparator", () => {
    const coreSource = fs.readFileSync(path.resolve("src/core/minidora.ts"), "utf8");
    const routes = fs.readFileSync(path.resolve("src/api/routes.ts"), "utf8");
    expect(coreSource).not.toMatch(/Gemini|GoogleGenAI|generateContent/);
    expect(routes).toContain('apiRouter.post("/gemini"');
    expect(routes).toContain("generateContent");
    const chatSection = routes.split('apiRouter.post("/chat"')[1].split('apiRouter.get("/trace')[0];
    expect(chatSection).not.toMatch(/GoogleGenAI|generateContent/);
  });
});

function walk(dir: string): string[] {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap(entry => {
    const full = path.join(dir, entry.name);
    return entry.isDirectory() ? walk(full) : [full];
  });
}
