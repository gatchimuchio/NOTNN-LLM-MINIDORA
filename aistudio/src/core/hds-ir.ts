import { extractRelations, LanguageRelation, semanticTokens } from "./semantic.js";
import { normalizeLanguage } from "./language-model.js";

export type OperationKind =
  | "calculation"
  | "summarization"
  | "extraction"
  | "transformation"
  | "search"
  | "knowledge_reference"
  | "conversation"
  | "comparison";

export interface SemanticOperation {
  kind: OperationKind;
  instruction: string;
  position: number;
  target?: string;
  arguments: Record<string, string | number | boolean | string[]>;
}

export interface OutputRequirement {
  format: "text" | "json" | "bullets" | "table" | "lines";
  maxSentences?: number;
  maxLines?: number;
  concise: boolean;
}

export interface HDSResidual {
  type: "unknown_operation" | "missing_data" | "missing_reference" | "ambiguous" | "unsupported";
  reason: string;
  reopenWhen?: string;
}

export interface HDSCoordinates {
  target: {
    entity: string[];
    currentState: string[];
    context: string[];
  };
  purpose: {
    necessity: string[];
    targetState: string[];
    evaluationRule: string[];
  };
  means: {
    actions: string[];
    boundaries: string[];
    validations: string[];
  };
}

export interface HDSIR {
  schema: "minidora.hds-semantic-ir.ts.v1";
  original: string;
  normalized: string;
  inputLanguage: string;
  outputLanguage: string;
  coordinates: HDSCoordinates;
  operations: SemanticOperation[];
  data: string;
  referenceQueries: string[];
  relations: LanguageRelation[];
  output: OutputRequirement;
  residuals: HDSResidual[];
  executable: boolean;
}

/**
 * 公開MINIDORAのHDS semantic frontendに相当する決定論的射影。
 * HDS-IR自体をLLM核や計算中間表現とは扱わない。
 */
export function compileHDSIR(rawInput: string): HDSIR {
  const original = String(rawInput);
  const normalized = normalizeLanguage(original).trim();
  const language = detectLanguage(normalized);
  const output = detectOutputRequirement(normalized);
  const operations = detectOperations(normalized, output);
  const data = extractOperationalData(normalized, operations);
  const referenceQueries = operations
    .filter(op => op.kind === "search" || op.kind === "knowledge_reference")
    .map(op => String(op.arguments.query ?? op.target ?? "").trim())
    .filter(Boolean);
  const relations = extractRelations(data || normalized, language);
  const residuals: HDSResidual[] = [];

  if (operations.length === 0) {
    residuals.push({
      type: "unknown_operation",
      reason: "要求から実行可能な作用を確定できませんでした",
      reopenWhen: "Capabilityまたは明示的な処理要求が追加されたとき",
    });
  }

  for (const operation of operations) {
    if (["summarization", "extraction", "transformation"].includes(operation.kind) && !data.trim()) {
      residuals.push({
        type: "missing_data",
        reason: `${operation.kind}に必要なDataが入力内で閉じていません`,
        reopenWhen: "会話状態または明示Dataが与えられたとき",
      });
    }
    if ((operation.kind === "search" || operation.kind === "knowledge_reference") && !String(operation.arguments.query ?? "").trim()) {
      residuals.push({ type: "missing_reference", reason: "参照対象を抽出できませんでした" });
    }
  }

  const coordinates = buildCoordinates(normalized, operations, data, output);
  const executable = operations.length > 0 && !residuals.some(r => r.type === "unknown_operation");

  return {
    schema: "minidora.hds-semantic-ir.ts.v1",
    original,
    normalized,
    inputLanguage: language,
    outputLanguage: language,
    coordinates,
    operations,
    data,
    referenceQueries,
    relations,
    output,
    residuals: dedupeResiduals(residuals),
    executable,
  };
}

