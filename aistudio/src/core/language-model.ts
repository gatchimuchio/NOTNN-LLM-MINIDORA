import { ExactRational } from "./exact-rational.js";

export const BOS = "<BOS>";
export const EOS = "<EOS>";
export const UNK = "<UNK>";

export interface LanguageModelAudit {
  ok: boolean;
  contextsChecked: number;
  minimumEndProbability: ExactRational;
  reasons: string[];
}

export interface ConditionalDistribution {
  context: string[];
  probabilities: Map<string, ExactRational>;
}

export interface StrictLanguageModelState {
  schema: "minidora.strict-language-model.ts.v1";
  order: number;
  alpha: string;
  vocabulary: string[];
  formationDocuments: number;
  counts: Array<[string, Array<[string, string]>]>;
}

/**
 * MINIDORAの非ニューラル厳密言語模型核。
 * Unicode文字n-gram + finite-state。Capabilityの意味判断とは分離する。
 */
export class StrictLanguageModel {
  readonly order: number;
  readonly alpha: bigint;
  readonly vocabulary: string[];
  readonly formationDocuments: number;

  private readonly counts: Map<string, Map<string, bigint>>;
  private readonly vocabularySet: Set<string>;

  private constructor(
    order: number,
    alpha: bigint,
    vocabulary: string[],
    counts: Map<string, Map<string, bigint>>,
    formationDocuments: number,
  ) {
    if (!Number.isInteger(order) || order < 1) throw new Error("言語模型次数は1以上である必要があります");
    if (alpha < 1n) throw new Error("加算平滑化は1以上である必要があります");
    if (!vocabulary.includes(EOS) || !vocabulary.includes(UNK)) throw new Error("語彙にはEOS/UNKが必要です");
    if (vocabulary.includes(BOS)) throw new Error("BOSを出力語彙に含められません");
    this.order = order;
    this.alpha = alpha;
    this.vocabulary = [...vocabulary].sort();
    this.vocabularySet = new Set(this.vocabulary);
    this.counts = counts;
    this.formationDocuments = formationDocuments;
  }

  static restore(state: StrictLanguageModelState): StrictLanguageModel {
    if (state.schema !== "minidora.strict-language-model.ts.v1") throw new Error("未知の言語模型state schemaです");
    const counts = new Map<string, Map<string, bigint>>();
    for (const [context, rows] of state.counts) {
      counts.set(context, new Map(rows.map(([token, count]) => [token, BigInt(count)])));
    }
    return new StrictLanguageModel(
      state.order,
      BigInt(state.alpha),
      [...state.vocabulary],
      counts,
      state.formationDocuments,
    );
  }

  static train(documents: Iterable<string>, order = 3, alpha = 1): StrictLanguageModel {
    const observed = new Set<string>();
    const rawCounts = new Map<string, Map<string, bigint>>();
    let documentCount = 0;

    const add = (context: string[], token: string) => {
      const key = StrictLanguageModel.contextKey(context);
      let row = rawCounts.get(key);
      if (!row) {
        row = new Map();
        rawCounts.set(key, row);
      }
      row.set(token, (row.get(token) ?? 0n) + 1n);
    };

    const maxHistory = Math.max(0, order - 1);
    for (const doc of documents) {
      const normalized = normalizeLanguage(String(doc));
      const chars = Array.from(normalized);
      chars.forEach(char => observed.add(char));
      let history = Array(maxHistory).fill(BOS) as string[];
      for (const token of [...chars, EOS]) {
        for (let width = 0; width < order; width += 1) {
          add(width === 0 ? [] : history.slice(-width), token);
        }
        if (maxHistory > 0) history = [...history, token].slice(-maxHistory);
      }
      documentCount += 1;
    }

    // 空Corpusでも厳密分布を成立させるため、EOS/UNKを語彙へ置く。
    const vocabulary = [...observed, UNK, EOS].sort();
    return new StrictLanguageModel(order, BigInt(alpha), vocabulary, rawCounts, documentCount);
  }

