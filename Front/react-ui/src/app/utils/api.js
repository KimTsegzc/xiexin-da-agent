import { CONFIG_PATH, INFO_REACTIONS_BASE_PATH, PROJECT_INFO_ID, STREAM_PATH, UPLOAD_OMNI_MODEL, UPLOAD_PATH } from "../constants";

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

export function getClientSessionId() {
  return getOrCreateWelcomeSessionId();
}

async function uploadFilesToSharedSpace({ apiBase, files, sessionId }) {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file, file.name);
  }
  if (sessionId) {
    formData.append("session_id", sessionId);
  }

  const response = await fetch(`${apiBase}${UPLOAD_PATH}`, {
    method: "POST",
    body: formData,
  });

  let payload = {};
  try {
    payload = await response.json();
  } catch {
    payload = {};
  }

  if (response.status === 413) {
    throw new Error("上传文件过大，请压缩后重试（当前上限约 16MB）。");
  }

  if (!response.ok || payload.ok === false) {
    throw new Error(payload?.message || `HTTP ${response.status}`);
  }

  return payload.data || {};
}

function createWelcomeSessionId() {
  return (
    (typeof window.crypto?.randomUUID === "function"
      ? window.crypto.randomUUID().replace(/-/g, "")
      : `${Date.now()}${Math.floor(Math.random() * 1e9)}`)
  );
}

export function resetWelcomeSessionId() {
  try {
    const next = createWelcomeSessionId();
    window.localStorage.setItem(WELCOME_SESSION_STORAGE_KEY, next);
    return next;
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

export async function streamChatResponse({ apiBase, userInput, model, files, onEvent }) {
  const debug = isDebugModeEnabled();
  const welcomeSessionId = getOrCreateWelcomeSessionId();
  const selectedFiles = Array.isArray(files) ? files.filter(Boolean) : [];
  if (selectedFiles.some((file) => !String(file?.type || "").startsWith("image/"))) {
    throw new Error("暂时只支持图片解析，请上传 jpg、png、webp 等图片文件。");
  }
  let metadata = {};
  let resolvedModel = model || undefined;

  if (selectedFiles.length) {
    const uploadData = await uploadFilesToSharedSpace({
      apiBase,
      files: selectedFiles,
      sessionId: welcomeSessionId || undefined,
    });
    metadata = {
      attachments: Array.isArray(uploadData.attachments) ? uploadData.attachments : [],
    };
    resolvedModel = UPLOAD_OMNI_MODEL;
    onEvent?.({
      type: "upload",
      attachments: metadata.attachments,
    });
  }

  const response = await fetch(withClientDebugQuery(`${apiBase}${STREAM_PATH}`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_input: userInput,
      smooth: true,
      model: resolvedModel,
      session_id: welcomeSessionId || undefined,
      metadata,
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

async function requestInfoApi(url, options = {}) {
  const response = await fetch(withClientDebugQuery(url), {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  let payload = {};
  try {
    payload = await response.json();
  } catch {
    payload = {};
  }

  if (!response.ok || payload.ok === false) {
    const message = payload?.message || `HTTP ${response.status}`;
    throw new Error(message);
  }

  return payload.data || {};
}

function buildInfoPath(apiBase, infoId = PROJECT_INFO_ID, action = "") {
  const cleanAction = action ? `/${action}` : "";
  return `${apiBase}${INFO_REACTIONS_BASE_PATH}/${encodeURIComponent(infoId)}${cleanAction}`;
}

export async function fetchInfoReactions({ apiBase, infoId = PROJECT_INFO_ID, sessionId }) {
  const params = new URLSearchParams();
  if (sessionId) {
    params.set("session_id", sessionId);
  }
  const query = params.toString();
  const url = `${buildInfoPath(apiBase, infoId, "reactions")}${query ? `?${query}` : ""}`;
  return requestInfoApi(url);
}

export async function likeInfo({ apiBase, infoId = PROJECT_INFO_ID, sessionId }) {
  return requestInfoApi(buildInfoPath(apiBase, infoId, "like"), {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
  });
}

export async function unlikeInfo({ apiBase, infoId = PROJECT_INFO_ID, sessionId }) {
  return requestInfoApi(buildInfoPath(apiBase, infoId, "unlike"), {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
  });
}

export async function commentInfo({ apiBase, infoId = PROJECT_INFO_ID, sessionId, content, userName }) {
  return requestInfoApi(buildInfoPath(apiBase, infoId, "comment"), {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      content,
      user_name: userName || "",
    }),
  });
}
