import { useEffect, useMemo, useRef, useState } from "react";
import { SettingsControl } from "./app/components/SettingsControl";
import { useAppScrollLock } from "./app/hooks/useAppScrollLock";
import { useChatSession } from "./app/hooks/useChatSession";
import { useClientMode } from "./app/hooks/useClientMode";
import { useDismissKeyboardOnThreadScroll } from "./app/hooks/useDismissKeyboardOnThreadScroll";
import { useDocumentFlags } from "./app/hooks/useDocumentFlags";
import { useFrontendConfig } from "./app/hooks/useFrontendConfig";
import { useHeroTyping } from "./app/hooks/useHeroTyping";
import { useSettingsHotkeys } from "./app/hooks/useSettingsHotkeys";
import { useTextareaAutoSize } from "./app/hooks/useTextareaAutoSize";
import { useThreadAutoScroll } from "./app/hooks/useThreadAutoScroll";
import { useViewportMetrics } from "./app/hooks/useViewportMetrics";
import { DesktopShell } from "./app/shells/DesktopShell";
import { MobileShell } from "./app/shells/MobileShell";
import { WechatShell } from "./app/shells/WechatShell";
import { resetWelcomeSessionId } from "./app/utils/api";
import { resolveApiBase } from "./app/utils/clientMode";

