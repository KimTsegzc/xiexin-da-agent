import { Composer } from "./Composer";
import { InteractiveAvatar } from "./InteractiveAvatar";

function splitWelcomeTitle(text) {
  const value = String(text || "").trim();
  const characters = Array.from(value);
  if (characters.length <= 16) {
    return { multiline: false, lines: [value] };
  }

  const commaMatches = Array.from(value.matchAll(/[，,]/g));
  const commaIndex = commaMatches.length
    ? commaMatches[commaMatches.length - 1].index ?? -1
    : -1;
  if (commaIndex >= 0) {
    const firstLine = value.slice(0, commaIndex).trim();
    const secondLine = value.slice(commaIndex + 1).trim();
    if (firstLine && secondLine) {
      return {
        multiline: true,
        lines: [firstLine, secondLine],
      };
    }
  }

  return {
    multiline: true,
    lines: [characters.slice(0, 10).join(""), characters.slice(10).join("")],
  };
}

export function WelcomeShell({ statusText, composerProps }) {
  const title = splitWelcomeTitle(statusText);

  return (
    <div className="welcome-stack-shell">
      <div className="welcome-hero-shell">
        <section className="hero-panel">
          <InteractiveAvatar className="hero-avatar" alt="鑫哥头像" />
          <div className={`hero-copy${title.multiline ? " is-multiline" : " is-singleline"}`}>
            <h1 className={`hero-title${title.multiline ? " is-multiline" : " is-singleline"}`}>
              {title.lines.map((line, index) => (
                <span key={`${line}-${index}`} className="hero-title-line">
                  {line}
                </span>
              ))}
            </h1>
          </div>
        </section>
      </div>

      <div className="welcome-composer-shell">
        <Composer {...composerProps} />
      </div>
    </div>
  );
}
