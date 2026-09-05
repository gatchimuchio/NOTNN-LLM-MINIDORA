/**
 * MINIDORA内部の厳密有理数。
 * 言語確率核と計算Capabilityで共有し、浮動小数点への無言丸めを避ける。
 */
export class ExactRational {
  readonly numerator: bigint;
  readonly denominator: bigint;

  constructor(numerator: bigint | number | string, denominator: bigint | number | string = 1n) {
    let n = BigInt(numerator);
    let d = BigInt(denominator);
    if (d === 0n) throw new Error("分母は0にできません");
    if (d < 0n) {
      n = -n;
      d = -d;
    }
    const g = ExactRational.gcd(n < 0n ? -n : n, d);
    this.numerator = n / g;
    this.denominator = d / g;
  }

  static zero(): ExactRational { return new ExactRational(0n); }
  static one(): ExactRational { return new ExactRational(1n); }

  static fromDecimal(raw: string): ExactRational {
    const text = raw.trim();
    if (!/^[+-]?(?:\d+(?:\.\d+)?|\.\d+)$/.test(text)) {
      throw new Error(`数値形式が不正です: ${raw}`);
    }
    const negative = text.startsWith("-");
    const body = text.replace(/^[+-]/, "");
    const [integerPartRaw, fractional = ""] = body.split(".");
    const integerPart = integerPartRaw || "0";
    const scale = 10n ** BigInt(fractional.length);
    const n = BigInt(integerPart) * scale + BigInt(fractional || "0");
    return new ExactRational(negative ? -n : n, scale);
  }

  add(other: ExactRational): ExactRational {
    return new ExactRational(
      this.numerator * other.denominator + other.numerator * this.denominator,
      this.denominator * other.denominator,
    );
  }

  subtract(other: ExactRational): ExactRational {
    return new ExactRational(
      this.numerator * other.denominator - other.numerator * this.denominator,
      this.denominator * other.denominator,
    );
  }

  multiply(other: ExactRational): ExactRational {
    return new ExactRational(
      this.numerator * other.numerator,
      this.denominator * other.denominator,
    );
  }

  divide(other: ExactRational): ExactRational {
    if (other.numerator === 0n) throw new Error("0で除算できません");
    return new ExactRational(
      this.numerator * other.denominator,
      this.denominator * other.numerator,
    );
  }

  negate(): ExactRational { return new ExactRational(-this.numerator, this.denominator); }

  powInteger(exponent: number): ExactRational {
    if (!Number.isInteger(exponent)) throw new Error("指数は整数である必要があります");
    if (Math.abs(exponent) > 1000) throw new Error("指数が大きすぎます");
    if (exponent === 0) return ExactRational.one();
    if (exponent < 0) {
      if (this.numerator === 0n) throw new Error("0の負指数は定義できません");
      const positive = this.powInteger(-exponent);
      return new ExactRational(positive.denominator, positive.numerator);
    }
    return new ExactRational(this.numerator ** BigInt(exponent), this.denominator ** BigInt(exponent));
  }

  compare(other: ExactRational): number {
    const left = this.numerator * other.denominator;
    const right = other.numerator * this.denominator;
    return left < right ? -1 : left > right ? 1 : 0;
  }

  equals(other: ExactRational): boolean {
    return this.numerator === other.numerator && this.denominator === other.denominator;
  }

  isInteger(): boolean { return this.denominator === 1n; }

  /** 有限小数なら小数表記、循環小数なら既定で分数表記。 */
  toDisplayString(maxDecimalDigits = 12): string {
    if (this.denominator === 1n) return this.numerator.toString();

    let d = this.denominator;
    while (d % 2n === 0n) d /= 2n;
    while (d % 5n === 0n) d /= 5n;
    if (d !== 1n) return `${this.numerator}/${this.denominator}`;

    const negative = this.numerator < 0n;
    let n = negative ? -this.numerator : this.numerator;
    const integer = n / this.denominator;
    let remainder = n % this.denominator;
    if (remainder === 0n) return `${negative ? "-" : ""}${integer}`;

    let fraction = "";
    for (let i = 0; i < maxDecimalDigits && remainder !== 0n; i += 1) {
      remainder *= 10n;
      fraction += (remainder / this.denominator).toString();
      remainder %= this.denominator;
    }
    fraction = fraction.replace(/0+$/, "");
    return `${negative ? "-" : ""}${integer}.${fraction || "0"}`;
  }

  toJSON(): { numerator: string; denominator: string } {
    return { numerator: this.numerator.toString(), denominator: this.denominator.toString() };
  }

  static sum(values: Iterable<ExactRational>): ExactRational {
    let out = ExactRational.zero();
    for (const value of values) out = out.add(value);
    return out;
  }

  private static gcd(a: bigint, b: bigint): bigint {
    let x = a;
    let y = b;
    while (y !== 0n) {
      const r = x % y;
      x = y;
      y = r;
    }
    return x === 0n ? 1n : x;
  }
}
