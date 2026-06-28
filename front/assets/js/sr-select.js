/* ============================================================================
   sr-select.js — searchable select (combobox) for long option lists.
   Progressive enhancement over a native <select>: the native element stays in
   the DOM (keeps its value, form submission and existing change listeners);
   a searchable popup drives it. Auto-enhances any <select data-searchable>.

   Usage:
     <select id="estado" data-searchable> ... </select>
     SRSelect.enhance(el)        // enhance one
     SRSelect.enhanceAll(root)   // enhance all [data-searchable] under root
   Dynamic options (e.g. municipios loaded on change) are picked up live.
   ========================================================================== */
(function () {
  "use strict";

  function enhance(select) {
    if (!select || select.dataset.srEnhanced) return;
    select.dataset.srEnhanced = "1";

    var wrap = document.createElement("div");
    wrap.className = "sr-select";
    select.parentNode.insertBefore(wrap, select);
    wrap.appendChild(select);
    select.classList.add("sr-select__native");
    select.setAttribute("tabindex", "-1");
    select.setAttribute("aria-hidden", "true");

    var trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "sr-select__trigger";
    trigger.setAttribute("aria-haspopup", "listbox");
    trigger.setAttribute("aria-expanded", "false");
    if (select.id) trigger.setAttribute("aria-label", _labelFor(select));
    wrap.appendChild(trigger);

    var triggerLabel = document.createElement("span");
    triggerLabel.className = "sr-select__label";
    trigger.appendChild(triggerLabel);

    var caret = document.createElement("span");
    caret.className = "material-symbols-outlined sr-select__caret";
    caret.setAttribute("aria-hidden", "true");
    caret.textContent = "expand_more";
    trigger.appendChild(caret);

    var pop = document.createElement("div");
    pop.className = "sr-select__pop hidden";
    pop.setAttribute("role", "listbox");

    var search = document.createElement("input");
    search.type = "text";
    search.className = "sr-select__search";
    search.placeholder = "Buscar…";
    search.setAttribute("aria-label", "Buscar opción");
    search.autocomplete = "off";

    var list = document.createElement("div");
    list.className = "sr-select__list";

    pop.appendChild(search);
    pop.appendChild(list);
    wrap.appendChild(pop);

    var items = [];
    var activeIdx = -1;

    function _labelFor(sel) {
      var lbl = sel.id && document.querySelector('label[for="' + sel.id + '"]');
      return lbl ? lbl.textContent.trim() : "Seleccionar";
    }

    function syncLabel() {
      var opt = select.options[select.selectedIndex];
      var txt = opt ? opt.textContent.trim() : "";
      var hasValue = !!select.value;
      triggerLabel.textContent = txt || "Seleccionar…";
      triggerLabel.classList.toggle("sr-select__placeholder", !hasValue);
    }

    function buildList(filter) {
      list.innerHTML = "";
      items = [];
      var f = (filter || "").trim().toLowerCase();
      Array.prototype.forEach.call(select.options, function (opt) {
        var label = opt.textContent.trim();
        if (f && label.toLowerCase().indexOf(f) === -1) return;
        var el = document.createElement("div");
        el.className = "sr-select__opt";
        el.setAttribute("role", "option");
        el.textContent = label;
        if (opt.value === select.value && opt.value !== "") {
          el.setAttribute("aria-selected", "true");
        }
        el.addEventListener("mousedown", function (e) {
          e.preventDefault();
          choose(opt.value);
        });
        list.appendChild(el);
        items.push({ value: opt.value, el: el });
      });
      if (items.length === 0) {
        var empty = document.createElement("div");
        empty.className = "sr-select__empty";
        empty.textContent = "Sin resultados";
        list.appendChild(empty);
      }
      activeIdx = -1;
    }

    function isOpen() { return !pop.classList.contains("hidden"); }

    function open() {
      if (select.disabled) return;
      buildList("");
      pop.classList.remove("hidden");
      trigger.setAttribute("aria-expanded", "true");
      search.value = "";
      setTimeout(function () { search.focus(); }, 0);
    }

    function close() {
      pop.classList.add("hidden");
      trigger.setAttribute("aria-expanded", "false");
    }

    function choose(value) {
      select.value = value;
      select.dispatchEvent(new Event("change", { bubbles: true }));
      syncLabel();
      close();
      trigger.focus();
    }

    function setActive(idx) {
      if (!items.length) return;
      activeIdx = (idx + items.length) % items.length;
      items.forEach(function (it, i) { it.el.classList.toggle("active", i === activeIdx); });
      items[activeIdx].el.scrollIntoView({ block: "nearest" });
    }

    trigger.addEventListener("click", function () { isOpen() ? close() : open(); });
    trigger.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); }
    });
    search.addEventListener("input", function () { buildList(search.value); });
    search.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown") { e.preventDefault(); setActive(activeIdx + 1); }
      else if (e.key === "ArrowUp") { e.preventDefault(); setActive(activeIdx - 1); }
      else if (e.key === "Enter") { e.preventDefault(); if (activeIdx >= 0) choose(items[activeIdx].value); }
      else if (e.key === "Escape") { e.preventDefault(); close(); trigger.focus(); }
    });
    document.addEventListener("click", function (e) { if (!wrap.contains(e.target)) close(); });

    // Keep the trigger label in sync when value changes or options repopulate
    select.addEventListener("change", syncLabel);
    new MutationObserver(syncLabel).observe(select, { childList: true });

    syncLabel();
  }

  function enhanceAll(root) {
    (root || document).querySelectorAll("select[data-searchable]").forEach(enhance);
  }

  window.SRSelect = { enhance: enhance, enhanceAll: enhanceAll };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { enhanceAll(); });
  } else {
    enhanceAll();
  }
})();
