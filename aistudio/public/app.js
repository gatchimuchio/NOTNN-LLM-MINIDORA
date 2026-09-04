const messages = document.querySelector('#messages');
const form = document.querySelector('#composer');
const input = document.querySelector('#input');
const sendButton = document.querySelector('#send');
const composerState = document.querySelector('#composerState');
const compareSync = document.querySelector('#compareSync');
const minidoraStatus = document.querySelector('#minidoraStatus');
const minidoraStatusText = document.querySelector('#minidoraStatusText');
const traceBackdrop = document.querySelector('#traceBackdrop');
const traceDrawer = document.querySelector('#traceDrawer');
const traceContent = document.querySelector('#traceContent');
const closeTraceButton = document.querySelector('#closeTrace');

function storageGet(key) { try { return localStorage.getItem(key); } catch { return null; } }
function storageSet(key, value) { try { localStorage.setItem(key, value); } catch {} }
function newId() {
  try { if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID(); } catch {}
  return `id_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 12)}`;
}

let sessionId = storageGet('minidora_session') || newId();
storageSet('minidora_session', sessionId);
let busy = false;
let comparatorWindow = null;
let comparatorReady = false;
let pendingComparePrompt = null;
let compareChannel = null;
try {
  if ('BroadcastChannel' in globalThis) {
    compareChannel = new BroadcastChannel('minidora-gemini-compare-v1');
    compareChannel.onmessage = event => {
      if (event.data?.type === 'ready') {
        comparatorReady = true;
        if (pendingComparePrompt) {
          compareChannel.postMessage({ type: 'prompt', text: pendingComparePrompt });
          pendingComparePrompt = null;
        }
      }
    };
  }
} catch {}

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
}
function safeUrl(value) {
  try {
    const url = new URL(String(value || ''), location.origin);
    return /^https?:$/.test(url.protocol) ? url.href : '';
  } catch { return ''; }
}
function nowLabel() {
  return new Intl.DateTimeFormat('ja-JP', { hour: '2-digit', minute: '2-digit' }).format(new Date());
}

function welcome() {
  messages.innerHTML = `<div class="welcome">
    <div class="welcome-mark">M</div>
    <h1>MINIDORA</h1>
    <p>非ニューラルCoreに交換可能なCapability Moduleを接続した製品版です。検索・要約・計算・参照・会話をMINIDORA自身の経路で処理し、応答の成立経路をTraceできます。</p>
    <div class="welcome-chips">
      <button type="button" class="welcome-chip" data-prompt="今日のニュースは？">今日のニュースは？</button>
      <button type="button" class="welcome-chip" data-prompt="3行で要約して">3行で要約して</button>
      <button type="button" class="welcome-chip" data-prompt="(12+8)*3">(12+8)*3</button>
      <button type="button" class="welcome-chip" data-prompt="MINIDORAは何ができる？">何ができる？</button>
    </div>
  </div>`;
  messages.querySelectorAll('[data-prompt]').forEach(button => {
    button.addEventListener('click', () => {
      input.value = button.dataset.prompt || '';
      resizeInput();
      input.focus();
    });
  });
}
welcome();

