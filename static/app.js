const API_BASE = "";
const API_KEY_STORAGE = "snippetVaultApiKey";

const authPanel = document.querySelector("#auth-panel");
const vaultPanel = document.querySelector("#vault-panel");
const signOutButton = document.querySelector("#sign-out");
const errorMessage = document.querySelector("#error");
const noticeMessage = document.querySelector("#notice");
const snippetList = document.querySelector("#snippet-list");

function showMessage(element, message) {
  element.textContent = message;
  element.classList.remove("hidden");
}

function clearMessages() {
  errorMessage.classList.add("hidden");
  noticeMessage.classList.add("hidden");
}

function apiKey() {
  return localStorage.getItem(API_KEY_STORAGE);
}

async function apiRequest(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (apiKey()) headers.Authorization = `Bearer ${apiKey()}`;
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.message || "Request failed.");
  return payload;
}

function renderAuthState() {
  const signedIn = Boolean(apiKey());
  authPanel.classList.toggle("hidden", signedIn);
  vaultPanel.classList.toggle("hidden", !signedIn);
  signOutButton.classList.toggle("hidden", !signedIn);
  if (signedIn) loadSnippets();
}

async function loadSnippets() {
  try {
    const payload = await apiRequest("/snippets");
    snippetList.replaceChildren();
    payload.data.snippets.forEach(renderSnippet);
    if (!payload.data.snippets.length) snippetList.textContent = "No snippets yet.";
  } catch (error) {
    showMessage(errorMessage, error.message);
    if (error.message.includes("API key")) signOut();
  }
}

function renderSnippet(snippet) {
  const card = document.createElement("article");
  card.className = "snippet-card";
  card.innerHTML = `<header><h3></h3><span class="category"></span></header><pre><code></code></pre><div class="card-actions"><button class="button secondary copy-code" type="button">Copy code</button><button class="button delete-snippet" type="button">Delete</button></div>`;
  card.querySelector("h3").textContent = snippet.title;
  card.querySelector(".category").textContent = snippet.category;
  card.querySelector("code").textContent = snippet.code;
  card.querySelector(".copy-code").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(snippet.code);
      showMessage(noticeMessage, "Code copied.");
    } catch (error) {
      showMessage(errorMessage, "Could not copy code. Copy it manually instead.");
    }
  });
  card.querySelector(".delete-snippet").addEventListener("click", async () => {
    if (!window.confirm(`Delete "${snippet.title}"?`)) return;
    clearMessages();
    try {
      await apiRequest(`/snippets/${snippet.id}`, { method: "DELETE" });
      await loadSnippets();
    } catch (error) { showMessage(errorMessage, error.message); }
  });
  snippetList.append(card);
}

function signOut() {
  localStorage.removeItem(API_KEY_STORAGE);
  snippetList.replaceChildren();
  renderAuthState();
}

document.querySelector("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault(); clearMessages();
  const key = document.querySelector("#api-key").value.trim();
  localStorage.setItem(API_KEY_STORAGE, key);
  try {
    await apiRequest("/snippets");
    renderAuthState();
  } catch (error) {
    localStorage.removeItem(API_KEY_STORAGE);
    showMessage(errorMessage, error.message);
  }
});

document.querySelector("#register-form").addEventListener("submit", async (event) => {
  event.preventDefault(); clearMessages();
  try {
    const name = document.querySelector("#name").value.trim();
    const payload = await apiRequest("/users", { method: "POST", body: JSON.stringify({ name }) });
    document.querySelector("#new-key-value").textContent = payload.data.api_key;
    document.querySelector("#new-key").classList.remove("hidden");
    showMessage(noticeMessage, "Account created. Save your API key before signing in.");
  } catch (error) { showMessage(errorMessage, error.message); }
});

document.querySelector("#copy-key").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(document.querySelector("#new-key-value").textContent);
    showMessage(noticeMessage, "API key copied.");
  } catch (error) {
    showMessage(errorMessage, "Could not copy the API key. Copy it manually instead.");
  }
});

document.querySelector("#snippet-form").addEventListener("submit", async (event) => {
  event.preventDefault(); clearMessages();
  const form = new FormData(event.target);
  try {
    await apiRequest("/snippets", { method: "POST", body: JSON.stringify(Object.fromEntries(form)) });
    event.target.reset();
    await loadSnippets();
  } catch (error) { showMessage(errorMessage, error.message); }
});

document.querySelector("#refresh").addEventListener("click", loadSnippets);
signOutButton.addEventListener("click", signOut);
renderAuthState();