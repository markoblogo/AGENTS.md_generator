(() => {
  // Theme toggle: keep it idempotent even if scripts are injected twice.
  if (!window.__agentsgenThemeInit) {
    window.__agentsgenThemeInit = true;

    const applyTheme = (t) => {
      document.documentElement.dataset.theme = t;
      try {
        localStorage.setItem("theme", t);
      } catch {}
    };

    const getTheme = () => document.documentElement.dataset.theme || "light";

    const themeBtn = document.getElementById("theme-toggle");
    if (themeBtn) {
      const sync = () => {
        const t = getTheme();
        themeBtn.setAttribute("aria-pressed", t === "dark" ? "true" : "false");
        themeBtn.setAttribute(
          "aria-label",
          t === "dark" ? "Switch to light theme" : "Switch to dark theme",
        );
        themeBtn.setAttribute(
          "title",
          t === "dark" ? "Switch to light theme" : "Switch to dark theme",
        );
      };

      sync();
      themeBtn.addEventListener("click", () => {
        const next = getTheme() === "dark" ? "light" : "dark";
        applyTheme(next);
        sync();
      });
    }
  }

  const btn = document.querySelector("[data-copy-target]");
  if (!btn) return;

  const targetSel = btn.getAttribute("data-copy-target");
  if (!targetSel) return;

  const target = document.querySelector(targetSel);
  if (!target) return;

  const getText = () => {
    const code = target.querySelector("code");
    return (code ? code.textContent : target.textContent) || "";
  };

  btn.addEventListener("click", async () => {
    const text = getText().trimEnd();
    try {
      await navigator.clipboard.writeText(text + "\n");
      const prev = btn.textContent;
      btn.textContent = "Copied";
      window.setTimeout(() => (btn.textContent = prev), 900);
    } catch {
      // Best-effort fallback. No UI spam.
    }
  });
})();
