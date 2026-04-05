import { useEffect, useState } from "react";
import { isMobileWidth, resolveClientMode } from "../utils/clientMode";

export function useClientMode() {
  const [clientMode] = useState(() => resolveClientMode());
  const [isMobileViewport, setIsMobileViewport] = useState(() => isMobileWidth());

  useEffect(() => {
    function syncMobileViewportFlag() {
      setIsMobileViewport(isMobileWidth());
    }

    syncMobileViewportFlag();
    window.addEventListener("resize", syncMobileViewportFlag);
    return () => window.removeEventListener("resize", syncMobileViewportFlag);
  }, []);

  const isMobileDefault = clientMode === "default" && isMobileViewport;
  const mobileLikeWechat = clientMode === "wechat" || isMobileDefault;

  return {
    clientMode,
    isMobileViewport,
    isMobileDefault,
    mobileLikeWechat,
  };
}