  addDocuments(documents: Iterable<string>): StrictLanguageModel {
    const mergedDocuments: string[] = [];
    // 旧状態から原文は復元できないため、既存countへ直接加算して新状態を形成する。
    const observed = new Set(this.vocabulary.filter(token => token !== UNK && token !== EOS));
    const counts = cloneCounts(this.counts);
    let added = 0;
    const maxHistory = Math.max(0, this.order - 1);

    const add = (context: string[], token: string) => {
      const key = StrictLanguageModel.contextKey(context);
      let row = counts.get(key);
      if (!row) {
        row = new Map();
        counts.set(key, row);
      }
      row.set(token, (row.get(token) ?? 0n) + 1n);
    };

    for (const doc of documents) {
      const normalized = normalizeLanguage(String(doc));
      mergedDocuments.push(normalized);
      const chars = Array.from(normalized);
      chars.forEach(char => observed.add(char));
      let history = Array(maxHistory).fill(BOS) as string[];
      for (const token of [...chars, EOS]) {
        for (let width = 0; width < this.order; width += 1) add(width === 0 ? [] : history.slice(-width), token);
        if (maxHistory > 0) history = [...history, token].slice(-maxHistory);
      }
      added += 1;
    }

    return new StrictLanguageModel(
      this.order,
      this.alpha,
      [...observed, UNK, EOS],
      counts,
      this.formationDocuments + added,
    );
  }

  distribution(prefix = ""): ConditionalDistribution {
    const history = this.encode(prefix);
    const context = this.effectiveContext(history);
    const row = this.counts.get(StrictLanguageModel.contextKey(context)) ?? new Map<string, bigint>();
    const rawTotal = [...row.values()].reduce((sum, value) => sum + value, 0n);
    const denominator = rawTotal + this.alpha * BigInt(this.vocabulary.length);
    const probabilities = new Map<string, ExactRational>();
    for (const token of this.vocabulary) {
      probabilities.set(token, new ExactRational((row.get(token) ?? 0n) + this.alpha, denominator));
    }
    return { context, probabilities };
  }

  nextTokenProbability(prefix: string, token: string): ExactRational {
    const mapped = this.vocabularySet.has(token) ? token : UNK;
    return this.distribution(prefix).probabilities.get(mapped) ?? ExactRational.zero();
  }

  sequenceProbability(text: string): ExactRational {
    return this.probabilityFromHistory([], this.encode(text));
  }

  conditionalSequenceProbability(prefix: string, continuation: string): ExactRational {
    const maxHistory = Math.max(0, this.order - 1);
    const encodedPrefix = this.encode(prefix);
    const history = maxHistory > 0 ? encodedPrefix.slice(-maxHistory) : [];
    return this.probabilityFromHistory(history, this.encode(continuation));
  }

  bestCandidate(prefix: string, candidates: string[]): { text: string; probability: ExactRational } | null {
    const unique = [...new Set(candidates.map(value => String(value)).filter(Boolean))];
    if (unique.length === 0) return null;
    let bestText = unique[0];
    let bestProbability = this.conditionalSequenceProbability(prefix, bestText);
    for (const candidate of unique.slice(1)) {
      const probability = this.conditionalSequenceProbability(prefix, candidate);
      const cmp = probability.compare(bestProbability);
      if (cmp > 0 || (cmp === 0 && candidate.localeCompare(bestText, "ja") < 0)) {
        bestText = candidate;
        bestProbability = probability;
      }
    }
    return { text: bestText, probability: bestProbability };
  }

  audit(): LanguageModelAudit {
    const reasons: string[] = [];
    const contextKeys = new Set<string>([...this.counts.keys(), ""]);
    let minimumEnd: ExactRational | null = null;
    let checked = 0;
    for (const key of contextKeys) {
      const context = StrictLanguageModel.contextFromKey(key);
      const row = this.counts.get(key) ?? new Map<string, bigint>();
      const rawTotal = [...row.values()].reduce((sum, value) => sum + value, 0n);
      const denominator = rawTotal + this.alpha * BigInt(this.vocabulary.length);
      const values = this.vocabulary.map(token => new ExactRational((row.get(token) ?? 0n) + this.alpha, denominator));
      const sum = ExactRational.sum(values);
      if (!sum.equals(ExactRational.one())) reasons.push(`条件分布が1ではありません: ${key}`);
      const end = new ExactRational((row.get(EOS) ?? 0n) + this.alpha, denominator);
      if (end.compare(ExactRational.zero()) <= 0) reasons.push(`EOS確率が正ではありません: ${key}`);
      if (minimumEnd === null || end.compare(minimumEnd) < 0) minimumEnd = end;
      // contextを読むことで復元可能性の最低限も検証する。
      if (context.length >= this.order) reasons.push(`文脈長が次数以上です: ${key}`);
      checked += 1;
    }
    return {
      ok: reasons.length === 0,
      contextsChecked: checked,
      minimumEndProbability: minimumEnd ?? ExactRational.one(),
      reasons,
    };
  }

