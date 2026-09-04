import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PUBLIC_DIR = path.join(__dirname, 'public');
const PORT = Number.parseInt(process.env.PORT || '3000', 10);
const HOST = process.env.HOST || '0.0.0.0';
const BACKEND = (process.env.MINIDORA_BACKEND_URL || '').trim().replace(/\/$/, '');
const REQUEST_TIMEOUT_MS = Number.parseInt(process.env.MINIDORA_PROXY_TIMEOUT_MS || '30000', 10);
const MAX_BODY = 256_000;

const GEMINI_API_KEY = (process.env.GEMINI_API_KEY || '').trim();
const GEMINI_MODEL = (process.env.GEMINI_MODEL || 'gemini-2.5-flash').trim();
const GEMINI_API_BASE = (process.env.GEMINI_API_BASE || 'https://generativelanguage.googleapis.com').trim().replace(/\/$/, '');
const GEMINI_TIMEOUT_MS = Number.parseInt(process.env.GEMINI_TIMEOUT_MS || '45000', 10);

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
};

function sendJson(res, status, body) {
  const raw = Buffer.from(JSON.stringify(body));
  res.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': raw.length,
    'cache-control': 'no-store',
  });
  res.end(raw);
}

function sendFile(res, filename) {
  const target = path.resolve(PUBLIC_DIR, filename);
  const publicRoot = path.resolve(PUBLIC_DIR);
  if (!target.startsWith(publicRoot + path.sep) && target !== path.resolve(PUBLIC_DIR, 'index.html')) {
    return sendJson(res, 403, { error: 'forbidden' });
  }
  if (!fs.existsSync(target) || !fs.statSync(target).isFile()) {
    return sendJson(res, 404, { error: 'not_found' });
  }
  const raw = fs.readFileSync(target);
  res.writeHead(200, {
    'content-type': MIME[path.extname(target)] || 'application/octet-stream',
    'content-length': raw.length,
    'cache-control': 'no-cache',
  });
  res.end(raw);
}

