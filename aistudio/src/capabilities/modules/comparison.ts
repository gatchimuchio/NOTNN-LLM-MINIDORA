import type { CapabilityModule } from "../interface.js";
import type { CapabilityContext, CapabilityResult } from "../../types.js";
import type { HDSIR, SemanticOperation } from "../../core/hds-ir.js";
import { semanticTokens } from "../../core/semantic.js";
import { valueToText } from "../../core/text-utils.js";
import { ExactRational } from "../../core/exact-rational.js";

export class ComparisonModule implements CapabilityModule {
  readonly id = "comparison";
  readonly name = "比較Capability";
  readonly description = "数値または二つの明示Dataを決定論的に比較する";
  readonly operations = ["comparison"] as const;

  canHandle(_ir: HDSIR, operation: SemanticOperation) {
    return operation.kind === "comparison"
      ? { score: 0.9, reason: "HDS-IRが比較作用を要求" }
      : { score: 0, reason: "非対象作用" };
  }

  async execute(context: CapabilityContext): Promise<CapabilityResult> {
    const text = valueToText(context.input.previousValue ?? context.input.text).trim();
    if (!text) throw new Error("比較対象Dataがありません");

    const numeric = [...text.matchAll(/[-+]?(?:\d+(?:\.\d+)?|\.\d+)/g)].map(match => match[0]);
    if (numeric.length === 2) {
      const left = ExactRational.fromDecimal(numeric[0]);
      const right = ExactRational.fromDecimal(numeric[1]);
      const cmp = left.compare(right);
      const symbol = cmp > 0 ? ">" : cmp < 0 ? "<" : "=";
      const sentence = `${numeric[0]} ${symbol} ${numeric[1]}`;
      return {
        kind: "comparison",
        value: { left: left.toJSON(), right: right.toJSON(), relation: symbol },
        textCandidates: [sentence, `比較結果: ${sentence}`],
        evidenceText: sentence,
        stateText: sentence,
      };
    }

    const parts = splitPair(text);
    if (!parts) throw new Error("比較対象を二つに分離できませんでした");
    const leftTokens = semanticTokens(parts[0]);
    const rightTokens = semanticTokens(parts[1]);
    const common = [...leftTokens].filter(token => rightTokens.has(token)).sort();
    const leftOnly = [...leftTokens].filter(token => !rightTokens.has(token)).sort();
    const rightOnly = [...rightTokens].filter(token => !leftTokens.has(token)).sort();
    const result = {
      left: parts[0], right: parts[1], common, leftOnly, rightOnly,
    };
    const output = [
      `共通: ${common.join(", ") || "なし"}`,
      `左のみ: ${leftOnly.join(", ") || "なし"}`,
      `右のみ: ${rightOnly.join(", ") || "なし"}`,
    ].join("\n");
    return {
      kind: "comparison",
      value: result,
      textCandidates: [output],
      evidenceText: JSON.stringify(result),
      stateText: output,
    };
  }
}

function splitPair(text: string): [string, string] | null {
  for (const pattern of [/\s+(?:と|vs\.?|VS\.?|対)\s+/i, /\s*[|｜]\s*/, /\n-{3,}\n/]) {
    const parts = text.split(pattern).map(value => value.trim()).filter(Boolean);
    if (parts.length === 2) return [parts[0], parts[1]];
  }
  return null;
}
