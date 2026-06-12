/* mascot.js — Sparky, the UG success mascot.
   A small orange spark character (Claude Code style) that pops in,
   blinks, waves, and shows a speech bubble on key success moments.

   Usage:
     SR_Mascot.showSuccess("Enviado correctamente", () => { ...redirect... });

   Self-contained: injects its own styles, respects prefers-reduced-motion,
   works in light and dark mode (uses theme.css variables). */
(function (global) {
  "use strict";

  var STYLE_ID = "sr-mascot-styles";

  var CSS = [
    "#sr-mascot-overlay{position:fixed;inset:0;z-index:90;display:flex;align-items:center;justify-content:center;",
    "background:rgba(43,6,61,0.55);backdrop-filter:blur(4px);opacity:0;transition:opacity .25s ease;}",
    "#sr-mascot-overlay.sr-show{opacity:1;}",
    ".sr-mascot-stage{display:flex;flex-direction:column;align-items:center;gap:18px;transform:scale(.6);opacity:0;",
    "transition:transform .45s cubic-bezier(.22,1.4,.36,1),opacity .3s ease;}",
    "#sr-mascot-overlay.sr-show .sr-mascot-stage{transform:scale(1);opacity:1;}",

    /* Speech bubble */
    ".sr-mascot-bubble{position:relative;background:var(--c-sidebar,#fff);color:var(--c-title,#2D073F);",
    "border:1px solid rgba(128,128,128,.18);border-radius:16px;padding:14px 22px;font-weight:800;font-size:17px;",
    "display:flex;align-items:center;gap:10px;box-shadow:0 14px 40px rgba(0,0,0,.30);}",
    ".sr-mascot-bubble::after{content:'';position:absolute;left:50%;bottom:-7px;width:14px;height:14px;",
    "transform:translateX(-50%) rotate(45deg);background:inherit;border-right:1px solid rgba(128,128,128,.18);",
    "border-bottom:1px solid rgba(128,128,128,.18);}",
    ".sr-mascot-bubble .sr-check{width:26px;height:26px;border-radius:9999px;background:#22c55e;color:#fff;",
    "display:flex;align-items:center;justify-content:center;flex-shrink:0;}",
    ".sr-mascot-bubble .sr-check svg{width:15px;height:15px;}",

    /* Mascot bob + parts */
    ".sr-mascot{animation:sr-bob 2.4s ease-in-out infinite;}",
    ".sr-mascot .sr-spark{transform-origin:60px 60px;animation:sr-spin-settle .9s cubic-bezier(.22,1.2,.36,1) both;}",
    ".sr-mascot .sr-eye{transform-origin:center;animation:sr-blink 2.8s ease-in-out .9s infinite;}",
    ".sr-mascot .sr-arm{transform-origin:96px 78px;animation:sr-wave 1.5s ease-in-out .45s 2 both;}",
    ".sr-sparkle{position:absolute;font-size:18px;opacity:0;animation:sr-sparkle 1.8s ease-out .5s 2;}",

    "@keyframes sr-bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}",
    "@keyframes sr-spin-settle{from{transform:rotate(-120deg) scale(.4)}to{transform:rotate(0) scale(1)}}",
    "@keyframes sr-blink{0%,92%,100%{transform:scaleY(1)}95%{transform:scaleY(.08)}}",
    "@keyframes sr-wave{0%,100%{transform:rotate(0)}30%{transform:rotate(28deg)}60%{transform:rotate(-12deg)}80%{transform:rotate(20deg)}}",
    "@keyframes sr-sparkle{0%{opacity:0;transform:translateY(6px) scale(.5)}30%{opacity:1}100%{opacity:0;transform:translateY(-26px) scale(1.15)}}",

    "@media (prefers-reduced-motion: reduce){",
    ".sr-mascot,.sr-mascot .sr-spark,.sr-mascot .sr-eye,.sr-mascot .sr-arm,.sr-sparkle{animation:none !important;}",
    ".sr-mascot-stage{transition:opacity .2s ease;}}",
  ].join("");

  /* Orange spark character: 8-point spark body, face, waving arm. */
  var MASCOT_SVG =
    '<div style="position:relative">' +
    '<span class="sr-sparkle" style="left:-14px;top:8px;">✦</span>' +
    '<span class="sr-sparkle" style="right:-10px;top:22px;animation-delay:.9s;">✦</span>' +
    '<svg class="sr-mascot" width="132" height="132" viewBox="0 0 120 120" aria-hidden="true">' +
    '<g class="sr-spark">' +
    '<g fill="#FF5A1F">' +
    '<rect x="52" y="6" width="16" height="108" rx="8"/>' +
    '<rect x="6" y="52" width="108" height="16" rx="8"/>' +
    '<rect x="52" y="6" width="16" height="108" rx="8" transform="rotate(45 60 60)"/>' +
    '<rect x="52" y="6" width="16" height="108" rx="8" transform="rotate(-45 60 60)"/>' +
    "</g>" +
    '<circle cx="60" cy="60" r="27" fill="#FF7A3F"/>' +
    "</g>" +
    '<g class="sr-face">' +
    '<g class="sr-eye"><circle cx="51" cy="55" r="4.2" fill="#2B063D"/></g>' +
    '<g class="sr-eye"><circle cx="69" cy="55" r="4.2" fill="#2B063D"/></g>' +
    '<path d="M50 67 Q60 76 70 67" stroke="#2B063D" stroke-width="3.4" stroke-linecap="round" fill="none"/>' +
    '<circle cx="44" cy="64" r="3.4" fill="#FFD0B8" opacity=".85"/>' +
    '<circle cx="76" cy="64" r="3.4" fill="#FFD0B8" opacity=".85"/>' +
    "</g>" +
    '<g class="sr-arm">' +
    '<rect x="92" y="72" width="20" height="9" rx="4.5" fill="#FF5A1F" transform="rotate(-30 96 78)"/>' +
    '<circle cx="110" cy="66" r="6.5" fill="#FF7A3F"/>' +
    "</g>" +
    "</svg></div>";

  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;
    var style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = CSS;
    document.head.appendChild(style);
  }

  function showSuccess(message, onDone, options) {
    ensureStyles();
    var duration = (options && options.duration) || 2600;
    var finished = false;

    var overlay = document.createElement("div");
    overlay.id = "sr-mascot-overlay";
    overlay.setAttribute("role", "status");
    overlay.innerHTML =
      '<div class="sr-mascot-stage">' +
      '<div class="sr-mascot-bubble">' +
      '<span class="sr-check"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.2">' +
      '<path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></span>' +
      "<span></span>" +
      "</div>" +
      MASCOT_SVG +
      "</div>";
    overlay.querySelector(".sr-mascot-bubble span:last-child").textContent =
      message || "Enviado correctamente";
    document.body.appendChild(overlay);

    function finish() {
      if (finished) return;
      finished = true;
      overlay.classList.remove("sr-show");
      setTimeout(function () {
        overlay.remove();
        if (typeof onDone === "function") onDone();
      }, 260);
    }

    // Click anywhere to skip the wait
    overlay.addEventListener("click", finish);

    requestAnimationFrame(function () {
      overlay.classList.add("sr-show");
    });
    setTimeout(finish, duration);
  }

  global.SR_Mascot = { showSuccess: showSuccess };
})(window);
