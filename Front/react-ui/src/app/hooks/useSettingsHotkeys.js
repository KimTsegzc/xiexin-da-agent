import { useEffect } from "react";

export function useSettingsHotkeys({
  models,
  settingsOpen,
  settingsAnchor,
  activeModelIndex,
  setSettingsAnchor,
  setSettingsOpen,
  setActiveModelIndex,
  setSelectedModel,
  getPreferredSettingsAnchor,
  focusComposer,
}) {
  useEffect(() => {
    function handleGlobalKeyDown(event) {
      if (event.isComposing || event.repeat) return;

      if (event.altKey && !event.ctrlKey && !event.metaKey && event.key.toLowerCase() === "s") {
        event.preventDefault();
        const nextAnchor = getPreferredSettingsAnchor();
        setSettingsAnchor(nextAnchor);
        setSettingsOpen((current) => (settingsAnchor === nextAnchor ? !current : true));
        return;
      }

      if (!settingsOpen) return;

      if (event.key === "Escape") {
        event.preventDefault();
        setSettingsOpen(false);
        focusComposer();
        return;
      }

      if (event.key === "ArrowDown") {
        event.preventDefault();
        setActiveModelIndex((current) => {
          if (!models.length) return -1;
          return current < 0 ? 0 : (current + 1) % models.length;
        });
        return;
      }

      if (event.key === "ArrowUp") {
        event.preventDefault();
        setActiveModelIndex((current) => {
          if (!models.length) return -1;
          return current < 0 ? models.length - 1 : (current - 1 + models.length) % models.length;
        });
        return;
      }

      if (event.key === "Enter") {
        const nextModel = models[activeModelIndex];
        if (!nextModel) return;
        event.preventDefault();
        setSelectedModel(nextModel);
        setSettingsOpen(false);
        focusComposer();
      }
    }

    window.addEventListener("keydown", handleGlobalKeyDown);
    return () => window.removeEventListener("keydown", handleGlobalKeyDown);
  }, [
    activeModelIndex,
    focusComposer,
    getPreferredSettingsAnchor,
    models,
    setActiveModelIndex,
    setSelectedModel,
    setSettingsAnchor,
    setSettingsOpen,
    settingsAnchor,
    settingsOpen,
  ]);
}
