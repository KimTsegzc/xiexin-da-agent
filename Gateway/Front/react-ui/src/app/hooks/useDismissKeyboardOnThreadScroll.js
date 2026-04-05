import { useEffect } from "react";

export function useDismissKeyboardOnThreadScroll({ enabled, threadRef, textareaRef }) {
  useEffect(() => {
    if (!enabled || !threadRef.current) return undefined;

    const threadElement = threadRef.current;
    let lastTouchY = null;

    function dismissKeyboard() {
      const textarea = textareaRef.current;
      if (!textarea || document.activeElement !== textarea) return;
      textarea.blur();
    }

    function handleTouchStart(event) {
      lastTouchY = event.touches[0]?.clientY ?? null;
    }

    function handleTouchMove(event) {
      const currentY = event.touches[0]?.clientY;
      if (currentY == null || lastTouchY == null) return;
      if (Math.abs(currentY - lastTouchY) < 6) return;
      lastTouchY = currentY;
      dismissKeyboard();
    }

    function resetTouchState() {
      lastTouchY = null;
    }

    function handleWheel() {
      dismissKeyboard();
    }

    threadElement.addEventListener("touchstart", handleTouchStart, { passive: true });
    threadElement.addEventListener("touchmove", handleTouchMove, { passive: true });
    threadElement.addEventListener("touchend", resetTouchState, { passive: true });
    threadElement.addEventListener("touchcancel", resetTouchState, { passive: true });
    threadElement.addEventListener("wheel", handleWheel, { passive: true });

    return () => {
      threadElement.removeEventListener("touchstart", handleTouchStart);
      threadElement.removeEventListener("touchmove", handleTouchMove);
      threadElement.removeEventListener("touchend", resetTouchState);
      threadElement.removeEventListener("touchcancel", resetTouchState);
      threadElement.removeEventListener("wheel", handleWheel);
    };
  }, [enabled, threadRef, textareaRef]);
}