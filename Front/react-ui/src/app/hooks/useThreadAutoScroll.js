import { useEffect } from "react";

export function useThreadAutoScroll(threadRef, deps) {
  useEffect(() => {
    if (!threadRef.current) return;
    threadRef.current.scrollTop = threadRef.current.scrollHeight;
  }, deps);
}