function useSettingsState({ chatMode, models, selectedModel }) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [activeModelIndex, setActiveModelIndex] = useState(-1);
  const [settingsAnchor, setSettingsAnchor] = useState("header");
  const headerSettingsRef = useRef(null);
  const railSettingsRef = useRef(null);

  function getPreferredSettingsAnchor() {
    return chatMode && window.innerWidth > 900 ? "rail" : "header";
  }

  function toggleSettings(anchor) {
    setSettingsAnchor(anchor);
    setSettingsOpen((current) => (settingsAnchor === anchor ? !current : true));
  }

  useEffect(() => {
    if (!settingsOpen) return undefined;

    function handlePointerDown(event) {
      const insideHeader = headerSettingsRef.current?.contains(event.target);
      const insideRail = railSettingsRef.current?.contains(event.target);
      if (!insideHeader && !insideRail) {
        setSettingsOpen(false);
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, [settingsOpen]);

  useEffect(() => {
    if (!settingsOpen) return;
    const selectedIndex = models.indexOf(selectedModel);
    setActiveModelIndex(selectedIndex >= 0 ? selectedIndex : 0);
  }, [models, selectedModel, settingsOpen]);

  return {
    settingsOpen,
    setSettingsOpen,
    activeModelIndex,
    setActiveModelIndex,
    settingsAnchor,
    setSettingsAnchor,
    headerSettingsRef,
    railSettingsRef,
    getPreferredSettingsAnchor,
    toggleSettings,
  };
}

export default function App() {
  const apiBase = useMemo(() => resolveApiBase(), []);
  const { clientMode, isMobileViewport, isMobileDefault, mobileLikeWechat } = useClientMode();
  const {
    models,
    selectedModel,
    setSelectedModel,
    heroWelcomeText,
    configReady,
    refreshFrontendConfig,
  } = useFrontendConfig(apiBase);
  const {
    messages,
    input,
    setInput,
    attachments,
    appendAttachments,
    removeAttachment,
    effectiveComposerModel,
    loading,
    chatMode,
    handleSubmit,
    resetSession,
  } = useChatSession({
    apiBase,
    selectedModel,
  });
  const [heroTypingSeed, setHeroTypingSeed] = useState(0);
  const statusText = useHeroTyping(heroWelcomeText, heroTypingSeed);
  const textareaRef = useRef(null);
  const threadRef = useRef(null);
  const previousLoadingRef = useRef(false);
  const appLockActive = mobileLikeWechat;
  const welcomeLockActive = mobileLikeWechat && !chatMode;
  const allowWelcomeAutoFocus = !mobileLikeWechat;

  useViewportMetrics({ clientMode, isMobileViewport, welcomeLockActive, chatMode });
  useDocumentFlags({ clientMode, appLockActive, welcomeLockActive });
  useAppScrollLock(appLockActive);
  useTextareaAutoSize(textareaRef, input);
  useThreadAutoScroll(threadRef, [messages, loading]);
  useDismissKeyboardOnThreadScroll({
    enabled: mobileLikeWechat && chatMode,
    threadRef,
    textareaRef,
  });

  function focusComposer() {
    textareaRef.current?.focus();
  }

  useEffect(() => {
    const completedReply = previousLoadingRef.current && !loading;
    previousLoadingRef.current = loading;
    if (!completedReply || !chatMode || isMobileViewport) {
      return;
    }

    const focusTimer = window.setTimeout(() => {
      textareaRef.current?.focus();
    }, 0);
    return () => window.clearTimeout(focusTimer);
  }, [loading, chatMode, isMobileViewport]);

  const settingsState = useSettingsState({
    chatMode,
    models,
    selectedModel,
  });

  useSettingsHotkeys({
    models,
    settingsOpen: settingsState.settingsOpen,
    settingsAnchor: settingsState.settingsAnchor,
    activeModelIndex: settingsState.activeModelIndex,
    setSettingsAnchor: settingsState.setSettingsAnchor,
    setSettingsOpen: settingsState.setSettingsOpen,
    setActiveModelIndex: settingsState.setActiveModelIndex,
    setSelectedModel,
    getPreferredSettingsAnchor: settingsState.getPreferredSettingsAnchor,
    focusComposer,
  });

  function handleComposerKeyDown(event) {
    if (event.isComposing) return;
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void handleSubmit();
    }
  }

  async function handleComposerSubmit(event) {
    settingsState.setSettingsOpen(false);
    await handleSubmit(event);
  }

  function handleModelSelect(model) {
    setSelectedModel(model);
    settingsState.setSettingsOpen(false);
    focusComposer();
  }

  async function handleNewChat() {
    settingsState.setSettingsOpen(false);
    resetSession();
    resetWelcomeSessionId();
    await refreshFrontendConfig();
    setHeroTypingSeed((current) => current + 1);
  }

  const newChatPlacement = mobileLikeWechat ? "below" : "above";

  const headerSettingsControl = (
    <SettingsControl
      apiBase={apiBase}
      clientMode={clientMode}
      anchor="header"
      anchorRef={settingsState.headerSettingsRef}
      showNewChat={chatMode}
      newChatPlacement={newChatPlacement}
      models={models}
      selectedModel={selectedModel}
      settingsOpen={settingsState.settingsOpen}
      settingsAnchor={settingsState.settingsAnchor}
      activeModelIndex={settingsState.activeModelIndex}
      onToggle={settingsState.toggleSettings}
      onHover={settingsState.setActiveModelIndex}
      onSelect={handleModelSelect}
      onNewChat={handleNewChat}
    />
  );

  const railSettingsControl = (
    <SettingsControl
      apiBase={apiBase}
      clientMode={clientMode}
      anchor="rail"
      anchorRef={settingsState.railSettingsRef}
      showNewChat={chatMode}
      newChatPlacement="above"
      models={models}
      selectedModel={selectedModel}
      settingsOpen={settingsState.settingsOpen}
      settingsAnchor={settingsState.settingsAnchor}
      activeModelIndex={settingsState.activeModelIndex}
      onToggle={settingsState.toggleSettings}
      onHover={settingsState.setActiveModelIndex}
      onSelect={handleModelSelect}
      onNewChat={handleNewChat}
    />
  );

  const composerProps = {
    input,
    setInput,
    attachments,
    onAttachFiles: appendAttachments,
    onRemoveAttachment: removeAttachment,
    handleSubmit: handleComposerSubmit,
    handleComposerKeyDown,
    loading,
    configReady,
    selectedModel: effectiveComposerModel,
    textareaRef,
    autoFocus: !chatMode && allowWelcomeAutoFocus,
  };

  const shellProps = {
    clientMode,
    chatMode,
    statusText,
    headerSettingsControl,
    railSettingsControl,
    threadRef,
    messages,
    composerProps,
  };

  if (clientMode === "wechat") {
    return <WechatShell {...shellProps} />;
  }

  if (isMobileDefault) {
    return <MobileShell {...shellProps} />;
  }

  return <DesktopShell {...shellProps} />;
}
