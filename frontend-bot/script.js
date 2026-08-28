// ============================================================
// SETTINGS — change these two if needed, or use the gear icon
// in the widget itself (it saves your choice in the browser).
// ============================================================
const DEFAULTS = {
  baseUrl: (window.location.protocol !== 'file:') ? window.location.origin : 'http://localhost:8000',
  prefix: '/api/v1',       // must match API_PREFIX in your backend's config.py
  maxLength: 2000       // must match CHAT_MAX_LENGTH in your backend's config.py
};

// ============================================================
// GRAB ALL THE HTML ELEMENTS WE NEED
// ============================================================
const els = {
  launcher: document.getElementById('launcher'),
  launchBadge: document.getElementById('launchBadge'),
  panel: document.getElementById('panel'),
  settingsBtn: document.getElementById('settingsBtn'),
  collapseBtn: document.getElementById('collapseBtn'),
  settingsSheet: document.getElementById('settingsSheet'),
  baseUrlInput: document.getElementById('baseUrlInput'),
  prefixInput: document.getElementById('prefixInput'),
  endpointPreview: document.getElementById('endpointPreview'),
  statusDot: document.getElementById('statusDot'),
  statusText: document.getElementById('statusText'),
  panelBody: document.getElementById('panelBody'),
  emptyState: document.getElementById('emptyState'),
  questionInput: document.getElementById('questionInput'),
  sendBtn: document.getElementById('sendBtn'),
};

// ============================================================
// STATE
// ============================================================
let state = {
  baseUrl: localStorage.getItem('rag_base_url') || DEFAULTS.baseUrl,
  prefix: localStorage.getItem('rag_prefix') || DEFAULTS.prefix,
  maxLength: DEFAULTS.maxLength,
  open: false,
  collapsed: false,
  busy: false,
};

function persist(){
  localStorage.setItem('rag_base_url', state.baseUrl);
  localStorage.setItem('rag_prefix', state.prefix);
}
function chatEndpoint(){
  return state.baseUrl.replace(/\/$/, '') + state.prefix.replace(/\/$/, '') + '/chat';
}
function refreshPreview(){ els.endpointPreview.textContent = chatEndpoint(); }

els.baseUrlInput.value = state.baseUrl;
els.prefixInput.value = state.prefix;
refreshPreview();

els.baseUrlInput.addEventListener('input', () => {
  state.baseUrl = els.baseUrlInput.value.trim() || DEFAULTS.baseUrl;
  persist(); refreshPreview(); checkStatus();
});
els.prefixInput.addEventListener('input', () => {
  let v = els.prefixInput.value.trim() || DEFAULTS.prefix;
  if (!v.startsWith('/')) v = '/' + v;
  state.prefix = v;
  persist(); refreshPreview();
});

// ============================================================
// OPEN / CLOSE / COLLAPSE THE WIDGET
// ============================================================
els.launcher.addEventListener('click', () => {
  state.open = !state.open;
  els.launcher.classList.toggle('open', state.open);
  els.panel.classList.toggle('open', state.open);
  els.launchBadge.classList.add('hidden');
  if (state.open) setTimeout(() => els.questionInput.focus(), 200);
});

els.collapseBtn.addEventListener('click', () => {
  state.collapsed = !state.collapsed;
  els.panel.classList.toggle('collapsed', state.collapsed);
});

els.settingsBtn.addEventListener('click', () => {
  els.settingsSheet.classList.toggle('open');
});

// ============================================================
// CHECK IF THE BACKEND IS ONLINE (calls GET /ready)
// ============================================================
async function checkStatus(){
  setStatus('checking', 'connecting…');
  try{
    const res = await fetch(state.baseUrl.replace(/\/$/, '') + '/ready');
    if (res.ok) setStatus('ready', 'Online');
    else if (res.status === 503) setStatus('down', 'Index not ready');
    else setStatus('down', `HTTP ${res.status}`);
  } catch(e){
    setStatus('down', 'Offline');
  }
}
function setStatus(kind, label){
  els.statusDot.className = 'dot' + (kind === 'ready' ? ' ready' : kind === 'down' ? ' down' : ' pulsing');
  els.statusText.textContent = label;
}
checkStatus();
setInterval(checkStatus, 20000); // re-check every 20 seconds

// ============================================================
// RENDERING MESSAGES IN THE CHAT WINDOW
// ============================================================
function botSvg(){
  return `<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <rect x="4" y="8" width="16" height="12" rx="3"/><path d="M12 8V4"/>
    <circle cx="12" cy="3" r="1.2" fill="white" stroke="none"/>
    <circle cx="9" cy="14" r="1.3" fill="white" stroke="none"/>
    <circle cx="15" cy="14" r="1.3" fill="white" stroke="none"/>
  </svg>`;
}

function addMessage({ role, text, refused }){
  if (els.emptyState) { els.emptyState.remove(); }
  const row = document.createElement('div');
  row.className = 'row ' + role + (refused ? ' refused' : '');

  if (role === 'bot'){
    const av = document.createElement('div');
    av.className = 'mini-avatar';
    av.innerHTML = botSvg();
    row.appendChild(av);
  }

  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;
  row.appendChild(bubble);

  els.panelBody.appendChild(row);
  els.panelBody.scrollTop = els.panelBody.scrollHeight;

  if (role === 'bot' && !state.open){
    els.launchBadge.classList.remove('hidden');
  }
}

function addThinking(){
  if (els.emptyState) els.emptyState.remove();
  const row = document.createElement('div');
  row.className = 'thinking-row';
  row.id = 'thinkingRow';
  row.innerHTML = `
    <div class="mini-avatar">${botSvg()}</div>
    <div class="thinking-bubble"><span></span><span></span><span></span></div>`;
  els.panelBody.appendChild(row);
  els.panelBody.scrollTop = els.panelBody.scrollHeight;
}
function removeThinking(){
  const t = document.getElementById('thinkingRow');
  if (t) t.remove();
}

function setBusy(busy){
  state.busy = busy;
  els.sendBtn.disabled = busy;
  els.questionInput.disabled = busy;
}

// ============================================================
// SEND A QUESTION TO THE BACKEND (POST {prefix}/chat)
// ============================================================
async function send(){
  const question = els.questionInput.value.trim();
  if (!question || state.busy) return;
  if (question.length > state.maxLength){
    addMessage({ role: 'bot', text: `That's over the ${state.maxLength}-character limit — try a shorter question.`, refused: true });
    return;
  }

  addMessage({ role: 'user', text: question });
  els.questionInput.value = '';
  setBusy(true);
  addThinking();

  try{
    const res = await fetch(chatEndpoint(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });

    let data;
    try{ data = await res.json(); }
    catch(e){ throw new Error(`Non-JSON response (HTTP ${res.status})`); }

    removeThinking();

    if (!res.ok && res.status >= 500){
      addMessage({ role: 'bot', text: data.answer || 'Something went wrong processing that.', refused: true });
      return;
    }

    addMessage({ role: 'bot', text: data.answer, refused: !data.success });

  } catch(err){
    removeThinking();
    addMessage({ role: 'bot', text: `Couldn't reach the server. Check the gear icon to confirm the API address is correct.`, refused: true });
  } finally{
    setBusy(false);
    if (state.open) els.questionInput.focus();
  }
}

els.sendBtn.addEventListener('click', send);
els.questionInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') send();
});
