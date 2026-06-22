(function () {
  const MODAL_ID = "app-confirmation-modal";

  function ensureModal() {
    let overlay = document.getElementById(MODAL_ID);
    if (overlay) return overlay;

    overlay = document.createElement("div");
    overlay.id = MODAL_ID;
    overlay.className = "hidden fixed inset-0 z-[90] bg-black/40 flex items-center justify-center p-4";
    overlay.innerHTML = `
      <div class="animate-fade-in bg-white w-full max-w-md rounded-2xl shadow-2xl p-6 relative" role="dialog" aria-modal="true" aria-labelledby="app-confirmation-title" aria-describedby="app-confirmation-message">
        <button type="button" data-confirmation-close class="absolute right-3 top-3 w-8 h-8 rounded-xl bg-slate-100 hover:bg-slate-200 flex items-center justify-center text-slate-500 hover:text-slate-700 transition-all shrink-0" aria-label="Cerrar aviso">
          <span class="material-symbols-outlined text-lg">close</span>
        </button>
        <div class="text-center mb-4">
          <div data-confirmation-icon-wrap class="w-14 h-14 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-3">
            <span data-confirmation-icon class="material-symbols-outlined text-amber-600 text-3xl">warning</span>
          </div>
          <h3 id="app-confirmation-title" data-confirmation-title class="text-lg font-bold text-slate-900">Confirmar acción</h3>
          <p id="app-confirmation-subtitle" data-confirmation-subtitle class="text-sm text-slate-500 mt-1"></p>
        </div>
        <p id="app-confirmation-message" data-confirmation-message class="text-sm text-slate-600 mb-5"></p>
        <div class="flex items-center justify-end gap-3">
          <button type="button" data-confirmation-cancel class="px-4 py-2 text-sm font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-xl transition-colors">Cancelar</button>
          <button type="button" data-confirmation-confirm class="btn-primary px-4 py-2 text-sm rounded-xl">Confirmar</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    return overlay;
  }

  function setTone(overlay, tone) {
    const iconWrap = overlay.querySelector("[data-confirmation-icon-wrap]");
    const icon = overlay.querySelector("[data-confirmation-icon]");
    const confirm = overlay.querySelector("[data-confirmation-confirm]");
    iconWrap.className = "w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-3";
    icon.className = "material-symbols-outlined text-3xl";
    icon.style.color = "";
    confirm.className = "px-4 py-2 text-sm rounded-xl transition-colors font-bold";

    if (tone === "danger") {
      iconWrap.classList.add("bg-red-100");
      icon.classList.add("text-red-600");
      confirm.classList.add("text-white", "bg-red-600", "hover:bg-red-700");
      return;
    }

    if (tone === "orange") {
      iconWrap.classList.add("bg-orange-50");
      icon.style.color = "var(--c-orange)";
      confirm.classList.add("btn-primary");
      return;
    }

    iconWrap.classList.add("bg-amber-100");
    icon.classList.add("text-amber-600");
    confirm.classList.add("btn-primary");
  }

  function confirmAction(options) {
    const opts = options || {};
    const overlay = ensureModal();
    const title = overlay.querySelector("[data-confirmation-title]");
    const subtitle = overlay.querySelector("[data-confirmation-subtitle]");
    const message = overlay.querySelector("[data-confirmation-message]");
    const icon = overlay.querySelector("[data-confirmation-icon]");
    const closeBtn = overlay.querySelector("[data-confirmation-close]");
    const cancelBtn = overlay.querySelector("[data-confirmation-cancel]");
    const confirmBtn = overlay.querySelector("[data-confirmation-confirm]");

    title.textContent = opts.title || "Confirmar acción";
    subtitle.textContent = opts.subtitle || "";
    subtitle.classList.toggle("hidden", !opts.subtitle);
    message.textContent = opts.message || "¿Deseas continuar?";
    icon.textContent = opts.icon || "warning";
    cancelBtn.textContent = opts.cancelText || "Cancelar";
    confirmBtn.textContent = opts.confirmText || "Confirmar";
    setTone(overlay, opts.tone || "warning");

    return new Promise(function (resolve) {
      let lastFocused = document.activeElement;

      function cleanup(result) {
        overlay.classList.add("hidden");
        closeBtn.removeEventListener("click", onCancel);
        cancelBtn.removeEventListener("click", onCancel);
        confirmBtn.removeEventListener("click", onConfirm);
        overlay.removeEventListener("click", onBackdrop);
        document.removeEventListener("keydown", onKeydown);
        if (lastFocused && typeof lastFocused.focus === "function") lastFocused.focus();
        resolve(result);
      }

      function onCancel() { cleanup(false); }
      function onConfirm() { cleanup(true); }
      function onBackdrop(event) { if (event.target === overlay) cleanup(false); }
      function onKeydown(event) {
        if (event.key === "Escape") cleanup(false);
        if (event.key !== "Tab") return;

        const focusableElements = [closeBtn, cancelBtn, confirmBtn].filter(function (element) {
          return element && !element.disabled;
        });
        if (!focusableElements.length) return;

        const firstFocusable = focusableElements[0];
        const lastFocusable = focusableElements[focusableElements.length - 1];

        if (event.shiftKey && document.activeElement === firstFocusable) {
          event.preventDefault();
          lastFocusable.focus();
          return;
        }

        if (!event.shiftKey && document.activeElement === lastFocusable) {
          event.preventDefault();
          firstFocusable.focus();
        }
      }

      closeBtn.addEventListener("click", onCancel);
      cancelBtn.addEventListener("click", onCancel);
      confirmBtn.addEventListener("click", onConfirm);
      overlay.addEventListener("click", onBackdrop);
      document.addEventListener("keydown", onKeydown);
      overlay.classList.remove("hidden");
      confirmBtn.focus();
    });
  }

  function confirmLogout() {
    return confirmAction({
      title: "Cerrar sesión",
      subtitle: "Tu sesión actual terminará.",
      message: "Se limpiarán los datos temporales de esta sesión y volverás a la pantalla de inicio.",
      confirmText: "Cerrar sesión",
      cancelText: "Cancelar",
      icon: "logout",
      tone: "orange",
    });
  }

  function confirmUnsavedNavigation() {
    return confirmAction({
      title: "Cambios sin guardar",
      subtitle: "Tienes datos capturados en este flujo.",
      message: "Si sales ahora, los cambios no guardados se perderán.",
      confirmText: "Salir sin guardar",
      cancelText: "Regresar",
      icon: "warning",
      tone: "warning",
    });
  }

  window.AppConfirmation = {
    confirm: confirmAction,
    confirmLogout,
    confirmUnsavedNavigation,
  };
})();
