import { CONFIG_PATH, STREAM_PATH } from "../constants";

const WELCOME_SESSION_STORAGE_KEY = "xiexin.welcome.session.id";

function isDebugModeEnabled() {
  const params = new URLSearchParams(window.location.search || "");
  const raw = (params.get("debug") || "").trim().toLowerCase();
  return raw === "1" || raw === "true" || raw === "yes" || raw === "on" || raw === "debug";
}

function withClientDebugQuery(url) {
  const debug = isDebugModeEnabled();
  const welcomeSessionId = getOrCreateWelcomeSessionId();

  if (!debug && !welcomeSessionId) return url;

  const params = new URLSearchParams();
  if (debug) {
    params.set("debug", "1");
  }
  if (welcomeSessionId) {
    params.set("session_id", welcomeSessionId);
  }

  const sep = url.includes("?") ? "&" : "?";
  return `${url}${sep}${params.toString()}`;
}

export function isClientDebugEnabled() {
  return isDebugModeEnabled();
}

function getOrCreateWelcomeSessionId() {
  try {
    const existing = (window.localStorage.getItem(WELCOME_SESSION_STORAGE_KEY) || "").trim();
    if (existing) return existing;
    const created =
      (typeof window.crypto?.randomUUID === "function"
        ? window.crypto.randomUUID().replace(/-/g, "")
        : `${Date.now()}${Math.floor(Math.random() * 1e9)}`);
    window.localStorage.setItem(WELCOME_SESSION_STORAGE_KEY, created);
    return created;
  } catch {
    return "";
  }
}

export async function fetchFrontendConfig(apiBase) {
  const response = await fetch(withClientDebugQuery(`${apiBase}${CONFIG_PATH}`));
  if (!response.ok) {
    throw new Error(`Failed to load frontend config: HTTP ${response.status}`);
  }

  return response.json();
}

function parseEventLines(buffer, onEvent) {
  const lines = buffer.split("\n");
  const remainder = lines.pop() || "";

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) continue;
    onEvent(JSON.parse(line));
  }

  return remainder;
}

export async function streamChatResponse({ apiBase, userInput, model, onEvent }) {
  const debug = isDebugModeEnabled();
  const response = await fetch(withClientDebugQuery(`${apiBase}${STREAM_PATH}`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_input: userInput,
      smooth: true,
      model: model || undefined,
      debug,
    }),
  });

  if (!response.ok || !response.body) {
    throw new Error(`HTTP ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    buffer = parseEventLines(buffer, onEvent);
  }

  buffer += decoder.decode();
  if (buffer.trim()) {
    parseEventLines(`${buffer}\n`, onEvent);
  }
}
