import type { CapabilityModule } from "../interface.js";
import type { CapabilityContext, CapabilityResult, Source } from "../../types.js";
import type { HDSIR, SemanticOperation } from "../../core/hds-ir.js";

export class KnowledgeReferenceModule implements CapabilityModule {
  readonly id = "knowledge-reference";
  readonly name = "知識参照Capability";
  readonly description = "外部Data Providerから参照記録を取得し、由来と信頼境界を保持する";
  readonly operations = ["knowledge_reference"] as const;

  canHandle(_ir: HDSIR, operation: SemanticOperation) {
    const query = String(operation.arguments.query ?? operation.target ?? "").trim();
    return query ? { score: 1, reason: "参照対象が閉包済み" } : { score: 0, reason: "参照対象が未閉包" };
  }

  async execute(context: CapabilityContext): Promise<CapabilityResult> {
    const query = String(context.input.operation.arguments.query ?? context.input.operation.target ?? "").trim();
    if (!query) throw new Error("参照対象が空です");
    if (!context.referenceProvider.isConfigured()) throw new Error("外部Data Providerが設定されていません");

    const records = await context.referenceProvider.lookup(query);
    const sources: Source[] = records.flatMap(record => record.source ? [{ ...record.source, fetchedAt: record.fetchedAt, identifier: record.identifier, trustBoundary: record.trustBoundary }] : []);
    if (records.length === 0) {
      return {
        kind: "knowledge_reference",
        value: { query, records: [], text: "現在のDataからは確認できません。" },
        textCandidates: ["現在のDataからは確認できません。"],
        sources,
        externalDataAccess: [`reference:${context.referenceProvider.id}:${query}`],
      };
    }

    const text = records.map((record, index) => `${index + 1}. ${record.content}`).join("\n");
    return {
      kind: "knowledge_reference",
      value: { query, records, text },
      textCandidates: [text, `参照Dataに基づく結果です。\n${text}`],
      evidenceText: text,
      sources,
      externalDataAccess: [`reference:${context.referenceProvider.id}:${query}`],
      stateText: text,
    };
  }
}
