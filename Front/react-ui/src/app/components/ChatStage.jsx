import { InteractiveAvatar } from "./InteractiveAvatar";
import { MessageBubble } from "./MessageBubble";

export function ChatStage({ messages, threadRef, railSettingsControl, showRail }) {
  return (
    <main className="chat-stage">
      {showRail ? (
        <aside className="chat-rail" aria-hidden="true">
          <div className="chat-rail-inner">
            <InteractiveAvatar className="chat-rail-avatar" alt="" ariaLabel="侧边头像互动" />
            <div className="chat-rail-settings">{railSettingsControl}</div>
          </div>
        </aside>
      ) : null}
      <section className="chat-surface" ref={threadRef}>
        {messages.map((message, index) => <MessageBubble key={`${message.role}-${index}`} message={message} />)}
      </section>
    </main>
  );
}
