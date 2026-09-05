import type { CapabilityModule } from "../interface.js";
import type { CapabilityContext, CapabilityResult } from "../../types.js";
import type { HDSIR, SemanticOperation } from "../../core/hds-ir.js";
import { uniquePreserveOrder, valueToText } from "../../core/text-utils.js";

export class TransformationModule implements CapabilityModule {
  readonly id = "transformation";
  readonly name = "変換Capability";
  readonly description = "構造化Dataまたは本文をJSON・箇条書き・表・行形式へ決定論的に変換する";
  readonly operations = ["transformation"] as const;

  canHandle(_ir: HDSIR, operation: SemanticOperation) {
    return operation.kind === "transformation"
      ? { score: 1, reason: "HDS-IRが変換作用を要求" }
      : { score: 0, reason: "非対象作用" };
  }

  async execute(context: CapabilityContext): Promise<CapabilityResult> {
    const mode = String(context.input.operation.arguments.mode ?? context.ir.output.format ?? "text");
    const inputValue = context.input.previousValue ?? context.input.text;
    const text = valueToText(inputValue).trim();
    if (!text && inputValue == null) throw new Error("変換対象Dataがありません");

    let output: string;
    let value: unknown = inputValue;

    switch (mode) {
      case "json":
        output = toJson(inputValue, text);
        try { value = JSON.parse(output); } catch { value = { text }; }
        break;
      case "bullets":
        output = toBullets(inputValue, text);
        value = output.split("\n").filter(Boolean).map(line => line.replace(/^[-*・]\s*/, ""));
        break;
      case "table":
        output = toMarkdownTable(inputValue, text);
        value = output;
        break;
      case "line_numbers":
      case "lines":
        output = normalizedLines(text).map((line, index) => `${index + 1}. ${line}`).join("\n");
        value = output;
        break;
      case "dedupe":
        output = uniquePreserveOrder(normalizedLines(text)).join("\n");
        value = output;
        break;
      case "whitespace":
        output = text.split(/\r?\n/).map(line => line.replace(/[\t ]+/g, " ").trim()).filter(Boolean).join("\n");
        value = output;
        break;
      case "uppercase":
        output = text.toUpperCase();
        value = output;
        break;
      case "lowercase":
        output = text.toLowerCase();
        value = output;
        break;
      default:
        output = text;
        value = inputValue;
    }

    return {
      kind: "transformation",
      value,
      textCandidates: [output],
      evidenceText: valueToText(inputValue),
      stateText: output,
    };
  }
}

function toJson(input: unknown, text: string): string {
  if (input !== null && typeof input === "object") return JSON.stringify(input, null, 2);
  const keyValues = parseKeyValueLines(text);
  if (keyValues.length > 0) return JSON.stringify(Object.fromEntries(keyValues.map(row => [row.key, row.value])), null, 2);
  const lines = normalizedLines(text);
  return JSON.stringify(lines.length > 1 ? { lines } : { text }, null, 2);
}

function toBullets(input: unknown, text: string): string {
  if (Array.isArray(input)) return input.map(item => `- ${valueToText(item).trim()}`).filter(line => line !== "- ").join("\n");
  if (input && typeof input === "object") {
    return Object.entries(input as Record<string, unknown>).map(([key, value]) => `- ${key}: ${inlineValue(value)}`).join("\n");
  }
  return normalizedLines(text).map(line => `- ${line.replace(/^[-*・]\s*/, "")}`).join("\n");
}

function toMarkdownTable(input: unknown, text: string): string {
  const rows: Array<Record<string, unknown>> = [];
  if (Array.isArray(input) && input.every(item => item && typeof item === "object" && !Array.isArray(item))) {
    rows.push(...input as Array<Record<string, unknown>>);
  } else if (input && typeof input === "object" && !Array.isArray(input)) {
    const record = input as Record<string, unknown>;
    for (const [key, value] of Object.entries(record)) rows.push({ 項目: key, 値: inlineValue(value) });
  } else {
    const kv = parseKeyValueLines(text);
    if (kv.length > 0) rows.push(...kv.map(item => ({ 項目: item.key, 値: item.value })));
    else rows.push(...normalizedLines(text).map((line, index) => ({ 行: index + 1, 内容: line })));
  }
  if (rows.length === 0) return "";
  const headers = uniquePreserveOrder(rows.flatMap(row => Object.keys(row)));
  const escape = (value: unknown) => inlineValue(value).replace(/\|/g, "\\|").replace(/\n/g, " ");
  return [
    `| ${headers.join(" | ")} |`,
    `| ${headers.map(() => "---").join(" | ")} |`,
    ...rows.map(row => `| ${headers.map(header => escape(row[header] ?? "")).join(" | ")} |`),
  ].join("\n");
}

function parseKeyValueLines(text: string): Array<{ key: string; value: string }> {
  const out: Array<{ key: string; value: string }> = [];
  for (const line of normalizedLines(text)) {
    const match = line.match(/^([^:：=]{1,80})\s*[:：=]\s*(.+)$/);
    if (match) out.push({ key: match[1].trim(), value: match[2].trim() });
  }
  return out;
}

function normalizedLines(text: string): string[] {
  const byLine = text.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
  if (byLine.length > 1) return byLine;
  return text.split(/(?<=[。！？!?])\s*/).map(line => line.trim()).filter(Boolean);
}

function inlineValue(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean" || typeof value === "bigint") return String(value);
  return JSON.stringify(value);
}
