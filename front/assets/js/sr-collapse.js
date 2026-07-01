/* ============================================================================
   sr-collapse.js — collapsible sections for optional form content.
   Pure CSS animation (grid-template-rows 0fr→1fr); this only toggles state.
   Delegated, so no per-element init is needed — just use the markup:

     <div class="sr-collapse">                (add " open" to start expanded)
       <button type="button" class="sr-collapse__head" data-collapse-toggle
               aria-expanded="false">
         <span>Justificación</span>
         <span class="material-symbols-outlined sr-collapse__chevron"
               aria-hidden="true">expand_more</span>
       </button>
       <div class="sr-collapse__body"><div class="sr-collapse__inner">
         ... optional fields ...
       </div></div>
     </div>
   ========================================================================== */
(function () {
  "use strict";
  document.addEventListener("click", function (e) {
    var head = e.target.closest("[data-collapse-toggle]");
    if (!head) return;
    var collapse = head.closest(".sr-collapse");
    if (!collapse) return;
    var open = collapse.classList.toggle("open");
    head.setAttribute("aria-expanded", open ? "true" : "false");
  });
})();
