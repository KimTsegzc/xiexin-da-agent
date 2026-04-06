import { ExperienceShell } from "./ExperienceShell";

export function MobileShell(props) {
  const { clientMode, chatMode } = props;
  return (
    <ExperienceShell
      {...props}
      shellClassName={`app-shell is-${clientMode} is-mobile-default ${chatMode ? "chat-mode" : "welcome-mode"}`}
      showRail={false}
    />
  );
}