function removeWelcome() { messages.querySelector('.welcome')?.remove(); }
function addUser(text) {
  removeWelcome();
  const el = document.createElement('article');
  el.className = 'message user';
  el.innerHTML = `<div class="message-bubble">${esc(text)}</div>`;
  messages.appendChild(el);
  messages.scrollTop = messages.scrollHeight;
}
function addLoading(id) {
  removeWelcome();
  const el = document.createElement('article');
  el.className = 'message assistant';
  el.dataset.loadingId = id;
  el.innerHTML = `<div class="message-head"><div class="message-author"><span class="author-dot"></span> MINIDORA</div></div><div class="loading-row">応答を生成中...</div>`;
  messages.appendChild(el);
  messages.scrollTop = messages.scrollHeight;
}
function replaceLoading(id, html) {
  const target = messages.querySelector(`[data-loading-id="${CSS.escape(id)}"]`);
  if (target) target.outerHTML = html;
  else messages.insertAdjacentHTML('beforeend', html);
  messages.scrollTop = messages.scrollHeight;
}
function sourceHtml(sources = []) {
  if (!sources.length) return '';
  const items = sources.map((source, index) => {
    const title = source.題名 || source.title || source.name || `Source ${index + 1}`;
    const publisher = source.出典 || source.source || source.publisher || '';
    const url = safeUrl(source.URL || source.url || source.link || '');
    const label = url ? `<a href="${esc(url)}" target="_blank" rel="noreferrer">${esc(title)}</a>` : esc(title);
    return `<div class="source-item">${label}${publisher ? `<div class="source-meta">${esc(publisher)}</div>` : ''}</div>`;
  }).join('');
  return `<div class="sources-panel" hidden>${items}</div>`;
}
function assistantHtml(data) {
  const sources = data.sources || [];
  const traceId = data.trace_id || '';
  const route = data.route || '';
  return `<article class="message assistant">
    <div class="message-head"><div class="message-author"><span class="author-dot"></span> MINIDORA</div><time class="message-time">${nowLabel()}</time></div>
    <div class="message-bubble">${esc(data.response || '')}</div>
    <div class="message-actions">
      ${traceId ? `<button class="action-button" data-trace="${esc(traceId)}" type="button">Trace</button>` : ''}
      ${sources.length ? `<button class="action-button" data-sources type="button">Sources ${sources.length}</button>` : ''}
      ${route ? `<span class="route-label">${esc(route)}</span>` : ''}
    </div>
    ${sourceHtml(sources)}
  </article>`;
}
function errorHtml(message) {
  return `<article class="message assistant"><div class="message-head"><div class="message-author"><span class="author-dot"></span> MINIDORA</div><time class="message-time">${nowLabel()}</time></div><div class="message-bubble error-message">${esc(message)}</div></article>`;
}

function bindMessageActions() {
  messages.querySelectorAll('[data-trace]').forEach(button => {
    if (button.dataset.bound) return;
    button.dataset.bound = '1';
    button.addEventListener('click', () => openTrace(button.dataset.trace));
  });
  messages.querySelectorAll('[data-sources]').forEach(button => {
    if (button.dataset.bound) return;
    button.dataset.bound = '1';
    button.addEventListener('click', () => {
      const panel = button.closest('.message')?.querySelector('.sources-panel');
      if (!panel) return;
      panel.hidden = !panel.hidden;
      button.textContent = panel.hidden ? `Sources ${panel.children.length}` : 'Sources 閉じる';
    });
  });
}

function openComparator() {
  try {
    if (comparatorWindow && !comparatorWindow.closed) {
      comparatorWindow.focus();
      return comparatorWindow;
    }
    comparatorReady = false;
    comparatorWindow = window.open('/gemini', 'minidora-gemini-comparator', 'popup=yes,width=760,height=900,resizable=yes,scrollbars=yes');
    return comparatorWindow;
  } catch { return null; }
}
document.querySelector('#openComparator').addEventListener('click', openComparator);
document.querySelector('#openComparatorTop').addEventListener('click', openComparator);

function syncPromptToGemini(text) {
  if (!compareSync.checked) return;
  const win = openComparator();
  if (!win) {
    composerState.textContent = 'Gemini比較窓を開けませんでした';
    return;
  }
  if (compareChannel && comparatorReady) {
    compareChannel.postMessage({ type: 'prompt', text });
  } else if (compareChannel) {
    pendingComparePrompt = text;
  }
}

function openDrawer() {
  traceBackdrop.classList.remove('hidden');
  traceDrawer.classList.remove('hidden');
  traceDrawer.setAttribute('aria-hidden', 'false');
}
function closeDrawer() {
  traceBackdrop.classList.add('hidden');
  traceDrawer.classList.add('hidden');
  traceDrawer.setAttribute('aria-hidden', 'true');
}
closeTraceButton.addEventListener('click', closeDrawer);
traceBackdrop.addEventListener('click', closeDrawer);
document.addEventListener('keydown', event => { if (event.key === 'Escape') closeDrawer(); });

