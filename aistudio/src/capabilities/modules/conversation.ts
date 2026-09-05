import type { CapabilityModule } from "../interface.js";
import type { CapabilityContext, CapabilityResult } from "../../types.js";
import type { HDSIR, SemanticOperation } from "../../core/hds-ir.js";

export class ConversationModule implements CapabilityModule {
  readonly id = "conversation";
  readonly name = "会話Capability";
  readonly description = "会話内状態と明示された自己情報だけを使う決定論的会話作用";
  readonly operations = ["conversation"] as const;

  canHandle(_ir: HDSIR, operation: SemanticOperation) {
    return operation.kind === "conversation"
      ? { score: 1, reason: "HDS-IRが会話作用を要求" }
      : { score: 0, reason: "非対象作用" };
  }

  async execute(context: CapabilityContext): Promise<CapabilityResult> {
    const text = context.normalizedText;
    let candidates: string[];
    let value: unknown;

    if (/(こんにちは|おはよう|こんばんは|はじめまして)/.test(text)) {
      candidates = ["こんにちは。MINIDORAです。", "こんにちは。"];
      value = { speechAct: "greeting" };
    } else if (/(ありがとう|どうも)/.test(text)) {
      candidates = ["どういたしまして。", "こちらこそ、ありがとうございます。"];
      value = { speechAct: "thanks" };
    } else if (/(あなたは誰|君は誰|何者|MINIDORAとは|ミニドラとは)/i.test(text)) {
      candidates = [
        "MINIDORAは、ニューラルネットワークやTransformerを中核に使わず、厳密言語模型核・能力模型核・Capability・外部Data参照を分離して動作する言語処理系です。",
        "私はMINIDORAです。非ニューラル・非Transformer型の言語処理系として、言語模型と能力作用を分離して処理します。",
      ];
      value = { speechAct: "self-description", system: "MINIDORA" };
    } else if (/(何ができる|できること|Capability|機能を教えて)/i.test(text)) {
      const modules = [
        "計算", "要約", "情報抽出", "テキスト変換", "比較", "会話",
        context.searchProvider.isConfigured() ? "外部検索" : "外部検索(Provider未設定)",
        context.referenceProvider.isConfigured() ? "外部Data参照" : "外部Data参照(Provider未設定)",
      ];
      candidates = [`現在利用できるCapabilityは、${modules.join("、")}です。`];
      value = { speechAct: "capability-list", modules };
    } else if (/(さっき|前に|直前).*(言った|話した|何)/.test(text)) {
      const previous = context.session.turns.at(-1)?.input;
      if (previous) {
        candidates = [`直前の入力は「${previous}」です。`];
        value = { speechAct: "session-recall", previousInput: previous };
      } else {
        candidates = ["このセッションには参照できる直前の入力がありません。"];
        value = { speechAct: "session-recall", previousInput: null };
      }
    } else if (/^(はい|いいえ|そう|なるほど|了解|わかった)[。！!\s]*$/.test(text)) {
      candidates = ["確認しました。"];
      value = { speechAct: "acknowledgement" };
    } else {
      throw new Error("会話作用として閉包できませんでした");
    }

    return {
      kind: "conversation",
      value,
      textCandidates: candidates,
      evidenceText: JSON.stringify(value),
      stateText: candidates[0],
    };
  }
}
