import { Composer } from "./Composer";
import { InteractiveAvatar } from "./InteractiveAvatar";

export function WelcomeShell({ statusText, composerProps }) {
  return (
    <div className="welcome-stack-shell">
      <section className="hero-panel">
        <InteractiveAvatar className="hero-avatar" alt="鑫哥头像" />
        <div className="hero-copy">
          <h1 className="hero-title">{statusText}</h1>
        </div>
      </section>

      <Composer {...composerProps} />
    </div>
  );
}
