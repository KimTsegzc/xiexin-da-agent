import { useEffect, useRef, useState } from "react";
import { MAX_PERSISTED_MESSAGES, SESSION_STORAGE_KEY } from "../constants";
import { isClientDebugEnabled, streamChatResponse } from "../utils/api";


function shouldLogContextToConsole() {
  if (isClientDebugEnabled()) return true;
  const hostname = window.location.hostname || "";
  return hostname === "localhost" || hostname === "127.0.0.1";
}


function logContextMetrics(metrics) {
  const context = metrics?.context;
  if (!context || !shouldLogContextToConsole()) return;
  console.groupCollapsed("[xiexin-context]");
  console.log("summary", {
    session_id: context.session_id,
    recent: context.recent_message_count,
    history: context.history_message_count,
    summary: context.summary_applied,
    updated: context.summary_updated,
    period: context.time_period,
  });
  console.log("recent_preview", context.recent_preview || []);
  console.log("summary_preview", context.summary_preview || "");
  console.log("context", {
    session_id: context.session_id,
    recent: context.recent_message_count,
    history: context.history_message_count,
    summary: context.summary_applied,
    updated: context.summary_updated,
    period: context.time_period,
  });
  console.groupEnd();
}

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

function toSkillActionLabel(skillName, skillLabel) {
  if (skillName === "send_email") return "发送邮件";
  if (skillName === "skill_ccb_get_handler") return "查询职能";
  if (skillName === "direct_chat") return "通用对话";
  const normalized = (skillLabel || "").trim();
  if (!normalized) return "";
  if (normalized === "邮件发送") return "发送邮件";
  return normalized;
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
        { role: "assistant", content: "连接中", metrics: null, pending: true, pendingLabel: "连接中" },
      ];
    });

    let assistantText = "";
    let activeSkillLabel = "";
    let activeSkillName = "";

    try {
      await streamChatResponse({
        apiBase,
        userInput: trimmed,
        model: selectedModel,
        onEvent: (eventPayload) => {
          if (sessionVersionRef.current !== sessionVersion) return;

          if (isClientDebugEnabled() && eventPayload.type === "debug") {
            console.log("[xiexin-debug] stream", eventPayload.payload || eventPayload);
          }

          if (eventPayload.type === "pulse") {
            const pulseText = eventPayload.stage === "accepted"
              ? (activeSkillLabel ? `技能运行中（${activeSkillLabel}）` : "路由中")
              : "处理中";
            setMessages((current) => current.map((message, index) => (
              index === assistantIndex ? { ...message, content: pulseText, pending: true, pendingLabel: pulseText } : message
            )));
          }

          if (eventPayload.type === "skill") {
            activeSkillName = eventPayload?.skill?.name || "";
            activeSkillLabel = toSkillActionLabel(
              activeSkillName,
              eventPayload?.skill?.label || eventPayload?.skill?.name || "",
            );
            if (activeSkillName === "direct_chat" || activeSkillLabel === "通用对话") {
                activeSkillLabel = "";
                return;
            }
            const skillHint = activeSkillLabel ? `技能运行中（${activeSkillLabel}）` : "技能运行中";
            setMessages((current) => current.map((message, index) => (
              index === assistantIndex ? { ...message, content: skillHint, pending: true, pendingLabel: skillHint } : message
            )));
          }

          if (eventPayload.type === "delta") {
            assistantText += eventPayload.content || "";
            setMessages((current) => current.map((message, index) => (
              index === assistantIndex ? { ...message, content: assistantText, pending: false, pendingLabel: "" } : message
            )));
          }

          if (eventPayload.type === "done") {
            assistantText = eventPayload.content || assistantText;
            logContextMetrics(eventPayload.metrics || null);
            setMessages((current) => current.map((message, index) => (
              index === assistantIndex
                ? { ...message, content: assistantText, metrics: eventPayload.metrics || null, pending: false, pendingLabel: "" }
                : message
            )));
          }

          if (eventPayload.type === "error") {
            setMessages((current) => current.map((message, index) => (
              index === assistantIndex
                ? { ...message, content: `请求失败：${eventPayload.message || "unknown error"}`, pending: false, pendingLabel: "" }
                : message
            )));
          }
        },
      });
    } catch (error) {
      if (sessionVersionRef.current !== sessionVersion) return;
      setMessages((current) => current.map((message, index) => (
        index === assistantIndex
          ? { ...message, content: `请求失败：${error.message || error}`, pending: false, pendingLabel: "" }
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
