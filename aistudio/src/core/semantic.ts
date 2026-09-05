import { normalizeLanguage } from "./language-model.js";

export interface LanguageRelation {
  type: string;
  subject: string[];
  object: string[];
  positive: boolean;
  conditions: string[][];
  predicate: string[];
}

const WORD = /[A-Za-z0-9_+\-.]+|[Α-Ωα-ωϐ-Ͽ]+|[ぁ-んァ-ヶー]+|[一-龥々]+/g;
const STOP = new Set([
  "the", "a", "an", "of", "to", "in", "on", "at", "for", "from", "with", "and", "or",
  "is", "are", "was", "were", "be", "been", "being", "which", "what", "who", "when", "where",
  "why", "how", "this", "that", "these", "those", "it", "its", "as", "by", "than", "then",
  "do", "does", "did", "have", "has", "had", "will", "shall", "would", "could", "should",
  "may", "might", "can", "about", "into", "through", "during", "after", "before", "between", "among",
  "following", "statement", "statements", "answer", "answers", "option", "options", "choice", "choices",
  "correct", "incorrect", "true", "false", "most", "least", "likely", "unlikely", "best", "except",
]);

const JAPANESE_FUNCTION_WORDS = new Set([
  "は", "が", "を", "に", "へ", "で", "と", "や", "の", "も", "から", "まで", "より", "について",
  "これ", "それ", "あれ", "この", "その", "あの", "です", "ます", "する", "して", "ください", "下さい",
]);

const SYMBOL_RELATION = /([A-Za-zΑ-Ωα-ωϐ-Ͽ0-9_µμΩ.+\-]+)\s*(->|=>|→|⇒|>=|<=|≥|≤|!=|≠|>|<|=)\s*([A-Za-zΑ-Ωα-ωϐ-Ͽ0-9_µμΩ.+\-]+)/g;
const SYMBOL_TYPES: Record<string, string> = {
  "->": "方向", "=>": "方向", "→": "方向", "⇒": "方向",
  ">": "比較.大", "<": "比較.小", ">=": "比較.以上", "≥": "比較.以上",
  "<=": "比較.以下", "≤": "比較.以下", "=": "等価", "!=": "不同", "≠": "不同",
};

const JAPANESE_RELATIONS: Array<{ type: string; verbs: string[] }> = [
  { type: "因果", verbs: ["引き起こす", "生じさせる", "もたらす", "原因となる"] },
  { type: "増加", verbs: ["増加させる", "高める", "促進する"] },
  { type: "減少", verbs: ["減少させる", "低下させる", "抑える"] },
  { type: "阻害", verbs: ["阻害する", "抑制する", "遮断する"] },
  { type: "活性化", verbs: ["活性化する", "刺激する"] },
  { type: "生成", verbs: ["生成する", "産生する", "作る"] },
  { type: "要求", verbs: ["必要とする", "依存する"] },
  { type: "包含", verbs: ["含む", "包含する"] },
  { type: "使用", verbs: ["使う", "使用する", "利用する"] },
  { type: "防止", verbs: ["防ぐ", "予防する"] },
];

const NEGATIVE = /(?:ではない|じゃない|しない|ない|ず|ぬ)|\b(?:do|does|did|is|are|was|were|can|could|may|might|must|will|would|should|has|have|had)\s+not\b|\bnever\b/i;

export function semanticTokens(text: unknown): Set<string> {
  const raw = normalizeLanguage(String(text));
  const out = new Set<string>();

  for (const m of raw.matchAll(/(?<![A-Za-z0-9_])[-+]?(?:\d+(?:\.\d+)?|\.\d+)(?:\s*(?:\/|\^|\*|×)\s*[-+]?(?:\d+(?:\.\d+)?|\.\d+))?(?![A-Za-z0-9_])/g)) {
    const compact = m[0].replace(/\s+/g, "").replace(/×/g, "*");
    if (compact) out.add(`math:${compact.toLowerCase()}`);
  }

  const words = raw.match(WORD) ?? [];
  for (const original of words) {
    const value = original.toLowerCase().replace(/^[-_.]+|[-_.]+$/g, "");
    if (!value) continue;
    if (/^[+-]?(?:\d+(?:\.\d+)?|\.\d+)$/.test(value)) {
      out.add(value);
      continue;
    }
    if (/^[A-ZΑ-Ω]$/.test(original)) {
      out.add(`sym:${value}`);
      continue;
    }
    if (STOP.has(value) || JAPANESE_FUNCTION_WORDS.has(value) || value.length <= 1) continue;
    out.add(englishStem(value));
  }
  return out;
}

export function semanticSequence(text: string): string[] {
  const raw = normalizeLanguage(text);
  const words = raw.match(WORD) ?? [];
  const out: string[] = [];
  for (const surface of words) {
    const values = [...semanticTokens(surface)].sort();
    out.push(...values);
  }
  return out;
}

