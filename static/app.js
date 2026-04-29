const messagesEl = document.getElementById('messages');
const settingsModal = document.getElementById('settings-modal');
let charactersCache = [];

function appendMessage(role, text, meta = '') {
  const empty = messagesEl.querySelector('.empty-state');
  if (empty) empty.remove();

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

function openSettings() {
  settingsModal.classList.remove('hidden');
}

function closeSettings() {
  settingsModal.classList.add('hidden');
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

function characterCard(c, compact = false) {
  const state = c.state || {};
  const div = document.createElement('div');
  div.className = 'character-item';
  div.innerHTML = `
    <strong>${c.name}</strong>
    <span>${c.character_id}</span>
    <small>目标：${state.goal || '未设置'}</small>
    <small>情绪：${state.mood || 'neutral'} / 状态：${state.status || 'active'}</small>
  `;
  if (!compact) return div;
  div.onclick = () => fillCharacterForm(c);
  return div;
}

function fillCharacterForm(c) {
  const state = c.state || {};
  document.getElementById('mc-id').value = c.character_id || '';
  document.getElementById('mc-name').value = c.name || '';
  document.getElementById('mc-persona').value = c.persona || '';
  document.getElementById('mc-style').value = c.speaking_style || '';
  document.getElementById('mc-goal').value = state.goal || '';
  document.getElementById('mc-mood').value = state.mood || 'neutral';
  document.getElementById('mc-location').value = state.location || 'unknown';
  document.getElementById('mc-status').value = state.status || 'active';
}

async function loadMultiCharacters() {
  const res = await fetch('/multi-characters');
  charactersCache = await res.json();

  const npcList = document.getElementById('npc-list');
  const settingsList = document.getElementById('settings-character-list');
  npcList.innerHTML = '';
  settingsList.innerHTML = '';

  const activeCharacters = charactersCache.filter(c => (c.state || {}).status !== 'inactive');
  if (!activeCharacters.length) {
    npcList.innerHTML = '<div class="hint-card">还没有 active NPC。点击右上角“设置”创建。</div>';
  }

  activeCharacters.forEach(c => npcList.appendChild(characterCard(c, false)));
  charactersCache.forEach(c => settingsList.appendChild(characterCard(c, true)));
}

async function createMultiCharacter(e) {
  e.preventDefault();
  const payload = {
    character_id: document.getElementById('mc-id').value.trim(),
    name: document.getElementById('mc-name').value.trim(),
    persona: document.getElementById('mc-persona').value,
    speaking_style: document.getElementById('mc-style').value,
    goal: document.getElementById('mc-goal').value,
    mood: document.getElementById('mc-mood').value || 'neutral',
    location: document.getElementById('mc-location').value || 'unknown',
    status: document.getElementById('mc-status').value || 'active',
  };
  if (!payload.character_id || !payload.name) return;

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

  const sendButton = e.submitter || document.querySelector('#multi-chat-form button[type="submit"]');
  sendButton.disabled = true;
  sendButton.textContent = '生成中...';

  try {
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
    const replies = data.replies || [];
    if (!replies.length) {
      appendMessage('assistant error', '没有 NPC 回复。请检查是否已有 active NPC。', '系统');
    }
    replies.forEach(r => appendMessage('assistant', r.text, r.character_name || r.character_id));
  } catch (err) {
    appendMessage('assistant error', String(err), '错误');
  } finally {
    sendButton.disabled = false;
    sendButton.textContent = '发送';
  }
}

document.getElementById('open-settings').onclick = openSettings;
document.getElementById('close-settings').onclick = closeSettings;
document.getElementById('close-settings-backdrop').onclick = closeSettings;
document.getElementById('model-config-form').onsubmit = saveModelConfig;
document.getElementById('multi-character-form').onsubmit = createMultiCharacter;
document.getElementById('multi-chat-form').onsubmit = sendMultiChat;

loadModelConfig();
loadMultiCharacters();
