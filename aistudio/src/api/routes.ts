import { Router } from "express";
import { globalCore } from "../core/minidora.js";

export const apiRouter = Router();

export function healthPayload() {
  return {
    ...globalCore.health(),
    geminiComparator: Boolean(process.env.GEMINI_API_KEY),
  };
}

apiRouter.get("/health", (_req, res) => {
  res.json(healthPayload());
});

apiRouter.get("/capabilities", (_req, res) => {
  const modules = globalCore.getRegistry().getModules().map(module => ({
    id: module.id,
    name: module.name,
    description: module.description,
    operations: module.operations,
  }));
  res.json(modules);
});

apiRouter.post("/chat", async (req, res) => {
  try {
    const { text, sessionId } = req.body ?? {};
    if (typeof text !== "string" || !text.trim()) return res.status(400).json({ error: "No text provided" });

    // MINIDORA経路。Gemini関連APIをここから呼び出してはならない。
    const request = {
      id: `req_${globalThis.crypto.randomUUID()}`,
      text,
      sessionId: typeof sessionId === "string" ? sessionId : undefined,
      timestamp: Date.now(),
    };
    const response = await globalCore.process(request);
    return res.json(response);
  } catch (error) {
    return res.status(500).json({ error: error instanceof Error ? error.message : String(error) });
  }
});

apiRouter.get("/trace/:traceId", (req, res) => {
  const trace = globalCore.traceManager.getTrace(req.params.traceId);
  if (!trace) return res.status(404).json({ error: "Trace not found" });
  return res.json(trace);
});

/**
 * 比較用Gemini。MINIDORAの結果・Trace・Sourceを受け取らず、同一User inputだけを別経路で処理する。
 */
apiRouter.post("/gemini", async (req, res) => {
  try {
    const { text } = req.body ?? {};
    if (typeof text !== "string" || !text.trim()) return res.status(400).json({ error: "No text provided" });
    if (!process.env.GEMINI_API_KEY) return res.status(400).json({ error: "Gemini comparator is not configured" });

    const { GoogleGenAI } = await import("@google/genai");
    const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
    const response = await ai.models.generateContent({
      model: process.env.GEMINI_MODEL || "gemini-2.5-flash",
      contents: text,
    });
    return res.json({ text: response.text });
  } catch (error) {
    return res.status(500).json({ error: error instanceof Error ? error.message : String(error) });
  }
});
