import { useEffect, useMemo, useRef, useState } from "react";
import Taro from "@tarojs/taro";
import { SESSION_STORAGE_KEY } from "../../../../frontend-core/constants";
import {
  clampPersistedMessages,
  createAssistantMessage,
  createUserMessage,
} from "../../../../frontend-core/chatProtocol";
import { requestChatCompletion } from "../utils/api";

function readPersistedSession() {
  try {
    const raw = Taro.getStorageSync(SESSION_STORAGE_KEY);
    if (!raw) {
      return { messages: [], chatMode: false };
    }

    const parsed = typeof raw === "string" ? JSON.parse(raw) : raw;
    const messages = Array.isArray(parsed?.messages) ? parsed.messages : [];
    return {
      messages,
      chatMode: messages.length > 0,
    };
  } catch {
    return { messages: [], chatMode: false };
  }
}

function persistSession(messages) {
  try {
    Taro.setStorageSync(SESSION_STORAGE_KEY, {
      messages: clampPersistedMessages(messages),
    });
  } catch {
    // Ignore container storage failures.
  }
}

export function useChatSession({ apiBase, selectedModel }) {
  const initialState = useMemo(() => readPersistedSession(), []);
  const [messages, setMessages] = useState(initialState.messages);
  const [chatMode, setChatMode] = useState(initialState.chatMode);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [composerLines, setComposerLines] = useState(1);
  const sessionVersionRef = useRef(0);

  useEffect(() => {
    persistSession(messages);
  }, [messages]);

  async function submitMessage(rawValue) {
    const trimmed = String(rawValue || "").trim();
    if (!trimmed || loading) return;

    const sessionVersion = sessionVersionRef.current;
    const userMessage = createUserMessage(trimmed);

    setChatMode(true);
    setLoading(true);
    setInput("");
    setComposerLines(1);
    setMessages((current) => [...current, userMessage, createAssistantMessage("正在生成回复...")]);

    try {
      const result = await requestChatCompletion({
        apiBase,
        userInput: trimmed,
        model: selectedModel,
      });

      if (sessionVersionRef.current !== sessionVersion) return;

      setMessages((current) => current.map((message, index) => (
        index === current.length - 1
          ? createAssistantMessage(result.content, result.metrics)
          : message
      )));
    } catch (error) {
      if (sessionVersionRef.current !== sessionVersion) return;
      setMessages((current) => current.map((message, index) => (
        index === current.length - 1
          ? createAssistantMessage(`请求失败：${error?.message || error || "unknown error"}`)
          : message
      )));
    } finally {
      if (sessionVersionRef.current === sessionVersion) {
        setLoading(false);
      }
    }
  }

  async function handleSubmit(event) {
    event?.preventDefault?.();
    await submitMessage(input);
  }

  function resetSession() {
    sessionVersionRef.current += 1;
    setMessages([]);
    setInput("");
    setChatMode(false);
    setLoading(false);
    setComposerLines(1);
    try {
      Taro.removeStorageSync(SESSION_STORAGE_KEY);
    } catch {
      // Ignore reset storage failures.
    }
  }

  return {
    messages,
    input,
    setInput,
    loading,
    chatMode,
    composerLines,
    setComposerLines,
    handleSubmit,
    resetSession,
  };
}