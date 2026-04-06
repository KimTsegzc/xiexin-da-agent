import { ExperienceShell } from "./ExperienceShell";

export function WechatShell(props) {
  const { clientMode, chatMode } = props;
  return (
    <ExperienceShell
      {...props}
      shellClassName={`app-shell is-${clientMode} ${chatMode ? "chat-mode" : "welcome-mode"}`}
      showRail={false}
    />
  );
}
