/* theme-toggle.js — shared dark mode toggle for Ecosistema VIDA UG.
   Include in <head> right after theme.css: applies the saved theme
   immediately (no flash) and injects a floating toggle button. */
(function () {
  var STORAGE_KEY = "theme";

  function isDark() {
    return document.documentElement.classList.contains("dark");
  }

  function applyTheme(theme) {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }

  applyTheme(localStorage.getItem(STORAGE_KEY) || "light");

  function injectButton() {
    if (document.getElementById("theme-toggle")) return;
    var btn = document.createElement("button");
    btn.id = "theme-toggle";
    btn.type = "button";
    btn.setAttribute("aria-label", "Cambiar tema claro/oscuro");
    btn.title = "Cambiar tema";
    btn.style.cssText =
      "position:fixed;bottom:18px;right:18px;z-index:60;width:44px;height:44px;" +
      "border-radius:9999px;display:flex;align-items:center;justify-content:center;" +
      "cursor:pointer;border:1px solid rgba(128,128,128,0.25);" +
      "box-shadow:0 6px 20px rgba(0,0,0,0.18);backdrop-filter:blur(6px);" +
      "background:var(--c-sidebar,#fff);color:var(--c-title,#2D073F);" +
      "transition:transform 0.15s;";
    btn.innerHTML =
      '<span class="material-symbols-outlined" style="font-size:22px;">dark_mode</span>';

    function syncIcon() {
      var icon = btn.querySelector("span");
      if (icon) icon.textContent = isDark() ? "light_mode" : "dark_mode";
    }

    btn.addEventListener("click", function () {
      var dark = document.documentElement.classList.toggle("dark");
      localStorage.setItem(STORAGE_KEY, dark ? "dark" : "light");
      syncIcon();
    });
    btn.addEventListener("mousedown", function () {
      btn.style.transform = "scale(0.92)";
    });
    btn.addEventListener("mouseup", function () {
      btn.style.transform = "";
    });

    document.body.appendChild(btn);
    syncIcon();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", injectButton);
  } else {
    injectButton();
  }
})();
