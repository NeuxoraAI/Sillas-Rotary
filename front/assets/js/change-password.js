/* change-password.js — Shared "change my password" form for Ecosistema VIDA UG.

   Self-contained IIFE (plain global — no ES modules, consistent with
   session-guard.js / apiClient.js). Renders a small form into a container and
   POSTs { current_password, new_password } to the authenticated endpoint.

   Usage (after loading apiClient.js, and session-guard.js on protected pages):

     ChangePassword.init({
       containerId: 'change-password-section', // <div> to inject into
       apiPath:     '/me/password',             // default '/me/password'
       authFetchFn: SessionGuard.authFetch,     // optional; defaults to ApiClient
     });

   Shared across the 4 role profiles so the change-password UI never drifts. */
(function () {
  "use strict";

  function _esc(str) {
    return String(str == null ? "" : str)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  // Post the payload. When an authFetchFn is provided (e.g. SessionGuard.authFetch),
  // build the absolute URL via ApiClient; otherwise use ApiClient.post which
  // already attaches the Bearer token.
  function _post(apiPath, payload, authFetchFn) {
    if (typeof authFetchFn === "function") {
      return authFetchFn(ApiClient.url(apiPath), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    }
    return ApiClient.post(apiPath, { json: payload });
  }

  function init(opts) {
    opts = opts || {};
    var container = document.getElementById(opts.containerId);
    if (!container) return; // page did not provide the mount point
    var apiPath = opts.apiPath || "/me/password";
    var authFetchFn = opts.authFetchFn;

    container.innerHTML = [
      '<form class="space-y-4" novalidate>',
      '  <div class="space-y-1.5">',
      '    <label class="block text-xs font-semibold text-slate-600" for="cp-current">Contraseña actual</label>',
      '    <input id="cp-current" type="password" autocomplete="current-password" placeholder="Tu contraseña actual" class="w-full px-4 py-3 text-sm"/>',
      '  </div>',
      '  <div class="space-y-1.5">',
      '    <label class="block text-xs font-semibold text-slate-600" for="cp-new">Nueva contraseña</label>',
      '    <input id="cp-new" type="password" autocomplete="new-password" placeholder="Mínimo 8 caracteres" class="w-full px-4 py-3 text-sm"/>',
      '  </div>',
      '  <div class="space-y-1.5">',
      '    <label class="block text-xs font-semibold text-slate-600" for="cp-confirm">Confirmar nueva contraseña</label>',
      '    <input id="cp-confirm" type="password" autocomplete="new-password" placeholder="Repetí la nueva contraseña" class="w-full px-4 py-3 text-sm"/>',
      '  </div>',
      '  <p id="cp-error" class="hidden text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-4 py-2.5" role="alert"></p>',
      '  <p id="cp-success" class="hidden text-green-700 text-sm bg-green-50 border border-green-200 rounded-lg px-4 py-2.5" role="status"></p>',
      '  <button id="cp-submit" type="submit" class="btn-primary w-full sm:w-auto px-6 py-3 text-sm rounded-xl flex items-center justify-center gap-2 disabled:opacity-60">',
      '    <span class="material-symbols-outlined text-lg">lock_reset</span>',
      '    <span id="cp-submit-text">Cambiar contraseña</span>',
      '  </button>',
      '</form>',
    ].join("");

    var form = container.querySelector("form");
    var errorEl = container.querySelector("#cp-error");
    var successEl = container.querySelector("#cp-success");

    function showError(msg) {
      successEl.classList.add("hidden");
      errorEl.textContent = msg;
      errorEl.classList.remove("hidden");
    }
    function showSuccess(msg) {
      errorEl.classList.add("hidden");
      successEl.textContent = msg;
      successEl.classList.remove("hidden");
    }

    form.addEventListener("submit", async function (e) {
      e.preventDefault();
      errorEl.classList.add("hidden");
      successEl.classList.add("hidden");

      var current = container.querySelector("#cp-current").value;
      var next = container.querySelector("#cp-new").value;
      var confirm = container.querySelector("#cp-confirm").value;

      if (!current) { showError("Ingresá tu contraseña actual."); return; }
      if (next.length < 8) { showError("La nueva contraseña debe tener al menos 8 caracteres."); return; }
      if (next !== confirm) { showError("Las contraseñas no coinciden."); return; }

      var btn = container.querySelector("#cp-submit");
      var btnText = container.querySelector("#cp-submit-text");
      btn.disabled = true;
      btnText.textContent = "Guardando…";

      try {
        var res = await _post(apiPath, { current_password: current, new_password: next }, authFetchFn);
        if (res.status === 204 || res.ok) {
          form.reset();
          showSuccess("Contraseña actualizada.");
        } else {
          var data = await res.json().catch(function () { return {}; });
          showError(_esc(data.detail) || "No se pudo cambiar la contraseña.");
        }
      } catch (_) {
        showError("No se pudo conectar con el servidor.");
      } finally {
        btn.disabled = false;
        btnText.textContent = "Cambiar contraseña";
      }
    });
  }

  window.ChangePassword = { init: init };
})();
