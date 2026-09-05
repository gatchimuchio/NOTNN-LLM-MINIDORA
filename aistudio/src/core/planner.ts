import type { CapabilityRegistry } from "../capabilities/registry.js";
import type { CapabilityApplicability } from "../capabilities/interface.js";
import type { HDSIR, OperationKind, SemanticOperation } from "./hds-ir.js";
import type { OperationPlan, PlanStep } from "../types.js";
import type { SessionSnapshot } from "./state.js";
import { lowerOperationToInstructionP } from "./instruction-p.js";

export interface PlanCandidateRecord {
  id: string;
  confidence: number;
  reason: string;
  operation: OperationKind;
}

export interface PlanBuildResult {
  plan: OperationPlan;
  candidates: PlanCandidateRecord[];
}

/**
 * HDS-IRからCapability実行計画へ降下する。原文をModule側で再ルーティングしない。
 */
export class OperationPlanner {
  constructor(private readonly registry: CapabilityRegistry) {}

  build(ir: HDSIR, session: SessionSnapshot): PlanBuildResult {
    const steps: PlanStep[] = [];
    const residuals: string[] = [];
    const candidates: PlanCandidateRecord[] = [];

    for (const operation of ir.operations) {
      const available = this.registry.forOperation(operation.kind);
      const evaluated = available.map(module => ({ module, applicability: module.canHandle(ir, operation) }));
      for (const row of evaluated) {
        candidates.push({
          id: row.module.id,
          confidence: clamp(row.applicability.score),
          reason: row.applicability.reason,
          operation: operation.kind,
        });
      }

      const selected = evaluated
        .filter(row => row.applicability.score > 0)
        .sort((a, b) => b.applicability.score - a.applicability.score || a.module.id.localeCompare(b.module.id))[0];
      if (!selected) {
        residuals.push(`作用 ${operation.kind} を実行できるCapabilityがありません`);
        continue;
      }

      const source = chooseSource(operation, ir, session, steps);
      if (requiresData(operation.kind) && source === "session-data" && !session.workingData && !session.lastResponse) {
        residuals.push(`作用 ${operation.kind} に必要なDataがありません`);
        continue;
      }

      steps.push({
        stepId: `step_${String(steps.length + 1).padStart(2, "0")}`,
        operation: operation.kind,
        moduleId: selected.module.id,
        instruction: operation.instruction,
        instructionP: lowerOperationToInstructionP(ir, operation),
        source,
        arguments: { ...operation.arguments },
      });
    }

    return {
      plan: {
        schema: "minidora.operation-plan.ts.v1",
        steps,
        residuals,
        executable: steps.length > 0 && residuals.length === 0,
      },
      candidates,
    };
  }
}

function chooseSource(operation: SemanticOperation, ir: HDSIR, session: SessionSnapshot, priorSteps: PlanStep[]): PlanStep["source"] {
  if (priorSteps.length > 0) return "previous-result";
  if (operation.kind === "search" || operation.kind === "knowledge_reference") return "request-data";
  if (ir.data.trim()) return "request-data";
  if (session.workingData || session.lastResponse) return "session-data";
  return "request-data";
}

function requiresData(kind: OperationKind): boolean {
  return ["summarization", "extraction", "transformation", "comparison"].includes(kind);
}

function clamp(value: number): number {
  return Math.max(0, Math.min(1, Number.isFinite(value) ? value : 0));
}
