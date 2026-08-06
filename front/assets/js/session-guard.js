/* session-guard.js — Cross-tab session consistency for SIG-Tec.
   Include via <script src="...assets/js/session-guard.js"></script> BEFORE
   page logic. Exposes window.SessionGuard (plain global — no ES modules). */
(function () {
  "use strict";

  // Role-to-home mapping (relative to /front/).
  // Must match the post-login routing in login.html.
  var ROLE_HOME = {
    admin:        "admin-beneficiarios.html",
    capturista:   "Capturista-view/perfil-capturista.html",
    tecnico:      "Tecnico-view/vista_tecnicos.html",
    organizacion: "perfil-organizacion.html",
  };

  // Snapshot captured by requireRole() — checked on storage/visibility events.
  var _allowedRoles = null;
  var _loadUserId   = null;
  var _loginPath    = "login.html"; // default, overridden by requireRole()

  // ── Core helpers ─────────────────────────────────────────────────────────

  function getSession() {
    try { return JSON.parse(localStorage.getItem("session") || "null"); }
    catch (_) { return null; }
  }

  /** Resolve a role to its home page.
   *  @param {string}  rol
   *  @param {string}  [loginPath] - path to login.html relative to this page
   *  @returns {string}
   */
  function _homeForRole(rol, loginPath) {
    // Build the home path: navigate up from loginPath to /front/ root, then append.
    // loginPath is always the path from the current page to login.html.
    // e.g. "../login.html" means we are one level deep.
    var depth = (loginPath || _loginPath).split("/").length - 1; // segments before "login.html"
    var prefix = "";
    for (var i = 0; i < depth; i++) { prefix += "../"; }
    return prefix + (ROLE_HOME[rol] || "login.html");
  }

  /** Redirect to login (or role home). Called when the session is gone or the
   *  role changed under the current page. */
  function _redirect(loginPath) {
    var s = getSession();
    if (!s || !s.token) {
      window.location.replace(loginPath || _loginPath);
    } else {
      // Session exists but role is wrong for this page — send to correct home.
      window.location.replace(_homeForRole(s.rol, loginPath || _loginPath));
    }
  }

  // ── requireRole ──────────────────────────────────────────────────────────

  /**
   * Call once at page load.
   * @param {string[]} allowedRoles - e.g. ['admin'] or ['capturista','tecnico']
   * @param {string}   loginPath    - relative path from this page to login.html
   *                                  e.g. '../login.html' or 'login.html'
   */
  function requireRole(allowedRoles, loginPath) {
    _allowedRoles = allowedRoles;
    _loginPath    = loginPath || "login.html";

    var s = getSession();
    if (!s || !s.token) {
      window.location.replace(_loginPath);
      return;
    }
    if (allowedRoles.indexOf(s.rol) === -1) {
      window.location.replace(_homeForRole(s.rol));
      return;
    }

    // Snapshot the user seen at load — changes trigger a redirect.
    _loadUserId = s.usuario_id;

    _attachListeners();
  }

  // ── Cross-tab / focus listeners ───────────────────────────────────────────

  function _check() {
    if (!_allowedRoles) return; // guard not yet initialized
    var s = getSession();

    // Session removed (logout in another tab).
    if (!s || !s.token) {
      window.location.replace(_loginPath);
      return;
    }

    // A different user logged in, or the role changed.
    if (s.usuario_id !== _loadUserId || _allowedRoles.indexOf(s.rol) === -1) {
      _redirect();
    }
  }

  function _attachListeners() {
    // localStorage writes from another tab fire "storage" in this tab.
    window.addEventListener("storage", function (e) {
      if (e.key === "session") { _check(); }
    });

    // Tab becomes visible again (user switches back) — re-validate.
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "visible") { _check(); }
    });

    // Window regains focus (e.g. alt-tab back).
    window.addEventListener("focus", _check);
  }

  // ── authHeaders / authFetch ───────────────────────────────────────────────

  /**
   * Returns headers object with a fresh Bearer token.
   * Redirects and throws if the session is gone or role is no longer allowed.
   */
  function authHeaders(extra) {
    var s = getSession();
    if (!s || !s.token || (_allowedRoles && _allowedRoles.indexOf(s.rol) === -1)) {
      _redirect();
      throw new Error("Session invalid — redirecting");
    }
    return Object.assign({ "Authorization": "Bearer " + s.token }, extra || {});
  }

  /**
   * Drop-in replacement for fetch() that always uses a fresh token.
   * @param {string}  url
   * @param {object}  [opts]
   * @returns {Promise<Response>}
   */
  function authFetch(url, opts) {
    opts = opts || {};
    opts.headers = authHeaders(opts.headers || {});
    return fetch(url, opts);
  }

  // ── Public API ────────────────────────────────────────────────────────────

  window.SessionGuard = {
    getSession:   getSession,
    requireRole:  requireRole,
    authHeaders:  authHeaders,
    authFetch:    authFetch,
  };
})();
