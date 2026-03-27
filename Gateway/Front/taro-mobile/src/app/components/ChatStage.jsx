import { ScrollView, View } from "@tarojs/components";
import { MessageBubble } from "./MessageBubble";

export function ChatStage({ chatMode, messages, scrollAnchorId }) {
  return (
    <ScrollView
      className={`thread-panel ${chatMode ? "is-chat" : "is-hidden"}`}
      scrollY
      enhanced
      showScrollbar={false}
      scrollIntoView={scrollAnchorId}
    >
      <View className="thread-surface">
        {messages.map((message, index) => <MessageBubble key={`${message.role}-${index}`} message={message} />)}
        <View id={scrollAnchorId || "msg-0"} className="thread-anchor" />
      </View>
    </ScrollView>
  );
}