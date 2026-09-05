import type { ReferenceProvider, ReferenceRecord } from "../types.js";

/** 世界知識の参照先が未接続であることを表す。 */
export class DisabledReferenceProvider implements ReferenceProvider {
  readonly id = "reference.disabled";
  isConfigured(): boolean { return false; }
  async lookup(_query: string): Promise<ReferenceRecord[]> {
    throw new Error("外部Data Providerが設定されていません");
  }
}
