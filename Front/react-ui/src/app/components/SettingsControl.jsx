import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { PROJECT_INFO, PROJECT_INFO_ID } from "../constants";
import {
  commentInfo,
  fetchInfoReactions,
  getClientSessionId,
  likeInfo,
  unlikeInfo,
} from "../utils/api";

const SHARE_CARD_WIDTH = 1080;
const SHARE_CARD_HEIGHT = 1560;
const SHARE_QR_SIZE = 560;
const SHARE_PADDING = 72;
const SHARE_BODY_LINE_HEIGHT = 56;
const SHARE_LABEL_LINE_HEIGHT = 56;
const SHARE_QR_SHIFT = 40;
const LIKE_COUNT_DISPLAY_BASE = 7;

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = reject;
    image.src = src;
  });
}

function drawWrappedText(ctx, text, x, y, maxWidth, lineHeight, maxLines, align = "left") {
  const words = String(text || "").split("");
  const lines = [];
  let currentLine = "";

  words.forEach((word) => {
    const candidate = `${currentLine}${word}`;
    const width = ctx.measureText(candidate).width;
    if (width <= maxWidth || !currentLine) {
      currentLine = candidate;
      return;
    }
    lines.push(currentLine);
    currentLine = word;
  });

  if (currentLine) {
    lines.push(currentLine);
  }

  const visibleLines = lines.slice(0, Math.max(1, maxLines));
  if (lines.length > visibleLines.length) {
    const lastLine = visibleLines[visibleLines.length - 1];
    visibleLines[visibleLines.length - 1] = `${lastLine.slice(0, Math.max(0, lastLine.length - 1))}…`;
  }

  const previousAlign = ctx.textAlign;
  ctx.textAlign = align;
  visibleLines.forEach((line, index) => {
    const drawX = align === "center" ? x + maxWidth / 2 : x;
    ctx.fillText(line, drawX, y + index * lineHeight);
  });
  ctx.textAlign = previousAlign;

  return y + visibleLines.length * lineHeight;
}

function fillRoundedRect(ctx, x, y, width, height, radius, fillStyle) {
  ctx.fillStyle = fillStyle;
  ctx.beginPath();
  ctx.roundRect(x, y, width, height, radius);
  ctx.fill();
}

function drawShareSection(ctx, label, content, x, y, maxWidth, labelFont, contentFont, labelColor, contentColor) {
  ctx.fillStyle = labelColor;
  ctx.font = labelFont;
  ctx.textAlign = "left";
  ctx.fillText(label, x, y);

  ctx.fillStyle = contentColor;
  ctx.font = contentFont;
  return drawWrappedText(ctx, content, x, y + SHARE_LABEL_LINE_HEIGHT, maxWidth, SHARE_BODY_LINE_HEIGHT, 3) + 10;
}

function drawShareValue(ctx, content, x, y, maxWidth, contentFont, contentColor) {
  ctx.fillStyle = contentColor;
  ctx.font = contentFont;
  return drawWrappedText(ctx, content, x, y + SHARE_LABEL_LINE_HEIGHT, maxWidth, SHARE_BODY_LINE_HEIGHT, 3) + 10;
}

