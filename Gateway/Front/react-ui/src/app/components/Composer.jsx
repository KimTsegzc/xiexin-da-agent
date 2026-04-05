export function Composer({
  input,
  setInput,
  handleSubmit,
  handleComposerKeyDown,
  loading,
  configReady,
  selectedModel,
  textareaRef,
  autoFocus,
}) {
  return (
    <form className="composer-shell" onSubmit={handleSubmit}>
      <div className={`composer-box ${input.trim() ? "has-text" : "is-empty"}`}>
        <div className="composer-leading">
          <div className="composer-model">{selectedModel || "MODEL"}</div>
        </div>
        <textarea
          ref={textareaRef}
          rows={1}
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleComposerKeyDown}
          placeholder="Ask anything"
          disabled={!configReady || loading}
          autoFocus={autoFocus}
        />
        <button type="submit" className="send-button" disabled={!configReady || loading}>
          {loading ? "..." : "➤"}
        </button>
      </div>
    </form>
  );
}
