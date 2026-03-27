import { MAX_PERSISTED_MESSAGES } from "./constants";

export function normalizeFrontendConfig(config) {
  const availableModels = Array.isArray(config?.availableModels) ? config.availableModels : [];
  return {
    availableModels,
    defaultModel: config?.defaultModel || availableModels[0] || "",
    requestOptions: config?.requestOptions || {},
  };
}

export function buildChatPayload({ userInput, model, smooth } = {}) {
  return {
    user_input: String(userInput || "").trim(),
    model: model || undefined,
    smooth,
  };
}

export function normalizeChatResponse(payload) {
  if (!payload?.ok) {
    throw new Error(payload?.message || "CHAT_REQUEST_FAILED");
  }

  return {
    content: payload.content || "",
    metrics: payload.metrics || null,
  };
}

export function clampPersistedMessages(messages, limit = MAX_PERSISTED_MESSAGES) {
  return Array.isArray(messages) ? messages.slice(-limit) : [];
}

export function createUserMessage(content) {
  return { role: "user", content };
}

export function createAssistantMessage(content, metrics = null) {
  return { role: "assistant", content, metrics };
}
