import type { HDSIR } from "./hds-ir.js";
import type { LanguageRelation } from "./semantic.js";
import type { Source } from "../types.js";

export interface SessionTurn {
  requestId: string;
  input: string;
  normalizedInput: string;
  response: string;
  operations: string[];
  relations: LanguageRelation[];
  sources: Source[];
  timestamp: number;
}

export interface SessionSnapshot {
  sessionId: string;
  turns: SessionTurn[];
  workingData: string | null;
  workingValue: unknown;
  workingRelations: LanguageRelation[];
  lastResponse: string | null;
}

interface MutableSession {
  turns: SessionTurn[];
  workingData: string | null;
  workingValue: unknown;
  workingRelations: LanguageRelation[];
  lastResponse: string | null;
}

/**
 * 会話内だけの作業状態。世界知識や永続人格を兼ねない。
 */
export class SessionStateStore {
  private readonly sessions = new Map<string, MutableSession>();
  constructor(private readonly maxTurns = 24) {}

  snapshot(sessionId: string): SessionSnapshot {
    const state = this.ensure(sessionId);
    return {
      sessionId,
      turns: state.turns.map(turn => ({ ...turn, relations: [...turn.relations], sources: [...turn.sources] })),
      workingData: state.workingData,
      workingValue: state.workingValue,
      workingRelations: [...state.workingRelations],
      lastResponse: state.lastResponse,
    };
  }

  resolveData(sessionId: string, ir: HDSIR): string {
    if (ir.data.trim()) return ir.data;
    const state = this.ensure(sessionId);
    return state.workingData ?? state.lastResponse ?? "";
  }

  commit(sessionId: string, turn: SessionTurn, ir: HDSIR, finalValue?: unknown, finalStructuredText?: string): void {
    const state = this.ensure(sessionId);
    state.turns.push(turn);
    if (state.turns.length > this.maxTurns) state.turns.splice(0, state.turns.length - this.maxTurns);

    const observedData = ir.data.trim();
    if (finalStructuredText?.trim()) {
      state.workingData = finalStructuredText.trim();
      state.workingValue = finalValue;
    } else if (observedData) {
      state.workingData = observedData;
      state.workingValue = observedData;
    }
    if (ir.relations.length) state.workingRelations = [...ir.relations];
    state.lastResponse = turn.response;
  }

  previousUserInput(sessionId: string): string | null {
    const turns = this.ensure(sessionId).turns;
    return turns.length ? turns[turns.length - 1].input : null;
  }

  previousResponse(sessionId: string): string | null {
    return this.ensure(sessionId).lastResponse;
  }

  recentContext(sessionId: string, limit = 6): string[] {
    const turns = this.ensure(sessionId).turns.slice(-limit);
    const out: string[] = [];
    for (const turn of turns) {
      out.push(turn.input, turn.response);
    }
    return out.filter(Boolean);
  }

  private ensure(sessionId: string): MutableSession {
    let state = this.sessions.get(sessionId);
    if (!state) {
      state = { turns: [], workingData: null, workingValue: undefined, workingRelations: [], lastResponse: null };
      this.sessions.set(sessionId, state);
    }
    return state;
  }
}
