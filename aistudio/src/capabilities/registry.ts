import type { CapabilityModule } from "./interface.js";
import type { OperationKind } from "../core/hds-ir.js";

export class CapabilityRegistry {
  private readonly modules = new Map<string, CapabilityModule>();

  register(module: CapabilityModule): void {
    if (this.modules.has(module.id)) throw new Error(`Capability IDが重複しています: ${module.id}`);
    this.modules.set(module.id, module);
  }

  getModules(): CapabilityModule[] {
    return [...this.modules.values()];
  }

  getModule(id: string): CapabilityModule | undefined {
    return this.modules.get(id);
  }

  forOperation(operation: OperationKind): CapabilityModule[] {
    return this.getModules().filter(module => module.operations.includes(operation));
  }
}