async function readBody(req) {
  return await new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on('data', chunk => {
      size += chunk.length;
      if (size > MAX_BODY) {
        reject(Object.assign(new Error('body_too_large'), { code: 'BODY_TOO_LARGE' }));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
  });
}

function backendConfigured() {
  if (!BACKEND) return false;
  try {
    const url = new URL(BACKEND);
    return url.protocol === 'https:' || url.protocol === 'http:';
  } catch {
    return false;
  }
}

function geminiConfigured() {
  return Boolean(GEMINI_API_KEY && GEMINI_MODEL && GEMINI_API_BASE);
}

async function backendFetch(endpoint, options = {}) {
  if (!backendConfigured()) {
    const error = new Error('MINIDORA_BACKEND_URL is not configured');
    error.code = 'BACKEND_NOT_CONFIGURED';
    throw error;
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    return await fetch(BACKEND + endpoint, {
      ...options,
      signal: controller.signal,
      headers: {
        ...(options.body ? { 'content-type': 'application/json' } : {}),
        ...(options.headers || {}),
      },
    });
  } finally {
    clearTimeout(timer);
  }
}

async function proxyJson(res, endpoint, options = {}) {
  try {
    const upstream = await backendFetch(endpoint, options);
    const text = await upstream.text();
    let body;
    try { body = JSON.parse(text); }
    catch { body = { error: 'invalid_backend_response', detail: text.slice(0, 500) }; }
    return sendJson(res, upstream.status, body);
  } catch (error) {
    if (error.code === 'BACKEND_NOT_CONFIGURED') {
      return sendJson(res, 503, {
        error: 'minidora_backend_not_configured',
        detail: 'The MINIDORA product UI is running, but the real MINIDORA backend URL is not configured.',
      });
    }
    if (error.name === 'AbortError') {
      return sendJson(res, 504, { error: 'minidora_backend_timeout' });
    }
    return sendJson(res, 502, {
      error: 'minidora_backend_unreachable',
      detail: String(error?.message || error),
    });
  }
}

function normalizeGeminiHistory(history) {
  if (!Array.isArray(history)) return [];
  const cleaned = [];
  for (const item of history.slice(-24)) {
    const role = item?.role === 'model' ? 'model' : item?.role === 'user' ? 'user' : null;
    if (!role || !Array.isArray(item.parts)) continue;
    const text = item.parts.map(part => String(part?.text || '')).join('').trim();
    if (!text) continue;
    cleaned.push({ role, parts: [{ text: text.slice(0, 20_000) }] });
  }
  return cleaned;
}

async function callGemini(payload) {
  if (!geminiConfigured()) {
    const error = new Error('GEMINI_API_KEY is not configured');
    error.code = 'GEMINI_NOT_CONFIGURED';
    throw error;
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), GEMINI_TIMEOUT_MS);
  try {
    const endpoint = `${GEMINI_API_BASE}/v1beta/models/${encodeURIComponent(GEMINI_MODEL)}:generateContent?key=${encodeURIComponent(GEMINI_API_KEY)}`;
    const response = await fetch(endpoint, {
      method: 'POST',
      signal: controller.signal,
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const text = await response.text();
    let body;
    try { body = JSON.parse(text); }
    catch { body = { error: { message: text.slice(0, 500) } }; }
    if (!response.ok) {
      const error = new Error(body?.error?.message || `Gemini HTTP ${response.status}`);
      error.status = response.status;
      throw error;
    }
    return body;
  } finally {
    clearTimeout(timer);
  }
}

function extractGeminiText(body) {
  const parts = body?.candidates?.[0]?.content?.parts;
  if (!Array.isArray(parts)) return '';
  return parts.map(part => typeof part?.text === 'string' ? part.text : '').join('').trim();
}

async function handleBridgeStatus(res) {
  let minidoraOk = false;
  let minidoraStatus = null;
  let minidoraDetail = null;
  if (backendConfigured()) {
    try {
      const response = await backendFetch('/health');
      minidoraStatus = response.status;
      minidoraOk = response.ok;
      if (!response.ok) minidoraDetail = (await response.text()).slice(0, 300);
    } catch (error) {
      minidoraDetail = String(error?.message || error);
    }
  }
  return sendJson(res, 200, {
    ok: true,
    frontend: 'ready',
    minidora: {
      configured: backendConfigured(),
      ok: minidoraOk,
      status: minidoraStatus,
      detail: minidoraDetail,
    },
    gemini: {
      configured: geminiConfigured(),
      model: geminiConfigured() ? GEMINI_MODEL : null,
    },
  });
}

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url || '/', `http://${req.headers.host || 'localhost'}`);
    const pathname = url.pathname;

    if (req.method === 'GET' && pathname === '/') return sendFile(res, 'index.html');
    if (req.method === 'GET' && (pathname === '/gemini' || pathname === '/gemini.html')) return sendFile(res, 'gemini.html');
    if (req.method === 'GET' && pathname.startsWith('/static/')) {
      const rel = pathname.slice('/static/'.length);
      if (!rel || rel.includes('..')) return sendJson(res, 403, { error: 'forbidden' });
      return sendFile(res, rel);
    }

    if (req.method === 'GET' && pathname === '/bridge/status') {
      return await handleBridgeStatus(res);
    }

    if (req.method === 'GET' && pathname === '/health') {
      if (!backendConfigured()) {
        return sendJson(res, 503, {
          ok: false,
          frontend: 'ready',
          backend: 'not_configured',
          service: 'MINIDORA Product UI',
        });
      }
      return await proxyJson(res, '/health');
    }

    if (req.method === 'GET' && pathname === '/api/capabilities') {
      return await proxyJson(res, '/api/capabilities');
    }

    const traceMatch = pathname.match(/^\/api\/trace\/([A-Za-z0-9_-]+)$/);
    if (req.method === 'GET' && traceMatch) {
      return await proxyJson(res, `/api/trace/${encodeURIComponent(traceMatch[1])}`);
    }

    if (req.method === 'POST' && pathname === '/api/chat') {
      let raw;
      try { raw = await readBody(req); }
      catch (error) {
        if (error.code === 'BODY_TOO_LARGE') return sendJson(res, 413, { error: 'body_too_large' });
        throw error;
      }
      let payload;
      try { payload = JSON.parse(raw.toString('utf-8')); }
      catch { return sendJson(res, 400, { error: 'invalid_json' }); }
      const message = String(payload?.message || '').trim();
      const sessionId = String(payload?.session_id || 'default').trim() || 'default';
      if (!message) return sendJson(res, 400, { error: 'message_required' });
      return await proxyJson(res, '/api/chat', {
        method: 'POST',
        body: JSON.stringify({ message, session_id: sessionId }),
      });
    }

    if (req.method === 'POST' && pathname === '/api/gemini') {
      let raw;
      try { raw = await readBody(req); }
      catch (error) {
        if (error.code === 'BODY_TOO_LARGE') return sendJson(res, 413, { error: 'body_too_large' });
        throw error;
      }
      let payload;
      try { payload = JSON.parse(raw.toString('utf-8')); }
      catch { return sendJson(res, 400, { error: 'invalid_json' }); }
      const message = String(payload?.message || '').trim();
      if (!message) return sendJson(res, 400, { error: 'message_required' });

      try {
        const history = normalizeGeminiHistory(payload?.history);
        const body = await callGemini({
          contents: [...history, { role: 'user', parts: [{ text: message.slice(0, 20_000) }] }],
        });
        const responseText = extractGeminiText(body);
        if (!responseText) return sendJson(res, 502, { error: 'gemini_empty_response' });
        return sendJson(res, 200, {
          response: responseText,
          model: GEMINI_MODEL,
          usage: body?.usageMetadata || null,
        });
      } catch (error) {
        if (error.code === 'GEMINI_NOT_CONFIGURED') {
          return sendJson(res, 503, {
            error: 'gemini_not_configured',
            detail: 'Gemini comparison is independent and requires GEMINI_API_KEY to be configured.',
          });
        }
        if (error.name === 'AbortError') return sendJson(res, 504, { error: 'gemini_timeout' });
        return sendJson(res, error.status || 502, {
          error: 'gemini_request_failed',
          detail: String(error?.message || error),
        });
      }
    }

    return sendJson(res, 404, { error: 'not_found' });
  } catch (error) {
    return sendJson(res, 500, { error: 'bridge_internal_error', detail: String(error?.message || error) });
  }
});

server.listen(PORT, HOST, () => {
  console.log(`MINIDORA Product UI listening on http://${HOST}:${PORT}`);
  console.log(BACKEND ? 'MINIDORA backend configured.' : 'MINIDORA_BACKEND_URL is NOT configured.');
  console.log(geminiConfigured() ? `Gemini comparator configured (${GEMINI_MODEL}).` : 'GEMINI_API_KEY is NOT configured.');
});
