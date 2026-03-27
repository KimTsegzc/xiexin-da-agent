import { RichText, Text, View } from "@tarojs/components";
import { Cell, Loading, Skeleton, Tag } from "react-vant";
import { renderMarkdown } from "../../../../frontend-core/markdown";

const THINKING_TEXT = "正在生成回复...";

export function MessageBubble({ message }) {
  const isAssistant = message.role === "assistant";
  const isThinking = isAssistant && message.content === THINKING_TEXT && !message.metrics;

  return (
    <View className={`message-row ${message.role}`}>
      <Cell
        className="message-cell"
        border={false}
        title={(
          <View className="message-header">
            <Tag className="message-role-tag" round plain type={isAssistant ? "primary" : "success"}>
              {isAssistant ? "AI" : "我"}
            </Tag>
          </View>
        )}
        label={(
          <View className="message-label-content">
            {isThinking ? (
              <View className="message-thinking-block">
                <View className="message-pending">
                  <Loading className="message-pending-loading" size="18px" />
                  <Text className="message-pending-text">AI 正在思考...</Text>
                </View>
                <Skeleton className="message-skeleton" title={false} row={2} rowWidth={["92%", "64%"]} loading animate round />
              </View>
            ) : isAssistant ? (
              <RichText className="message-richtext" nodes={renderMarkdown(message.content)} />
            ) : (
              <Text className="message-content">{message.content}</Text>
            )}
            {message.metrics ? (
              <Text className="message-meta">
                模型: {message.metrics.model || "N/A"} / 总耗时: {message.metrics.latency_seconds?.toFixed?.(1) || "N/A"}s
              </Text>
            ) : null}
          </View>
        )}
      />
    </View>
  );
}