/* apiClient.js — Centralized API layer for SIG-Tec.

   Single point for: (1) the API base URL, (2) the Authorization header, and
   (3) request/error plumbing. Every view calls the backend through this module
   instead of hardcoding "/api/..." paths, so splitting the frontend onto a
   different origin (or building the future mobile app) is a one-line config
   change.

   Include via <script src="...assets/js/apiClient.js"></script> AFTER
   session-guard.js and BEFORE page logic. Exposes window.ApiClient (plain
   global — no ES modules, consistent with the other assets/js helpers). */
(function () {
  "use strict";

  // ── Base URL resolution (the single configurable point) ───────────────────
  // Cascade: window.API_BASE_URL → localStorage 'api_base_url' → "" (same-origin).
  //  • window.API_BASE_URL — set by a deploy-time inline script / config.js.
  //  • localStorage 'api_base_url' — handy dev/QA override without a redeploy.
  //  • ""  — default: relative requests against the serving origin (today's
  //          behavior, since FastAPI serves front/ same-origin).
  // Any trailing slash is trimmed so url() can concatenate safely.
  function baseUrl() {
    var b = "";
    try {
      if (typeof window.API_BASE_URL === "string" && window.API_BASE_URL) {
        b = window.API_BASE_URL;
      } else {
        var ls = localStorage.getItem("api_base_url");
        if (ls) { b = ls; }
      }
    } catch (_) { /* localStorage may be unavailable (private mode) */ }
    return (b || "").replace(/\/+$/, "");
  }

  /** Build an absolute API URL from a path like "/estudios/123" or
   *  "/regiones?pais_id=1". The "/api" prefix lives here — callers never
   *  hardcode it. Safe to use for <img src>, downloads, or manual fetch(). */
  function url(path) {
    path = path || "";
    if (path.charAt(0) !== "/") { path = "/" + path; }
    return baseUrl() + "/api" + path;
  }

  // Alias for readability at <img>/blob/download call sites.
  function documentUrl(path) { return url(path); }

  // ── Auth headers (reuse SessionGuard when present) ────────────────────────
  function authHeaders(extra) {
    if (window.SessionGuard && typeof SessionGuard.authHeaders === "function") {
      // Respects SessionGuard's role check + redirect-on-invalid-session.
      return SessionGuard.authHeaders(extra);
    }
    // Fallback for pages without SessionGuard (e.g. login.html shouldn't reach
    // here because it uses { auth:false }, but keep a safe default).
    var s = null;
    try { s = JSON.parse(localStorage.getItem("session") || "null"); } catch (_) {}
    var h = Object.assign({}, extra || {});
    if (s && s.token) { h["Authorization"] = "Bearer " + s.token; }
    return h;
  }

  // ── Core request ──────────────────────────────────────────────────────────
  /**
   * Drop-in-ish replacement for fetch(), addressed by an API path (no "/api").
   * @param {string} path  e.g. "/estudios" or `/estudios/${id}`.
   * @param {object} [opts] standard fetch options plus:
   *   - auth {boolean}  attach the Bearer token (default true; false for login).
   *   - json {any}      body serialized as JSON (sets Content-Type for you).
   * @returns {Promise<Response>}  the raw Response, so existing call sites can
   *                               keep using res.ok / await res.json().
   */
  function request(path, opts) {
    opts = Object.assign({}, opts || {});
    var headers = Object.assign({}, opts.headers || {});

    if (opts.json !== undefined) {
      headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(opts.json);
      delete opts.json;
    }

    var useAuth = opts.auth !== false;
    delete opts.auth;
    if (useAuth) { headers = authHeaders(headers); }

    opts.headers = headers;

    // Match the prior per-view behavior of disabling the browser cache on GET.
    if ((!opts.method || opts.method === "GET") && opts.cache === undefined) {
      opts.cache = "no-store";
    }

    return fetch(url(path), opts);
  }

  // Verb sugar — all resolve with the raw Response.
  function get(path, opts)   { return request(path, Object.assign({ method: "GET" },    opts || {})); }
  function post(path, opts)  { return request(path, Object.assign({ method: "POST" },   opts || {})); }
  function patch(path, opts) { return request(path, Object.assign({ method: "PATCH" },  opts || {})); }
  function del(path, opts)   { return request(path, Object.assign({ method: "DELETE" }, opts || {})); }

  window.ApiClient = {
    baseUrl:     baseUrl,
    url:         url,
    documentUrl: documentUrl,
    authHeaders: authHeaders,
    fetch:       request,
    request:     request,
    get:         get,
    post:        post,
    patch:       patch,
    del:         del,
  };
})();
