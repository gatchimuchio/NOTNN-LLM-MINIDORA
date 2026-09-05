import type { CapabilityModule } from "../interface.js";
import type { CapabilityContext, CapabilityResult, Source } from "../../types.js";
import type { HDSIR, SemanticOperation } from "../../core/hds-ir.js";

export class SearchModule implements CapabilityModule {
  readonly id = "search";
  readonly name = "検索Capability";
  readonly description = "交換可能なSearchProviderから外部Dataを取得し、由来を保持する";
  readonly operations = ["search"] as const;

  canHandle(_ir: HDSIR, operation: SemanticOperation) {
    const query = String(operation.arguments.query ?? operation.target ?? "").trim();
    return query ? { score: 1, reason: "参照対象queryが閉包済み" } : { score: 0, reason: "queryが未閉包" };
  }

  async execute(context: CapabilityContext): Promise<CapabilityResult> {
    const query = String(context.input.operation.arguments.query ?? context.input.operation.target ?? "").trim();
    if (!query) throw new Error("検索queryが空です");
    if (!context.searchProvider.isConfigured()) throw new Error("検索Providerが設定されていません");

    const results = await context.searchProvider.search(query);
    const sources: Source[] = results.map(item => ({
      title: item.title,
      url: item.url,
      snippet: item.snippet,
      provider: item.provider,
      fetchedAt: item.fetchedAt,
      identifier: item.identifier,
      trustBoundary: "external-search-data",
    }));
    if (results.length === 0) {
      return {
        kind: "search",
        value: { query, results: [], text: "現在のDataからは確認できません。" },
        textCandidates: ["現在のDataからは確認できません。"],
        sources: [],
        externalDataAccess: [`search:${context.searchProvider.id}:${query}`],
        stateText: "",
      };
    }

    const text = results.map((item, index) => `${index + 1}. ${item.title}\n${item.snippet}`).join("\n\n");
    return {
      kind: "search",
      value: { query, results, text },
      textCandidates: [text, `「${query}」の参照Dataを取得しました。\n${text}`],
      evidenceText: text,
      sources,
      externalDataAccess: [`search:${context.searchProvider.id}:${query}`],
      stateText: text,
    };
  }
}