async function openTrace(id) {
  if (!id) return;
  openDrawer();
  traceContent.innerHTML = '<div class="trace-loading">Traceを読み込んでいます...</div>';
  try {
    const response = await fetch('/api/trace/' + encodeURIComponent(id));
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || data.error || `HTTP ${response.status}`);
    const trace = data.trace || {};
    const events = trace['イベント'] || trace.events || [];
    const eventHtml = events.map(event => {
      const number = event['番号'] ?? event.number ?? '';
      const stage = event['段階'] ?? event.stage ?? '';
      const module = event['モジュール'] ?? event.module ?? '';
      const version = event['版'] ?? event.version ?? '';
      const payload = { input: event['入力'] ?? event.input, output: event['出力'] ?? event.output, evidence: event['根拠'] ?? event.evidence };
      return `<section class="trace-event"><div class="trace-event-title"><span>${esc(number)}. ${esc(stage)}</span></div><div class="trace-event-sub">${esc(module)}${version ? ` / ${esc(version)}` : ''}</div><pre>${esc(JSON.stringify(payload, null, 2))}</pre></section>`;
    }).join('');
    const valid = data.valid !== false;
    traceContent.innerHTML = `<div class="trace-summary">
      <div class="trace-key">検証</div><div class="${valid ? 'trace-valid' : 'trace-invalid'}">${valid ? 'hash chain valid' : 'invalid trace'}</div>
      <div class="trace-key">経路</div><div>${esc(trace['経路'] ?? trace.route ?? '—')}</div>
      <div class="trace-key">状態</div><div>${esc(trace['状態'] ?? trace.status ?? '—')}</div>
      <div class="trace-key">Trace ID</div><div class="trace-hash">${esc(trace['追跡ID'] ?? trace.trace_id ?? id)}</div>
      <div class="trace-key">Root hash</div><div class="trace-hash">${esc(trace['ルートハッシュ'] ?? trace.root_hash ?? '—')}</div>
      <div class="trace-key">前応答hash</div><div class="trace-hash">${esc(trace['前応答ハッシュ'] ?? trace.previous_hash ?? '—')}</div>
    </div>${eventHtml || '<div class="trace-loading">イベント記録はありません。</div>'}`;
  } catch (error) {
    traceContent.innerHTML = `<div class="trace-loading error-message">Trace取得失敗: ${esc(error.message)}</div>`;
  }
}

async function submit(text) {
  text = String(text || '').trim();
  if (busy || !text) return;
  busy = true;
  sendButton.disabled = true;
  addUser(text);
  const requestId = newId();
  addLoading(requestId);
  syncPromptToGemini(text);
  input.value = '';
  resizeInput();
  composerState.textContent = compareSync.checked ? 'MINIDORAへ送信 / Gemini比較窓へ入力同期' : 'MINIDORAへ送信中';
  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message: text }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || data.error || `HTTP ${response.status}`);
    replaceLoading(requestId, assistantHtml(data));
    bindMessageActions();
    composerState.textContent = compareSync.checked ? 'MINIDORA応答完了 / Geminiは独立比較窓' : 'MINIDORA応答完了';
  } catch (error) {
    replaceLoading(requestId, errorHtml(`接続または処理に失敗しました: ${error.message}`));
    composerState.textContent = 'MINIDORA接続を確認してください';
  } finally {
    busy = false;
    sendButton.disabled = false;
    input.focus();
  }
}

function resizeInput() {
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 160) + 'px';
}
form.addEventListener('submit', event => { event.preventDefault(); submit(input.value); });
input.addEventListener('input', resizeInput);
input.addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

document.querySelector('#newChat').addEventListener('click', () => {
  sessionId = newId();
  storageSet('minidora_session', sessionId);
  welcome();
  closeDrawer();
  composerState.textContent = 'MINIDORAへ送信';
  input.focus();
});

function setBackendStatus(ok, configured) {
  minidoraStatus.classList.remove('ok', 'bad', 'pending');
  minidoraStatus.classList.add(ok ? 'ok' : 'bad');
  minidoraStatusText.textContent = ok ? '接続済み' : (configured ? '接続失敗' : '未設定');
}
async function refreshStatus() {
  try {
    const response = await fetch('/bridge/status', { cache: 'no-store' });
    const data = await response.json();
    const status = data.minidora || {};
    setBackendStatus(Boolean(status.ok), Boolean(status.configured));
  } catch { setBackendStatus(false, true); }
}
refreshStatus();
setInterval(refreshStatus, 30000);