export function extractRelations(text: string, language = "自然言語:ja"): LanguageRelation[] {
  const raw = normalizeLanguage(text);
  const units = sentenceUnits(raw);
  const result: LanguageRelation[] = [];
  const seen = new Set<string>();

  const add = (type: string, subjectText: string, objectText: string, predicateText: string, positive: boolean, conditions: string[][]) => {
    const subject = [...semanticTokens(subjectText)].sort();
    const object = [...semanticTokens(objectText)].sort();
    const predicate = [...semanticTokens(predicateText)].sort();
    if (subject.length === 0 || object.length === 0) return;
    const relation: LanguageRelation = { type, subject, object, positive, conditions, predicate };
    const key = JSON.stringify(relation);
    if (!seen.has(key)) {
      seen.add(key);
      result.push(relation);
    }
  };

  for (const unit of units) {
    const conditions = extractConditions(unit);
    const negative = NEGATIVE.test(unit);

    for (const match of unit.matchAll(SYMBOL_RELATION)) {
      add(SYMBOL_TYPES[match[2]] ?? "記号関係", match[1], match[3], match[2], !negative, conditions);
    }

    if (language.startsWith("自然言語:ja") || /[ぁ-んァ-ヶ一-龥]/.test(unit)) {
      for (const definition of JAPANESE_RELATIONS) {
        for (const verb of definition.verbs) {
          const index = unit.indexOf(verb);
          if (index < 0) continue;
          const before = unit.slice(0, index);
          const match = before.match(/(.{1,100}?)(?:が|は)(.{1,100}?)(?:を)?$/);
          if (!match) continue;
          add(definition.type, match[1], match[2], verb, !negative, conditions);
        }
      }
    }

    // 英語の最低限の明示関係。一般文章を語順だけで過剰解釈しない。
    if (/[A-Za-z]/.test(unit)) {
      const patterns: Array<[string, RegExp]> = [
        ["因果", /(.{1,100}?)\s+(?:causes?|produces?|creates?)\s+(.{1,100})/i],
        ["包含", /(.{1,100}?)\s+(?:contains?|includes?)\s+(.{1,100})/i],
        ["要求", /(.{1,100}?)\s+(?:requires?|depends on)\s+(.{1,100})/i],
      ];
      for (const [type, pattern] of patterns) {
        const match = unit.match(pattern);
        if (match) add(type, match[1], match[2], match[0], !negative, conditions);
      }
    }
  }
  return result;
}

export function jaccard(a: Iterable<string>, b: Iterable<string>): number {
  const left = new Set(a);
  const right = new Set(b);
  if (left.size === 0 && right.size === 0) return 1;
  let intersection = 0;
  for (const value of left) if (right.has(value)) intersection += 1;
  const union = new Set([...left, ...right]).size;
  return union === 0 ? 0 : intersection / union;
}

export function relationSignature(relation: LanguageRelation): string {
  return JSON.stringify({
    type: relation.type,
    subject: [...relation.subject].sort(),
    object: [...relation.object].sort(),
    positive: relation.positive,
    conditions: relation.conditions.map(row => [...row].sort()),
  });
}

function extractConditions(text: string): string[][] {
  const patterns = [
    /(?:もし|場合|とき|条件下|前提(?:として)?)([^。！？、]{1,120})/g,
    /\b(?:if|when|given|assuming|unless)\s+([^,;.!?]{1,160})/gi,
    /\bunder\s+([^,;.!?]{1,160})/gi,
  ];
  const out: string[][] = [];
  const seen = new Set<string>();
  for (const pattern of patterns) {
    for (const match of text.matchAll(pattern)) {
      const tokens = [...semanticTokens(match[1])].sort();
      if (tokens.length === 0) continue;
      const key = tokens.join("\u001f");
      if (!seen.has(key)) {
        seen.add(key);
        out.push(tokens);
      }
    }
  }
  return out;
}

function sentenceUnits(text: string): string[] {
  const value = normalizeLanguage(text);
  const pieces: string[] = [];
  let start = 0;
  for (let i = 0; i < value.length; i += 1) {
    const char = value[i];
    let end = "。！？!?\n".includes(char);
    if (char === ".") {
      const leftDigit = i > 0 && /\d/.test(value[i - 1]);
      const rightDigit = i + 1 < value.length && /\d/.test(value[i + 1]);
      end = !(leftDigit && rightDigit);
    }
    if (end) {
      const piece = value.slice(start, i).trim();
      if (piece) pieces.push(...piece.split(/\s*,\s*(?:but|whereas)\s+|\s*;\s*(?:but|whereas)\s+|、?しかし(?:、)?/i).map(v => v.trim()).filter(Boolean));
      start = i + 1;
    }
  }
  const tail = value.slice(start).trim();
  if (tail) pieces.push(tail);
  return pieces.length ? pieces : [value];
}

function englishStem(value: string): string {
  if (!/^[a-z]+$/.test(value)) return value;
  if (value === "species" || value === "series") return value;
  if (value.length > 4 && value.endsWith("ies")) return value.slice(0, -3) + "y";
  if (value.length > 4 && value.endsWith("ing")) return value.slice(0, -3).replace(/([^aeiou])\1$/, "$1");
  if (value.length > 4 && value.endsWith("ied")) return value.slice(0, -3) + "y";
  if (value.length > 4 && value.endsWith("ed")) return value.slice(0, -2).replace(/([^aeiou])\1$/, "$1");
  if (value.length > 3 && value.endsWith("s") && !/(ss|is|us)$/.test(value)) return value.slice(0, -1);
  return value;
}
