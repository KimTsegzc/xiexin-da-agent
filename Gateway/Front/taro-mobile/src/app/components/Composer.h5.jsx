import { Picker, Text, View } from "@tarojs/components";
import { useEffect, useRef } from "react";
import { Button as VantButton, Field } from "react-vant";
import "react-vant/lib/index.css";

function getNativeTextArea(textAreaRef) {
  return textAreaRef.current?.nativeElement || null;
}

export function Composer({
  input,
  setInput,
  loading,
  configReady,
  models,
  selectedModel,
  onModelChange,
  onSubmit,
  keyboardHeight,
  composerLines,
  setComposerLines,
  compact = false,
  showModel = true,
}) {
  const textAreaRef = useRef(null);
  const modelOptions = Array.isArray(models) ? models : [];

  useEffect(() => {
    if (typeof window === "undefined") {
      return undefined;
    }

    const frameId = window.requestAnimationFrame(() => {
      const nativeTextArea = getNativeTextArea(textAreaRef);
      if (!nativeTextArea) {
        return;
      }

      const computedStyle = window.getComputedStyle(nativeTextArea);
      const lineHeight = Number.parseFloat(computedStyle.lineHeight) || 24;
      const scrollHeight = nativeTextArea.scrollHeight || lineHeight;
      const nextLines = Math.max(1, Math.min(4, Math.round(scrollHeight / lineHeight)));
      setComposerLines(nextLines);
    });

    return () => window.cancelAnimationFrame(frameId);
  }, [input, setComposerLines]);

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent?.isComposing) {
      event.preventDefault();
      void onSubmit(event);
    }
  }

  return (
    <View className={`composer-wrap ${compact ? "is-chat" : "is-welcome"}`} style={{ paddingBottom: `${keyboardHeight}px` }}>
      <View className={`composer-shell ${showModel ? "has-model" : "plain-input"} ${input.trim() ? "has-text" : "is-empty"}`}>
        {showModel ? (
          <Picker mode="selector" range={modelOptions} onChange={onModelChange} disabled={!modelOptions.length || loading}>
            <View className="composer-model-pill">
              <Text className="composer-model-pill-text">{selectedModel || (configReady ? "MODEL" : "加载中")}</Text>
            </View>
          </Picker>
        ) : null}

        <Field
          ref={textAreaRef}
          className="composer-vant-field"
          value={input}
          type="textarea"
          border={false}
          rows={1}
          maxLength={4000}
          showWordLimit={false}
          autoSize={{
            minHeight: compact ? 44 : 29,
            maxHeight: compact ? 110 : 90,
          }}
          placeholder="Ask anything"
          disabled={!configReady || loading}
          onKeyPress={handleKeyDown}
          onChange={setInput}
        />

        <VantButton
          className={`send-button ${composerLines > 1 ? "is-tall" : ""}`}
          round
          type="primary"
          loading={loading}
          disabled={!configReady || loading}
          onClick={onSubmit}
        >
          {!loading ? <Text className="send-button-icon">➤</Text> : null}
        </VantButton>
      </View>
    </View>
  );
}