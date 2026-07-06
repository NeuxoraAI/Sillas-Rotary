// Shared frontend helpers. Keep these context-safe: _esc is used in both text
// nodes and HTML attributes built with innerHTML.
(function () {
  function _esc(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function _getSession() {
    try {
      return JSON.parse(localStorage.getItem("session") || "null");
    } catch (_) {
      return null;
    }
  }

  function _formatRol(rol) {
    const map = {
      admin: "Administrador",
      capturista: "Capturista",
      tecnico: "Técnico",
      organizacion: "Organización",
    };
    return map[rol] || rol || "—";
  }

  function _formatDate(iso) {
    if (!iso) return "—";
    try {
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return iso;
      return d.toLocaleDateString("es-MX", {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    } catch (_) {
      return iso;
    }
  }

  function _clearDraftStorage() {
    localStorage.removeItem("draft_socioeconomico");
    localStorage.removeItem("draft_tecnica");
    localStorage.removeItem("draft_gestion");
    localStorage.removeItem("estudio_id");
    localStorage.removeItem("beneficiario_id");
    localStorage.removeItem("solicitud_id");
    // Issue #123: validation highlights carried across forms.
    sessionStorage.removeItem("sr_pending_field_errors");
  }

  function _clearAllStorage() {
    localStorage.removeItem("session");
    localStorage.removeItem("region_ctx");
    localStorage.removeItem("guest_ctx");
    _clearDraftStorage();
  }

  window._esc = _esc;
  window._escapeHtml = _esc;
  window._getSession = _getSession;
  window._formatRol = _formatRol;
  window._formatDate = _formatDate;
  window._clearDraftStorage = _clearDraftStorage;
  window._clearAllStorage = _clearAllStorage;
})();
