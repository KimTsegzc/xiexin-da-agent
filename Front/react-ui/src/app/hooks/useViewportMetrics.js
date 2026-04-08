import { useEffect, useRef } from "react";

function isEditableTarget(target) {
  const tag = target?.tagName?.toLowerCase();
  return tag === "textarea" || tag === "input";
}

function shouldUseViewportFreezeWindow() {
  const userAgent = navigator.userAgent.toLowerCase();
  if (!userAgent.includes("android")) return false;
  if (userAgent.includes("micromessenger")) return false;
  return userAgent.includes("edga/") || userAgent.includes("edge/") || userAgent.includes("chrome/");
}

export function useViewportMetrics({ clientMode, isMobileViewport, welcomeLockActive }) {
  const stableViewportHeightRef = useRef(0);
  const stableViewportWidthRef = useRef(0);
  const frameRef = useRef(0);
  const timerRef = useRef(0);
  const freezeUntilRef = useRef(0);
  const shouldFreezeRef = useRef(false);

  useEffect(() => {
    const root = document.documentElement;
    const isMobileLikeWechat = clientMode === "wechat" || (clientMode === "default" && isMobileViewport);
    const shouldTrackViewportScroll = !welcomeLockActive && !isMobileLikeWechat;
    shouldFreezeRef.current = isMobileLikeWechat || shouldUseViewportFreezeWindow();

    function writeViewportMetrics() {
      const viewport = window.visualViewport;
      const viewportHeight = Math.round(viewport?.height || window.innerHeight);
      const viewportOffsetTop = Math.round(viewport?.offsetTop || 0);
      const viewportWidth = Math.round(window.innerWidth);
      const observedViewportWidth = Math.round(viewport?.width || viewportWidth);
      const nextStableHeight = Math.max(stableViewportHeightRef.current || 0, viewportHeight, window.innerHeight);
      const nextStableWidth = Math.max(stableViewportWidthRef.current || 0, observedViewportWidth, viewportWidth);
      const viewportBottom = viewportOffsetTop + viewportHeight;
      const keyboardOffsetRaw = Math.max(0, nextStableHeight - viewportBottom);
      const keyboardThreshold = Math.max(72, Math.round(nextStableHeight * 0.12));
      const hasEditableFocus = isEditableTarget(document.activeElement);
      const keyboardOffset = hasEditableFocus && keyboardOffsetRaw > keyboardThreshold ? keyboardOffsetRaw : 0;

      stableViewportHeightRef.current = nextStableHeight;
      stableViewportWidthRef.current = nextStableWidth;
      root.style.setProperty("--app-height", welcomeLockActive ? `${nextStableHeight}px` : `${viewportHeight}px`);
      root.style.setProperty("--app-height-stable", `${nextStableHeight}px`);
      root.style.setProperty("--app-width", `${viewportWidth}px`);
      root.style.setProperty("--app-width-stable", `${nextStableWidth}px`);
      root.style.setProperty("--keyboard-offset", welcomeLockActive ? "0px" : `${keyboardOffset}px`);

      if (welcomeLockActive) {
        const isDefaultMobileMode = clientMode === "default" && isMobileViewport;
        const fallbackLockRatio = isDefaultMobileMode ? 0.45 : 0.41;
        const fallbackLock = Math.round(nextStableHeight * fallbackLockRatio);

        root.style.setProperty(
          "--wechat-welcome-lock-bottom",
          `${fallbackLock}px`,
        );
      }
    }

    function syncViewportMetrics(force = false) {
      if (!force && shouldFreezeRef.current && Date.now() < freezeUntilRef.current) {
        return;
      }
      writeViewportMetrics();
    }

    function scheduleSyncViewportMetrics(force = false) {
      if (frameRef.current) {
        window.cancelAnimationFrame(frameRef.current);
      }

      frameRef.current = window.requestAnimationFrame(() => {
        frameRef.current = 0;
        syncViewportMetrics(force);
      });
    }

    function handleViewportEvent() {
      if (welcomeLockActive) return;
      scheduleSyncViewportMetrics();
    }

    function handleOrientationChange() {
      scheduleSyncViewportMetrics(true);
    }

    function scheduleSettledSync(delay) {
      if (timerRef.current) {
        window.clearTimeout(timerRef.current);
      }

      timerRef.current = window.setTimeout(() => {
        timerRef.current = 0;
        scheduleSyncViewportMetrics(true);
      }, delay);
    }

    function handleFocusIn(event) {
      if (!isEditableTarget(event.target)) return;
      if (welcomeLockActive) return;
      if (shouldFreezeRef.current) {
        freezeUntilRef.current = Date.now() + 280;
        scheduleSettledSync(320);
        return;
      }
      scheduleSyncViewportMetrics();
    }

    function handleFocusOut(event) {
      if (!isEditableTarget(event.target)) return;
      if (welcomeLockActive) return;
      if (shouldFreezeRef.current) {
        freezeUntilRef.current = Date.now() + 140;
        scheduleSettledSync(200);
        return;
      }
      scheduleSyncViewportMetrics();
    }

    writeViewportMetrics();
    window.addEventListener("resize", handleViewportEvent);
    window.addEventListener("orientationchange", handleOrientationChange);
    window.visualViewport?.addEventListener("resize", handleViewportEvent);
    if (shouldTrackViewportScroll) {
      window.visualViewport?.addEventListener("scroll", handleViewportEvent);
    }
    document.addEventListener("focusin", handleFocusIn, true);
    document.addEventListener("focusout", handleFocusOut, true);

    return () => {
      if (frameRef.current) {
        window.cancelAnimationFrame(frameRef.current);
      }
      if (timerRef.current) {
        window.clearTimeout(timerRef.current);
      }
      window.removeEventListener("resize", handleViewportEvent);
      window.removeEventListener("orientationchange", handleOrientationChange);
      window.visualViewport?.removeEventListener("resize", handleViewportEvent);
      if (shouldTrackViewportScroll) {
        window.visualViewport?.removeEventListener("scroll", handleViewportEvent);
      }
      document.removeEventListener("focusin", handleFocusIn, true);
      document.removeEventListener("focusout", handleFocusOut, true);
    };
  }, [clientMode, isMobileViewport, welcomeLockActive]);
}
