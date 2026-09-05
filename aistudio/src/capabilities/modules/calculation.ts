import type { CapabilityModule } from "../interface.js";
import type { CapabilityContext, CapabilityResult } from "../../types.js";
import type { HDSIR, SemanticOperation } from "../../core/hds-ir.js";
import { ExactRational } from "../../core/exact-rational.js";

export class CalculationModule implements CapabilityModule {
  readonly id = "calculation";
  readonly name = "計算Capability";
  readonly description = "安全なTokenizer + Parserで四則演算・括弧・整数指数を厳密計算する";
  readonly operations = ["calculation"] as const;

  canHandle(_ir: HDSIR, operation: SemanticOperation) {
    const expression = String(operation.arguments.expression ?? "");
    return expression ? { score: 1, reason: "HDS-IRに閉包済み数式がある" } : { score: 0, reason: "数式が未閉包" };
  }

  async execute(context: CapabilityContext): Promise<CapabilityResult> {
    const expression = String(context.input.operation.arguments.expression ?? context.input.text).trim();
    if (!expression) throw new Error("計算対象の数式がありません");
    const parser = new ExpressionParser(expression);
    const value = parser.parse();
    const display = value.toDisplayString();
    return {
      kind: "calculation",
      value: { expression, exact: value.toJSON(), display },
      textCandidates: [display, `計算結果は ${display} です。`, `計算結果は次のとおりです。\n${display}`],
      evidenceText: `${expression} = ${display}`,
      stateText: display,
    };
  }
}

class ExpressionParser {
  private index = 0;
  constructor(private readonly source: string) {
    if (!/^[\d\s.+\-*/^()]+$/.test(source)) throw new Error("許可されていない記号が数式に含まれています");
    if (source.length > 500) throw new Error("数式が長すぎます");
  }

  parse(): ExactRational {
    this.skipSpace();
    const value = this.parseExpression();
    this.skipSpace();
    if (this.index !== this.source.length) throw new Error(`数式を解釈できません: ${this.source.slice(this.index)}`);
    return value;
  }

  private parseExpression(): ExactRational {
    let left = this.parseTerm();
    while (true) {
      this.skipSpace();
      if (this.consume("+")) left = left.add(this.parseTerm());
      else if (this.consume("-")) left = left.subtract(this.parseTerm());
      else break;
    }
    return left;
  }

  private parseTerm(): ExactRational {
    let left = this.parsePower();
    while (true) {
      this.skipSpace();
      if (this.consume("*")) left = left.multiply(this.parsePower());
      else if (this.consume("/")) left = left.divide(this.parsePower());
      else break;
    }
    return left;
  }

  private parsePower(): ExactRational {
    let left = this.parseUnary();
    this.skipSpace();
    if (this.consume("^")) {
      const right = this.parsePower();
      if (!right.isInteger()) throw new Error("指数は整数である必要があります");
      const exponent = Number(right.numerator);
      if (!Number.isSafeInteger(exponent)) throw new Error("指数が大きすぎます");
      left = left.powInteger(exponent);
    }
    return left;
  }

  private parseUnary(): ExactRational {
    this.skipSpace();
    if (this.consume("+")) return this.parseUnary();
    if (this.consume("-")) return this.parseUnary().negate();
    return this.parsePrimary();
  }

  private parsePrimary(): ExactRational {
    this.skipSpace();
    if (this.consume("(")) {
      const value = this.parseExpression();
      this.skipSpace();
      if (!this.consume(")")) throw new Error("閉じ括弧がありません");
      return value;
    }
    const match = this.source.slice(this.index).match(/^(?:\d+(?:\.\d+)?|\.\d+)/);
    if (!match) throw new Error(`数値を解釈できません: ${this.source.slice(this.index)}`);
    this.index += match[0].length;
    return ExactRational.fromDecimal(match[0]);
  }

  private consume(char: string): boolean {
    if (this.source[this.index] === char) {
      this.index += 1;
      return true;
    }
    return false;
  }

  private skipSpace(): void {
    while (/\s/.test(this.source[this.index] ?? "")) this.index += 1;
  }
}
