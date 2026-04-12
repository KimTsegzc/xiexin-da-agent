import { renderMarkdown } from "../utils/markdown";

function formatAttachmentSize(sizeBytes) {
  const size = Number(sizeBytes || 0);
  if (!size) return "";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function Metrics({ metrics }) {
  if (!metrics) return null;
  const firstToken = metrics.first_token_latency_seconds != null
    ? `${metrics.first_token_latency_seconds.toFixed(1)}s`
    : "";
  const total = metrics.latency_seconds != null ? `${metrics.latency_seconds.toFixed(1)}s` : "";
  const selectedSkill = metrics.routing?.selected_skill_label || metrics.routing?.selected_skill || "";
  const selectedSkillName = metrics.routing?.selected_skill || "";
  const showSkill = Boolean(selectedSkill) && selectedSkillName !== "direct_chat" && selectedSkill !== "通用对话";
  const sendEmailMetrics = metrics.send_email || {};
  const implementationHint = selectedSkillName === "send_email"
    ? (sendEmailMetrics.implementation_hint
      || (sendEmailMetrics.search_provider_ok ? "百度智能搜索+大模型汇总" : "大模型互联网搜索"))
    : "";
  const modelName = metrics.model || "";
  const parts = [];

  if (modelName) parts.push(`模型: ${modelName}`);
  if (showSkill) {
    const skillPart = implementationHint
      ? `技能: ${selectedSkill} | 实现方式：${implementationHint}`
      : `技能: ${selectedSkill}`;
    parts.push(skillPart);
  }
  if (firstToken) parts.push(`首 token: ${firstToken}`);
  if (total) parts.push(`总耗时: ${total}`);

  if (!parts.length) return null;

  return <div className="message-meta">{parts.join(" | ")}</div>;
}

export function MessageBubble({ message }) {
  const showPendingSpinner = message.role === "assistant" && message.pending === true;
  const pendingLabel = message.pendingLabel || message.content || "处理中...";
  const attachments = Array.isArray(message.attachments) ? message.attachments : [];

  return (
    <div className={`message-row ${message.role}`}>
      <div className="message-bubble">
        {showPendingSpinner ? (
          <div className="message-loading-row" aria-live="polite">
            <span className="message-loading-spinner" aria-hidden="true" />
            <span className="message-loading-text">{pendingLabel}</span>
          </div>
        ) : null}
        {message.role === "assistant" && !showPendingSpinner ? (
          <div className="message-content" dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }} />
        ) : (
          message.role === "assistant" ? null : message.content ? <div className="message-content">{message.content}</div> : null
        )}
        {attachments.length ? (
          <div className="message-attachments">
            {attachments.map((item, index) => (
              <div key={`${item.name || 'file'}-${index}`} className="message-attachment-chip">
                <span className="message-attachment-kind">{item.media_type === "image" ? "IMG" : "FILE"}</span>
                <span className="message-attachment-name">{item.name || item.original_name || "未命名文件"}</span>
                <span className="message-attachment-size">{formatAttachmentSize(item.size_bytes)}</span>
              </div>
            ))}
          </div>
        ) : null}
        <Metrics metrics={message.metrics} />
      </div>
    </div>
  );
}
