(() => {
  const root = document.documentElement;

  const normalizeStyle = (value) => (value === "ascii" ? "ascii" : "default");

  const makeBox = (text) => {
    const label = String(text || "").replace(/\s+/g, " ").trim();
    const inner = `  ${label}  `;
    const top = `┌${"─".repeat(inner.length)}┐`;
    const mid = `│${inner}│`;
    const bot = `└${"─".repeat(inner.length)}┘`;
    return `${top}\n${mid}\n${bot}`;
  };

  const stickerNodes = Array.from(document.querySelectorAll("[data-ascii-sticker]"));
  for (const node of stickerNodes) {
    if (!node.dataset.asciiOriginalHtml) {
      node.dataset.asciiOriginalHtml = node.innerHTML;
    }
  }

  const renderStickers = (style) => {
    const ascii = style === "ascii";
    for (const node of stickerNodes) {
      const label = (node.getAttribute("data-ascii-sticker") || "").trim();
      if (!label) continue;

      if (ascii) {
        node.innerHTML = "";
        const pre = document.createElement("pre");
        pre.className = "ascii-sticker";
        pre.textContent = makeBox(label);
        pre.setAttribute("aria-label", label);
        node.appendChild(pre);
      } else {
        node.innerHTML = node.dataset.asciiOriginalHtml || label;
      }
    }
  };

  const updateAsciiToggleUI = () => {
    const toggle = document.querySelector("[data-ascii-toggle]");
    if (!toggle) return;
    const style = normalizeStyle(root.dataset.style || "default");
    const asciiEnabled = style === "ascii";
    toggle.textContent = asciiEnabled ? "Default" : "ASCII";
    toggle.setAttribute(
      "aria-label",
      asciiEnabled ? "Switch to default style" : "Switch to ASCII style",
    );
    toggle.setAttribute(
      "title",
      asciiEnabled ? "Switch to default style" : "Switch to ASCII style",
    );
  };

  const applyStyle = (style) => {
    const next = normalizeStyle(style);
    root.dataset.style = next;
    renderStickers(next);
    updateAsciiToggleUI();
  };

  const init = () => {
    // ASCII is opt-in only for this landing: never auto-restore from storage.
    const initial = "default";
    applyStyle(initial);

    const toggle = document.querySelector("[data-ascii-toggle]");
    if (toggle) {
      toggle.addEventListener("click", () => {
        const current = normalizeStyle(root.dataset.style || "default");
        const next = current === "ascii" ? "default" : "ascii";
        applyStyle(next);
      });
    }
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
