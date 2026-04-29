const messagesEl = document.getElementById('messages');

function appendMessage(role, text, meta = '') {
  const div = document.createElement('div');
  div.className = `message ${role}`;
  if (meta) {
    const name = document.createElement('div');
    name.className = 'message-meta';
    name.textContent = meta;
    div.appendChild(name);
  }
  const body = document.createElement('div');
  body.textContent = text;
  div.appendChild(body);
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function loadModelConfig() {
  const res = await fetch('/model-config');
  const cfg = await res.json();
  document.getElementById('model-name').value = cfg.name || 'default';
  document.getElementById('model-provider').value = cfg.provider || 'mock';
  document.getElementById('model-id').value = cfg.model || 'mock-roleplay';
  document.getElementById('model-base-url').value = cfg.base_url || '';
  document.getElementById('model-api-key').value = '';
  document.getElementById('model-config-status').textContent = cfg.api_key_set ? 'API Key 已保存' : '未保存 API Key';
}

async function saveModelConfig(e) {
  e.preventDefault();
  const payload = {
    name: document.getElementById('model-name').value || 'default',
    provider: document.getElementById('model-provider').value,
    model: document.getElementById('model-id').value || 'mock-roleplay',
    base_url: document.getElementById('model-base-url').value,
    api_key: document.getElementById('model-api-key').value,
    is_default: true,
  };
  const res = await fetch('/model-config', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload),
  });
  const cfg = await res.json();
  document.getElementById('model-config-status').textContent = `已保存：${cfg.provider} / ${cfg.model}${cfg.api_key_set ? ' / key已设置' : ''}`;
  document.getElementById('model-api-key').value = '';
}

async function loadMultiCharacters() {
  const res = await fetch('/multi-characters');
  const data = await res.json();
  const list = document.getElementById('multi-character-list');
  list.innerHTML = '';
  data.forEach(c => {
    const div = document.createElement('div');
    div.className = 'character-item';
    const state = c.state || {};
    div.innerHTML = `<strong>${c.name}</strong><br><span>${c.character_id}</span><br><small>goal: ${state.goal || ''} | mood: ${state.mood || 'neutral'}</small>`;
    list.appendChild(div);
  });
}

async function createMultiCharacter(e) {
  e.preventDefault();
  const payload = {
    character_id: document.getElementById('mc-id').value,
    name: document.getElementById('mc-name').value,
    persona: document.getElementById('mc-persona').value,
    speaking_style: '',
    goal: document.getElementById('mc-goal').value,
    mood: document.getElementById('mc-mood').value || 'neutral',
    location: 'unknown',
    status: 'active',
  };
  await fetch('/multi-characters', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload),
  });
  await loadMultiCharacters();
}

async function sendMultiChat(e) {
  e.preventDefault();
  const input = document.getElementById('chat-message');
  const content = input.value.trim();
  if (!content) return;
  input.value = '';
  appendMessage('user', content, '你');

  const payload = {
    content,
    max_speakers: Number(document.getElementById('max-speakers').value || 2),
    auto_simulate_world: document.getElementById('auto-simulate-world').checked,
  };

  const res = await fetch('/chat/multi', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const text = await res.text();
    appendMessage('assistant error', text, '错误');
    return;
  }

  const data = await res.json();
  (data.replies || []).forEach(r => appendMessage('assistant', r.text, r.character_name || r.character_id));
  document.getElementById('debug-scheduler').textContent = `${data.scheduler || ''}\n\n${data.world_simulation || ''}`;
  await refreshDebug();
}

async function refreshDebug() {
  const [worldRes, graphRes] = await Promise.all([fetch('/world'), fetch('/graph')]);
  const world = await worldRes.json();
  const graph = await graphRes.json();
  document.getElementById('debug-world').textContent = JSON.stringify(world, null, 2);
  document.getElementById('debug-graph').textContent = JSON.stringify(graph, null, 2);
}

document.getElementById('model-config-form').onsubmit = saveModelConfig;
document.getElementById('multi-character-form').onsubmit = createMultiCharacter;
document.getElementById('multi-chat-form').onsubmit = sendMultiChat;
document.getElementById('refresh-debug').onclick = refreshDebug;

loadModelConfig();
loadMultiCharacters();
refreshDebug();
