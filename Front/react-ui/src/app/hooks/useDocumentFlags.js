import { useEffect } from "react";

function useDocumentDataset(key, value) {
  useEffect(() => {
    if (value == null) return undefined;

    document.documentElement.dataset[key] = value;
    document.body.dataset[key] = value;

    return () => {
      delete document.documentElement.dataset[key];
      delete document.body.dataset[key];
    };
  }, [key, value]);
}

export function useDocumentFlags({ clientMode, appLockActive, welcomeLockActive }) {
  useDocumentDataset("clientMode", clientMode);
  useDocumentDataset("appLock", appLockActive ? "true" : "false");
  useDocumentDataset("welcomeLock", welcomeLockActive ? "true" : "false");
}