function detectOperations(text: string, output: OutputRequirement): SemanticOperation[] {
  const found: SemanticOperation[] = [];
  const push = (kind: OperationKind, position: number, instruction: string, args: Record<string, any> = {}, target?: string) => {
    if (found.some(item => item.kind === kind && Math.abs(item.position - position) < 3)) return;
    found.push({ kind, position, instruction, arguments: args, target });
  };

  // 計算は記号形と自然言語指示の両方を見る。
  const expression = extractExpression(text);
  const calcWord = /(計算して|計算せよ|求めて|算出して)/.exec(text);
  if (expression && (calcWord || looksLikePureExpression(text))) {
    push("calculation", calcWord?.index ?? 0, calcWord?.[0] ?? "数式", { expression });
  }

  for (const match of text.matchAll(/(要約して|まとめて|短くして|要点(?:を)?(?:出して|教えて)|要約せよ)/g)) {
    push("summarization", match.index ?? 0, match[0]);
  }

  for (const match of text.matchAll(/(抽出して|抜き出して|抜いて|抜き取って|取り出して|拾って|列挙して)/g)) {
    const fields = detectExtractionFields(text);
    push("extraction", match.index ?? 0, match[0], { fields });
  }

  for (const match of text.matchAll(/(JSON(?:形式)?にして|JSON化して|箇条書きにして|表(?:形式)?にして|行番号(?:を)?(?:付けて|つけて)|重複(?:行)?を?(?:消して|除いて)|空白(?:を)?(?:整理して|整えて)|大文字にして|小文字にして)/gi)) {
    const mode = transformationMode(match[0]);
    push("transformation", match.index ?? 0, match[0], { mode });
  }

  for (const match of text.matchAll(/(検索して|検索せよ|調べて|調査して|ウェブで探して|Webで探して)/gi)) {
    const query = extractReferenceQuery(text, match[0], match.index ?? 0);
    push("search", match.index ?? 0, match[0], { query }, query);
  }

  // 「について教えて」は外部事実要求になり得るため参照要求へ置く。
  for (const match of text.matchAll(/(.{1,100}?)(?:について|とは)(?:教えて|説明して|知りたい|何[?？]?)/g)) {
    const query = cleanQuery(match[1]);
    if (query && !isSelfQuery(query)) push("knowledge_reference", match.index ?? 0, match[0], { query }, query);
  }

  for (const match of text.matchAll(/(比較して|比べて|違い(?:は|を)|どちらが|どっちが)/g)) {
    push("comparison", match.index ?? 0, match[0]);
  }

  if (isConversationInput(text)) {
    push("conversation", firstConversationPosition(text), "会話");
  }

  // output指定だけで変換要求が暗黙になっている場合。
  if (output.format !== "text" && !found.some(op => op.kind === "transformation")) {
    const pos = text.search(/JSON|箇条書き|表形式|行番号/i);
    if (pos >= 0) push("transformation", pos, "出力形式", { mode: output.format });
  }

  // 「検索して3行でまとめて」等は原文上の順序を保つ。
  return found.sort((a, b) => a.position - b.position || operationOrder(a.kind) - operationOrder(b.kind));
}

function extractOperationalData(text: string, operations: SemanticOperation[]): string {
  if (operations.length === 1 && operations[0].kind === "calculation") {
    return String(operations[0].arguments.expression ?? "");
  }

  // 明示Data境界を最優先する。
  const markers = [
    /(?:以下|次|本文|文章|テキスト|データ|Data)\s*(?:を|は)?\s*[:：]\s*([\s\S]+)$/i,
    /(?:以下|次)\s*(?:を|の文章を|のテキストを)?\s*(?:要約|抽出|変換|JSON化)?(?:して|せよ)?\s*[\n]+([\s\S]+)$/i,
  ];
  for (const pattern of markers) {
    const match = text.match(pattern);
    if (match?.[1]?.trim()) return match[1].trim();
  }

  // コロン/改行の後ろが十分長い場合は命令とDataの境界とみなす。
  const boundary = text.search(/[:：\n]/);
  if (boundary >= 0) {
    const tail = text.slice(boundary + 1).trim();
    if (tail) return stripTrailingInstructions(tail);
  }

  // 「Xを要約して」のXを取り出す。検索語はDataではなく参照要求なので除外。
  if (operations.some(op => ["summarization", "extraction", "transformation", "comparison"].includes(op.kind))) {
    let candidate = text;
    const instructionPatterns = [
      /(?:を)?(?:要約して|まとめて|短くして|要約せよ)/g,
      /(?:から)?[^。！？]{0,30}?(?:抽出して|抜き出して|抜いて|抜き取って|取り出して|拾って|列挙して)/g,
      /(?:を)?(?:JSON(?:形式)?にして|JSON化して|箇条書きにして|表(?:形式)?にして|行番号(?:を)?(?:付けて|つけて)|大文字にして|小文字にして)/gi,
      /(?:を)?(?:比較して|比べて)/g,
    ];
    for (const pattern of instructionPatterns) candidate = candidate.replace(pattern, " ");
    candidate = candidate.replace(/^(?:この|以下の|次の)?(?:文章|テキスト|データ)?\s*/i, "").trim();
    candidate = candidate.replace(/\s+/g, " ").trim();
    // 命令しか残っていない短文はDataなし。
    if (candidate.length >= 2 && !isInstructionOnly(candidate) && !isAnaphoraOnly(candidate)) return candidate;
  }
  return "";
}

