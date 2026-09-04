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
  if (!target.startsWith(path.resolve(PUBLIC_DIR) + path.sep) && target !== path.resolve(PUBLIC_DIR, 'index.html')) {
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
    const u = new URL(BACKEND);
    return u.protocol === 'https:' || u.protocol === 'http:';
  } catch {
    return false;
  }
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
        detail: 'AI Studio frontend is running, but the real MINIDORA backend URL is not configured.',
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

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url || '/', `http://${req.headers.host || 'localhost'}`);
    const pathname = url.pathname;

    if (req.method === 'GET' && pathname === '/') return sendFile(res, 'index.html');
    if (req.method === 'GET' && pathname.startsWith('/static/')) {
      const rel = pathname.slice('/static/'.length);
      if (!rel || rel.includes('..')) return sendJson(res, 403, { error: 'forbidden' });
      return sendFile(res, rel);
    }

    if (req.method === 'GET' && pathname === '/health') {
      if (!backendConfigured()) {
        return sendJson(res, 503, {
          ok: false,
          frontend: 'ready',
          backend: 'not_configured',
          service: 'MINIDORA AI Studio Bridge',
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
      catch (e) {
        if (e.code === 'BODY_TOO_LARGE') return sendJson(res, 413, { error: 'body_too_large' });
        throw e;
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

    return sendJson(res, 404, { error: 'not_found' });
  } catch (error) {
    return sendJson(res, 500, { error: 'bridge_internal_error', detail: String(error?.message || error) });
  }
});

server.listen(PORT, HOST, () => {
  console.log(`MINIDORA AI Studio Bridge listening on http://${HOST}:${PORT}`);
  console.log(BACKEND ? 'MINIDORA backend configured.' : 'MINIDORA_BACKEND_URL is NOT configured.');
});
