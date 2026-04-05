import { renderMarkdown } from "../utils/markdown";

function Metrics({ metrics }) {
  if (!metrics) return null;
  const firstToken = metrics.first_token_latency_seconds != null
    ? `${metrics.first_token_latency_seconds.toFixed(1)}s`
    : "N/A";
  const total = metrics.latency_seconds != null ? `${metrics.latency_seconds.toFixed(1)}s` : "N/A";

  return <div className="message-meta">模型: {metrics.model || "N/A"} | 首 token: {firstToken} | 总耗时: {total}</div>;
}

export function MessageBubble({ message }) {
  return (
    <div className={`message-row ${message.role}`}>
      <div className="message-bubble">
        {message.role === "assistant" ? (
          <div className="message-content" dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }} />
        ) : (
          <div className="message-content">{message.content}</div>
        )}
        <Metrics metrics={message.metrics} />
      </div>
    </div>
  );
}
