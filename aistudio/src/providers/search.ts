import type { SearchProvider, SearchResult } from "../types.js";

/** 外部検索が未接続であることを明示するProvider。架空Dataは生成しない。 */
export class DisabledSearchProvider implements SearchProvider {
  readonly id = "search.disabled";
  isConfigured(): boolean { return false; }
  async search(_query: string): Promise<SearchResult[]> {
    throw new Error("検索Providerが設定されていません");
  }
}
