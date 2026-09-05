import type { TraceRecord, TraceStage } from "../types.js";

/** 実行経路から逐次Traceを構成する。後付け説明生成には使わない。 */
export class TraceGovernance {
  private readonly traces = new Map<string, TraceRecord>();
  constructor(private readonly maxRecords = 500) {}

  createTrace(input: string, sessionId: string): TraceRecord {
    const traceId = `trace_${globalThis.crypto.randomUUID()}`;
    const trace: TraceRecord = {
      traceId,
      timestamp: Date.now(),
      originalInput: input,
      normalizedInput: "",
      sessionId,
      semanticIR: null,
      operationPlan: null,
      selectedCapability: null,
      candidateCapabilities: [],
      modulesExecuted: [],
      moduleInputs: {},
      moduleOutputs: {},
      stages: [],
      modelEvaluation: null,
      languageModel: null,
      externalDataAccess: [],
      sources: [],
      validationResult: false,
      finalComposition: "",
      failures: [],
      warnings: [],
    };
    this.traces.set(traceId, trace);
    this.trim();
    return trace;
  }

  getTrace(traceId: string): TraceRecord | undefined {
    return this.traces.get(traceId);
  }

  recordCandidate(traceId: string, id: string, confidence: number, reason?: string): void {
    const trace = this.traces.get(traceId);
    if (!trace) return;
    trace.candidateCapabilities.push({ id, confidence, reason });
  }

  stage(traceId: string, stage: Omit<TraceStage, "timestamp">): void {
    const trace = this.traces.get(traceId);
    if (!trace) return;
    trace.stages.push({ ...stage, timestamp: Date.now() });
  }

  private trim(): void {
    while (this.traces.size > this.maxRecords) {
      const first = this.traces.keys().next().value as string | undefined;
      if (!first) break;
      this.traces.delete(first);
    }
  }
}
