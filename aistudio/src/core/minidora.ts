import { CapabilityRegistry } from "../capabilities/registry.js";
import { TraceGovernance } from "../governance/trace.js";
import type {
  CapabilityContext,
  CapabilityResult,
  CoreHealth,
  MinidoraRequest,
  MinidoraResponse,
  ReferenceProvider,
  SearchProvider,
} from "../types.js";
import { CalculationModule } from "../capabilities/modules/calculation.js";
import { SummarizationModule } from "../capabilities/modules/summarization.js";
import { ExtractionModule } from "../capabilities/modules/extraction.js";
import { TransformationModule } from "../capabilities/modules/transformation.js";
import { SearchModule } from "../capabilities/modules/search.js";
import { KnowledgeReferenceModule } from "../capabilities/modules/knowledge-reference.js";
import { ConversationModule } from "../capabilities/modules/conversation.js";
import { ComparisonModule } from "../capabilities/modules/comparison.js";
import { DisabledSearchProvider } from "../providers/search.js";
import { DisabledReferenceProvider } from "../providers/reference.js";
import { compileHDSIR, SemanticOperation } from "./hds-ir.js";
import { OperationPlanner } from "./planner.js";
import { SessionStateStore } from "./state.js";
import { CapabilityModelKernel } from "./model-kernel.js";
import { createBaseLanguageModel, StrictLanguageModel } from "./language-model.js";
import { ResponseComposer } from "./composer.js";
import { valueToText } from "./text-utils.js";
import type { DataEnvelope } from "./instruction-p.js";

export interface MinidoraCoreOptions {
  searchProvider?: SearchProvider;
  referenceProvider?: ReferenceProvider;
  languageModel?: StrictLanguageModel;
  sessionStore?: SessionStateStore;
}

/**
 * MINIDORA AI Studio Port v1。
 *
 * 実行経路:
 * 外部入力 → HDS semantic frontend → OperationPlan → Capability
 *          → 能力模型核 → 厳密言語模型核 → 検証 → 表面出力
 *
 * Geminiはこのクラスから参照しない。
 */
export class MinidoraCore {
  private readonly registry: CapabilityRegistry;
  private readonly planner: OperationPlanner;
  private readonly searchProvider: SearchProvider;
  private readonly referenceProvider: ReferenceProvider;
  private readonly sessionStore: SessionStateStore;
  private readonly capabilityModel: CapabilityModelKernel;
  private readonly languageModel: StrictLanguageModel;
  private readonly composer: ResponseComposer;
  readonly traceManager: TraceGovernance;

  constructor(options: MinidoraCoreOptions = {}) {
    this.registry = new CapabilityRegistry();
    this.traceManager = new TraceGovernance();
    this.searchProvider = options.searchProvider ?? new DisabledSearchProvider();
    this.referenceProvider = options.referenceProvider ?? new DisabledReferenceProvider();
    this.sessionStore = options.sessionStore ?? new SessionStateStore();
    this.capabilityModel = new CapabilityModelKernel();
    this.languageModel = options.languageModel ?? createBaseLanguageModel();
    this.composer = new ResponseComposer(this.capabilityModel, this.languageModel);
    this.registerBuiltInModules();
    this.planner = new OperationPlanner(this.registry);
  }

  getRegistry(): CapabilityRegistry { return this.registry; }
  getSearchProvider(): SearchProvider { return this.searchProvider; }
  getReferenceProvider(): ReferenceProvider { return this.referenceProvider; }
  getLanguageModel(): StrictLanguageModel { return this.languageModel; }

  health(): CoreHealth {
    try {
      const lm = this.languageModel.audit();
      const capabilities = this.registry.getModules().length;
      const coreReady = lm.ok && capabilities >= 8;
      return {
        ok: coreReady,
        service: "MINIDORA",
        core: coreReady ? "ready" : "error",
        strictLanguageModel: {
          ready: lm.ok,
          stateHash: this.languageModel.stateHash(),
          contextsChecked: lm.contextsChecked,
          minimumEndProbability: lm.minimumEndProbability.toJSON(),
        },
        capabilityModel: { ready: true },
        semanticFrontend: { ready: true },
        capabilities,
        searchProvider: this.searchProvider.isConfigured(),
        referenceProvider: this.referenceProvider.isConfigured(),
      };
    } catch {
      return {
        ok: false,
        service: "MINIDORA",
        core: "error",
        strictLanguageModel: { ready: false, stateHash: "", contextsChecked: 0, minimumEndProbability: { numerator: "0", denominator: "1" } },
        capabilityModel: { ready: false },
        semanticFrontend: { ready: false },
        capabilities: this.registry.getModules().length,
        searchProvider: false,
        referenceProvider: false,
      };
    }
  }

