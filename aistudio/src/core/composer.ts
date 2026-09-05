import type { CapabilityResult, TraceRecord } from "../types.js";
import type { HDSIR } from "./hds-ir.js";
import { StrictLanguageModel } from "./language-model.js";
import { CapabilityModelKernel, ModelCandidate } from "./model-kernel.js";

export interface CompositionResult {
  text: string;
  modelEvaluation: ReturnType<CapabilityModelKernel["evaluate"]>;
  probability: { numerator: string; denominator: string };
}

/**
 * Capability結果を最終言語表層へ落とす。
 * 能力核の成立差を一次順位、厳密言語模型確率を同率候補の表面選択に使う。
 */
export class ResponseComposer {
  constructor(
    private readonly capabilityModel: CapabilityModelKernel,
    private readonly languageModel: StrictLanguageModel,
  ) {}

  compose(ir: HDSIR, result: CapabilityResult, history: string[], trace: TraceRecord): CompositionResult {
    const texts = [...new Set(result.textCandidates.map(value => String(value)).filter(value => value.trim()))];
    if (texts.length === 0) throw new Error("Capabilityが表面候補を返しませんでした");

    const candidates: ModelCandidate[] = texts.map((text, index) => ({
      id: `surface_${String(index + 1).padStart(2, "0")}`,
      text,
      evidenceText: result.evidenceText,
    }));
    const modelEvaluation = this.capabilityModel.evaluate(ir, candidates, history);
    const scoreMap = new Map(modelEvaluation.candidateDifferences.map(item => [item.candidateId, item.difference]));
    const maximum = Math.max(...candidates.map(candidate => scoreMap.get(candidate.id) ?? 0));
    const shortlist = candidates.filter(candidate => (scoreMap.get(candidate.id) ?? 0) === maximum);

    const languageChoice = this.languageModel.bestCandidate("", shortlist.map(candidate => candidate.text));
    if (!languageChoice) throw new Error("言語表層候補を選択できませんでした");

    trace.modelEvaluation = modelEvaluation;
    trace.languageModel = {
      stateHash: this.languageModel.stateHash(),
      chosenCandidate: languageChoice.text,
      chosenProbability: languageChoice.probability.toJSON(),
    };

    return {
      text: languageChoice.text,
      modelEvaluation,
      probability: languageChoice.probability.toJSON(),
    };
  }
}
