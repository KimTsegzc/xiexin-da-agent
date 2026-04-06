import { useEffect } from "react";

export function useTextareaAutoSize(textareaRef, value) {
  useEffect(() => {
    if (!textareaRef.current) return;
    textareaRef.current.style.height = "0px";
    const nextHeight = Math.min(textareaRef.current.scrollHeight, 136);
    textareaRef.current.style.height = `${nextHeight}px`;
  }, [textareaRef, value]);
}
