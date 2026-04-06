import { ChatStage } from "../components/ChatStage";
import { Composer } from "../components/Composer";
import { InteractiveAvatar } from "../components/InteractiveAvatar";
import { WelcomeShell } from "../components/WelcomeShell";

export function ExperienceShell({
  shellClassName,
  chatMode,
  statusText,
  headerSettingsControl,
  railSettingsControl,
  showRail,
  threadRef,
  messages,
  composerProps,
}) {
  return (
    <div className={shellClassName}>
      <header className="topbar">
        {chatMode ? <InteractiveAvatar className="topbar-avatar" alt="鑫哥头像" /> : null}
        {headerSettingsControl}
      </header>

      {!chatMode ? <WelcomeShell statusText={statusText} composerProps={composerProps} /> : null}

      <ChatStage
        messages={messages}
        threadRef={threadRef}
        railSettingsControl={railSettingsControl}
        showRail={showRail}
      />

      {chatMode ? <Composer {...composerProps} /> : null}
    </div>
  );
}
