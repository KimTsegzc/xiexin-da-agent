import { useEffect, useRef, useState } from "react";
import { MAX_PERSISTED_MESSAGES, SESSION_STORAGE_KEY } from "../constants";
import { streamChatResponse } from "../utils/api";

function readPersistedSession() {
  try {
    const raw = window.localStorage.getItem(SESSION_STORAGE_KEY);
    if (!raw) return { messages: [], chatMode: false };
    const parsed = JSON.parse(raw);
    const nextMessages = Array.isArray(parsed.messages) ? parsed.messages : [];
    return {
      messages: nextMessages,
      chatMode: nextMessages.length > 0,
    };
  } catch {
    return { messages: [], chatMode: false };
  }
}

function persistSession(messages) {
  try {
    const trimmedMessages = messages.slice(-MAX_PERSISTED_MESSAGES);
    window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify({ messages: trimmedMessages }));
  } catch {
    // Ignore storage quota and privacy mode failures.
  }
}

export function useChatSession({ apiBase, selectedModel }) {
  const [sessionState] = useState(() => readPersistedSession());
  const [messages, setMessages] = useState(sessionState.messages);
  const [chatMode, setChatMode] = useState(sessionState.chatMode);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const sessionVersionRef = useRef(0);

  useEffect(() => {
    persistSession(messages);
  }, [messages]);

  async function submitMessage(submitValue) {
    const trimmed = submitValue.trim();
    if (!trimmed || loading) return;
    const sessionVersion = sessionVersionRef.current;

    const userMessage = { role: "user", content: trimmed };
    let assistantIndex = -1;

    setChatMode(true);
    setInput("");
    setLoading(true);
    setMessages((current) => {
      assistantIndex = current.length + 1;
      return [
        ...current,
        userMessage,
        { role: "assistant", content: "正在连接服务...", metrics: null },
      ];
    });

    let assistantText = "";

    try {
      await streamChatResponse({
        apiBase,
        userInput: trimmed,
        model: selectedModel,
        onEvent: (eventPayload) => {
          if (sessionVersionRef.current !== sessionVersion) return;

          if (eventPayload.type === "pulse") {
            const pulseText = eventPayload.stage === "accepted" ? "正在连接模型..." : "正在生成回复...";
            setMessages((current) => current.map((message, index) => (
              index === assistantIndex ? { ...message, content: pulseText } : message
            )));
          }

          if (eventPayload.type === "delta") {
            assistantText += eventPayload.content || "";
            setMessages((current) => current.map((message, index) => (
              index === assistantIndex ? { ...message, content: assistantText } : message
            )));
          }

          if (eventPayload.type === "done") {
            assistantText = eventPayload.content || assistantText;
            setMessages((current) => current.map((message, index) => (
              index === assistantIndex
                ? { ...message, content: assistantText, metrics: eventPayload.metrics || null }
                : message
            )));
          }

          if (eventPayload.type === "error") {
            setMessages((current) => current.map((message, index) => (
              index === assistantIndex
                ? { ...message, content: `请求失败：${eventPayload.message || "unknown error"}` }
                : message
            )));
          }
        },
      });
    } catch (error) {
      if (sessionVersionRef.current !== sessionVersion) return;
      setMessages((current) => current.map((message, index) => (
        index === assistantIndex
          ? { ...message, content: `请求失败：${error.message || error}` }
          : message
      )));
    } finally {
      if (sessionVersionRef.current === sessionVersion) {
        setLoading(false);
      }
    }
  }

  function resetSession() {
    sessionVersionRef.current += 1;
    setMessages([]);
    setInput("");
    setChatMode(false);
    setLoading(false);
    try {
      window.localStorage.removeItem(SESSION_STORAGE_KEY);
    } catch {
      // Ignore storage failures during reset.
    }
  }

  async function handleSubmit(event) {
    event?.preventDefault();
    await submitMessage(input);
  }

  return {
    messages,
    input,
    setInput,
    loading,
    chatMode,
    setChatMode,
    handleSubmit,
    resetSession,
  };
}
