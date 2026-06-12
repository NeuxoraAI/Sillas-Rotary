/* delight.js — count-up animation for profile statistics.
   Mark any element with data-countup; when page JS sets its textContent
   to a number, the value animates from 0 to the target with an ease-out
   curve and a small pop at the end. No page JS changes required. */
(function () {
  "use strict";

  var DURATION = 700;
  var reduceMotion =
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function animateCount(el, target) {
    var start = performance.now();

    function frame(now) {
      var t = Math.min((now - start) / DURATION, 1);
      var eased = 1 - Math.pow(1 - t, 3); // ease-out cubic
      var value = Math.round(target * eased);
      el.dataset.counting = "1";
      el.textContent = String(value);
      if (t < 1) {
        requestAnimationFrame(frame);
      } else {
        delete el.dataset.counting;
        el.classList.add("sr-stat-pop");
        el.addEventListener(
          "animationend",
          function () {
            el.classList.remove("sr-stat-pop");
          },
          { once: true },
        );
      }
    }
    requestAnimationFrame(frame);
  }

  function watch(el) {
    var observer = new MutationObserver(function () {
      if (el.dataset.counting) return; // our own writes
      var target = parseInt(el.textContent, 10);
      if (!Number.isFinite(target) || target <= 0) return;
      if (el.dataset.lastCounted === String(target)) return;
      el.dataset.lastCounted = String(target);
      if (reduceMotion) return; // leave the final value as-is
      animateCount(el, target);
    });
    observer.observe(el, { childList: true, characterData: true, subtree: true });
  }

  function init() {
    document.querySelectorAll("[data-countup]").forEach(watch);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