  async process(request: MinidoraRequest): Promise<MinidoraResponse> {
    const sessionId = request.sessionId?.trim() || "session_default";
    const trace = this.traceManager.createTrace(request.text, sessionId);
    const responseId = `res_${globalThis.crypto.randomUUID()}`;

    try {
      const ir = compileHDSIR(request.text);
      trace.normalizedInput = ir.normalized;
      trace.semanticIR = ir;
      this.traceManager.stage(trace.traceId, { stage: "HDS_SEMANTIC_FRONTEND", input: request.text, output: ir, status: "ok" });

      const session = this.sessionStore.snapshot(sessionId);
      const planning = this.planner.build(ir, session);
      trace.operationPlan = planning.plan;
      for (const candidate of planning.candidates) {
        this.traceManager.recordCandidate(trace.traceId, candidate.id, candidate.confidence, `${candidate.operation}: ${candidate.reason}`);
      }
      trace.selectedCapability = planning.plan.steps.length ? planning.plan.steps.map(step => step.moduleId).join(" -> ") : null;
      this.traceManager.stage(trace.traceId, {
        stage: "OPERATION_PLANNING",
        input: ir.operations,
        output: planning.plan,
        status: planning.plan.steps.length ? "ok" : "held",
      });

      if (!planning.plan.executable) {
        const text = planning.plan.residuals.length
          ? planning.plan.residuals.join("\n")
          : "現在のMINIDORAにはこの要求を処理できるCapabilityがありません。";
        trace.failures.push(...planning.plan.residuals);
        trace.finalComposition = text;
        trace.validationResult = false;
        return this.makeResponse(responseId, request, text, [], trace.traceId, planning.plan.residuals.length ? "held" : "unsupported");
      }

      let previousResult: CapabilityResult | undefined;
      for (let index = 0; index < planning.plan.steps.length; index += 1) {
        const step = planning.plan.steps[index];
        const module = this.registry.getModule(step.moduleId);
        if (!module) throw new Error(`計画されたCapabilityがRegistryにありません: ${step.moduleId}`);
        const operation: SemanticOperation = {
          kind: step.operation,
          instruction: step.instruction,
          position: index,
          arguments: { ...step.arguments },
        };
        const inputValue = resolveStepValue(step.source, ir.data, session.workingData, session.workingValue, session.lastResponse, previousResult);
        const inputText = valueToText(inputValue);
        const dataEnvelope: DataEnvelope = {
          schema: "minidora.data-envelope.ts.v1",
          source: step.source,
          observed: inputValue !== undefined && inputValue !== null && inputText.trim().length > 0,
          value: inputValue,
          text: inputText,
          provenance: step.source === "request-data"
            ? [`request:${request.id}`]
            : step.source === "session-data"
              ? [`session:${sessionId}:working`]
              : [`module:${planning.plan.steps[index - 1]?.moduleId ?? "unknown"}`],
        };
        const context: CapabilityContext = {
          request,
          sessionId,
          normalizedText: ir.normalized,
          ir,
          session,
          input: {
            operation,
            text: inputText,
            previousValue: previousResult?.value ?? (step.source === "session-data" ? session.workingValue : undefined),
            previousText: previousResult?.stateText,
            dataEnvelope,
          },
          searchProvider: this.searchProvider,
          referenceProvider: this.referenceProvider,
        };

        trace.modulesExecuted.push(module.id);
        trace.moduleInputs[step.stepId] = {
          moduleId: module.id,
          operation,
          instructionP: step.instructionP,
          data: dataEnvelope,
        };
        this.traceManager.stage(trace.traceId, {
          stage: `P_DATA_BIND:${module.id}`,
          input: { instructionP: step.instructionP, data: dataEnvelope },
          status: dataEnvelope.observed || ["search", "knowledge_reference", "conversation"].includes(step.operation) ? "ok" : "held",
        });
        this.traceManager.stage(trace.traceId, { stage: `CAPABILITY_BEGIN:${module.id}`, input: trace.moduleInputs[step.stepId], status: "ok" });

        try {
          const result = await module.execute(context);
          previousResult = result;
          trace.moduleOutputs[step.stepId] = {
            moduleId: module.id,
            kind: result.kind,
            value: result.value,
            stateText: result.stateText,
          };
          if (result.externalDataAccess?.length) trace.externalDataAccess.push(...result.externalDataAccess);
          if (result.sources?.length) trace.sources.push(...result.sources);
          if (result.warnings?.length) trace.warnings.push(...result.warnings);
          this.traceManager.stage(trace.traceId, { stage: `CAPABILITY_END:${module.id}`, output: trace.moduleOutputs[step.stepId], status: "ok" });
        } catch (error) {
          const message = errorMessage(error);
          trace.failures.push(message);
          this.traceManager.stage(trace.traceId, { stage: `CAPABILITY_END:${module.id}`, output: { error: message }, status: "failed" });
          throw error;
        }
      }

      if (!previousResult) throw new Error("Capability結果がありません");
      const history = this.sessionStore.recentContext(sessionId);
      const composed = this.composer.compose(ir, previousResult, history, trace);
      this.traceManager.stage(trace.traceId, {
        stage: "MODEL_COMPOSITION",
        input: previousResult.textCandidates,
        output: { text: composed.text, probability: composed.probability },
        status: "ok",
      });

      const validation = validateFinal(ir, previousResult, composed.text, trace.modulesExecuted, planning.plan.steps.map(step => step.moduleId));
      trace.validationResult = validation.ok;
      trace.warnings.push(...validation.warnings);
      if (!validation.ok) trace.failures.push(...validation.failures);
      trace.finalComposition = composed.text;
      this.traceManager.stage(trace.traceId, { stage: "FINAL_VALIDATION", output: validation, status: validation.ok ? "ok" : "failed" });

      if (!validation.ok) {
        const held = "検証境界を満たさないため結果を確定しません。";
        trace.finalComposition = held;
        return this.makeResponse(responseId, request, held, trace.sources, trace.traceId, "held");
      }

      this.sessionStore.commit(sessionId, {
        requestId: request.id,
        input: request.text,
        normalizedInput: ir.normalized,
        response: composed.text,
        operations: ir.operations.map(operation => operation.kind),
        relations: ir.relations,
        sources: [...trace.sources],
        timestamp: Date.now(),
      }, ir, previousResult.value, previousResult.stateText ?? valueToText(previousResult.value));

      return this.makeResponse(responseId, request, composed.text, trace.sources, trace.traceId, "ok");
    } catch (error) {
      const message = errorMessage(error);
      if (!trace.failures.includes(message)) trace.failures.push(message);
      const held = isProviderError(message);
      const text = held ? message : `処理を確定できませんでした: ${message}`;
      trace.finalComposition = text;
      trace.validationResult = false;
      this.traceManager.stage(trace.traceId, { stage: "CORE_FAILURE", output: { error: message }, status: "failed" });
      return this.makeResponse(responseId, request, text, trace.sources, trace.traceId, held ? "held" : "error");
    }
  }

