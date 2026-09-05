import React, { useEffect, useRef, useState } from "react";
import type { CoreHealth, MinidoraResponse, TraceRecord } from "../types.js";

type Message = {
  role: "user" | "minidora";
  text: string;
  traceId?: string;
  sources?: MinidoraResponse["sources"];
  status?: MinidoraResponse["status"];
};

type HealthPayload = CoreHealth & { geminiComparator?: boolean };

export function ChatUI() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [traceData, setTraceData] = useState<TraceRecord | null>(null);
  const [showTrace, setShowTrace] = useState(false);
  const [health, setHealth] = useState<HealthPayload | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const sessionId = useRef(`web_${globalThis.crypto.randomUUID()}`);

  useEffect(() => {
    fetch("/health")
      .then(response => response.json())
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!input.trim() || loading) return;
    const userText = input.trim();
    setInput("");
    setMessages(previous => [...previous, { role: "user", text: userText }]);
    setLoading(true);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: userText, sessionId: sessionId.current }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
      const result = data as MinidoraResponse;
      setMessages(previous => [...previous, {
        role: "minidora",
        text: result.text,
        traceId: result.traceId,
        sources: result.sources,
        status: result.status,
      }]);
    } catch (error) {
      setMessages(previous => [...previous, {
        role: "minidora",
        text: `通信経路でエラーが発生しました: ${error instanceof Error ? error.message : String(error)}`,
        status: "error",
      }]);
    } finally {
      setLoading(false);
    }
  };

  const loadTrace = async (traceId: string) => {
    const response = await fetch(`/api/trace/${encodeURIComponent(traceId)}`);
    if (!response.ok) return;
    setTraceData(await response.json());
    setShowTrace(true);
  };

  const openGeminiCompare = (text: string) => {
    window.open(`/compare.html?q=${encodeURIComponent(text)}`, "_blank", "width=880,height=700");
  };

  const coreState = health?.core ?? "degraded";
  const statusLabel = health ? `Core ${coreState}` : "Core checking";
  const statusDot = coreState === "ready" ? "bg-emerald-500" : coreState === "error" ? "bg-red-500" : "bg-amber-500";

  return (
    <div className="flex flex-col h-full bg-slate-50 text-slate-900 font-sans">
      <header className="flex justify-between items-center px-5 py-4 bg-white border-b border-slate-200">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-slate-800">MINIDORA</h1>
          <p className="text-xs text-slate-400 mt-0.5">Non-neural language system</p>
        </div>
        <div className="flex items-center gap-2" title={health ? `LM ${health.strictLanguageModel.stateHash}` : "health未取得"}>
          <span className={`inline-flex rounded-full h-2.5 w-2.5 ${statusDot}`} />
          <span className="text-sm text-slate-500">{statusLabel}</span>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
        {messages.length === 0 && (
          <div className="max-w-2xl mx-auto mt-16 text-center text-slate-500">
            <div className="text-lg font-medium text-slate-700 mb-2">MINIDORA</div>
            <p className="text-sm">計算・要約・抽出・変換・比較・会話を、生成AIへフォールバックせず処理します。</p>
          </div>
        )}

        {messages.map((message, index) => (
          <div key={index} className={`flex flex-col ${message.role === "user" ? "items-end" : "items-start"}`}>
            <div className={`max-w-2xl px-5 py-3.5 rounded-2xl ${
              message.role === "user"
                ? "bg-indigo-600 text-white"
                : "bg-white border border-slate-200 shadow-sm text-slate-800 whitespace-pre-wrap"
            }`}>
              {message.text}
            </div>

            {message.role === "minidora" && message.traceId && (
              <div className="mt-2 flex gap-2 items-center">
                <button
                  onClick={() => loadTrace(message.traceId!)}
                  className="text-xs text-slate-500 hover:text-indigo-600 transition-colors border border-slate-200 px-3 py-1.5 rounded-full bg-white shadow-sm"
                >
                  Trace
                </button>
                {health?.geminiComparator && messages[index - 1]?.role === "user" && (
                  <button
                    onClick={() => openGeminiCompare(messages[index - 1].text)}
                    className="text-xs text-slate-500 hover:text-purple-600 transition-colors border border-slate-200 px-3 py-1.5 rounded-full bg-white shadow-sm"
                  >
                    Geminiで比較
                  </button>
                )}
                {message.status && message.status !== "ok" && (
                  <span className="text-[11px] text-amber-600">{message.status}</span>
                )}
              </div>
            )}

            {message.sources && message.sources.length > 0 && (
              <details className="mt-2 bg-slate-100 p-3 rounded-lg border border-slate-200 max-w-2xl w-full">
                <summary className="text-xs font-semibold text-slate-600 cursor-pointer">Sources ({message.sources.length})</summary>
                <ul className="text-xs text-slate-600 space-y-2 mt-2">
                  {message.sources.map((source, sourceIndex) => (
                    <li key={sourceIndex}>
                      {source.url ? (
                        <a href={source.url} target="_blank" rel="noreferrer" className="text-indigo-600 hover:underline">{source.title}</a>
                      ) : (
                        <span className="font-medium">{source.title}</span>
                      )}
                      <span className="text-slate-400"> — {source.provider}</span>
                      {source.snippet && <div className="mt-0.5">{source.snippet}</div>}
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex items-start">
            <div className="bg-white border border-slate-200 shadow-sm px-5 py-3.5 rounded-2xl flex gap-1 items-center">
              {[0, 1, 2].map(index => <div key={index} className="w-2 h-2 bg-slate-300 rounded-full animate-bounce" style={{ animationDelay: `${index * 0.1}s` }} />)}
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </main>

      <footer className="p-4 bg-white border-t border-slate-200">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto relative flex items-center">
          <input
            type="text"
            value={input}
            onChange={event => setInput(event.target.value)}
            placeholder="MINIDORAにメッセージを送信..."
            className="w-full px-5 py-4 pr-14 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-slate-50 shadow-inner"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="absolute right-2 p-2 bg-indigo-600 text-white rounded-lg disabled:opacity-50 hover:bg-indigo-700 transition-colors"
            aria-label="送信"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
            </svg>
          </button>
        </form>
      </footer>

      {showTrace && traceData && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-end sm:items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl w-full max-w-3xl max-h-[85vh] flex flex-col overflow-hidden shadow-2xl">
            <div className="p-4 border-b border-slate-200 flex justify-between items-center bg-slate-50">
              <div>
                <h2 className="text-lg font-semibold text-slate-800">Execution Trace</h2>
                <div className="text-xs text-slate-400 font-mono">{traceData.traceId}</div>
              </div>
              <button onClick={() => setShowTrace(false)} className="text-slate-500 hover:text-slate-800" aria-label="閉じる">✕</button>
            </div>
            <div className="p-6 overflow-y-auto space-y-5 text-sm text-slate-700">
              <TraceBlock title="Normalized Input" value={traceData.normalizedInput} />
              <TraceBlock title="Semantic IR" value={traceData.semanticIR} />
              <TraceBlock title="Operation Plan" value={traceData.operationPlan} />
              <TraceBlock title="Modules Executed" value={traceData.modulesExecuted} />
              <TraceBlock title="Module Outputs" value={traceData.moduleOutputs} />
              <TraceBlock title="Capability Model" value={traceData.modelEvaluation} />
              <TraceBlock title="Strict Language Model" value={traceData.languageModel} />
              <TraceBlock title="External Data Access" value={traceData.externalDataAccess} />
              <TraceBlock title="Stages" value={traceData.stages} />
              <div>
                <strong className="text-slate-900">Validation:</strong>{" "}
                <span className={traceData.validationResult ? "text-emerald-600" : "text-red-600"}>{traceData.validationResult ? "Passed" : "Not passed"}</span>
              </div>
              {traceData.warnings.length > 0 && <TraceBlock title="Warnings" value={traceData.warnings} />}
              {traceData.failures.length > 0 && <TraceBlock title="Failures" value={traceData.failures} danger />}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function TraceBlock({ title, value, danger = false }: { title: string; value: unknown; danger?: boolean }) {
  return (
    <div>
      <strong className={danger ? "text-red-600 block mb-1" : "text-slate-900 block mb-1"}>{title}</strong>
      <pre className={`p-3 rounded-lg overflow-x-auto text-xs whitespace-pre-wrap ${danger ? "bg-red-50 text-red-700" : "bg-slate-900 text-slate-100"}`}>
        {typeof value === "string" ? value : JSON.stringify(value, null, 2)}
      </pre>
    </div>
  );
}
