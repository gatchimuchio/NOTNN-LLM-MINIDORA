import type { HDSIR, OperationKind, SemanticOperation } from "../core/hds-ir.js";
import type { CapabilityContext, CapabilityResult } from "../types.js";

export interface CapabilityApplicability {
  score: number;
  reason: string;
}

export interface CapabilityModule {
  readonly id: string;
  readonly name: string;
  readonly description: string;
  readonly operations: readonly OperationKind[];

  /** HDS semantic IRと対象作用から発火可否を決める。 */
  canHandle(ir: HDSIR, operation: SemanticOperation): CapabilityApplicability;

  /** Moduleは構造化結果を返し、最終表面化はCore側が担う。 */
  execute(context: CapabilityContext): Promise<CapabilityResult>;
}
