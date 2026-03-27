import Taro from "@tarojs/taro";
import { CHAT_PATH, CONFIG_PATH } from "../../../../frontend-core/constants";
import { normalizeChatResponse, normalizeFrontendConfig } from "../../../../frontend-core/chatProtocol";

export function resolveApiBase() {
  const envBase = typeof TARO_APP_API_BASE === "string" ? TARO_APP_API_BASE : "";
  if (envBase) {
    return envBase.replace(/\/$/, "");
  }

  if (typeof window !== "undefined" && window.location?.hostname) {
    const protocol = window.location.protocol === "https:" ? "https:" : "http:";
    return `${protocol}//${window.location.hostname}:8765`;
  }

  return "http://127.0.0.1:8765";
}

export async function requestJson(url, data) {
  const response = await Taro.request({
    url,
    method: data ? "POST" : "GET",
    data,
    header: {
      "Content-Type": "application/json",
    },
  });

  if (response.statusCode < 200 || response.statusCode >= 300) {
    throw new Error(`HTTP ${response.statusCode}`);
  }

  return response.data;
}

export async function fetchFrontendConfig(apiBase) {
  const payload = await requestJson(`${apiBase}${CONFIG_PATH}`);
  return normalizeFrontendConfig(payload);
}

export async function requestChatCompletion({ apiBase, userInput, model }) {
  const payload = await requestJson(`${apiBase}${CHAT_PATH}`, {
    user_input: userInput,
    model: model || undefined,
  });

  return normalizeChatResponse(payload);
}