function formatCommentTime(value) {
  if (!value) {
    return "";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  const year = String(date.getFullYear()).slice(-2);
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${year}年${month}月${day}日 ${hours}:${minutes}`;
}

async function tryNativeWechatShare({ title, desc, link, imgUrl }) {
  function waitForBridge() {
    if (window.WeixinJSBridge?.invoke) {
      return Promise.resolve(window.WeixinJSBridge);
    }

    return new Promise((resolve) => {
      const timer = window.setTimeout(() => resolve(null), 1200);
      const onReady = () => {
        window.clearTimeout(timer);
        document.removeEventListener("WeixinJSBridgeReady", onReady);
        resolve(window.WeixinJSBridge || null);
      };
      document.addEventListener("WeixinJSBridgeReady", onReady, { once: true });
    });
  }

  const bridge = await waitForBridge();
  if (!bridge?.invoke) {
    return false;
  }

  const payload = {
    title,
    desc,
    link,
    img_url: imgUrl,
  };

  return new Promise((resolve) => {
    bridge.invoke("sendAppMessage", payload, (result) => {
      const status = String(result?.err_msg || "").toLowerCase();
      resolve(status.includes("ok"));
    });
  });
}

async function createShareImageDataUrl() {
  const canvas = document.createElement("canvas");
  canvas.width = SHARE_CARD_WIDTH;
  canvas.height = SHARE_CARD_HEIGHT;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    throw new Error("canvas is not available");
  }

  const backgroundGradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
  backgroundGradient.addColorStop(0, "#f6f7fb");
  backgroundGradient.addColorStop(1, "#eef2f7");
  ctx.fillStyle = backgroundGradient;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  ctx.fillStyle = "rgba(148, 163, 184, 0.12)";
  ctx.beginPath();
  ctx.arc(172, 154, 136, 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.arc(940, 1180, 176, 0, Math.PI * 2);
  ctx.fill();

  const cardX = 64;
  const cardY = 52;
  const cardWidth = canvas.width - cardX * 2;
  const cardHeight = canvas.height - cardY * 2;
  const contentX = cardX + SHARE_PADDING;
  const contentWidth = cardWidth - SHARE_PADDING * 2;
  const cardBottom = cardY + cardHeight;

  ctx.shadowColor = "rgba(15, 23, 42, 0.08)";
  ctx.shadowBlur = 28;
  ctx.shadowOffsetY = 10;
  fillRoundedRect(ctx, cardX, cardY, cardWidth, cardHeight, 36, "#ffffff");
  ctx.shadowColor = "transparent";
  ctx.shadowBlur = 0;
  ctx.shadowOffsetY = 0;

  const LABEL_COLOR = "#7a8598";
  const CONTENT_COLOR = "#111827";
  const DIVIDER_COLOR = "#e7ebf2";
  const KICKER_FONT = "600 30px 'Avenir Next', 'SF Pro Display', 'Segoe UI Variable Display', 'PingFang SC', 'Microsoft YaHei', sans-serif";
  const TITLE_FONT = "700 56px 'Avenir Next', 'SF Pro Display', 'Segoe UI Variable Display', 'PingFang SC', 'Microsoft YaHei', sans-serif";
  const LABEL_FONT = "600 44px 'Avenir Next', 'SF Pro Display', 'Segoe UI Variable Display', 'PingFang SC', 'Microsoft YaHei', sans-serif";
  const CONTENT_FONT = "500 44px 'Avenir Next', 'SF Pro Display', 'Segoe UI Variable Display', 'PingFang SC', 'Microsoft YaHei', sans-serif";
  const CONTENT_FONT_REGULAR = "400 44px 'Avenir Next', 'SF Pro Display', 'Segoe UI Variable Display', 'PingFang SC', 'Microsoft YaHei', sans-serif";
  const CAPTION_FONT = "600 32px 'Avenir Next', 'SF Pro Display', 'Segoe UI Variable Display', 'PingFang SC', 'Microsoft YaHei', sans-serif";

  let cursorY = cardY + 90;
  ctx.fillStyle = LABEL_COLOR;
  ctx.font = KICKER_FONT;
  cursorY = drawWrappedText(ctx, "INFO", contentX, cursorY, contentWidth, 36, 1, "center") + 26;

  ctx.fillStyle = CONTENT_COLOR;
  ctx.font = TITLE_FONT;
  cursorY = drawWrappedText(ctx, PROJECT_INFO.projectName, contentX, cursorY, contentWidth, 68, 2, "center") + 28;

  ctx.strokeStyle = DIVIDER_COLOR;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(cardX + 120, cursorY);
  ctx.lineTo(cardX + cardWidth - 120, cursorY);
  ctx.stroke();
  cursorY += 42 + SHARE_BODY_LINE_HEIGHT;

  cursorY = drawShareSection(
    ctx,
    "项目说明",
    PROJECT_INFO.info,
    contentX,
    cursorY,
    contentWidth,
    LABEL_FONT,
    CONTENT_FONT,
    LABEL_COLOR,
    CONTENT_COLOR,
  );
  cursorY = drawShareSection(
    ctx,
    "开发单位",
    PROJECT_INFO.developer,
    contentX,
    cursorY,
    contentWidth,
    LABEL_FONT,
    CONTENT_FONT,
    LABEL_COLOR,
    CONTENT_COLOR,
  );
  ctx.fillStyle = LABEL_COLOR;
  ctx.font = LABEL_FONT;
  ctx.textAlign = "left";
  ctx.fillText("版本编号", contentX, cursorY);
  cursorY = drawShareValue(ctx, PROJECT_INFO.version, contentX, cursorY, contentWidth, CONTENT_FONT_REGULAR, CONTENT_COLOR);

  const qrPanelY = Math.max(cursorY + 20, cardY + 760);
  const qrPanelHeight = cardBottom - qrPanelY - 52;
  fillRoundedRect(ctx, contentX, qrPanelY, contentWidth, qrPanelHeight, 30, "#f6f8fb");

  const qr = await loadImage("/app-qr-code.png");
  const qrPanelPadding = 24;
  const qrCaptionGap = 20;
  const qrCaptionLineHeight = 40;
  const qrCaptionOffset = qrCaptionLineHeight * 2;
  const qrCaptionBottomPadding = 26;
  const qrSize = Math.min(
    SHARE_QR_SIZE,
    contentWidth - qrPanelPadding * 2 - 20,
    qrPanelHeight - qrPanelPadding * 2 - qrCaptionGap - qrCaptionOffset - qrCaptionLineHeight - qrCaptionBottomPadding,
  );
  const qrBlockHeight = qrSize + qrCaptionGap + qrCaptionOffset + qrCaptionLineHeight;
  const qrX = Math.round((canvas.width - qrSize) / 2);
  const qrY = qrPanelY + Math.max(qrPanelPadding, Math.round((qrPanelHeight - qrBlockHeight) / 2)) + SHARE_QR_SHIFT;

  fillRoundedRect(ctx, qrX - 18, qrY - 18, qrSize + 36, qrSize + 36, 24, "#ffffff");
  ctx.drawImage(qr, qrX, qrY, qrSize, qrSize);

  ctx.fillStyle = LABEL_COLOR;
  ctx.font = CAPTION_FONT;
  drawWrappedText(
    ctx,
    "微信扫一扫，进入应用",
    contentX,
    qrY + qrSize + qrCaptionGap + qrCaptionOffset,
    contentWidth,
    qrCaptionLineHeight,
    1,
    "center",
  );

  return canvas.toDataURL("image/png");
}

export function SettingsControl({
  apiBase,
  clientMode,
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
  const [likeCount, setLikeCount] = useState(0);
  const [userHasLiked, setUserHasLiked] = useState(false);
  const [comments, setComments] = useState([]);
  const [reactionsBusy, setReactionsBusy] = useState(false);
  const [actionBusy, setActionBusy] = useState(false);
  const [commentDraft, setCommentDraft] = useState("");
  const [commentBusy, setCommentBusy] = useState(false);
  const [commentEditorOpen, setCommentEditorOpen] = useState(false);
  const [errorText, setErrorText] = useState("");
  const [sharePanelOpen, setSharePanelOpen] = useState(false);
  const [shareBusy, setShareBusy] = useState(false);
  const [shareImageUrl, setShareImageUrl] = useState("");
  const commentInputRef = useRef(null);
  const commentsSectionRef = useRef(null);
  const shareImagePromiseRef = useRef(null);
  const sessionId = useMemo(() => getClientSessionId(), []);
  const isWechatClient = clientMode === "wechat";
  const displayedLikeCount = Math.max(0, likeCount) + LIKE_COUNT_DISPLAY_BASE;
  const likeCountText = displayedLikeCount > 99 ? "99+" : String(displayedLikeCount);
  const renderedComments = useMemo(
    () => [
      {
        id: `${PROJECT_INFO_ID}-release-comment`,
        user_name: "谢鑫",
        created_at: PROJECT_INFO.releaseTime,
        content: "感谢支持，欢迎大家多吐槽~",
      },
      ...comments,
    ],
    [comments],
  );

  async function ensureShareImageUrl() {
    if (shareImageUrl) {
      return shareImageUrl;
    }

    if (!shareImagePromiseRef.current) {
      shareImagePromiseRef.current = createShareImageDataUrl()
        .then((imageUrl) => {
          setShareImageUrl(imageUrl);
          return imageUrl;
        })
        .finally(() => {
          shareImagePromiseRef.current = null;
        });
    }

    return shareImagePromiseRef.current;
  }

  function handleCommentDraftChange(event) {
    const nextValue = event.target.value;
    setCommentDraft(nextValue);

    const inputElement = event.target;
    inputElement.style.height = "auto";
    const minHeight = 44;
    const maxHeight = 150;
    const nextHeight = Math.min(Math.max(inputElement.scrollHeight, minHeight), maxHeight);
    inputElement.style.height = `${nextHeight}px`;
    inputElement.style.overflowY = inputElement.scrollHeight > maxHeight ? "auto" : "hidden";
  }

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

  useEffect(() => {
    if (!infoOpen) return undefined;
    let active = true;

    async function loadReactions() {
      setReactionsBusy(true);
      setErrorText("");
      setCommentEditorOpen(false);
      try {
        const data = await fetchInfoReactions({
          apiBase,
          infoId: PROJECT_INFO_ID,
          sessionId,
        });
        if (!active) return;
        setLikeCount(Number(data.like_count || 0));
        setUserHasLiked(Boolean(data.user_has_liked));
        setComments(Array.isArray(data.comments) ? data.comments : []);
      } catch (error) {
        if (!active) return;
        setErrorText(error?.message || "加载互动信息失败");
      } finally {
        if (active) {
          setReactionsBusy(false);
        }
      }
    }

    void loadReactions();

    return () => {
      active = false;
    };
  }, [apiBase, infoOpen, sessionId]);

  useEffect(() => {
    if (!infoOpen || shareImageUrl) {
      return undefined;
    }

    let active = true;
    void ensureShareImageUrl().catch(() => {
      if (!active) {
        return;
      }
    });

    return () => {
      active = false;
    };
  }, [infoOpen, shareImageUrl]);

  async function handleToggleLike() {
    if (actionBusy || reactionsBusy) return;
    setActionBusy(true);
    setErrorText("");
    try {
      const data = userHasLiked
        ? await unlikeInfo({ apiBase, infoId: PROJECT_INFO_ID, sessionId })
        : await likeInfo({ apiBase, infoId: PROJECT_INFO_ID, sessionId });
      setLikeCount(Number(data.like_count || 0));
      setUserHasLiked(Boolean(data.user_has_liked));
    } catch (error) {
      setErrorText(error?.message || "点赞操作失败");
    } finally {
      setActionBusy(false);
    }
  }

  function handleFocusComment() {
    setCommentEditorOpen(true);
    setSharePanelOpen(false);
    commentsSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    window.setTimeout(() => {
      commentInputRef.current?.focus();
    }, 120);
  }

  async function handleSubmitComment(event) {
    event?.preventDefault();
    const trimmed = commentDraft.trim();
    if (!trimmed || commentBusy) return;

    setCommentBusy(true);
    setErrorText("");
    try {
      const data = await commentInfo({
        apiBase,
        infoId: PROJECT_INFO_ID,
        sessionId,
        content: trimmed,
      });
      if (data?.comment) {
        setComments((current) => [...current, data.comment]);
      }
      setCommentDraft("");
      if (commentInputRef.current) {
        commentInputRef.current.style.height = "44px";
        commentInputRef.current.style.overflowY = "hidden";
      }
      window.setTimeout(() => {
        commentsSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
      }, 90);
    } catch (error) {
      setErrorText(error?.message || "评论发送失败");
    } finally {
      setCommentBusy(false);
    }
  }

  async function handleShare() {
    if (shareBusy) return;
    setShareBusy(true);
    setErrorText("");
    try {
      const link = window.location.href;
      const shared = await tryNativeWechatShare({
        title: PROJECT_INFO.projectName,
        desc: `${PROJECT_INFO.info} ${PROJECT_INFO.version}`,
        link,
        imgUrl: `${window.location.origin}/app-qr-code.png`,
      });

      if (shared) {
        return;
      }

      const imageUrl = await ensureShareImageUrl();
      setSharePanelOpen(true);
    } catch (error) {
      setErrorText(error?.message || "转发失败，请稍后重试");
    } finally {
      setShareBusy(false);
    }
  }

  function handleDownloadShareImage() {
    if (!shareImageUrl) return;
    const anchorElement = document.createElement("a");
    anchorElement.href = shareImageUrl;
    anchorElement.download = `${PROJECT_INFO_ID}.png`;
    anchorElement.click();
  }

  const infoModal = infoOpen ? (
    <div className="info-modal-backdrop" role="presentation" onClick={() => setInfoOpen(false)}>
      <section
        className={`info-modal ${sharePanelOpen ? "is-share-only" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label="项目信息"
        onClick={(event) => event.stopPropagation()}
      >
        {sharePanelOpen ? (
          <div className="info-modal-head info-modal-head-share">
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
        ) : (
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
        )}
        <div className="info-modal-body">
          {sharePanelOpen ? (
            <div className="info-share-full">
              <div className="info-share-full-image-wrap">
                {shareImageUrl ? <img className="info-share-full-image" src={shareImageUrl} alt="分享提示图预览" /> : null}
              </div>
              {isWechatClient ? (
                <div className="info-share-full-note">长按图片保存</div>
              ) : (
                <div className="info-share-full-actions">
                  <button type="button" className="info-share-button" onClick={handleDownloadShareImage}>
                    保存图片
                  </button>
                  <button type="button" className="info-share-button is-ghost" onClick={() => setSharePanelOpen(false)}>
                    返回
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="info-modal-scroll-content">
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
          <div className="info-meta-block">
            <div className="info-meta-label">版本变更</div>
            <div className="info-meta-value">{PROJECT_INFO.versionChange}</div>
          </div>

          <div className={`info-actions ${isWechatClient ? "is-wechat-compact" : ""}`.trim()} role="group" aria-label="互动操作">
            <button
              type="button"
              className={`info-action-button is-like ${userHasLiked ? "is-active" : ""}`}
              onClick={handleToggleLike}
              disabled={actionBusy || reactionsBusy}
              aria-label={userHasLiked ? "取消点赞" : "点赞"}
            >
              <svg className="info-action-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path d="M12 20.2c-.2 0-.4-.1-.6-.2C8.1 18 3 14.3 3 9.9 3 7.2 5.1 5 7.8 5c1.6 0 3.1.8 4.2 2.1C13 5.8 14.5 5 16.2 5 18.9 5 21 7.2 21 9.9c0 4.4-5.1 8.1-8.4 9.9-.2.1-.4.2-.6.2z" />
              </svg>
              {!isWechatClient ? <span className="info-action-label">赞</span> : null}
              <span className="info-action-count">{likeCountText}</span>
            </button>
            <button
              type="button"
              className={`info-action-button ${shareBusy ? "is-busy" : ""}`}
              onClick={handleShare}
              disabled={shareBusy}
              aria-label="转发"
            >
              <svg className="info-action-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path d="M15 5l6 6-6 6" />
                <path d="M21 11H9a6 6 0 0 0-6 6" />
              </svg>
              {!isWechatClient ? <span className="info-action-label">转发</span> : null}
            </button>
            <button type="button" className="info-action-button" onClick={handleFocusComment} aria-label="评论">
              <svg className="info-action-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path d="M4 5h16a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H9l-5 3v-3H4a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z" />
              </svg>
              {!isWechatClient ? <span className="info-action-label">评论</span> : null}
            </button>
          </div>
          <div className="info-comments" ref={commentsSectionRef}>
            <div className="info-meta-label">评论区</div>
            <div className="info-comment-list" aria-live="polite">
              {renderedComments.length ? (
                renderedComments.map((item) => (
                  <div key={item.id || `${item.created_at}-${item.content}`} className="info-comment-item">
                    <div className="info-comment-head">
                      <span className="info-comment-user">{item.user_name || "匿名"}</span>
                      <span className="info-comment-time">{formatCommentTime(item.created_at)}</span>
                    </div>
                    <div className="info-comment-content">{item.content}</div>
                  </div>
                ))
              ) : (
                <div className="info-comment-empty">还没有评论，来做第一个评论的人吧。</div>
              )}
            </div>
            {commentEditorOpen ? (
              <form className="info-comment-editor" onSubmit={handleSubmitComment}>
                <textarea
                  ref={commentInputRef}
                  value={commentDraft}
                  onChange={handleCommentDraftChange}
                  placeholder="说点什么..."
                  maxLength={600}
                  rows={1}
                />
                <button type="submit" className="info-comment-submit" disabled={commentBusy || !commentDraft.trim()}>
                  {commentBusy ? "发布中" : "发布"}
                </button>
              </form>
            ) : null}
          </div>

          {errorText ? <div className="info-inline-error">{errorText}</div> : null}
            </div>
          )}
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
