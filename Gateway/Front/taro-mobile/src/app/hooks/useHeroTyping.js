import { useEffect, useState } from "react";
import { HERO_TEXT } from "../../../../frontend-core/constants";

export function useHeroTyping(restartKey = 0) {
  const [statusText, setStatusText] = useState(HERO_TEXT);

  useEffect(() => {
    if (typeof window === "undefined") {
      setStatusText(HERO_TEXT);
      return undefined;
    }

    let timer = 0;
    let frame = 0;
    setStatusText("");

    frame = window.requestAnimationFrame(() => {
      let index = 0;
      timer = window.setInterval(() => {
        index += 1;
        setStatusText(HERO_TEXT.slice(0, index) || HERO_TEXT);
        if (index >= HERO_TEXT.length) {
          window.clearInterval(timer);
        }
      }, 42);
    });

    return () => {
      window.cancelAnimationFrame(frame);
      if (timer) {
        window.clearInterval(timer);
      }
    };
  }, [restartKey]);

  return statusText || HERO_TEXT;
}