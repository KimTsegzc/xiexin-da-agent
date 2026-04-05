import { useEffect, useState } from "react";
import { HERO_TEXT } from "../constants";

export function useHeroTyping(restartKey = 0) {
  const [statusText, setStatusText] = useState("");

  useEffect(() => {
    let timer = 0;
    setStatusText("");

    const frame = requestAnimationFrame(() => {
      let index = 0;
      timer = window.setInterval(() => {
        index += 1;
        setStatusText(HERO_TEXT.slice(0, index) || HERO_TEXT);
        if (index >= HERO_TEXT.length) {
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
  }, [restartKey]);

  return statusText;
}
