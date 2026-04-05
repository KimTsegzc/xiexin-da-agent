export function SettingsControl({
  anchor,
  anchorRef,
  showNewChat,
  newChatPlacement,
  models,
  selectedModel,
  settingsOpen,
  settingsAnchor,
  activeModelIndex,
  onToggle,
  onHover,
  onSelect,
  onNewChat,
}) {
  const popoverOpen = settingsOpen && settingsAnchor === anchor;

  return (
    <div className="topbar-actions" ref={anchorRef}>
      {popoverOpen && showNewChat ? (
        <button
          type="button"
          className={`newchat-toggle ${newChatPlacement === "below" ? "is-below" : "is-above"}`}
          onClick={onNewChat}
          aria-label="开始新会话"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path d="M12 6v12" />
            <path d="M6 12h12" />
          </svg>
        </button>
      ) : null}
      <button
        className={`settings-toggle ${popoverOpen ? "is-open" : ""}`}
        type="button"
        onClick={() => onToggle(anchor)}
        aria-label="切换模型设置"
      >
        <span />
        <span />
        <span />
      </button>
      {popoverOpen ? (
        <div className="settings-popover">
          <div className="settings-title">MODEL</div>
          <div className="settings-list">
            {models.map((model, index) => (
              <button
                key={model}
                type="button"
                className={`settings-option ${selectedModel === model ? "is-selected" : ""} ${activeModelIndex === index ? "is-active" : ""}`}
                onMouseEnter={() => onHover(index)}
                onClick={() => onSelect(model)}
              >
                {model}
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
