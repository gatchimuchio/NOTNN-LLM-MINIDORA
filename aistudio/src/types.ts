import type { HDSIR, OperationKind, SemanticOperation } from "./core/hds-ir.js";
import type { ModelEvaluation } from "./core/model-kernel.js";
import type { SessionSnapshot } from "./core/state.js";
import type { DataEnvelope, InstructionP } from "./core/instruction-p.js";

export interface MinidoraRequest {
  id: string;
  text: string;
  timestamp: number;
  sessionId?: string;
}

export interface MinidoraResponse {
  id: string;
  requestId: string;
  text: string;
  sources: Source[];
  traceId: string;
  timestamp: number;
  status: "ok" | "unsupported" | "held" | "error";
}

export interface Source {
  title: string;
  url?: string;
  snippet?: string;
  provider: string;
  fetchedAt?: number;
  identifier?: string;
  trustBoundary?: string;
}

export interface SearchProvider {
  readonly id: string;
  isConfigured(): boolean;
  search(query: string): Promise<SearchResult[]>;
}

export interface SearchResult {
  title: string;
  url: string;
  snippet: string;
  provider: string;
  fetchedAt: number;
  identifier?: string;
}

export interface ReferenceProvider {
  readonly id: string;
  isConfigured(): boolean;
  lookup(query: string): Promise<ReferenceRecord[]>;
}

export interface ReferenceRecord {
  identifier: string;
  provider: string;
  fetchedAt: number;
  target: string;
  content: string;
  source?: Source;
  trustBoundary: string;
  modified: boolean;
}

export interface CapabilityStepInput {
  operation: SemanticOperation;
  text: string;
  previousValue?: unknown;
  previousText?: string;
  dataEnvelope?: DataEnvelope;
}

export interface CapabilityContext {
  request: MinidoraRequest;
  sessionId: string;
  normalizedText: string;
  ir: HDSIR;
  session: SessionSnapshot;
  input: CapabilityStepInput;
  searchProvider: SearchProvider;
  referenceProvider: ReferenceProvider;
}

export interface CapabilityResult {
  kind: OperationKind;
  value: unknown;
  textCandidates: string[];
  evidenceText?: string;
  sources?: Source[];
  externalDataAccess?: string[];
  stateText?: string;
  warnings?: string[];
}

export interface PlanStep {
  stepId: string;
  operation: OperationKind;
  moduleId: string;
  instruction: string;
  instructionP: InstructionP;
  source: "request-data" | "previous-result" | "session-data" | "reference-data";
  arguments: Record<string, string | number | boolean | string[]>;
}

export interface OperationPlan {
  schema: "minidora.operation-plan.ts.v1";
  steps: PlanStep[];
  residuals: string[];
  executable: boolean;
}

export interface TraceStage {
  stage: string;
  timestamp: number;
  input?: unknown;
  output?: unknown;
  status: "ok" | "held" | "failed";
  note?: string;
}

export interface TraceRecord {
  traceId: string;
  timestamp: number;
  originalInput: string;
  normalizedInput: string;
  sessionId: string;
  semanticIR: HDSIR | null;
  operationPlan: OperationPlan | null;
  selectedCapability: string | null;
  candidateCapabilities: { id: string; confidence: number; reason?: string }[];
  modulesExecuted: string[];
  moduleInputs: Record<string, unknown>;
  moduleOutputs: Record<string, unknown>;
  stages: TraceStage[];
  modelEvaluation: ModelEvaluation | null;
  languageModel: {
    stateHash: string;
    chosenCandidate?: string;
    chosenProbability?: { numerator: string; denominator: string };
  } | null;
  externalDataAccess: string[];
  sources: Source[];
  validationResult: boolean;
  finalComposition: string;
  failures: string[];
  warnings: string[];
}

export interface CoreHealth {
  ok: boolean;
  service: "MINIDORA";
  core: "ready" | "degraded" | "error";
  strictLanguageModel: {
    ready: boolean;
    stateHash: string;
    contextsChecked: number;
    minimumEndProbability: { numerator: string; denominator: string };
  };
  capabilityModel: { ready: boolean };
  semanticFrontend: { ready: boolean };
  capabilities: number;
  searchProvider: boolean;
  referenceProvider: boolean;
}
