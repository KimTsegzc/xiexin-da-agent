import { useRef } from "react";

export function Composer({
  input,
  setInput,
  attachments,
  onAttachFiles,
  onRemoveAttachment,
  handleSubmit,
  handleComposerKeyDown,
  loading,
  configReady,
  selectedModel,
  textareaRef,
  autoFocus,
}) {
  const fileInputRef = useRef(null);

  function handleAttachClick() {
    fileInputRef.current?.click();
  }

  function handleFileChange(event) {
    onAttachFiles?.(event.target.files);
    event.target.value = "";
  }

  return (
    <form className="composer-shell" onSubmit={handleSubmit}>
      <div className={`composer-box ${input.trim() ? "has-text" : "is-empty"}${attachments?.length ? " has-attachments" : ""}`}>
        {attachments?.length ? (
          <div className="composer-attachments" aria-label="已选上传文件">
            {attachments.map((file, index) => (
              <div key={`${file.name}-${file.size}-${index}`} className="composer-attachment-chip">
                <span className="composer-attachment-kind">{(file.type || "").startsWith("image/") ? "IMG" : "FILE"}</span>
                <span className="composer-attachment-name">{file.name}</span>
                <button
                  type="button"
                  className="composer-attachment-remove"
                  onClick={() => onRemoveAttachment?.(index)}
                  disabled={loading}
                  aria-label={`移除 ${file.name}`}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        ) : null}
        <div className="composer-row">
          <div className="composer-leading">
            <button
              type="button"
              className="composer-attach-button"
              onClick={handleAttachClick}
              disabled={!configReady || loading}
              aria-label="上传图片或文件"
              title="上传图片或文件"
            >
              +
            </button>
            <div className="composer-model">{selectedModel || "MODEL"}</div>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileChange}
            className="composer-file-input"
            disabled={!configReady || loading}
          />
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleComposerKeyDown}
            placeholder={attachments?.length ? "结合上传内容继续提问" : "Ask anything"}
            disabled={!configReady || loading}
            autoFocus={autoFocus}
          />
          <button
            type="submit"
            className="send-button"
            disabled={(!configReady || loading) || (!input.trim() && !attachments?.length)}
          >
            {loading ? "..." : "➤"}
          </button>
        </div>
      </div>
    </form>
  );
}
