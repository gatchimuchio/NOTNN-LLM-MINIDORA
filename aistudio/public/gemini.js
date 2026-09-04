const messages = document.querySelector('#geminiMessages');
const form = document.querySelector('#geminiComposer');
const input = document.querySelector('#geminiInput');
const sendButton = document.querySelector('#geminiSend');
const statusEl = document.querySelector('#geminiStatus');
let history = [];
let busy = false;
let channel = null;
try {
  if ('BroadcastChannel' in globalThis) {
    channel = new BroadcastChannel('minidora-gemini-compare-v1');
    channel.onmessage = event => {
      if (event.data?.type === 'prompt') submit(event.data.text, true);
    };
    channel.postMessage({ type: 'ready' });
  }
} catch {}

function esc(value) { return String(value ?? '').replace(/[&<>"']/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c])); }
function nowLabel() { return new Intl.DateTimeFormat('ja-JP', { hour: '2-digit', minute: '2-digit' }).format(new Date()); }
function welcome() {
  messages.innerHTML = `<div class="gemini-welcome"><div class="gemini-mark">G</div><h1>Gemini Comparator</h1><p>MINIDORAとは完全に独立した比較窓です。比較モード中は同じユーザー入力だけを受け取り、MINIDORAの内部Data・Sources・Traceは受け取りません。</p></div>`;
}
welcome();
function removeWelcome() { messages.querySelector('.gemini-welcome')?.remove(); }
function addUser(text) {
  removeWelcome();
  const el = document.createElement('article');
  el.className = 'gemini-message user';
  el.innerHTML = `<div class="bubble">${esc(text)}</div>`;
  messages.appendChild(el); messages.scrollTop = messages.scrollHeight;
}
function addModel(text, model) {
  removeWelcome();
  const el = document.createElement('article');
  el.className = 'gemini-message model';
  el.innerHTML = `<div class="gemini-message-head"><strong>Gemini</strong><time>${nowLabel()}</time></div><div class="bubble">${esc(text)}</div>${model ? `<div class="gemini-model-label">${esc(model)}</div>` : ''}`;
  messages.appendChild(el); messages.scrollTop = messages.scrollHeight;
}
function addError(text) {
  removeWelcome();
  const el = document.createElement('article');
  el.className = 'gemini-message model';
  el.innerHTML = `<div class="gemini-message-head"><strong>Gemini</strong><time>${nowLabel()}</time></div><div class="bubble error-message">${esc(text)}</div>`;
  messages.appendChild(el); messages.scrollTop = messages.scrollHeight;
}
async function submit(text, synced = false) {
  text = String(text || '').trim();
  if (!text || busy) return;
  busy = true; sendButton.disabled = true; addUser(text);
  if (!synced) { input.value = ''; resizeInput(); }
  try {
    const response = await fetch('/api/gemini', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, history }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || data.error || `HTTP ${response.status}`);
    addModel(data.response || '', data.model || '');
    history.push({ role: 'user', parts: [{ text }] });
    history.push({ role: 'model', parts: [{ text: data.response || '' }] });
    if (history.length > 24) history = history.slice(-24);
  } catch (error) { addError(`Gemini比較失敗: ${error.message}`); }
  finally { busy = false; sendButton.disabled = false; input.focus(); }
}
function resizeInput() { input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 160) + 'px'; }
form.addEventListener('submit', event => { event.preventDefault(); submit(input.value, false); });
input.addEventListener('input', resizeInput);
input.addEventListener('keydown', event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); form.requestSubmit(); } });
document.querySelector('#clearGemini').addEventListener('click', () => { history = []; welcome(); input.focus(); });
async function refreshStatus() {
  try {
    const response = await fetch('/bridge/status', { cache: 'no-store' });
    const data = await response.json();
    const configured = Boolean(data.gemini?.configured);
    statusEl.classList.remove('ok', 'bad', 'pending');
    statusEl.classList.add(configured ? 'ok' : 'bad');
    statusEl.textContent = configured ? `準備済み${data.gemini?.model ? ` · ${data.gemini.model}` : ''}` : 'Gemini未設定';
  } catch {
    statusEl.classList.remove('ok', 'pending'); statusEl.classList.add('bad'); statusEl.textContent = '状態不明';
  }
}
refreshStatus(); setInterval(refreshStatus, 30000);
