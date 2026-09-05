import type { CapabilityModule } from "../interface.js";
import type { CapabilityContext, CapabilityResult } from "../../types.js";
import type { HDSIR, SemanticOperation } from "../../core/hds-ir.js";
import { extractRelations, jaccard, semanticTokens } from "../../core/semantic.js";
import { splitSentences, valueToText } from "../../core/text-utils.js";

export class SummarizationModule implements CapabilityModule {
  readonly id = "summarization";
  readonly name = "要約Capability";
  readonly description = "語頻度・関係密度・位置・冗長性を用いる決定論的抽出要約";
  readonly operations = ["summarization"] as const;

  canHandle(_ir: HDSIR, operation: SemanticOperation) {
    return operation.kind === "summarization"
      ? { score: 1, reason: "HDS-IRが要約作用を要求" }
      : { score: 0, reason: "非対象作用" };
  }

  async execute(context: CapabilityContext): Promise<CapabilityResult> {
    const content = valueToText(context.input.previousValue ?? context.input.text).trim();
    if (!content) throw new Error("要約対象Dataがありません");

    const sentences = splitSentences(content);
    if (sentences.length <= 1 || content.length < 20) {
      return {
        kind: "summarization",
        value: { sentences, selected: sentences, sourceLength: content.length },
        textCandidates: [content],
        evidenceText: content,
        stateText: content,
        warnings: ["Dataが短いため抽出圧縮を適用していません"],
      };
    }

    const tokenFrequency = new Map<string, number>();
    const sentenceTokens = sentences.map(sentence => semanticTokens(sentence));
    for (const tokens of sentenceTokens) {
      for (const token of tokens) tokenFrequency.set(token, (tokenFrequency.get(token) ?? 0) + 1);
    }

    const rawScores = sentences.map((sentence, index) => {
      const tokens = sentenceTokens[index];
      const lexical = [...tokens].reduce((sum, token) => sum + Math.log1p(tokenFrequency.get(token) ?? 0), 0);
      const relationBonus = extractRelations(sentence, context.ir.inputLanguage).length * 2.5;
      const numericBonus = /\d/.test(sentence) ? 0.75 : 0;
      const firstBonus = index === 0 ? 2 : index === 1 ? 0.75 : 0;
      const lengthPenalty = sentence.length > 240 ? (sentence.length - 240) / 120 : 0;
      return lexical + relationBonus + numericBonus + firstBonus - lengthPenalty;
    });

    const requested = context.ir.output.maxSentences ?? context.ir.output.maxLines;
    const target = Math.max(1, Math.min(sentences.length, requested ?? Math.ceil(Math.sqrt(sentences.length))));
    const selectedIndices: number[] = [];
    const remaining = new Set(sentences.map((_, index) => index));

    // Maximal Marginal Relevance相当。最高情報量だけで同義文が固まらないようにする。
    while (selectedIndices.length < target && remaining.size > 0) {
      let bestIndex: number | null = null;
      let bestScore = Number.NEGATIVE_INFINITY;
      for (const index of remaining) {
        const redundancy = selectedIndices.length === 0
          ? 0
          : Math.max(...selectedIndices.map(chosen => jaccard(sentenceTokens[index], sentenceTokens[chosen])));
        const score = rawScores[index] - redundancy * 4;
        if (score > bestScore || (score === bestScore && (bestIndex === null || index < bestIndex))) {
          bestScore = score;
          bestIndex = index;
        }
      }
      if (bestIndex === null) break;
      selectedIndices.push(bestIndex);
      remaining.delete(bestIndex);
    }

    selectedIndices.sort((a, b) => a - b);
    const selected = selectedIndices.map(index => sentences[index]);
    const compact = selected.join(context.ir.output.maxLines ? "\n" : " ").trim();
    const bullet = selected.map(sentence => `- ${sentence}`).join("\n");
    const candidates = context.ir.output.format === "bullets" ? [bullet] : [compact, `要点は次のとおりです。\n${compact}`];

    return {
      kind: "summarization",
      value: {
        sourceSentenceCount: sentences.length,
        selectedIndices,
        selected,
        scores: rawScores.map(value => Number(value.toFixed(4))),
      },
      textCandidates: candidates,
      evidenceText: selected.join("\n"),
      stateText: compact,
    };
  }
}
