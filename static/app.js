let activeCharacter = null;

async function loadCharacters() {
  const res = await fetch('/characters');
  const data = await res.json();
  const list = document.getElementById('character-list');
  list.innerHTML = '';
  data.forEach(c => {
    const div = document.createElement('div');
    div.className = 'character-item';
    div.textContent = c.name;
    div.onclick = () => selectCharacter(c);
    list.appendChild(div);
  });
}

function selectCharacter(c) {
  activeCharacter = c;
  document.getElementById('active-character').textContent = c.name;
  document.getElementById('active-description').textContent = c.description;
  document.getElementById('chat-message').disabled = false;
  document.getElementById('send-button').disabled = false;
  document.getElementById('memory-content').disabled = false;
  document.getElementById('memory-button').disabled = false;
  loadMessages();
  loadMemory();
}

async function loadMessages() {
  if (!activeCharacter) return;
  const res = await fetch(`/characters/${activeCharacter.id}/messages`);
  const data = await res.json();
  const container = document.getElementById('messages');
  container.innerHTML = '';
  data.forEach(m => {
    const div = document.createElement('div');
    div.className = `message ${m.role}`;
    div.textContent = m.content;
    container.appendChild(div);
  });
}

async function loadMemory() {
  if (!activeCharacter) return;
  const res = await fetch(`/characters/${activeCharacter.id}/memory`);
  const data = await res.json();
  const container = document.getElementById('memory-list');
  container.innerHTML = '';
  data.forEach(m => {
    const div = document.createElement('div');
    div.className = 'memory-item';
    div.textContent = m.content;
    container.appendChild(div);
  });
}

document.getElementById('character-form').onsubmit = async (e) => {
  e.preventDefault();
  const name = document.getElementById('character-name').value;
  const description = document.getElementById('character-description').value;
  await fetch('/characters', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name, description})
  });
  loadCharacters();
};

document.getElementById('chat-form').onsubmit = async (e) => {
  e.preventDefault();
  const content = document.getElementById('chat-message').value;
  document.getElementById('chat-message').value = '';
  await fetch(`/characters/${activeCharacter.id}/chat`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({content})
  });
  loadMessages();
};

document.getElementById('memory-form').onsubmit = async (e) => {
  e.preventDefault();
  const content = document.getElementById('memory-content').value;
  document.getElementById('memory-content').value = '';
  await fetch(`/characters/${activeCharacter.id}/memory`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({content})
  });
  loadMemory();
};

loadCharacters();
