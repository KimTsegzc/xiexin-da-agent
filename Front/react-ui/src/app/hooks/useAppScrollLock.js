import { useEffect } from "react";

export function useAppScrollLock(appLockActive) {
  useEffect(() => {
    if (!appLockActive) return undefined;

    function lockWindowScroll() {
      if (window.scrollX !== 0 || window.scrollY !== 0) {
        window.scrollTo(0, 0);
      }
    }

    function handleFocusIn(event) {
      const target = event.target;
      const tag = target?.tagName?.toLowerCase();
      if (tag !== "textarea" && tag !== "input") return;
      lockWindowScroll();
      window.setTimeout(lockWindowScroll, 350);
    }

    lockWindowScroll();
    window.addEventListener("scroll", lockWindowScroll, { passive: true });
    document.addEventListener("focusin", handleFocusIn, true);

    return () => {
      window.removeEventListener("scroll", lockWindowScroll);
      document.removeEventListener("focusin", handleFocusIn, true);
    };
  }, [appLockActive]);
}
