let conversationId = localStorage.getItem("conversationId") || null;
let agentConversationId = localStorage.getItem("agentConversationId") || null;

const filesInput = document.getElementById("files");
const uploadButton = document.getElementById("uploadButton");
const uploadStatus = document.getElementById("uploadStatus");
const documentsBox = document.getElementById("documents");
const chat = document.getElementById("chat");
const askForm = document.getElementById("askForm");
const question = document.getElementById("question");
const sources = document.getElementById("sources");
const agentForm = document.getElementById("agentForm");
const agentMessage = document.getElementById("agentMessage");
const agentResult = document.getElementById("agentResult");

function addMessage(role, text) {
  const node = document.createElement("div");
  node.className = `message ${role}`;
  node.textContent = text;
  chat.appendChild(node);
  chat.scrollTop = chat.scrollHeight;
}

async function loadDocuments() {
  const res = await fetch("/api/documents");
  const items = await res.json();
  documentsBox.innerHTML = items.length
    ? items.map(x => `<div class="doc"><strong>${escapeHtml(x.filename)}</strong> · ${x.chunk_count} chunks</div>`).join("")
    : '<div class="doc">Документов пока нет.</div>';
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
}

function renderMarkdown(value) {
  const lines = escapeHtml(value).split("\n");
  let html = "";
  let inList = false;
  const inline = line => line
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

  for (const raw of lines) {
    const match = raw.match(/^\s*[-*]\s+(.+)$/);
    if (match) {
      if (!inList) { html += "<ul>"; inList = true; }
      html += `<li>${inline(match[1])}</li>`;
    } else {
      if (inList) { html += "</ul>"; inList = false; }
      if (raw.trim()) html += `<div>${inline(raw)}</div>`;
      else html += "<br>";
    }
  }
  if (inList) html += "</ul>";
  return html;
}

uploadButton.addEventListener("click", async () => {
  if (!filesInput.files.length) return;
  const data = new FormData();
  [...filesInput.files].forEach(file => data.append("files", file));
  uploadStatus.textContent = "Индексирую документы...";
  try {
    const res = await fetch("/api/documents/upload", { method: "POST", body: data });
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || "Ошибка загрузки");
    uploadStatus.textContent = `Готово: ${body.uploaded.length} файл(а).`;
    filesInput.value = "";
    await loadDocuments();
  } catch (e) {
    uploadStatus.textContent = `Ошибка: ${e.message}`;
  }
});

askForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = question.value.trim();
  if (!text) return;
  addMessage("user", text);
  question.value = "";
  sources.innerHTML = "";
  addMessage("assistant", "Думаю...");
  const pending = chat.lastElementChild;
  try {
    const res = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: text, conversation_id: conversationId, top_k: 3 })
    });
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || "Ошибка запроса");
    conversationId = body.conversation_id;
    localStorage.setItem("conversationId", conversationId);
    pending.innerHTML = renderMarkdown(body.answer);
    sources.innerHTML = body.sources.map((s, i) => {
      const location = s.page ? `${s.source}, стр. ${s.page}` : s.source;
      return `<div class="source"><strong>[${i + 1}] ${escapeHtml(location)}</strong><br>${escapeHtml(s.preview)}</div>`;
    }).join("");
  } catch (e) {
    pending.textContent = `Ошибка: ${e.message}`;
  }
});

agentForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = agentMessage.value.trim();
  if (!text) return;
  agentResult.textContent = "Запускаю...";
  try {
    const res = await fetch("/api/agent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, conversation_id: agentConversationId })
    });
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || "Ошибка агента");
    agentConversationId = body.conversation_id;
    localStorage.setItem("agentConversationId", agentConversationId);
    agentResult.innerHTML = renderMarkdown(body.answer);
  } catch (e) {
    agentResult.textContent = `Ошибка: ${e.message}`;
  }
});

loadDocuments();
