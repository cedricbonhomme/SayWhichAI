/* The theme of the site: the one of the system, or the one the reader chose in the
   footer. Loaded in the head, so that the page is not drawn in the wrong colours first. */
(function () {
  "use strict";

  const KEY = "theme";
  const CHOICES = [["auto", "Auto"], ["light", "Light"], ["dark", "Dark"]];

  function stored() {
    // The storage of the browser may be closed: the theme of the system is used then.
    try {
      const value = localStorage.getItem(KEY);
      return value === "light" || value === "dark" ? value : "auto";
    } catch (error) {
      return "auto";
    }
  }

  function apply(choice) {
    if (choice === "auto") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", choice);
  }

  let current = stored();
  apply(current);

  document.addEventListener("DOMContentLoaded", () => {
    const footer = document.querySelector("footer.footer");
    if (!footer) return;
    const group = document.createElement("div");
    group.className = "toggle theme";
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", "Theme");
    const buttons = CHOICES.map(([value, label]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = label;
      button.addEventListener("click", () => {
        current = value;
        apply(current);
        try {
          if (current === "auto") localStorage.removeItem(KEY);
          else localStorage.setItem(KEY, current);
        } catch (error) { /* the choice lasts for this page only */ }
        show();
      });
      group.append(button);
      return button;
    });
    function show() {
      buttons.forEach((button, index) => button.setAttribute("aria-pressed", String(CHOICES[index][0] === current)));
    }
    show();
    footer.append(group);
  });
})();
