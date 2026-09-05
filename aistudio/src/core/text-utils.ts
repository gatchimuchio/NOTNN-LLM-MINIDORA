export function valueToText(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean" || typeof value === "bigint") return String(value);
  if (Array.isArray(value)) return value.map(valueToText).filter(Boolean).join("\n");
  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    if (typeof record.text === "string") return record.text;
    if (Array.isArray(record.results)) return record.results.map(valueToText).join("\n");
    return JSON.stringify(value, null, 2);
  }
  return String(value);
}

export function splitSentences(text: string): string[] {
  const value = String(text).normalize("NFKC").replace(/\r\n?/g, "\n").trim();
  if (!value) return [];
  const out: string[] = [];
  let start = 0;
  for (let i = 0; i < value.length; i += 1) {
    const char = value[i];
    let boundary = "。！？!?\n".includes(char);
    if (char === ".") {
      const leftDigit = i > 0 && /\d/.test(value[i - 1]);
      const rightDigit = i + 1 < value.length && /\d/.test(value[i + 1]);
      boundary = !(leftDigit && rightDigit);
    }
    if (!boundary) continue;
    const sentence = value.slice(start, i + (char === "\n" ? 0 : 1)).trim();
    if (sentence) out.push(sentence);
    start = i + 1;
  }
  const tail = value.slice(start).trim();
  if (tail) out.push(tail);
  return out;
}

export function uniquePreserveOrder<T>(values: Iterable<T>): T[] {
  const seen = new Set<T>();
  const out: T[] = [];
  for (const value of values) {
    if (seen.has(value)) continue;
    seen.add(value);
    out.push(value);
  }
  return out;
}
