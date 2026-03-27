import { Text, View } from "@tarojs/components";
import { useMemo, useRef, useState } from "react";
import { ChatStage } from "../../app/components/ChatStage";
import { Composer } from "../../app/components/Composer";
import { InteractiveAvatar } from "../../app/components/InteractiveAvatar";
import { SettingsControl } from "../../app/components/SettingsControl";
import { WelcomeShell } from "../../app/components/WelcomeShell";
import { useChatSession } from "../../app/hooks/useChatSession";
import { useFrontendConfig } from "../../app/hooks/useFrontendConfig";
import { useHeroTyping } from "../../app/hooks/useHeroTyping";
import { useKeyboardHeight } from "../../app/hooks/useKeyboardHeight";
import { resolveApiBase } from "../../app/utils/api";
import "./index.scss";

export default function ChatPage() {
  const apiBase = useMemo(() => resolveApiBase(), []);
  const { models, selectedModel, setSelectedModel, configReady } = useFrontendConfig(apiBase);
  const {
    messages,
    input,
    setInput,
    loading,
    chatMode,
    composerLines,
    setComposerLines,
    handleSubmit,
    resetSession,
  } = useChatSession({ apiBase, selectedModel });
  const keyboardHeight = useKeyboardHeight();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [heroSeed, setHeroSeed] = useState(0);
  const statusText = useHeroTyping(heroSeed);
  const scrollAnchorRef = useRef("");

  function handleReset() {
    setSettingsOpen(false);
    resetSession();
    setHeroSeed((current) => current + 1);
  }

  function handleOpenSettings() {
    setSettingsOpen(true);
  }

  function handleCloseSettings() {
    setSettingsOpen(false);
  }

  function handleSelectModel(model) {
    setSelectedModel(model);
    setSettingsOpen(false);
  }

  async function handleComposerSubmit(event) {
    setSettingsOpen(false);
    await handleSubmit(event);
  }

  scrollAnchorRef.current = `msg-${messages.length}`;

  return (
    <View className={`mobile-page ${chatMode ? "chat-mode" : "welcome-mode"}`}>
      <View className="mobile-topbar">
        <View className="mobile-topbar-leading">
          {chatMode ? <InteractiveAvatar className="topbar-avatar" size="topbar" /> : <View className="topbar-avatar-placeholder" />}
        </View>

        {chatMode ? (
          <View className="mobile-topbar-copy">
            <Text className="mobile-topbar-title">XIEXin-online</Text>
            <Text className="mobile-topbar-subtitle">{typeof window !== "undefined" ? window.location.hostname : "192.168.1.78"}</Text>
          </View>
        ) : <View />}

        <SettingsControl
          open={settingsOpen}
          models={models}
          selectedModel={selectedModel}
          onOpen={handleOpenSettings}
          onClose={handleCloseSettings}
          onSelect={handleSelectModel}
          onNewChat={handleReset}
          chatMode={chatMode}
        />
      </View>

      {!chatMode ? <WelcomeShell statusText={statusText} /> : null}

      <ChatStage chatMode={chatMode} messages={messages} scrollAnchorId={scrollAnchorRef.current} />

      <Composer
        input={input}
        setInput={setInput}
        loading={loading}
        configReady={configReady}
        selectedModel={selectedModel}
        onSubmit={handleComposerSubmit}
        keyboardHeight={keyboardHeight}
        composerLines={composerLines}
        setComposerLines={setComposerLines}
        compact={chatMode}
        showModel={!chatMode}
      />
    </View>
  );
}
