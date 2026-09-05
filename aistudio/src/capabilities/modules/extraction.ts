import type { CapabilityModule } from "../interface.js";
import type { CapabilityContext, CapabilityResult } from "../../types.js";
import type { HDSIR, SemanticOperation } from "../../core/hds-ir.js";
import { extractRelations } from "../../core/semantic.js";
import { uniquePreserveOrder, valueToText } from "../../core/text-utils.js";

export class ExtractionModule implements CapabilityModule {
  readonly id = "extraction";
  readonly name = "情報抽出Capability";
  readonly description = "観測可能な文字列から日付・数値・URL・メール・関係等を決定論的に抽出する";
  readonly operations = ["extraction"] as const;

  canHandle(_ir: HDSIR, operation: SemanticOperation) {
    return operation.kind === "extraction"
      ? { score: 1, reason: "HDS-IRが情報抽出作用を要求" }
      : { score: 0, reason: "非対象作用" };
  }

  async execute(context: CapabilityContext): Promise<CapabilityResult> {
    const text = valueToText(context.input.previousValue ?? context.input.text).trim();
    if (!text) throw new Error("抽出対象Dataがありません");

    const requested = new Set((context.input.operation.arguments.fields as string[] | undefined) ?? []);
    const all = requested.size === 0;
    const wants = (name: string) => all || requested.has(name);

    const emails = wants("email") ? uniquePreserveOrder(text.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi) ?? []) : [];
    const urls = wants("url") ? uniquePreserveOrder((text.match(/https?:\/\/[^\s<>()\[\]{}"']+/gi) ?? []).map(trimUrlPunctuation)) : [];
    const dates = wants("date") ? uniquePreserveOrder([
      ...(text.match(/\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b/g) ?? []),
      ...(text.match(/\b\d{4}年\s*\d{1,2}月\s*\d{1,2}日\b/g) ?? []),
      ...(text.match(/\b\d{1,2}月\s*\d{1,2}日\b/g) ?? []),
    ]) : [];
    const money = wants("money") ? uniquePreserveOrder([
      ...(text.match(/(?:¥|￥|\$|€|£)\s*\d[\d,]*(?:\.\d+)?/g) ?? []),
      ...(text.match(/\b\d[\d,]*(?:\.\d+)?\s*(?:円|ドル|USD|JPY|EUR|ユーロ)\b/gi) ?? []),
    ]) : [];
    const numbers = wants("number") ? uniquePreserveOrder(text.match(/(?<![\w.])[-+]?\d+(?:\.\d+)?(?:%|％)?(?![\w.])/g) ?? []) : [];
    const keyValues = wants("key_value") ? extractKeyValues(text) : [];
    const bullets = wants("bullet") ? uniquePreserveOrder(text.split(/\r?\n/).map(line => line.trim()).filter(line => /^(?:[-*・]|\d+[.)])\s*/.test(line)).map(line => line.replace(/^(?:[-*・]|\d+[.)])\s*/, ""))) : [];
    const relations = wants("relation") ? extractRelations(text, context.ir.inputLanguage) : [];
    const personCandidates = uniquePreserveOrder([
      ...[...text.matchAll(/([一-龥々]{2,6})(?:さん|氏|教授|先生|社長|首相|大統領)/g)].map(match => match[1]),
      ...[...text.matchAll(/\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b/g)].map(match => match[1]),
    ]);

    const result = {
      emails,
      urls,
      dates,
      money,
      numbers,
      keyValues,
      bullets,
      personCandidates,
      relations,
    };

    const plain = renderPlain(result);
    const json = JSON.stringify(result, null, 2);
    const candidates = context.ir.output.format === "json" ? [json] : [plain, `抽出結果は次のとおりです。\n${plain}`];

    return {
      kind: "extraction",
      value: result,
      textCandidates: candidates,
      evidenceText: json,
      stateText: json,
    };
  }
}

function extractKeyValues(text: string): Array<{ key: string; value: string }> {
  const out: Array<{ key: string; value: string }> = [];
  const seen = new Set<string>();
  for (const line of text.split(/\r?\n/)) {
    const match = line.match(/^\s*([^:：=]{1,80})\s*[:：=]\s*(.+?)\s*$/);
    if (!match) continue;
    const key = match[1].trim();
    const value = match[2].trim();
    const signature = `${key}\u001f${value}`;
    if (!seen.has(signature)) {
      seen.add(signature);
      out.push({ key, value });
    }
  }
  return out;
}

function renderPlain(result: Record<string, any>): string {
  const rows: string[] = [];
  const labels: Record<string, string> = {
    emails: "メール", urls: "URL", dates: "日付", money: "金額", numbers: "数値",
    keyValues: "Key-Value", bullets: "箇条書き", personCandidates: "人名候補", relations: "関係",
  };
  for (const [key, value] of Object.entries(result)) {
    if (!Array.isArray(value) || value.length === 0) continue;
    if (key === "relations") {
      rows.push(`${labels[key]}: ${value.map(item => `${item.type}(${item.subject.join("/")}→${item.object.join("/")})`).join(", ")}`);
    } else if (key === "keyValues") {
      rows.push(`${labels[key]}: ${value.map(item => `${item.key}=${item.value}`).join(", ")}`);
    } else {
      rows.push(`${labels[key]}: ${value.join(", ")}`);
    }
  }
  return rows.length ? rows.join("\n") : "指定された抽出対象はData内に見つかりませんでした。";
}

function trimUrlPunctuation(value: string): string {
  return value.replace(/[.,。、！？!?]+$/g, "");
}