  private registerBuiltInModules(): void {
    this.registry.register(new CalculationModule());
    this.registry.register(new SummarizationModule());
    this.registry.register(new ExtractionModule());
    this.registry.register(new TransformationModule());
    this.registry.register(new SearchModule());
    this.registry.register(new KnowledgeReferenceModule());
    this.registry.register(new ComparisonModule());
    this.registry.register(new ConversationModule());
  }

  private makeResponse(
    id: string,
    request: MinidoraRequest,
    text: string,
    sources: MinidoraResponse["sources"],
    traceId: string,
    status: MinidoraResponse["status"],
  ): MinidoraResponse {
    return { id, requestId: request.id, text, sources: dedupeSources(sources), traceId, timestamp: Date.now(), status };
  }
}

function resolveStepValue(
  source: "request-data" | "previous-result" | "session-data" | "reference-data",
  requestData: string,
  sessionData: string | null,
  sessionValue: unknown,
  sessionLastResponse: string | null,
  previousResult?: CapabilityResult,
): unknown {
  if (source === "previous-result" || source === "reference-data") {
    return previousResult?.value ?? previousResult?.stateText ?? "";
  }
  if (source === "session-data") return sessionValue ?? sessionData ?? sessionLastResponse ?? "";
  return requestData;
}

function validateFinal(
  ir: ReturnType<typeof compileHDSIR>,
  result: CapabilityResult,
  text: string,
  executed: string[],
  planned: string[],
): { ok: boolean; failures: string[]; warnings: string[] } {
  const failures: string[] = [];
  const warnings: string[] = [];
  if (!text.trim()) failures.push("最終出力が空です");
  if (executed.join("\u001f") !== planned.join("\u001f")) failures.push("実行Module列と計画Module列が一致しません");
  if (ir.output.format === "json") {
    try { JSON.parse(text); } catch { failures.push("JSON出力要求に対して妥当なJSONではありません"); }
  }
  if ((result.externalDataAccess?.length ?? 0) > 0 && (result.sources?.length ?? 0) === 0 && !/確認できません/.test(text)) {
    warnings.push("外部Dataアクセスは記録されていますが表示可能Sourceがありません");
  }
  return { ok: failures.length === 0, failures, warnings };
}

function dedupeSources(sources: MinidoraResponse["sources"]): MinidoraResponse["sources"] {
  const seen = new Set<string>();
  return sources.filter(source => {
    const key = `${source.provider}\u001f${source.identifier ?? ""}\u001f${source.url ?? ""}\u001f${source.title}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function isProviderError(message: string): boolean {
  return /Providerが設定されていません/.test(message);
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export const globalCore = new MinidoraCore();
