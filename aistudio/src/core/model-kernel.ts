import type { HDSIR } from "./hds-ir.js";
import { extractRelations, jaccard, LanguageRelation, semanticTokens } from "./semantic.js";

export interface ModelContribution {
  relation: string;
  delta: number;
  evidence: string[];
}

export interface ModelCandidate {
  id: string;
  text: string;
  evidenceText?: string;
}

export interface CandidateDifference {
  candidateId: string;
  difference: number;
  contributions: ModelContribution[];
}

export interface ModelCheckpoint {
  stage: string;
  candidateDifferences: Array<[string, number]>;
}

export interface ModelEvaluation {
  candidateDifferences: CandidateDifference[];
  bestCandidateId: string | null;
  tiedCandidateIds: string[];
  checkpoints: ModelCheckpoint[];
}

/**
 * MINIDORA能力模型核のTypeScript射影。
 * 厳密言語模型確率とは独立して、文脈・関係・履歴から成立差を作る。
 */
export class CapabilityModelKernel {
  evaluate(ir: HDSIR, candidates: ModelCandidate[], history: string[] = []): ModelEvaluation {
    if (candidates.length === 0) {
      return { candidateDifferences: [], bestCandidateId: null, tiedCandidateIds: [], checkpoints: [] };
    }
    const requestTokens = semanticTokens(ir.data || ir.normalized);
    const requestRelations = ir.relations;
    const historyRows = history.slice(-8).map((text, index) => ({ distance: history.slice(-8).length - index, tokens: semanticTokens(text) }));

    const differences: CandidateDifference[] = [];
    const checkpoints: ModelCheckpoint[] = [];

    for (const candidate of candidates) {
      const candidateTokens = semanticTokens(candidate.evidenceText || candidate.text);
      const candidateRelations = extractRelations(candidate.evidenceText || candidate.text, ir.outputLanguage);
      const contributions: ModelContribution[] = [];

      const shared = [...requestTokens].filter(token => candidateTokens.has(token));
      if (shared.length > 0) {
        contributions.push({ relation: "意味連続", delta: shared.length, evidence: shared.slice(0, 24).map(token => `共有:${token}`) });
      }

      const relationContribution = scoreRelations(requestRelations, candidateRelations);
      if (relationContribution.delta !== 0) contributions.push(relationContribution);

      let historyScore = 0;
      const historyEvidence: string[] = [];
      for (const row of historyRows) {
        const similarity = jaccard(row.tokens, candidateTokens);
        if (similarity <= 0) continue;
        const weight = Math.max(1, 5 - row.distance);
        const delta = Math.max(1, Math.round(similarity * weight * 4));
        historyScore += delta;
        historyEvidence.push(`履歴距離${row.distance}:${similarity.toFixed(2)}`);
      }
      if (historyScore > 0) contributions.push({ relation: "履歴近接", delta: historyScore, evidence: historyEvidence });

      const outputFit = scoreOutputFit(ir, candidate.text);
      if (outputFit.delta !== 0) contributions.push(outputFit);

      // 根拠テキストが明示されている候補を、表層だけの候補より僅かに優先する。
      if (candidate.evidenceText?.trim()) {
        contributions.push({ relation: "根拠接続", delta: 1, evidence: ["Capability構造Data由来"] });
      }

      differences.push({
        candidateId: candidate.id,
        difference: contributions.reduce((sum, item) => sum + item.delta, 0),
        contributions,
      });
    }

    checkpoints.push({
      stage: "STANDARD_RELATIONS",
      candidateDifferences: differences.map(item => [item.candidateId, item.difference]),
    });

    const max = Math.max(...differences.map(item => item.difference));
    const top = differences.filter(item => item.difference === max).map(item => item.candidateId).sort();
    return {
      candidateDifferences: differences,
      bestCandidateId: top.length === 1 ? top[0] : null,
      tiedCandidateIds: top.length > 1 ? top : [],
      checkpoints,
    };
  }
}

function scoreRelations(base: LanguageRelation[], candidates: LanguageRelation[]): ModelContribution {
  let score = 0;
  const evidence: string[] = [];
  for (const left of base) {
    for (const right of candidates) {
      if (left.type !== right.type) continue;
      const sameDirection = overlap(left.subject, right.subject) && overlap(left.object, right.object);
      const reverseDirection = overlap(left.subject, right.object) && overlap(left.object, right.subject);
      if (sameDirection) {
        if (left.positive === right.positive) {
          score += 4;
          evidence.push(`有向一致:${left.type}`);
        } else {
          score -= 3;
          evidence.push(`肯否不一致:${left.type}`);
        }
      } else if (reverseDirection) {
        score -= 2;
        evidence.push(`逆向:${left.type}`);
      }
    }
  }
  return { relation: "言語関係整合", delta: score, evidence };
}

function scoreOutputFit(ir: HDSIR, text: string): ModelContribution {
  let score = 0;
  const evidence: string[] = [];
  if (ir.output.format === "json") {
    try {
      JSON.parse(text);
      score += 4;
      evidence.push("JSON妥当");
    } catch {
      score -= 4;
      evidence.push("JSON不成立");
    }
  } else if (ir.output.format === "bullets") {
    const lines = text.split("\n").filter(Boolean);
    if (lines.length > 0 && lines.every(line => /^[-*・]\s*/.test(line))) {
      score += 3;
      evidence.push("箇条書き形式一致");
    }
  } else if (ir.output.format === "table") {
    if (/\|.+\|/.test(text)) {
      score += 3;
      evidence.push("表形式一致");
    }
  }

  if (ir.output.maxLines) {
    const lines = text.split("\n").filter(Boolean).length;
    if (lines <= ir.output.maxLines) {
      score += 2;
      evidence.push(`行数境界:${lines}<=${ir.output.maxLines}`);
    } else {
      score -= 2;
      evidence.push(`行数超過:${lines}>${ir.output.maxLines}`);
    }
  }
  if (ir.output.concise && text.length <= 240) {
    score += 1;
    evidence.push("簡潔要求一致");
  }
  return { relation: "出力条件整合", delta: score, evidence };
}

function overlap(a: string[], b: string[]): boolean {
  const right = new Set(b);
  return a.some(item => right.has(item));
}