function extractExpression(text: string): string | null {
  const normalized = text.replace(/×/g, "*").replace(/÷/g, "/").replace(/−/g, "-");
  const candidates = normalized.match(/(?:[-+]?\d+(?:\.\d+)?|\.\d+|[()+\-*/^\s])+/g) ?? [];
  const expression = candidates
    .map(value => value.trim())
    .filter(value => /\d/.test(value) && /[+\-*/^]/.test(value))
    .sort((a, b) => b.length - a.length)[0];
  return expression ? expression.replace(/\s+/g, "") : null;
}

function extractReferenceQuery(text: string, instruction: string, position: number): string {
  const before = text.slice(0, position).trim();
  const after = text.slice(position + instruction.length).trim();
  // 「OpenAIを検索して」の形。
  if (before) {
    const cleaned = cleanQuery(before.replace(/(?:を|について)$/g, ""));
    if (cleaned && !isInstructionOnly(cleaned)) return cleaned;
  }
  // 「検索して: OpenAI」「検索して OpenAI」の形。
  const cleanedAfter = cleanQuery(after.replace(/^[:：\s]+/, "").replace(/(?:を)?(?:\d+行で)?(?:要約して|まとめて).*$/g, ""));
  return cleanedAfter;
}

function cleanQuery(value: string): string {
  return value
    .replace(/^(?:これ|それ|この|その|以下|次)\s*/g, "")
    .replace(/(?:について|とは)$/g, "")
    .replace(/[。！？?]+$/g, "")
    .trim();
}

function detectExtractionFields(text: string): string[] {
  const fields: Array<[string, RegExp]> = [
    ["email", /メール|email|e-mail/i],
    ["url", /URL|リンク/i],
    ["date", /日付|日時|年月日/i],
    ["number", /数値|数字|数量/i],
    ["money", /金額|価格|円|ドル/i],
    ["key_value", /key.?value|キー.?バリュー|項目と値/i],
    ["relation", /関係|因果|依存/i],
    ["bullet", /箇条書き|項目/i],
  ];
  const result = fields.filter(([, pattern]) => pattern.test(text)).map(([name]) => name);
  return result.length ? result : ["email", "url", "date", "number", "money", "key_value", "relation", "bullet"];
}

function transformationMode(text: string): string {
  if (/JSON/i.test(text)) return "json";
  if (/箇条書き/.test(text)) return "bullets";
  if (/表/.test(text)) return "table";
  if (/行番号/.test(text)) return "line_numbers";
  if (/重複/.test(text)) return "dedupe";
  if (/空白/.test(text)) return "whitespace";
  if (/大文字/.test(text)) return "uppercase";
  if (/小文字/.test(text)) return "lowercase";
  return "text";
}

