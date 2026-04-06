import { useEffect, useState } from "react";

export function useHeroTyping(heroText, restartKey = 0) {
  const [statusText, setStatusText] = useState("");
  const resolvedHeroText = String(heroText || "");

  useEffect(() => {
    if (!resolvedHeroText) {
      setStatusText("");
      return undefined;
    }

    let timer = 0;
    setStatusText("");

    const frame = requestAnimationFrame(() => {
      let index = 0;
      timer = window.setInterval(() => {
        index += 1;
        setStatusText(resolvedHeroText.slice(0, index) || resolvedHeroText);
        if (index >= resolvedHeroText.length) {
          window.clearInterval(timer);
        }
      }, 45);
    });

    return () => {
      window.cancelAnimationFrame(frame);
      if (timer) {
        window.clearInterval(timer);
      }
    };
  }, [restartKey, resolvedHeroText]);

  return statusText;
}
