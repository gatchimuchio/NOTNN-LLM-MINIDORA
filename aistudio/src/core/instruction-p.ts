import type { HDSIR, SemanticOperation } from "./hds-ir.js";

/** 日本語命令形P。具体Data値を埋め込まず「どう作用するか」を保持する。 */
export interface InstructionP {
  schema: "minidora.instruction-p.ts.v1";
  name: string;
  target: string;
  conditions: string[];
  references: string[];
  action: string[];
  update: string[];
  boundaries: string[];
  stop: string[];
  evidence: string[];
}

/** Pとは分離された運用Data包。 */
export interface DataEnvelope {
  schema: "minidora.data-envelope.ts.v1";
  source: "request-data" | "previous-result" | "session-data" | "reference-data";
  observed: boolean;
  value: unknown;
  text: string;
  provenance: string[];
}

export function lowerOperationToInstructionP(ir: HDSIR, operation: SemanticOperation): InstructionP {
  const common = {
    schema: "minidora.instruction-p.ts.v1" as const,
    target: "現在Data",
    conditions: ["入力作用がHDS semantic IRで確定"],
    references: [] as string[],
    action: [] as string[],
    update: ["作用結果を作業状態へ保持"],
    boundaries: ["Data値を命令Pへ埋め込まない", "未観測Dataを推測で補完しない"],
    stop: ["作用結果が閉包した時点で停止"],
    evidence: [`HDSIR:${operation.kind}`, `instruction:${operation.instruction}`],
  };

  switch (operation.kind) {
    case "calculation":
      return { ...common, name: "厳密計算", action: ["数式Token化", "構文解析", "有理数計算", "検証"], boundaries: [...common.boundaries, "許可演算子以外を実行しない", "動的コード評価禁止"] };
    case "summarization":
      return { ...common, name: "抽出要約", action: ["文分割", "重要度評価", "冗長性抑制", "原順序再結合"] };
    case "extraction":
      return { ...common, name: "情報抽出", action: ["型別照合", "明示関係抽出", "重複除去"], boundaries: [...common.boundaries, "観測文字列以外を生成しない"] };
    case "transformation":
      return { ...common, name: "Data変換", action: ["出力形式選択", "決定論的変換", "形式検証"] };
    case "search":
      return { ...common, name: "外部検索参照", references: ir.referenceQueries, action: ["Provider選択", "Data取得", "由来結合"], boundaries: [...common.boundaries, "Provider未設定時は保留", "架空Source禁止"] };
    case "knowledge_reference":
      return { ...common, name: "外部Data参照", references: ir.referenceQueries, action: ["Provider選択", "参照取得", "由来結合"], boundaries: [...common.boundaries, "外部文を模型知識へ自動帰属しない"] };
    case "comparison":
      return { ...common, name: "比較", action: ["比較対象分離", "比較軸照合", "差分形成"] };
    case "conversation":
      return { ...common, name: "会話状態作用", references: ["session-state"], action: ["発話種別照合", "会話状態参照", "応答候補形成"] };
  }
}
