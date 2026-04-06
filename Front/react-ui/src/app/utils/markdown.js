function renderInlineMarkdown(text) {
  return String(text || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/__([^_]+)__/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>")
    .replace(/_([^_]+)_/g, "<em>$1</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer noopener">$1</a>');
}

export function renderMarkdown(markdownText) {
  const source = String(markdownText || "").replace(/\r\n/g, "\n");
  const blocks = source.split(/\n\n+/).filter(Boolean);

  return blocks
    .map((block) => {
      if (/^#{1,6}\s/.test(block)) {
        const match = block.match(/^(#{1,6})\s+(.*)$/);
        const level = match[1].length;
        return `<h${level}>${renderInlineMarkdown(match[2])}</h${level}>`;
      }

      if (/^[-*+]\s/m.test(block)) {
        const items = block
          .split("\n")
          .filter(Boolean)
          .map((item) => item.replace(/^[-*+]\s+/, ""))
          .map((item) => `<li>${renderInlineMarkdown(item)}</li>`)
          .join("");
        return `<ul>${items}</ul>`;
      }

      return `<p>${renderInlineMarkdown(block).replace(/\n/g, "<br />")}</p>`;
    })
    .join("");
}
