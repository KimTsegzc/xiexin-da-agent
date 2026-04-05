import { CONFIG_PATH, STREAM_PATH } from "../constants";

export async function fetchFrontendConfig(apiBase) {
  const response = await fetch(`${apiBase}${CONFIG_PATH}`);
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
  const response = await fetch(`${apiBase}${STREAM_PATH}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_input: userInput,
      smooth: true,
      model: model || undefined,
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