function detectOutputRequirement(text: string): OutputRequirement {
  let format: OutputRequirement["format"] = "text";
  if (/JSON/i.test(text)) format = "json";
  else if (/箇条書き/.test(text)) format = "bullets";
  else if (/表(?:形式)?/.test(text)) format = "table";
  else if (/行番号/.test(text)) format = "lines";

  const sentenceMatch = text.match(/(\d+)\s*(?:文|センテンス)(?:以内|程度|で)/);
  const lineMatch = text.match(/(\d+)\s*行(?:以内|程度|で)/);
  return {
    format,
    maxSentences: sentenceMatch ? Number(sentenceMatch[1]) : undefined,
    maxLines: lineMatch ? Number(lineMatch[1]) : undefined,
    concise: /(短く|簡潔|要点|ざっくり)/.test(text),
  };
}

function buildCoordinates(text: string, operations: SemanticOperation[], data: string, output: OutputRequirement): HDSCoordinates {
  const dataTokens = [...semanticTokens(data)];
  const requestTokens = [...semanticTokens(text)];
  const actionNames = operations.map(op => op.kind);
  return {
    target: {
      entity: dataTokens.slice(0, 32),
      currentState: data ? ["Data:observed"] : ["Data:unobserved"],
      context: requestTokens.slice(0, 48),
    },
    purpose: {
      necessity: actionNames,
      targetState: [output.format, output.concise ? "concise" : "standard"],
      evaluationRule: ["source-boundary", "deterministic", "trace-consistency"],
    },
    means: {
      actions: actionNames,
      boundaries: ["P/Data分離", "外部Dataは由来保持", "不明は確定しない"],
      validations: ["module-result", "source-provenance", "trace-path"],
    },
  };
}

function detectLanguage(text: string): string {
  const ja = (text.match(/[ぁ-んァ-ヶ一-龥々]/g) ?? []).length;
  const latin = (text.match(/[A-Za-z]/g) ?? []).length;
  return ja >= latin ? "自然言語:ja" : "自然言語:en";
}

function isConversationInput(text: string): boolean {
  if (/^(こんにちは|おはよう|こんばんは|ありがとう|どうも|よろしく|はじめまして)[。！!\s]*$/.test(text)) return true;
  if (/(あなたは誰|MINIDORAとは|ミニドラとは|君は誰|何者|何ができる|できること|Capability|機能を教えて)/i.test(text)) return true;
  if (/(さっき|前に|直前).*(言った|話した|何)/.test(text)) return true;
  if (/^(はい|いいえ|そう|なるほど|了解|わかった)[。！!\s]*$/.test(text)) return true;
  return false;
}

function firstConversationPosition(text: string): number {
  const values = ["こんにちは", "おはよう", "こんばんは", "ありがとう", "あなたは誰", "MINIDORA", "ミニドラ", "さっき", "前に", "直前"];
  return values.map(value => text.indexOf(value)).filter(index => index >= 0).sort((a, b) => a - b)[0] ?? 0;
}

function isSelfQuery(query: string): boolean {
  return /(MINIDORA|ミニドラ|あなた|君)/i.test(query);
}

function looksLikePureExpression(text: string): boolean {
  return /^[\s\d.+\-*/^()×÷−]+$/.test(text) && /\d/.test(text) && /[+\-*/^×÷−]/.test(text);
}

function isAnaphoraOnly(text: string): boolean {
  return /^(?:これ|それ|あれ|この文章|その文章|これを|それを|上の(?:文章|結果)|直前の(?:文章|結果))$/.test(text.trim());
}

function isInstructionOnly(text: string): boolean {
  return /^(?:要約|まとめ|抽出|変換|検索|調査|JSON|箇条書き|表|計算|して|してください|せよ|教えて|調べて|短く|この文章|以下|次)+[。！!\s]*$/i.test(text);
}

function stripTrailingInstructions(text: string): string {
  return text.replace(/\s*(?:\d+行で)?(?:要約して|まとめて|JSONにして|箇条書きにして)[。！!]*$/g, "").trim();
}

function operationOrder(kind: OperationKind): number {
  const order: OperationKind[] = ["search", "knowledge_reference", "calculation", "comparison", "extraction", "summarization", "transformation", "conversation"];
  return order.indexOf(kind);
}

function dedupeResiduals(items: HDSResidual[]): HDSResidual[] {
  const seen = new Set<string>();
  return items.filter(item => {
    const key = `${item.type}\u001f${item.reason}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
