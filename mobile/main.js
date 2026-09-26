const promptEl = document.getElementById("prompt");
const historyEl = document.getElementById("history");
const sendBtn = document.getElementById("send");
const btnText = sendBtn.querySelector(".btn-text");
const loader = sendBtn.querySelector(".loader");

const STORAGE_KEY = "ai-app-history";

function loadHistory() {
  const saved = localStorage.getItem(STORAGE_KEY);
  return saved ? JSON.parse(saved) : [];
}

function saveHistory(history) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(history.slice(0, 30))); // keep last 30
}

function renderHistory() {
  const history = loadHistory();
  historyEl.innerHTML = "";

  history.forEach(item => {
    const div = document.createElement("div");
    div.className = "message";

    div.innerHTML = `
      <div class="message-header">
        <span>${item.model || "AI"}</span>
        <span>${new Date(item.timestamp).toLocaleTimeString()}</span>
      </div>
      <div class="message-body">
        <div class="question">${item.prompt}</div>
        <div class="${item.error ? 'error-text' : 'answer'}">${item.answer}</div>
      </div>
    `;
    historyEl.appendChild(div);
  });
}

sendBtn.addEventListener("click", async () => {
  const prompt = promptEl.value.trim();
  if (!prompt) return;

  btnText.hidden = true;
  loader.hidden = false;
  sendBtn.disabled = true;

  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });

    const data = await res.json();

    const entry = {
      prompt,
      answer: res.ok ? data.text : (data.detail || "Error"),
      model: data.model_used || null,
      error: !res.ok,
      timestamp: Date.now()
    };

    const history = loadHistory();
    history.unshift(entry);
    saveHistory(history);
    renderHistory();

    promptEl.value = "";
  } catch (err) {
    const history = loadHistory();
    history.unshift({
      prompt,
      answer: err.message || "Network error",
      error: true,
      timestamp: Date.now()
    });
    saveHistory(history);
    renderHistory();
  } finally {
    btnText.hidden = false;
    loader.hidden = true;
    sendBtn.disabled = false;
  }
});

// Ctrl/Cmd + Enter
promptEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
    sendBtn.click();
  }
});

// Load history on start
renderHistory();