  serialize(): StrictLanguageModelState {
    const rows: Array<[string, Array<[string, string]>]> = [...this.counts.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([context, row]) => [
        context,
        [...row.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([token, count]) => [token, count.toString()] as [string, string]),
      ]);
    return {
      schema: "minidora.strict-language-model.ts.v1",
      order: this.order,
      alpha: this.alpha.toString(),
      vocabulary: [...this.vocabulary],
      formationDocuments: this.formationDocuments,
      counts: rows,
    };
  }

  stateHash(): string {
    return fnv1a64(JSON.stringify(this.serialize()));
  }

  private probabilityFromHistory(initialHistory: string[], tokens: string[]): ExactRational {
    let probability = ExactRational.one();
    const maxHistory = Math.max(0, this.order - 1);
    let history = [...initialHistory];
    for (const token of [...tokens, EOS]) {
      const context = this.effectiveContext(history);
      const key = StrictLanguageModel.contextKey(context);
      const row = this.counts.get(key) ?? new Map<string, bigint>();
      const rawTotal = [...row.values()].reduce((sum, value) => sum + value, 0n);
      const denominator = rawTotal + this.alpha * BigInt(this.vocabulary.length);
      probability = probability.multiply(new ExactRational((row.get(token) ?? 0n) + this.alpha, denominator));
      if (maxHistory > 0) history = [...history, token].slice(-maxHistory);
    }
    return probability;
  }

  private encode(text: string): string[] {
    return Array.from(normalizeLanguage(text)).map(char => this.vocabularySet.has(char) ? char : UNK);
  }

  private effectiveContext(history: string[]): string[] {
    const maxHistory = Math.max(0, this.order - 1);
    if (maxHistory === 0) return [];
    const tail = history.slice(-maxHistory);
    const padded = [...Array(Math.max(0, maxHistory - tail.length)).fill(BOS), ...tail];
    for (let width = maxHistory; width >= 0; width -= 1) {
      const context = width === 0 ? [] : padded.slice(-width);
      if (this.counts.has(StrictLanguageModel.contextKey(context))) return context;
    }
    return [];
  }

  private static contextKey(context: string[]): string { return context.join("\u001f"); }
  private static contextFromKey(key: string): string[] { return key === "" ? [] : key.split("\u001f"); }
}

export function normalizeLanguage(text: string): string {
  return String(text).normalize("NFKC").replace(/\r\n?/g, "\n");
}

function cloneCounts(source: Map<string, Map<string, bigint>>): Map<string, Map<string, bigint>> {
  const out = new Map<string, Map<string, bigint>>();
  for (const [key, row] of source) out.set(key, new Map(row));
  return out;
}

function fnv1a64(text: string): string {
  let hash = 0xcbf29ce484222325n;
  const prime = 0x100000001b3n;
  const mask = 0xffffffffffffffffn;
  for (const char of Array.from(text)) {
    hash ^= BigInt(char.codePointAt(0) ?? 0);
    hash = (hash * prime) & mask;
  }
  return hash.toString(16).padStart(16, "0");
}

/**
 * 最小基底模型。ここに世界知識を埋め込まない。
 * 文面選択に必要な機能語・応答骨格だけを形成する。
 */
export function createBaseLanguageModel(): StrictLanguageModel {
  return StrictLanguageModel.train([
    "確認しました。",
    "計算結果は次のとおりです。",
    "抽出結果は次のとおりです。",
    "要点は次のとおりです。",
    "現在のDataからは確認できません。",
    "検索Providerが設定されていません。",
    "処理可能なCapabilityがありません。",
    "根拠を確認できないため確定しません。",
    "入力されたDataに基づいて処理しました。",
    "MINIDORAは非ニューラル・非Transformer型の言語処理系です。",
    "どういたしまして。",
    "こんにちは。MINIDORAです。",
  ], 3, 1);
}
