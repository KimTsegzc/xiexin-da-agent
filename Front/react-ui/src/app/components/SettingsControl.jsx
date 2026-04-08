import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

import { PROJECT_INFO } from "../constants";

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
  const [infoOpen, setInfoOpen] = useState(false);

  useEffect(() => {
    if (!infoOpen) return undefined;

    function handleKeyDown(event) {
      if (event.key === "Escape") {
        setInfoOpen(false);
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [infoOpen]);

  const infoModal = infoOpen ? (
    <div className="info-modal-backdrop" role="presentation" onClick={() => setInfoOpen(false)}>
      <section
        className="info-modal"
        role="dialog"
        aria-modal="true"
        aria-label="项目信息"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="info-modal-head">
          <div>
            <div className="info-modal-kicker">INFO</div>
            <h2 className="info-modal-title">{PROJECT_INFO.projectName}</h2>
          </div>
          <button
            type="button"
            className="info-modal-close"
            onClick={() => setInfoOpen(false)}
            aria-label="关闭项目信息"
          >
            <span />
            <span />
          </button>
        </div>
        <div className="info-modal-body">
          <div className="info-meta-row">
            <span className="info-meta-label">开发单位</span>
            <span className="info-meta-value">{PROJECT_INFO.developer}</span>
          </div>
          <div className="info-meta-row">
            <span className="info-meta-label">版本编号</span>
            <span className="info-meta-value">{PROJECT_INFO.version}</span>
          </div>
          <div className="info-meta-block">
            <div className="info-meta-label">主要功能</div>
            <ul className="info-feature-list">
              {PROJECT_INFO.features.map((feature) => (
                <li key={feature}>{feature}</li>
              ))}
            </ul>
          </div>
        </div>
      </section>
    </div>
  ) : null;

  return (
    <div className="topbar-actions" ref={anchorRef}>
      {popoverOpen ? (
        <button
          type="button"
          className={`info-toggle ${newChatPlacement === "below" ? "is-below" : "is-above"} ${showNewChat ? "is-stacked" : ""}`}
          onClick={() => setInfoOpen(true)}
          aria-label="查看项目信息"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <circle cx="12" cy="12" r="9" />
            <path d="M12 10v6" />
            <circle cx="12" cy="7.2" r="1" className="info-dot" />
          </svg>
        </button>
      ) : null}

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

      {infoModal && typeof document !== "undefined" ? createPortal(infoModal, document.body) : null}
    </div>
  );
}
