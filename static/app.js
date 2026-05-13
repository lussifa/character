const messagesEl = document.getElementById("messages");
const settingsModal = document.getElementById("settings-modal");
const worldJsonView = document.getElementById("world-json-view");
const seedJsonEl = document.getElementById("seed-json");
let charactersCache = [];
let worldCache = null;

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

function setStatus(id, text, isError = false) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = text || "";
  el.classList.toggle("error-text", Boolean(isError));
}

function parseCsvIds(text) {
  return String(text || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function safeJsonParse(text, fallback) {
  if (!String(text || "").trim()) return fallback;
  return JSON.parse(text);
}

async function apiGet(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function apiPost(url, payload, method = "POST") {
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function loadModelConfig() {
  const cfg = await apiGet("/model-config");
  document.getElementById("model-name").value = cfg.name || "default";
  document.getElementById("model-provider").value = cfg.provider || "mock";
  document.getElementById("model-id").value = cfg.model || "mock-roleplay";
  document.getElementById("model-base-url").value = cfg.base_url || "";
  document.getElementById("model-api-key").value = "";
  setStatus("model-config-status", cfg.api_key_set ? "API Key 已保存" : "未保存 API Key");
}

async function saveModelConfig(event) {
  event.preventDefault();
  try {
    const payload = {
      name: document.getElementById("model-name").value || "default",
      provider: document.getElementById("model-provider").value,
      model: document.getElementById("model-id").value || "mock-roleplay",
      base_url: document.getElementById("model-base-url").value,
      api_key: document.getElementById("model-api-key").value,
      is_default: true,
    };
    const cfg = await apiPost("/model-config", payload);
    setStatus(
      "model-config-status",
      `已保存：${cfg.provider} / ${cfg.model}${cfg.api_key_set ? " / key 已设置" : ""}`
    );
    document.getElementById("model-api-key").value = "";
  } catch (err) {
    setStatus("model-config-status", String(err), true);
  }
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

  const action = document.createElement("small");
  action.textContent = `位置：${state.location || "unknown"} / 行为：${state.current_action || "idle"}`;

  div.append(name, id, goal, status, action);
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
  document.getElementById("mc-action").value = state.current_action || "idle";
  document.getElementById("mc-status").value = state.status || "active";
}

async function loadMultiCharacters() {
  charactersCache = await apiGet("/multi-characters");

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
    npcList.innerHTML = '<div class="hint-card">还没有 active NPC。打开设置创建一个角色，或先导入 seed。</div>';
  }

  activeCharacters.forEach((c) => npcList.appendChild(characterCard(c)));
  charactersCache.forEach((c) => {
    settingsList.appendChild(characterCard(c, true));
    sourceSelect.appendChild(new Option(`${c.name} (${c.character_id})`, c.character_id));
    targetSelect.appendChild(new Option(`${c.name} (${c.character_id})`, c.character_id));
  });
}

function renderWorldPreview(world) {
  document.getElementById("world-locations-count").textContent = Object.keys(world.locations || {}).length;
  document.getElementById("world-events-count").textContent = (world.events || []).length;
  document.getElementById("world-dialogues-count").textContent = (world.dialogues || []).length;
  document.getElementById("world-timeline-count").textContent = (world.timeline || []).length;

  const preview = document.getElementById("world-events-preview");
  preview.innerHTML = "";
  const items = [...(world.events || [])].slice(-6).reverse();
  if (!items.length) {
    preview.innerHTML = '<div class="hint-card">当前还没有世界事件。</div>';
  } else {
    items.forEach((event) => {
      const div = document.createElement("div");
      div.className = "timeline-item";
      div.innerHTML = `
        <strong>${event.title || event.event_id || "事件"}</strong>
        <small>${event.location || "unknown"} / ${event.visibility || "public"}</small>
        <span>${event.description || ""}</span>
      `;
      preview.appendChild(div);
    });
  }

  worldJsonView.value = JSON.stringify(world, null, 2);
}

async function loadWorld() {
  worldCache = await apiGet("/world");
  renderWorldPreview(worldCache);
}

async function createMultiCharacter(event) {
  event.preventDefault();
  try {
    const payload = {
      character_id: document.getElementById("mc-id").value.trim(),
      name: document.getElementById("mc-name").value.trim(),
      persona: document.getElementById("mc-persona").value,
      speaking_style: document.getElementById("mc-style").value,
      goal: document.getElementById("mc-goal").value,
      mood: document.getElementById("mc-mood").value || "neutral",
      location: document.getElementById("mc-location").value || "unknown",
      current_action: document.getElementById("mc-action").value || "idle",
      status: document.getElementById("mc-status").value || "active",
    };
    if (!payload.character_id || !payload.name) return;

    await apiPost("/multi-characters", payload);
    setStatus("character-status", `已保存角色：${payload.name}`);
    await Promise.all([loadMultiCharacters(), loadWorld()]);
  } catch (err) {
    setStatus("character-status", String(err), true);
  }
}

async function saveRelationship(event) {
  event.preventDefault();
  try {
    const sourceId = document.getElementById("rel-source").value;
    const targetId = document.getElementById("rel-target").value;
    if (!sourceId || !targetId || sourceId === targetId) {
      setStatus("relationship-status", "请选择两个不同角色。", true);
      return;
    }

    const payload = {
      source_id: sourceId,
      target_id: targetId,
      relation: document.getElementById("rel-relation").value || "knows",
      attitude: document.getElementById("rel-attitude").value || "neutral",
      confidence: Number(document.getElementById("rel-confidence").value || 0.8),
    };

    await apiPost("/multi-characters/relationships", payload);
    setStatus("relationship-status", "关系已保存。");
    await loadMultiCharacters();
  } catch (err) {
    setStatus("relationship-status", String(err), true);
  }
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

    const data = await apiPost("/chat/multi", payload);
    const replies = data.replies || [];
    if (!replies.length) {
      appendMessage("assistant error", "没有 NPC 回复。请检查是否已经创建 active NPC。", "系统");
    }
    replies.forEach((reply) => {
      appendMessage("assistant", reply.text, reply.character_name || reply.character_id);
    });

    await Promise.all([loadMultiCharacters(), loadWorld()]);
  } catch (err) {
    appendMessage("assistant error", String(err), "错误");
  } finally {
    sendButton.disabled = false;
    sendButton.textContent = "发送";
  }
}

async function saveWorldLocation(event) {
  event.preventDefault();
  try {
    const payload = {
      location_id: document.getElementById("world-location-id").value.trim(),
      name: document.getElementById("world-location-name").value.trim() || null,
      description: document.getElementById("world-location-description").value,
      metadata: {},
    };
    if (!payload.location_id) return;
    await apiPost("/world/locations", payload);
    setStatus("world-location-status", `已保存地点：${payload.location_id}`);
    await loadWorld();
  } catch (err) {
    setStatus("world-location-status", String(err), true);
  }
}

async function saveWorldEvent(event) {
  event.preventDefault();
  try {
    const payload = {
      title: document.getElementById("world-event-title").value.trim(),
      description: document.getElementById("world-event-description").value.trim(),
      participants: parseCsvIds(document.getElementById("world-event-participants").value),
      location: document.getElementById("world-event-location").value.trim(),
      effects: [],
      confidence: 0.8,
      visibility: document.getElementById("world-event-visibility").value,
      observable_by: parseCsvIds(document.getElementById("world-event-observable-by").value),
      event_type: "manual",
    };
    if (!payload.title || !payload.description) return;
    await apiPost("/world/events", payload);
    setStatus("world-event-status", `已创建事件：${payload.title}`);
    await loadWorld();
  } catch (err) {
    setStatus("world-event-status", String(err), true);
  }
}

async function saveWorldDialogue(event) {
  event.preventDefault();
  try {
    const payload = {
      title: document.getElementById("world-dialogue-title").value.trim() || "NPC dialogue",
      location: document.getElementById("world-dialogue-location").value.trim(),
      participants: parseCsvIds(document.getElementById("world-dialogue-participants").value),
      privacy: document.getElementById("world-dialogue-privacy").value,
      observable_by: parseCsvIds(document.getElementById("world-dialogue-observable-by").value),
      content: safeJsonParse(document.getElementById("world-dialogue-content").value, []),
      memory_writes: safeJsonParse(document.getElementById("world-dialogue-memory-writes").value, {}),
      confidence: 0.9,
    };
    if (!payload.participants.length) {
      setStatus("world-dialogue-status", "至少需要一个参与者。", true);
      return;
    }
    await apiPost("/world/dialogues", payload);
    setStatus("world-dialogue-status", `已创建对话：${payload.title}`);
    await loadWorld();
  } catch (err) {
    setStatus("world-dialogue-status", String(err), true);
  }
}

async function loadSeedFromTextarea() {
  try {
    const seed = safeJsonParse(seedJsonEl.value, null);
    if (!seed) {
      setStatus("seed-status", "请先粘贴 seed JSON 或加载示例。", true);
      return;
    }
    const payload = {
      seed,
      reset_graph: document.getElementById("seed-reset-graph").checked,
    };
    const result = await apiPost("/world/load-seed", payload);
    setStatus("seed-status", `Seed 导入完成：${result.characters} 个角色 / ${result.events} 个事件 / ${result.dialogues} 个对话`);
    await Promise.all([loadMultiCharacters(), loadWorld()]);
  } catch (err) {
    setStatus("seed-status", String(err), true);
  }
}

async function loadExampleSeed() {
  try {
    const res = await fetch("/static/worldx_seed.json");
    if (!res.ok) throw new Error(await res.text());
    const seed = await res.json();
    seedJsonEl.value = JSON.stringify(seed, null, 2);
    setStatus("seed-status", "已载入示例 seed，可直接点击“导入 Seed”。");
  } catch (err) {
    setStatus("seed-status", String(err), true);
  }
}

async function copyCurrentWorld() {
  try {
    if (!worldCache) await loadWorld();
    seedJsonEl.value = JSON.stringify(worldCache, null, 2);
    await navigator.clipboard.writeText(seedJsonEl.value);
    setStatus("seed-status", "当前 world JSON 已复制到剪贴板，并填入 Seed 文本框。" );
  } catch (err) {
    setStatus("seed-status", String(err), true);
  }
}

document.getElementById("open-settings").onclick = openSettings;
document.getElementById("close-settings").onclick = closeSettings;
document.getElementById("close-settings-backdrop").onclick = closeSettings;
document.getElementById("refresh-world").onclick = () => Promise.all([loadWorld(), loadMultiCharacters()]);
document.getElementById("model-config-form").onsubmit = saveModelConfig;
document.getElementById("multi-character-form").onsubmit = createMultiCharacter;
document.getElementById("relationship-form").onsubmit = saveRelationship;
document.getElementById("multi-chat-form").onsubmit = sendMultiChat;
document.getElementById("world-location-form").onsubmit = saveWorldLocation;
document.getElementById("world-event-form").onsubmit = saveWorldEvent;
document.getElementById("world-dialogue-form").onsubmit = saveWorldDialogue;
document.getElementById("load-seed-btn").onclick = loadSeedFromTextarea;
document.getElementById("load-example-seed").onclick = loadExampleSeed;
document.getElementById("copy-current-world").onclick = copyCurrentWorld;

Promise.all([loadModelConfig(), loadMultiCharacters(), loadWorld()]);
