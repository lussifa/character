const messagesEl = document.getElementById("messages");
const settingsModal = document.getElementById("settings-modal");
let charactersCache = [];

function appendMessage(role, text, meta = "") {
  const empty = messagesEl.querySelector(".empty-state");
  if (empty) empty.remove();

  const div = document.createElement("div");
  div.className = `message ${role}`;

  if (meta) {
    const name = document.createElement("div");
    name.className = "message-meta";
    name.textContent = meta;
    div.appendChild(name);
  }

  const body = document.createElement("div");
  body.textContent = text;
  div.appendChild(body);
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function openSettings() {
  settingsModal.classList.remove("hidden");
}

function closeSettings() {
  settingsModal.classList.add("hidden");
}

async function loadModelConfig() {
  const res = await fetch("/model-config");
  const cfg = await res.json();
  document.getElementById("model-name").value = cfg.name || "default";
  document.getElementById("model-provider").value = cfg.provider || "mock";
  document.getElementById("model-id").value = cfg.model || "mock-roleplay";
  document.getElementById("model-base-url").value = cfg.base_url || "";
  document.getElementById("model-api-key").value = "";
  document.getElementById("model-config-status").textContent = cfg.api_key_set
    ? "API Key 已保存"
    : "未保存 API Key";
}

async function saveModelConfig(event) {
  event.preventDefault();
  const payload = {
    name: document.getElementById("model-name").value || "default",
    provider: document.getElementById("model-provider").value,
    model: document.getElementById("model-id").value || "mock-roleplay",
    base_url: document.getElementById("model-base-url").value,
    api_key: document.getElementById("model-api-key").value,
    is_default: true,
  };

  const res = await fetch("/model-config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const cfg = await res.json();
  document.getElementById("model-config-status").textContent =
    `已保存：${cfg.provider} / ${cfg.model}${cfg.api_key_set ? " / key 已设置" : ""}`;
  document.getElementById("model-api-key").value = "";
}

function characterCard(character, compact = false) {
  const state = character.state || {};
  const div = document.createElement("div");
  div.className = "character-item";

  const name = document.createElement("strong");
  name.textContent = character.name || character.character_id;

  const id = document.createElement("span");
  id.textContent = character.character_id;

  const goal = document.createElement("small");
  goal.textContent = `目标：${state.goal || "未设置"}`;

  const status = document.createElement("small");
  status.textContent = `情绪：${state.mood || "neutral"} / 状态：${state.status || "active"}`;

  div.append(name, id, goal, status);
  if (compact) {
    div.onclick = () => fillCharacterForm(character);
  }
  return div;
}

function fillCharacterForm(character) {
  const state = character.state || {};
  document.getElementById("mc-id").value = character.character_id || "";
  document.getElementById("mc-name").value = character.name || "";
  document.getElementById("mc-persona").value = character.persona || "";
  document.getElementById("mc-style").value = character.speaking_style || "";
  document.getElementById("mc-goal").value = state.goal || "";
  document.getElementById("mc-mood").value = state.mood || "neutral";
  document.getElementById("mc-location").value = state.location || "unknown";
  document.getElementById("mc-status").value = state.status || "active";
}

async function loadMultiCharacters() {
  const res = await fetch("/multi-characters");
  charactersCache = await res.json();

  const npcList = document.getElementById("npc-list");
  const settingsList = document.getElementById("settings-character-list");
  const sourceSelect = document.getElementById("rel-source");
  const targetSelect = document.getElementById("rel-target");

  npcList.innerHTML = "";
  settingsList.innerHTML = "";
  sourceSelect.innerHTML = "";
  targetSelect.innerHTML = "";

  const activeCharacters = charactersCache.filter((c) => (c.state || {}).status !== "inactive");
  if (!activeCharacters.length) {
    npcList.innerHTML = '<div class="hint-card">还没有 active NPC。打开设置创建一个角色。</div>';
  }

  activeCharacters.forEach((c) => npcList.appendChild(characterCard(c)));
  charactersCache.forEach((c) => {
    settingsList.appendChild(characterCard(c, true));
    sourceSelect.appendChild(new Option(`${c.name} (${c.character_id})`, c.character_id));
    targetSelect.appendChild(new Option(`${c.name} (${c.character_id})`, c.character_id));
  });
}

async function createMultiCharacter(event) {
  event.preventDefault();
  const payload = {
    character_id: document.getElementById("mc-id").value.trim(),
    name: document.getElementById("mc-name").value.trim(),
    persona: document.getElementById("mc-persona").value,
    speaking_style: document.getElementById("mc-style").value,
    goal: document.getElementById("mc-goal").value,
    mood: document.getElementById("mc-mood").value || "neutral",
    location: document.getElementById("mc-location").value || "unknown",
    status: document.getElementById("mc-status").value || "active",
  };
  if (!payload.character_id || !payload.name) return;

  await fetch("/multi-characters", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await loadMultiCharacters();
}

async function saveRelationship(event) {
  event.preventDefault();
  const sourceId = document.getElementById("rel-source").value;
  const targetId = document.getElementById("rel-target").value;
  if (!sourceId || !targetId || sourceId === targetId) {
    document.getElementById("relationship-status").textContent = "请选择两个不同角色。";
    return;
  }

  const payload = {
    source_id: sourceId,
    target_id: targetId,
    relation: document.getElementById("rel-relation").value || "knows",
    attitude: document.getElementById("rel-attitude").value || "neutral",
    confidence: Number(document.getElementById("rel-confidence").value || 0.8),
  };

  await fetch("/multi-characters/relationships", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  document.getElementById("relationship-status").textContent = "关系已保存。";
  await loadMultiCharacters();
}

async function sendMultiChat(event) {
  event.preventDefault();
  const input = document.getElementById("chat-message");
  const content = input.value.trim();
  if (!content) return;

  input.value = "";
  appendMessage("user", content, "你");

  const sendButton = event.submitter || document.querySelector('#multi-chat-form button[type="submit"]');
  sendButton.disabled = true;
  sendButton.textContent = "生成中...";

  try {
    const payload = {
      content,
      max_speakers: Number(document.getElementById("max-speakers").value || 2),
      auto_simulate_world: document.getElementById("auto-simulate-world").checked,
    };

    const res = await fetch("/chat/multi", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const text = await res.text();
      appendMessage("assistant error", text, "错误");
      return;
    }

    const data = await res.json();
    const replies = data.replies || [];
    if (!replies.length) {
      appendMessage("assistant error", "没有 NPC 回复。请检查是否已经创建 active NPC。", "系统");
    }
    replies.forEach((reply) => {
      appendMessage("assistant", reply.text, reply.character_name || reply.character_id);
    });
  } catch (err) {
    appendMessage("assistant error", String(err), "错误");
  } finally {
    sendButton.disabled = false;
    sendButton.textContent = "发送";
  }
}

document.getElementById("open-settings").onclick = openSettings;
document.getElementById("close-settings").onclick = closeSettings;
document.getElementById("close-settings-backdrop").onclick = closeSettings;
document.getElementById("model-config-form").onsubmit = saveModelConfig;
document.getElementById("multi-character-form").onsubmit = createMultiCharacter;
document.getElementById("relationship-form").onsubmit = saveRelationship;
document.getElementById("multi-chat-form").onsubmit = sendMultiChat;

loadModelConfig();
loadMultiCharacters();
