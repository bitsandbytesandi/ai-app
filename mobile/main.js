// === Supabase client (anon key is veilig in frontend) ===
const SUPABASE_URL = "https://cwsqfssmjkecnplaoyrp.supabase.co";  
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN3c3Fmc3NtamtlY25wbGFveXJwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTA0NTY5MzMsImV4cCI6MjEwNjAzMjkzM30.hSrrpGmZB7oth19AsErjrVIqAal6oBlkrrewuLvcXp4";

const supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

const promptEl = document.getElementById("prompt");
const historyEl = document.getElementById("history");
const sendBtn = document.getElementById("send");
const btnText = sendBtn.querySelector(".btn-text");
const loader = sendBtn.querySelector(".loader");

const loginSection = document.getElementById("login-section");
const chatSection = document.getElementById("chat-section");
const authArea = document.getElementById("auth-area");
const authError = document.getElementById("auth-error");

// === Auth state ===
let currentSession = null;

async function initAuth() {
  const { data: { session } } = await supabase.auth.getSession();
  currentSession = session;
  updateUI();

  // Luister naar login/logout
  supabase.auth.onAuthStateChange((_event, session) => {
    currentSession = session;
    updateUI();
    if (session) loadHistoryFromDB();
  });
}
initAuth();

function updateUI() {
  const loginSection = document.getElementById("login-section");
  const chatSection = document.getElementById("chat-section");
  const authArea = document.getElementById("auth-area");

  if (currentSession) {
    // Ingelogd → toon chat, verberg login
    if (loginSection) loginSection.style.display = "none";
    if (chatSection) chatSection.style.display = "block";

    if (authArea) {
      authArea.innerHTML = `
        <span style="color:#888; font-size:0.9rem; margin-right:12px;">
          ${currentSession.user.email}
        </span>
        <button id="logout-btn" style="padding:6px 14px; font-size:0.85rem;">
          Logout
        </button>
      `;
      document.getElementById("logout-btn").onclick = () => {
        supabase.auth.signOut();
      };
    }
  } else {
    // Uitgelogd → toon login, verberg chat
    if (loginSection) loginSection.style.display = "flex";
    if (chatSection) chatSection.style.display = "none";
    if (authArea) authArea.innerHTML = "";
  }
}

// Login
document.getElementById("login-btn").onclick = async () => {
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const authError = document.getElementById("auth-error");

  if (authError) authError.textContent = "";

  const { data, error } = await supabase.auth.signInWithPassword({ email, password });

  if (error) {
    console.error("Login error:", error);
    if (authError) authError.textContent = error.message;
  }
};

// Signup
document.getElementById("signup-btn").onclick = async () => {
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const authError = document.getElementById("auth-error");

  if (authError) authError.textContent = "";

  if (password.length < 6) {
    if (authError) authError.textContent = "Wachtwoord moet minstens 6 tekens zijn";
    return;
  }

  const { data, error } = await supabase.auth.signUp({ email, password });

  if (error) {
    console.error("Signup error:", error);
    if (authError) authError.textContent = error.message;
  } else {
    if (authError) {
      authError.style.color = "#22c55e";
      authError.textContent = "Account aangemaakt! Je kunt nu inloggen.";
    }
  }
};

// === History uit database ===
async function loadHistoryFromDB() {
  if (!currentSession) return;

  const res = await fetch("/api/conversations", {
    headers: {
      "Authorization": `Bearer ${currentSession.access_token}`
    }
  });

  if (!res.ok) {
    console.error("Failed to load history");
    return;
  }

  const data = await res.json();
  historyEl.innerHTML = "";

  data.forEach(item => {
    const div = document.createElement("div");
    div.className = "message";
    div.innerHTML = `
      <div class="message-header">
        <span>${item.model_used || "AI"}</span>
        <span>${new Date(item.created_at).toLocaleString()}</span>
      </div>
      <div class="message-body">
        <div class="question">${item.prompt}</div>
        <div class="answer">${item.answer}</div>
      </div>
    `;
    historyEl.appendChild(div);
  });
}

// === Generate (nu met token) ===
sendBtn.addEventListener("click", async () => {
  const prompt = promptEl.value.trim();
  if (!prompt || !currentSession) return;

  btnText.hidden = true;
  loader.hidden = false;
  sendBtn.disabled = true;
  promptEl.disabled = true;

  // Tijdelijke bubble terwijl er gestreamd wordt
  const live = document.createElement("div");
  live.className = "message";
  live.innerHTML = `
    <div class="message-header">
      <span id="live-model">AI</span>
      <span>live</span>
    </div>
    <div class="message-body">
      <div class="question">${escapeHtml(prompt)}</div>
      <div class="answer" id="live-answer"></div>
    </div>
  `;
  historyEl.prepend(live);
  const answerEl = live.querySelector("#live-answer");
  const modelEl = live.querySelector("#live-model");

  try {
    const res = await fetch("/api/generate/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentSession.access_token}`,
      },
const history = [];
document.querySelectorAll("#history .message").forEach(msg => {
    const question = msg.querySelector(".question")?.textContent;
    const answer = msg.querySelector(".answer")?.textContent;
    if (question) history.push({ role: "user", content: question });
    if (answer && !answer.includes("Stream failed") && !answer.includes("error")) {
        history.push({ role: "assistant", content: answer });
    }
    });

history.reverse();

const res = await fetch("/api/generate/stream", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${currentSession.acces_token}`,
  },
  body: JSON.stringify({
    prompt,
    history: history.slice(-10)
  }),
});
    if (!res.ok || !res.body) {
      const err = await res.json().catch(() => ({ detail: "Stream failed" }));
      throw new Error(err.detail || "Stream failed");
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const parts = buffer.split("\n\n");
      buffer = parts.pop();

      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith("data:")) continue;
        const payload = JSON.parse(line.slice(5).trim());

        if (payload.type === "meta" && payload.model) {
          modelEl.textContent = payload.model;
        }
        if (payload.type === "token") {
          answerEl.textContent += payload.text;
          historyEl.scrollTop = 0;
        }
        if (payload.type === "error") {
          throw new Error(payload.detail);
        }
      }
    }

    promptEl.value = "";
  } catch (err) {
    answerEl.textContent = err.message || "Network error";
    answerEl.className = "error-text";
  } finally {
    btnText.hidden = false;
    loader.hidden = true;
    sendBtn.disabled = false;
    promptEl.disabled = false;
    promptEl.focus();
  }
});

function escapeHtml(str) {
  return str
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

// Ctrl/Cmd + Enter
promptEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
    sendBtn.click();
  }
});

