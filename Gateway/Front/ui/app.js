const heroTitleEl = document.getElementById("hero-title");
const heroTextEl = document.getElementById("hero-text");
const inputEl = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const pageEl = document.querySelector(".page");
const chatShellEl = document.getElementById("chat-shell");
const streamApiUrl = window.APP_CONFIG?.streamApiUrl;

const fullTitle = (heroTitleEl && heroTitleEl.dataset.fulltext) || "";
let titleIndex = 0;
let hasEnteredChatMode = false;
let requestInFlight = false;

function syncViewportMetrics() {
  const viewportHeight = Math.max(window.innerHeight || 0, document.documentElement.clientHeight || 0, 640);
  const chatGap = Math.max(12, Math.round(viewportHeight * 0.02));

  document.documentElement.style.setProperty("--page-height", `${viewportHeight}px`);
  document.documentElement.style.setProperty("--chat-page-gap", `${chatGap}px`);
}

function syncFrameHeight() {
  try {
    const frame = window.frameElement;
    if (!frame || !window.parent || !window.parent.document) {
      return;
    }

    const parentViewportHeight = window.parent.innerHeight || window.parent.document.documentElement.clientHeight;
    const frameTop = frame.getBoundingClientRect().top;
    const nextHeight = Math.max(640, Math.floor(parentViewportHeight - frameTop - 6));

    if (nextHeight > 0) {
      frame.style.height = `${nextHeight}px`;
    }
  } catch (error) {
    // Ignore sandbox or cross-frame access issues and keep the fallback height.
  }
}

function streamTitle() {
  if (!heroTextEl) return;
  if (titleIndex <= fullTitle.length) {
    heroTextEl.textContent = fullTitle.slice(0, titleIndex);
    titleIndex += 1;
    const nextDelay = 30 + Math.floor(Math.random() * 55);
    setTimeout(streamTitle, nextDelay);
  }
}

function ensureChatShell() {
  if (!chatShellEl || chatShellEl.dataset.initialized === "true") return;
  chatShellEl.innerHTML = '<div class="chat-thread" id="chat-thread"><div class="chat-empty" id="chat-empty">在这里开始对话</div></div>';
  chatShellEl.dataset.initialized = "true";
}

function getChatThread() {
  ensureChatShell();
  return document.getElementById("chat-thread");
}

function clearEmptyState() {
  const emptyEl = document.getElementById("chat-empty");
  if (emptyEl) emptyEl.remove();
}

function scrollChatToBottom() {
  const thread = getChatThread();
  if (!thread) return;
  thread.scrollTop = thread.scrollHeight;
}

function appendMessage(role, text, options = {}) {
  clearEmptyState();
  const thread = getChatThread();
  const row = document.createElement("div");
  row.className = `message-row ${role}`;

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  if (options.waiting) {
    bubble.classList.add("waiting");
  }
  bubble.textContent = text || "";

  row.appendChild(bubble);
  thread.appendChild(row);
  scrollChatToBottom();
  return bubble;
}

function appendMetrics(bubble, metrics) {
  if (!bubble || !metrics) return;
  const meta = document.createElement("div");
  meta.className = "message-meta";
  const latency = metrics.latency_seconds != null ? `${metrics.latency_seconds.toFixed(3)}s` : "N/A";
  const firstToken = metrics.first_token_latency_seconds != null ? `${metrics.first_token_latency_seconds.toFixed(3)}s` : "N/A";
  meta.textContent = `模型: ${metrics.model || "N/A"} | 首 token: ${firstToken} | 总耗时: ${latency}`;
  bubble.appendChild(meta);
}

function setComposerEnabled(enabled) {
  inputEl.disabled = !enabled;
  sendBtn.disabled = !enabled;
}

async function streamChat(userText) {
  if (!streamApiUrl) {
    throw new Error("streamApiUrl is not configured");
  }

  const response = await fetch(streamApiUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      user_input: userText,
      smooth: true,
    }),
  });

  if (!response.ok || !response.body) {
    throw new Error(`HTTP ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let assistantBubble = appendMessage("assistant", "正在等待响应...", { waiting: true });

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const rawLine of lines) {
      const line = rawLine.trim();
      if (!line) continue;
      const event = JSON.parse(line);

      if (event.type === "pulse") {
        if (event.stage === "accepted") {
          assistantBubble.textContent = "正在连接模型...";
          assistantBubble.classList.add("waiting");
        }
        if (event.stage === "first_token") {
          assistantBubble.textContent = "";
          assistantBubble.classList.remove("waiting");
        }
      }

      if (event.type === "delta") {
        assistantBubble.classList.remove("waiting");
        if (assistantBubble.textContent === "正在等待响应..." || assistantBubble.textContent === "正在连接模型...") {
          assistantBubble.textContent = "";
        }
        assistantBubble.textContent += event.content || "";
        scrollChatToBottom();
      }

      if (event.type === "done") {
        assistantBubble.classList.remove("waiting");
        assistantBubble.textContent = event.content || assistantBubble.textContent;
        appendMetrics(assistantBubble, event.metrics);
        scrollChatToBottom();
      }

      if (event.type === "error") {
        assistantBubble.classList.remove("waiting");
        assistantBubble.textContent = `请求失败：${event.message || "unknown error"}`;
      }
    }
  }
}

function enterChatMode() {
  if (hasEnteredChatMode || !pageEl) return;
  hasEnteredChatMode = true;
  ensureChatShell();
  pageEl.classList.add("chat-mode");
}

async function handleSubmit() {
  if (requestInFlight) return;
  const text = inputEl.value.trim();
  if (text) {
    enterChatMode();
    appendMessage("user", text);
    inputEl.value = "";
    requestInFlight = true;
    setComposerEnabled(false);

    try {
      await streamChat(text);
    } catch (error) {
      appendMessage("assistant", `请求失败：${error.message || error}`);
    } finally {
      requestInFlight = false;
      setComposerEnabled(true);
    }
  }
  inputEl.focus();
}

sendBtn.addEventListener("click", handleSubmit);
inputEl.addEventListener("keydown", function (e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    handleSubmit();
  }
});

function startHeroAnimation() {
  if (heroTitleEl && heroTitleEl.parentElement) {
    heroTitleEl.parentElement.classList.add("ready");
  }
  streamTitle();
  syncViewportMetrics();
  syncFrameHeight();
}

window.addEventListener("fullscreenchange", syncViewportMetrics);
window.addEventListener("resize", syncFrameHeight);
window.addEventListener("resize", syncViewportMetrics);
window.addEventListener("load", syncFrameHeight);
window.addEventListener("load", syncViewportMetrics);
setTimeout(syncViewportMetrics, 0);
setTimeout(syncViewportMetrics, 120);
setTimeout(syncViewportMetrics, 360);
setTimeout(syncFrameHeight, 0);
setTimeout(syncFrameHeight, 120);
setTimeout(syncFrameHeight, 360);

if (document.fonts && document.fonts.ready) {
  document.fonts.ready.then(() => requestAnimationFrame(startHeroAnimation));
} else {
  requestAnimationFrame(startHeroAnimation);
}

inputEl.focus();
