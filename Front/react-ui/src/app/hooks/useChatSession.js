import { useEffect, useRef, useState } from "react";
import { MAX_PERSISTED_MESSAGES, SESSION_STORAGE_KEY, UPLOAD_OMNI_MODEL } from "../constants";
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
  const [attachments, setAttachments] = useState([]);
  const [loading, setLoading] = useState(false);
  const sessionVersionRef = useRef(0);

  const effectiveComposerModel = attachments.length ? UPLOAD_OMNI_MODEL : selectedModel;

  function appendAttachments(fileList) {
    const nextFiles = Array.from(fileList || []).filter(Boolean);
    if (!nextFiles.length) return;
    setAttachments((current) => [...current, ...nextFiles]);
  }

  function removeAttachment(indexToRemove) {
    setAttachments((current) => current.filter((_, index) => index !== indexToRemove));
  }

  useEffect(() => {
    persistSession(messages);
  }, [messages]);

  async function submitMessage(submitValue) {
    const trimmed = submitValue.trim();
    const selectedFiles = attachments.slice();
    const promptText = trimmed || (selectedFiles.length ? "请帮我分析这次上传的内容。" : "");
    if ((!promptText && !selectedFiles.length) || loading) return;
    const sessionVersion = sessionVersionRef.current;

    const userMessage = {
      role: "user",
      content: promptText,
      attachments: selectedFiles.map((file) => ({
        name: file.name,
        size_bytes: file.size,
        content_type: file.type || "application/octet-stream",
        media_type: (file.type || "").startsWith("image/") ? "image" : "file",
      })),
    };
    let assistantIndex = -1;

    setChatMode(true);
    setInput("");
    setAttachments([]);
    setLoading(true);
    setMessages((current) => {
      assistantIndex = current.length + 1;
      return [
        ...current,
        userMessage,
        {
          role: "assistant",
          content: selectedFiles.length ? "上传中" : "连接中",
          metrics: null,
          pending: true,
          pendingLabel: selectedFiles.length ? "上传中" : "连接中",
        },
      ];
    });

    let assistantText = "";
    let activeSkillLabel = "";
    let activeSkillName = "";

    try {
      await streamChatResponse({
        apiBase,
        userInput: promptText,
        model: selectedModel,
        files: selectedFiles,
        onEvent: (eventPayload) => {
          if (sessionVersionRef.current !== sessionVersion) return;

          if (isClientDebugEnabled() && eventPayload.type === "debug") {
            console.log("[xiexin-debug] stream", eventPayload.payload || eventPayload);
          }

          if (eventPayload.type === "upload") {
            const uploadedCount = Array.isArray(eventPayload.attachments) ? eventPayload.attachments.length : 0;
            const uploadText = uploadedCount > 0 ? `已上传 ${uploadedCount} 个文件，正在理解内容` : "上传完成，正在理解内容";
            setMessages((current) => current.map((message, index) => (
              index === assistantIndex ? { ...message, content: uploadText, pending: true, pendingLabel: uploadText } : message
            )));
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
    setAttachments([]);
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
    attachments,
    appendAttachments,
    removeAttachment,
    effectiveComposerModel,
    loading,
    chatMode,
    setChatMode,
    handleSubmit,
    resetSession,
  };
}
