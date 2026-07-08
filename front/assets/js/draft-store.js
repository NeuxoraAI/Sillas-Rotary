/* DraftStore — única fuente de verdad del borrador durante la captura.
   Cargar DESPUÉS de apiClient.js y ANTES de la lógica de página. Expone
   window.DraftStore (objeto plano, sin ES modules — mismo patrón que ApiClient).

   Arquitectura local-first (Issue #161):
   - Los 3 drafts de localStorage (socioeconómico / técnica / gestión) son la
     fuente de verdad de los campos mientras se captura; cada vista restaura
     SOLO desde su draft local, de forma síncrona.
   - El backend interviene en dos puntos: hidratación única al reanudar un
     borrador (GET /borrador/{estudio_id} siembra los 3 drafts + IDs) y el
     guardado maestro desde gestion.html (POST /guardar-borrador con el
     payload construido por buildMasterPayload). */
(function () {
  "use strict";

  var KEYS = {
    SOCIO: "draft_socioeconomico",
    TECNICA: "draft_tecnica",
    GESTION: "draft_gestion",
    ESTUDIO_ID: "estudio_id",
    SOLICITUD_ID: "solicitud_id",
    BENEFICIARIO_ID: "beneficiario_id",
  };

  function getDraft(step) {
    var key = KEYS[step] || step;
    try {
      var parsed = JSON.parse(localStorage.getItem(key) || "null");
      return parsed && typeof parsed === "object" ? parsed : null;
    } catch (_e) {
      return null;
    }
  }

  function setDraft(step, obj) {
    var key = KEYS[step] || step;
    localStorage.setItem(key, JSON.stringify(obj));
  }

  function _intOrNull(raw) {
    var n = parseInt(raw, 10);
    return isNaN(n) ? null : n;
  }

  function getIds() {
    return {
      estudio_id: _intOrNull(localStorage.getItem(KEYS.ESTUDIO_ID)),
      solicitud_id: _intOrNull(localStorage.getItem(KEYS.SOLICITUD_ID)),
      beneficiario_id: _intOrNull(localStorage.getItem(KEYS.BENEFICIARIO_ID)),
    };
  }

  // Persistir los IDs devueltos por POST /guardar-borrador.
  function setIds(resp) {
    if (!resp) return;
    if (resp.estudio_id) localStorage.setItem(KEYS.ESTUDIO_ID, String(resp.estudio_id));
    if (resp.solicitud_id) localStorage.setItem(KEYS.SOLICITUD_ID, String(resp.solicitud_id));
    if (resp.beneficiario_id) localStorage.setItem(KEYS.BENEFICIARIO_ID, String(resp.beneficiario_id));
  }

  // Limpieza total del borrador (al finalizar el registro o al cambiar de
  // borrador en modo edición).
  function clearAll() {
    [KEYS.SOCIO, KEYS.TECNICA, KEYS.GESTION, KEYS.ESTUDIO_ID, KEYS.SOLICITUD_ID, KEYS.BENEFICIARIO_ID]
      .forEach(function (k) { localStorage.removeItem(k); });
  }

  function _clearIds() {
    [KEYS.ESTUDIO_ID, KEYS.SOLICITUD_ID, KEYS.BENEFICIARIO_ID]
      .forEach(function (k) { localStorage.removeItem(k); });
  }

  // ── Overlay de carga (Issue #161) ─────────────────────────────────────────
  // Cubre la hidratación desde backend y, vía la API pública showOverlay/
  // hideOverlay, cualquier ventana de restauración que la vista necesite
  // bloquear (p. ej. socioeconomico espera el catálogo de municipios antes de
  // pintar). Ref-counted: la vista puede sostener el overlay mientras la
  // hidratación anidada hace su propio show/hide sin retirarlo antes de
  // tiempo. Estilos inline para no depender del estado de carga de Tailwind.
  var _overlayEl = null;
  var _overlayCount = 0;

  function _showOverlay() {
    _overlayCount++;
    if (_overlayEl) return;
    _overlayEl = document.createElement("div");
    _overlayEl.setAttribute("data-purpose", "draft-hydration-overlay");
    _overlayEl.style.cssText =
      "position:fixed;inset:0;z-index:50;display:flex;flex-direction:column;" +
      "align-items:center;justify-content:center;gap:12px;" +
      "background:rgba(255,255,255,.75);backdrop-filter:blur(2px);";
    var spinner = document.createElement("div");
    spinner.style.cssText =
      "width:44px;height:44px;border-radius:9999px;border:4px solid #e2e8f0;" +
      "border-top-color:#ea580c;animation:sr-hydrate-spin .8s linear infinite;";
    var label = document.createElement("p");
    label.textContent = "Cargando borrador…";
    label.style.cssText = "font-weight:700;color:#334155;font-family:inherit;";
    var style = document.createElement("style");
    style.textContent = "@keyframes sr-hydrate-spin{to{transform:rotate(360deg)}}";
    _overlayEl.appendChild(style);
    _overlayEl.appendChild(spinner);
    _overlayEl.appendChild(label);
    (document.body || document.documentElement).appendChild(_overlayEl);
  }

  function _hideOverlay() {
    if (_overlayCount > 0) _overlayCount--;
    if (_overlayCount === 0 && _overlayEl) {
      _overlayEl.remove();
      _overlayEl = null;
    }
  }

  // ── Normalización de tutores (BD → shape del draft local) ────────────────
  // Desde la migración 0030 la tabla `tutores` guarda el nombre estructurado
  // (nombres/apellido_paterno/apellido_materno) además del `nombre` compuesto.
  // La división heurística de abajo queda SOLO como fallback para filas
  // guardadas antes de 0030 (campos estructurados en NULL); se autocorrigen
  // al siguiente guardado. `antiguedad_meses` sí sigue viviendo unificada.
  function _normalizeTutor(t) {
    var nombres = t.nombres || null;
    var apPat = t.apellido_paterno || null;
    var apMat = t.apellido_materno || null;
    if (!nombres && t.nombre) {
      var parts = String(t.nombre).trim().split(/\s+/).filter(Boolean);
      if (parts.length === 1) {
        nombres = parts[0];
      } else if (parts.length === 2) {
        nombres = parts[0];
        apPat = parts[1];
      } else if (parts.length > 2) {
        apMat = parts.pop();
        apPat = parts.pop();
        nombres = parts.join(" ");
      }
    }
    var meses = t.antiguedad_meses;
    return {
      numero_tutor: t.numero_tutor,
      nombres: nombres,
      apellido_paterno: apPat,
      apellido_materno: apMat,
      email: t.email || null,
      edad: t.edad != null ? t.edad : null,
      nivel_estudios: t.nivel_estudios || null,
      estado_civil: t.estado_civil || null,
      num_hijos: t.num_hijos != null ? t.num_hijos : null,
      vivienda: t.vivienda || null,
      fuente_empleo: t.fuente_empleo || null,
      antiguedad_aplica: t.antiguedad_aplica != null ? Boolean(t.antiguedad_aplica) : null,
      antiguedad_anios: meses != null ? Math.floor(meses / 12) : (t.antiguedad_anios != null ? t.antiguedad_anios : null),
      antiguedad_meses_extra: meses != null ? meses % 12 : (t.antiguedad_meses_extra != null ? t.antiguedad_meses_extra : null),
      ingreso_mensual: t.ingreso_mensual != null ? t.ingreso_mensual : null,
      sin_empleo: t.sin_empleo != null ? Boolean(t.sin_empleo) : null,
      otras_fuentes_aplica: t.otras_fuentes_aplica != null ? Boolean(t.otras_fuentes_aplica) : null,
      otras_fuentes_ingreso: t.otras_fuentes_ingreso || null,
      monto_otras_fuentes: t.monto_otras_fuentes != null ? t.monto_otras_fuentes : null,
      // GET /borrador ya convierte tiene_imss/tiene_infonavit → *_estatus
      imss_estatus: t.imss_estatus || null,
      infonavit_estatus: t.infonavit_estatus || null,
    };
  }

  // ── Sembrar los 3 drafts + IDs desde GET /borrador/{estudio_id} ──────────
  // `data` = estudio plano en la raíz + beneficiario/tutores/solicitud anidados.
  function seedFromBorrador(data) {
    var estudioId = data.estudio_id || data.id;
    var beneficiario = data.beneficiario || {};
    var beneficiarioId = data.beneficiario_id || beneficiario.id;
    var solicitud = data.solicitud || null;

    if (estudioId) localStorage.setItem(KEYS.ESTUDIO_ID, String(estudioId));
    if (beneficiarioId) localStorage.setItem(KEYS.BENEFICIARIO_ID, String(beneficiarioId));
    if (solicitud && solicitud.id) {
      localStorage.setItem(KEYS.SOLICITUD_ID, String(solicitud.id));
    } else {
      localStorage.removeItem(KEYS.SOLICITUD_ID);
    }

    // region_ctx: reconstruir si falta (reanudación directa desde el perfil,
    // sin pasar por seleccion-region).
    var existingRegionCtx = null;
    try { existingRegionCtx = JSON.parse(localStorage.getItem("region_ctx") || "null"); } catch (_e) { /* recrear */ }
    if (!existingRegionCtx && (beneficiario.region_id || data.sede)) {
      localStorage.setItem("region_ctx", JSON.stringify({
        region_id: beneficiario.region_id || null,
        sede: data.sede || "",
        region_nombre: data.ciudad_registro || "",
      }));
    }

    // Normalizar beneficiario al shape local: la BD guarda la CURP en
    // curp_benef; los consumidores locales (payload maestro) leen `curp`.
    var beneficiarioLocal = Object.assign({}, beneficiario, {
      curp: beneficiario.curp_benef || beneficiario.curp || null,
    });

    setDraft("SOCIO", {
      region_id: beneficiario.region_id || null,
      sede: data.sede || beneficiario.sede || null,
      ciudad_registro: data.ciudad_registro || null,
      beneficiario: beneficiarioLocal,
      tutores: (data.tutores || []).map(_normalizeTutor),
      estudio: {
        tuvo_silla_previa: data.tuvo_silla_previa != null ? data.tuvo_silla_previa : null,
        como_obtuvo_silla: data.como_obtuvo_silla || null,
        elaboro_estudio: data.elaboro_estudio || null,
        voluntario_contacto: data.voluntario_contacto || null,
        fecha_estudio: data.fecha_estudio || null,
        credencial_path: data.credencial_path || null,
        credencial_url: data.credencial_url || null,
        comprobante_domicilio_path: data.comprobante_domicilio_path || null,
        comprobante_domicilio_url: data.comprobante_domicilio_url || null,
        estudio_clinico_path: data.estudio_clinico_path || null,
        estudio_clinico_url: data.estudio_clinico_url || null,
        estudio_clinico_url_resolved: data.estudio_clinico_url_resolved || null,
        status: data.status || "borrador",
      },
    });

    if (solicitud) {
      setDraft("TECNICA", {
        entorno: solicitud.entorno || null,
        // El diagnóstico vive en beneficiarios; tecnica.html lo captura/edita.
        diagnostico: beneficiario.diagnostico || null,
        control_tronco: solicitud.control_tronco || null,
        control_cabeza: solicitud.control_cabeza || null,
        control_de_piernas: solicitud.control_de_piernas || null,
        padecimiento: solicitud.padecimiento || null,
        soporte_oxigeno: typeof solicitud.soporte_oxigeno === "boolean" ? solicitud.soporte_oxigeno : null,
        observaciones_posturales: solicitud.observaciones_posturales || null,
        altura_total_in: solicitud.altura_total_in != null ? solicitud.altura_total_in : null,
        peso_kg: solicitud.peso_kg != null ? solicitud.peso_kg : null,
        medida_cabeza_asiento: solicitud.medida_cabeza_asiento != null ? solicitud.medida_cabeza_asiento : null,
        medida_hombro_asiento: solicitud.medida_hombro_asiento != null ? solicitud.medida_hombro_asiento : null,
        medida_prof_asiento: solicitud.medida_prof_asiento != null ? solicitud.medida_prof_asiento : null,
        medida_rodilla_talon: solicitud.medida_rodilla_talon != null ? solicitud.medida_rodilla_talon : null,
        medida_ancho_cadera: solicitud.medida_ancho_cadera != null ? solicitud.medida_ancho_cadera : null,
        unidad_medida: solicitud.unidad_captura || solicitud.unidad_medida || null,
        unidad_peso_captura: solicitud.unidad_peso_captura || null,
        foto_path: solicitud.foto_path || null,
        foto_url: solicitud.foto_url || null,
        foto_url_resolved: solicitud.foto_url_resolved || null,
        equipo_solicitado: solicitud.equipo_solicitado || null,
        estudio_clinico_path: solicitud.estudio_clinico_path || data.estudio_clinico_path || null,
        estudio_clinico_url: solicitud.estudio_clinico_url || data.estudio_clinico_url || null,
        estudio_clinico_url_resolved: solicitud.estudio_clinico_url_resolved || data.estudio_clinico_url_resolved || null,
      });
    }
    // Sin solicitud en backend: se conserva el draft_tecnica local si existe —
    // puede contener capturas del usuario que aún no llegan al servidor.

    setDraft("GESTION", {
      silla_previa: data.tuvo_silla_previa === true || data.tuvo_silla_previa === 1
        ? "Sí"
        : (data.tuvo_silla_previa === false || data.tuvo_silla_previa === 0 ? "No" : null),
      como_obtuvo_silla: data.como_obtuvo_silla || null,
      fecha_estudio: data.fecha_estudio || null,
      entidad_solicitante: solicitud ? (solicitud.entidad_solicitante || null) : null,
      prioridad: solicitud ? (solicitud.prioridad || null) : null,
      justificacion: solicitud ? (solicitud.justificacion || null) : null,
    });
  }

  // ── Hidratación única ─────────────────────────────────────────────────────
  // Regla:
  //  - ?estudio_id= en la URL distinto del estudio_id local → clearAll() +
  //    hidratar (se cambia de borrador; el estado local pertenece a otro).
  //  - hay estudio_id (local o URL) y falta draft_socioeconomico → hidratar.
  //  - resto → no-op: el draft local es la fuente de verdad.
  // 404 → el borrador ya no existe (o dejó de ser borrador): limpiar IDs.
  async function hydrateIfNeeded(opts) {
    opts = opts || {};
    var urlEstudioId = opts.urlEstudioId != null ? _intOrNull(opts.urlEstudioId) : null;
    var localEstudioId = _intOrNull(localStorage.getItem(KEYS.ESTUDIO_ID));

    var target = null;
    if (urlEstudioId && urlEstudioId !== localEstudioId) {
      clearAll();
      target = urlEstudioId;
    } else if ((urlEstudioId || localEstudioId) && !localStorage.getItem(KEYS.SOCIO)) {
      target = urlEstudioId || localEstudioId;
    }

    if (!target) return { hydrated: false };

    _showOverlay();
    try {
      var res = await ApiClient.fetch("/borrador/" + target, {
        headers: { Accept: "application/json" },
      });
      if (res.status === 404) {
        _clearIds();
        return { hydrated: false };
      }
      if (!res.ok) {
        console.error("DraftStore: hidratación falló con status", res.status);
        return { hydrated: false };
      }
      var data = await res.json();
      seedFromBorrador(data);
      return { hydrated: true, data: data };
    } catch (err) {
      console.error("DraftStore: error de red al hidratar borrador:", err);
      return { hydrated: false, error: err };
    } finally {
      _hideOverlay();
    }
  }

  // ── Payload maestro para POST /guardar-borrador ───────────────────────────
  // ÚNICO builder (antes había tres copias divergentes, una por vista). Lee
  // exclusivamente localStorage: la vista que llama debe volcar su formulario
  // al draft correspondiente (setDraft) antes de invocarlo.
  function buildMasterPayload(status) {
    var draftSocio = getDraft("SOCIO") || {};
    var draftTecnica = getDraft("TECNICA") || {};
    var draftGestion = getDraft("GESTION") || {};
    var ids = getIds();

    var tutor1 = (draftSocio.tutores || []).find(function (t) { return t.numero_tutor === 1; }) || {};
    var tutor2 = (draftSocio.tutores || []).find(function (t) { return t.numero_tutor === 2; }) || {};

    function mapTutor(prefix, tutor) {
      var out = {};
      out[prefix + "_nombres"] = tutor.nombres || null;
      out[prefix + "_apellido_paterno"] = tutor.apellido_paterno || null;
      out[prefix + "_apellido_materno"] = tutor.apellido_materno || null;
      out[prefix + "_email"] = tutor.email || null;
      out[prefix + "_edad"] = tutor.edad != null ? tutor.edad : null;
      out[prefix + "_nivel_estudios"] = tutor.nivel_estudios || null;
      out[prefix + "_estado_civil"] = tutor.estado_civil || null;
      out[prefix + "_num_hijos"] = tutor.num_hijos != null ? tutor.num_hijos : null;
      out[prefix + "_vivienda"] = tutor.vivienda || null;
      out[prefix + "_fuente_empleo"] = tutor.fuente_empleo || null;
      out[prefix + "_antiguedad_aplica"] = tutor.antiguedad_aplica != null ? tutor.antiguedad_aplica : null;
      out[prefix + "_antiguedad_anios"] = tutor.antiguedad_anios != null ? tutor.antiguedad_anios : null;
      out[prefix + "_antiguedad_meses_extra"] = tutor.antiguedad_meses_extra != null ? tutor.antiguedad_meses_extra : null;
      out[prefix + "_ingreso_mensual"] = tutor.ingreso_mensual != null ? tutor.ingreso_mensual : null;
      out[prefix + "_sin_empleo"] = tutor.sin_empleo != null ? tutor.sin_empleo : null;
      out[prefix + "_otras_fuentes_aplica"] = tutor.otras_fuentes_aplica != null ? tutor.otras_fuentes_aplica : null;
      out[prefix + "_otras_fuentes_ingreso"] = tutor.otras_fuentes_ingreso || null;
      out[prefix + "_monto_otras_fuentes"] = tutor.monto_otras_fuentes != null ? tutor.monto_otras_fuentes : null;
      out[prefix + "_imss_estatus"] = tutor.imss_estatus || null;
      out[prefix + "_infonavit_estatus"] = tutor.infonavit_estatus || null;
      return out;
    }

    var gestionSilla = draftGestion.silla_previa === "Sí"
      ? true
      : (draftGestion.silla_previa === "No" ? false : null);

    var payload = {
      estudio_id: ids.estudio_id,
      solicitud_id: ids.solicitud_id,
      beneficiario_id: ids.beneficiario_id,
      region_id: draftSocio.region_id || null,
      sede: draftSocio.sede || null,
      ciudad_registro: draftSocio.ciudad_registro || null,

      // Beneficiario (paso 1)
      nombres: (draftSocio.beneficiario && draftSocio.beneficiario.nombres) || null,
      apellido_paterno: (draftSocio.beneficiario && draftSocio.beneficiario.apellido_paterno) || null,
      apellido_materno: (draftSocio.beneficiario && draftSocio.beneficiario.apellido_materno) || null,
      curp: (draftSocio.beneficiario && draftSocio.beneficiario.curp) || null,
      fecha_nacimiento: (draftSocio.beneficiario && draftSocio.beneficiario.fecha_nacimiento) || null,
      diagnostico: draftTecnica.diagnostico || (draftSocio.beneficiario && draftSocio.beneficiario.diagnostico) || null,
      calle: (draftSocio.beneficiario && draftSocio.beneficiario.calle) || null,
      num_ext: (draftSocio.beneficiario && draftSocio.beneficiario.num_ext) || null,
      num_int: (draftSocio.beneficiario && draftSocio.beneficiario.num_int) || null,
      colonia: (draftSocio.beneficiario && draftSocio.beneficiario.colonia) || null,
      ciudad: (draftSocio.beneficiario && draftSocio.beneficiario.ciudad) || null,
      estado_codigo: (draftSocio.beneficiario && draftSocio.beneficiario.estado_codigo) || null,
      estado_nombre: (draftSocio.beneficiario && draftSocio.beneficiario.estado_nombre) || null,
      sexo: (draftSocio.beneficiario && draftSocio.beneficiario.sexo) || null,
      telefonos: (draftSocio.beneficiario && draftSocio.beneficiario.telefonos) || null,
      email: (draftSocio.beneficiario && draftSocio.beneficiario.email) || null,

      // Estudio (pasos 1 y 3)
      tuvo_silla_previa: gestionSilla != null
        ? gestionSilla
        : ((draftSocio.estudio && draftSocio.estudio.tuvo_silla_previa) != null
            ? draftSocio.estudio.tuvo_silla_previa
            : null),
      como_obtuvo_silla: draftGestion.como_obtuvo_silla || (draftSocio.estudio && draftSocio.estudio.como_obtuvo_silla) || null,
      elaboro_estudio: (draftSocio.estudio && draftSocio.estudio.elaboro_estudio) || null,
      voluntario_contacto: (draftSocio.estudio && draftSocio.estudio.voluntario_contacto) || null,
      fecha_estudio: draftGestion.fecha_estudio || (draftSocio.estudio && draftSocio.estudio.fecha_estudio) || null,
      credencial_path: (draftSocio.estudio && draftSocio.estudio.credencial_path) || null,
      credencial_url: (draftSocio.estudio && draftSocio.estudio.credencial_url) || null,
      comprobante_domicilio_path: (draftSocio.estudio && draftSocio.estudio.comprobante_domicilio_path) || null,
      comprobante_domicilio_url: (draftSocio.estudio && draftSocio.estudio.comprobante_domicilio_url) || null,
      estudio_clinico_path: draftTecnica.estudio_clinico_path || (draftSocio.estudio && draftSocio.estudio.estudio_clinico_path) || null,
      estudio_clinico_url: draftTecnica.estudio_clinico_url || (draftSocio.estudio && draftSocio.estudio.estudio_clinico_url) || null,
      status: status || "borrador",

      // Solicitud técnica (paso 2)
      entorno: draftTecnica.entorno || null,
      control_tronco: draftTecnica.control_tronco || null,
      control_cabeza: draftTecnica.control_cabeza || null,
      control_de_piernas: draftTecnica.control_de_piernas || null,
      padecimiento: draftTecnica.padecimiento || null,
      soporte_oxigeno: typeof draftTecnica.soporte_oxigeno === "boolean" ? draftTecnica.soporte_oxigeno : null,
      observaciones_posturales: draftTecnica.observaciones_posturales || null,
      altura_total_in: draftTecnica.altura_total_in != null ? String(draftTecnica.altura_total_in) : null,
      peso_kg: draftTecnica.peso_kg != null ? String(draftTecnica.peso_kg) : null,
      medida_cabeza_asiento: draftTecnica.medida_cabeza_asiento != null ? String(draftTecnica.medida_cabeza_asiento) : null,
      medida_hombro_asiento: draftTecnica.medida_hombro_asiento != null ? String(draftTecnica.medida_hombro_asiento) : null,
      medida_prof_asiento: draftTecnica.medida_prof_asiento != null ? String(draftTecnica.medida_prof_asiento) : null,
      medida_rodilla_talon: draftTecnica.medida_rodilla_talon != null ? String(draftTecnica.medida_rodilla_talon) : null,
      medida_ancho_cadera: draftTecnica.medida_ancho_cadera != null ? String(draftTecnica.medida_ancho_cadera) : null,
      unidad_medida: draftTecnica.unidad_medida || null,
      unidad_peso_captura: draftTecnica.unidad_peso_captura || null,
      foto_path: draftTecnica.foto_path || null,
      foto_url: draftTecnica.foto_url || null,
      equipo_solicitado: draftTecnica.equipo_solicitado || null,

      // Gestión (paso 3)
      entidad_solicitante: draftGestion.entidad_solicitante || null,
      prioridad: draftGestion.prioridad || null,
      justificacion: draftGestion.justificacion || null,
    };

    Object.assign(payload, mapTutor("tutor1", tutor1), mapTutor("tutor2", tutor2));
    return payload;
  }

  window.DraftStore = {
    KEYS: KEYS,
    getDraft: getDraft,
    setDraft: setDraft,
    getIds: getIds,
    setIds: setIds,
    clearAll: clearAll,
    hydrateIfNeeded: hydrateIfNeeded,
    seedFromBorrador: seedFromBorrador,
    buildMasterPayload: buildMasterPayload,
    showOverlay: _showOverlay,
    hideOverlay: _hideOverlay,
  };
})();
