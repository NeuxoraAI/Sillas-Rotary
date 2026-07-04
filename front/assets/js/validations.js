/**
 * SR_Validations — Módulo compartido de validaciones
 * Espejo de: backend/validators.py
 *
 * Uso:
 *   <script src="assets/js/validations.js"></script>
 *   // Luego en cualquier formulario:
 *   SR_Validations.setupWhitelistField(inputEl, SR_Validations.OBS_WHITELIST_RE, 500);
 */
(function (global) {
  "use strict";

  // ─────────────────────────────────────────────────────────────────
  // Regex (espejo de validators.py)
  // ─────────────────────────────────────────────────────────────────

  const NOMBRE_RE = /^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ. ]+$/;
  const DIAGNOSTICO_RE = /^[A-Za-záéíóúÁÉÍÓÚüÜñÑ0-9\s\-().\/,$]+$/;
  const CALLE_RE = /^[A-Za-záéíóúÁÉÍÓÚüÜñÑ0-9.\- ]+$/;
  const COLONIA_RE = CALLE_RE;
  const NUM_DOMICILIO_RE = /^[A-Za-z0-9\-/]+$/;
  const TELEFONO_RE = /^[0-9]{10}$/;
  // CURP — must stay identical to validators.py _CURP_RE (Issue #32).
  const CURP_RE = /^[A-Z][AEIOUX][A-Z]{2}\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])[HM](AS|BC|BS|CC|CL|CM|CS|CH|DF|DG|GT|GR|HG|JC|MC|MN|MS|NT|NL|OC|PL|QT|QR|SP|SL|SR|TC|TS|TL|VZ|YN|ZS|NE)[B-DF-HJ-NP-TV-Z]{3}[A-Z\d]\d$/;
  const EMAIL_RE = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  const OBS_WHITELIST_RE =
    /^[a-zA-ZáéíóúÁÉÍÓÚäëïöüÄËÏÖÜñÑ0-9 ()\/\-.,:;]*$/;
  const ENTIDAD_WHITELIST_RE =
    /^[a-zA-ZáéíóúÁÉÍÓÚäëïöüÄËÏÖÜñÑ0-9 ()\/\-.,]*$/;
  const MEASURE_PARTIAL_RE = /^[0-9]+(\.[0-9]{0,3})?$/;
  const MEASURE_FINAL_RE = /^[0-9]+(\.[0-9]{1,3})?$/;

  // ─────────────────────────────────────────────────────────────────
  // Límites (espejo de validators.py)
  // ─────────────────────────────────────────────────────────────────

  const LIMITS = {
    NOMBRE_MAX: 60,
    APELLIDO_MAX: 40,
    DIAGNOSTICO_MAX: 160,
    CALLE_MAX: 120,
    COLONIA_MAX: 120,
    CIUDAD_MAX: 80,
    NUM_DOMICILIO_MAX: 10,
    TELEFONO_LEN: 10,
    OBS_MAX: 500,
    ENTIDAD_MAX: 64,
    JUST_MAX: 500,
    FUENTE_EMPLEO_MAX: 80,
    OTRAS_FUENTES_INGRESO_MAX: 100,
    INGRESO_MENSUAL_MAX: 999999999,
    MONTO_OTRAS_FUENTES_MAX: 999999999,
    NUM_HIJOS_MAX: 30,
    EDAD_MAX: 99,
    EMAIL_MAX: 254,
    TIEMPO_DX_ANIOS_MAX: 120,
    TIEMPO_DX_MESES_MAX: 11,
    MEASURE_INT_DIGITS: 4,
    MEASURE_DEC_DIGITS: 3,
  };

  // ─────────────────────────────────────────────────────────────────
  // Catálogos (espejo de validators.py)
  // ─────────────────────────────────────────────────────────────────

  const ENTORNO_OPTIONS = [
    "Urbano / Interiores",
    "Rural / Terreno irregular",
    "Mixto",
  ];
  const CONTROL_TRONCO_OPTIONS = [
    "Completo",
    "Parcial / Requiere apoyo lateral",
    "Nulo / Requiere soporte total",
  ];
  const CONTROL_CABEZA_OPTIONS = [
    "Independiente",
    "No posee / Requiere cabezal",
  ];
  const CONTROL_PIERNAS_OPTIONS = [
    "Parcial",
    "Nulo",
  ];
  const PRIORIDAD_OPTIONS = ["Alta", "Media"];
  const COMO_OBTUVO_OPTIONS = ["COMPRA", "DONACION"];
  const SEX_OPTIONS = ["M", "F"];
  const UNIDAD_MEDIDA_OPTIONS = ["in", "cm"];
  const STATUS_OPTIONS = ["borrador", "completo"];

  // ─────────────────────────────────────────────────────────────────
  // Etiquetas de campos — única fuente de verdad columna → etiqueta
  // visible. Espejo de FIELD_LABELS en backend/validators.py (Issue #122).
  // Evita exponer nombres técnicos de columnas (curp_benef, estado_codigo…)
  // en mensajes, validaciones y modales cuando el backend solo envía el
  // nombre del campo (p. ej. rutas `loc` de errores Pydantic 422).
  // ─────────────────────────────────────────────────────────────────

  const FIELD_LABELS = {
    // Beneficiario
    nombres: "Nombre(s)",
    apellido_paterno: "Apellido paterno",
    apellido_materno: "Apellido materno",
    curp_benef: "CURP",
    fecha_nacimiento: "Fecha de nacimiento",
    diagnostico: "Diagnóstico",
    calle: "Calle",
    colonia: "Colonia",
    ciudad: "Ciudad",
    estado_codigo: "Estado",
    sexo: "Sexo",
    telefonos: "Teléfono",
    // Estudio socioeconómico
    fecha_estudio: "Fecha del estudio",
    tuvo_silla_previa: "¿Tuvo silla previa?",
    como_obtuvo_silla: "¿Cómo obtuvo la silla?",
    elaboro_estudio: "Elaboró el estudio",
    sede: "Sede",
    ciudad_registro: "Ciudad de registro",
    credencial_url: "Credencial",
    comprobante_domicilio_url: "Comprobante de domicilio",
    // Gestión
    entidad_solicitante: "Entidad solicitante",
    prioridad: "Prioridad",
    // Solicitud técnica
    altura_total_in: "Altura total",
    peso_kg: "Peso",
    medida_cabeza_asiento: "Medida cabeza a asiento",
    medida_hombro_asiento: "Medida hombro a asiento",
    medida_prof_asiento: "Profundidad de asiento",
    medida_rodilla_talon: "Medida rodilla a talón",
    medida_ancho_cadera: "Ancho de cadera",
    entorno: "Entorno",
    control_tronco: "Control de tronco",
    control_cabeza: "Control de cabeza",
    control_de_piernas: "Control de piernas",
    foto_url: "Fotografía del paciente",
    // Tutor
    numero_tutor: "Tutor",
    edad: "Edad",
    nivel_estudios: "Nivel de estudios",
    estado_civil: "Estado civil",
    vivienda: "Vivienda",
    imss_estatus: "IMSS",
    infonavit_estatus: "Infonavit",
    fuente_empleo: "Fuente de empleo",
    ingreso_mensual: "Ingreso mensual",
    antiguedad_anios: "Antigüedad (años)",
    otras_fuentes_ingreso: "Otras fuentes de ingreso",
    monto_otras_fuentes: "Monto de otras fuentes",
  };

  // Prefijos de formulario presentes en rutas `loc` de errores Pydantic.
  const _FIELD_LABEL_PREFIXES = new Set([
    "beneficiario",
    "estudio",
    "solicitud",
    "tutor",
    "tutor1",
    "tutor2",
    "body",
  ]);

  // Resuelve un nombre de campo/columna a su etiqueta visible. Si el campo
  // no está en el catálogo, lo humaniza para no mostrar jamás el nombre crudo.
  function getFieldLabel(field) {
    if (field == null) return "Campo";
    const key = String(field).trim();
    if (FIELD_LABELS[key]) return FIELD_LABELS[key];
    return key
      .replace(/_/g, " ")
      .replace(/^\s*./, (c) => c.toUpperCase())
      .trim() || "Campo";
  }

  // Traduce una ruta `loc` de Pydantic (p. ej. "beneficiario.curp_benef")
  // a etiqueta visible, descartando prefijos de formulario.
  function getBackendPathLabel(path) {
    if (!path) return "Campo";
    const segments = String(path).split(".").filter(Boolean);
    const field = [...segments]
      .reverse()
      .find((seg) => !_FIELD_LABEL_PREFIXES.has(seg) && !/^\d+$/.test(seg));
    return getFieldLabel(field || segments[segments.length - 1]);
  }

  // ─────────────────────────────────────────────────────────────────
  // Utilidades de filtrado
  // ─────────────────────────────────────────────────────────────────

  function filterText(text, regex) {
    return Array.from(text)
      .filter((ch) => regex.test(ch))
      .join("");
  }

  function filterPaste(event, regex, inputEl) {
    const pasted = (event.clipboardData || window.clipboardData).getData("text");
    const filtered = filterText(pasted, regex);
    if (filtered !== pasted) {
      event.preventDefault();
      const start = inputEl.selectionStart;
      const end = inputEl.selectionEnd;
      const before = inputEl.value.slice(0, start);
      const after = inputEl.value.slice(end);
      inputEl.value = before + filtered + after;
      inputEl.selectionStart = inputEl.selectionEnd = start + filtered.length;
    }
  }

  function blockBeforeInput(event, regex) {
    if (event.data && !regex.test(event.data)) {
      event.preventDefault();
    }
  }

  function catchIME(inputEl, regex) {
    const filtered = filterText(inputEl.value, regex);
    if (filtered !== inputEl.value) {
      const cursor = inputEl.selectionStart;
      inputEl.value = filtered;
      inputEl.selectionStart = inputEl.selectionEnd = Math.min(
        cursor,
        filtered.length
      );
    }
  }

  // ─────────────────────────────────────────────────────────────────
  // Setup de campos (funciones reutilizables)
  // ─────────────────────────────────────────────────────────────────

  /**
   * Configura validación whitelist en un input/textarea.
   * Bloquea caracteres no permitidos en beforeinput, filtra paste, y atrapa IME.
   */
  function setupWhitelistField(inputEl, regex, maxLength) {
    if (!inputEl) return;

    inputEl.addEventListener("beforeinput", (e) => blockBeforeInput(e, regex));

    inputEl.addEventListener("paste", (e) => filterPaste(e, regex, inputEl));

    inputEl.addEventListener("input", () => catchIME(inputEl, regex));

    if (maxLength) {
      inputEl.setAttribute("maxlength", String(maxLength));
    }
  }

  /**
   * Configura validación de medidas técnicas (dígitos + punto decimal).
   */
  function setupMeasureField(inputEl) {
    if (!inputEl) return;

    inputEl.addEventListener("beforeinput", (e) => {
      if (!e.data) return;

      const current = inputEl.value;
      const start = inputEl.selectionStart;
      const end = inputEl.selectionEnd;
      const pending = current.slice(0, start) + e.data + current.slice(end);

      // Bloquear no-dígito/no-punto
      if (!/^[0-9.]$/.test(e.data)) {
        e.preventDefault();
        return;
      }

      // Bloquear segundo punto
      if (
        e.data === "." &&
        current.includes(".") &&
        !current.slice(start, end).includes(".")
      ) {
        e.preventDefault();
        return;
      }

      // Validar valor pendiente
      if (!MEASURE_PARTIAL_RE.test(pending)) {
        e.preventDefault();
        return;
      }

      // Verificar dígitos enteros (máx 4)
      const parts = pending.split(".");
      const intPart = parts[0].replace(/^0+/, "") || "0";
      if (intPart.length > LIMITS.MEASURE_INT_DIGITS) {
        e.preventDefault();
      }
    });

    inputEl.addEventListener("paste", (e) => {
      const pasted = (e.clipboardData || window.clipboardData)
        .getData("text")
        .trim();
      if (!MEASURE_FINAL_RE.test(pasted)) {
        e.preventDefault();
        return;
      }
      const parts = pasted.split(".");
      const intPart = parts[0].replace(/^0+/, "") || "0";
      if (intPart.length > LIMITS.MEASURE_INT_DIGITS) {
        e.preventDefault();
      }
    });

    inputEl.addEventListener("input", () => {
      const val = inputEl.value;
      if (!val) return;

      // Remover caracteres inválidos
      const cleaned = val.replace(/[^0-9.]/g, "");
      if (cleaned !== val) {
        inputEl.value = cleaned;
        return;
      }

      // Forzar un solo punto
      const dotCount = (cleaned.match(/\./g) || []).length;
      if (dotCount > 1) {
        inputEl.value = cleaned.replace(/\./g, (m, i, str) =>
          i === str.indexOf(".") ? "." : ""
        );
        return;
      }

      // Forzar máximo 4 dígitos enteros
      const parts = cleaned.split(".");
      const intPart = parts[0].replace(/^0+/, "") || "0";
      if (intPart.length > LIMITS.MEASURE_INT_DIGITS) {
        inputEl.value =
          intPart.slice(0, LIMITS.MEASURE_INT_DIGITS) +
          (parts.length > 1 ? "." + parts[1] : "");
        return;
      }

      // Forzar máximo 3 decimales
      if (parts.length > 1 && parts[1].length > LIMITS.MEASURE_DEC_DIGITS) {
        inputEl.value = parts[0] + "." + parts[1].slice(0, LIMITS.MEASURE_DEC_DIGITS);
      }
    });
  }

  /**
   * Configura validación de nombres (solo letras, espacio, punto).
   */
  function setupNameField(inputEl) {
    if (!inputEl) return;
    // Desactivar el autocompletado del navegador en los campos de nombre. Sin
    // esto, Chrome reconoce "apellido_paterno" como el campo canónico
    // `family-name` y SOBRESCRIBE con el autofill el valor que restauramos del
    // borrador al volver al formulario — se veía como si "no se persistiera" el
    // apellido paterno (los otros nombres no son campos de autofill estándar, por
    // eso solo se perdía ese). Se fija antes del restore diferido.
    inputEl.setAttribute("autocomplete", "off");
    inputEl.setAttribute("autocorrect", "off");
    inputEl.addEventListener("input", () => {
      inputEl.value = inputEl.value.replace(/[^a-zA-ZáéíóúÁÉÍÓÚüÜñÑ .]/g, "");
    });
  }

  /**
   * Configura sanitización de teléfono (solo 10 dígitos).
   */
  function setupTelefonoField(inputEl) {
    if (!inputEl) return;
    inputEl.addEventListener("input", () => {
      inputEl.value = String(inputEl.value || "")
        .replace(/\D/g, "")
        .slice(0, LIMITS.TELEFONO_LEN);
    });
    inputEl.value = String(inputEl.value || "")
      .replace(/\D/g, "")
      .slice(0, LIMITS.TELEFONO_LEN);
  }

  /**
   * Configura campo monetario (solo dígitos, con formato de miles).
   */
  function setupMoneyField(inputEl, max) {
    if (!inputEl) return;

    function sanitize(raw) {
      if (raw == null) return "";
      const cleaned = String(raw)
        .replace(/,/g, "")
        .replace(/[^\d.]/g, "");
      const firstDot = cleaned.indexOf(".");
      if (firstDot === -1) return cleaned;
      const intPart = cleaned.slice(0, firstDot);
      const decPart = cleaned.slice(firstDot + 1).replace(/\./g, "");
      return `${intPart}.${decPart}`;
    }

    inputEl.addEventListener("input", () => {
      const sanitized = sanitize(inputEl.value);
      if (sanitized) {
        const num = parseFloat(sanitized);
        if (!isNaN(num) && num > max) {
          inputEl.value = String(max);
          return;
        }
      }
      inputEl.value = sanitized;
    });
  }

  /**
   * Configura campo monetario con sanitización + máximo + formateo visual con comas.
   */
  function setupMoneyFieldWithFormatting(inputEl, max) {
    if (!inputEl) return;

    inputEl.addEventListener("input", () => {
      let raw = inputEl.value.replace(/,/g, "").replace(/[^\d.]/g, "");
      if (raw) {
        const num = parseFloat(raw);
        if (!isNaN(num) && num > max) raw = String(max);
      }
      inputEl.value = raw ? formatIntegerDisplay(raw) : raw;
    });

    if (inputEl.value) {
      inputEl.value = formatIntegerDisplay(inputEl.value.replace(/,/g, ""));
    }
  }

  /**
   * Configura campo de correo electrónico.
   * Sanitiza al blur: trim + toLowerCase.
   */
  function setupEmailField(inputEl) {
    if (!inputEl) return;

    inputEl.addEventListener("blur", () => {
      inputEl.value = inputEl.value.trim().toLowerCase();
    });

    inputEl.addEventListener("input", () => {
      if (inputEl.value.length > LIMITS.EMAIL_MAX) {
        inputEl.value = inputEl.value.slice(0, LIMITS.EMAIL_MAX);
      }
    });
  }

  /**
   * Configura campo entero con min/max.
   */
  function setupIntegerField(inputEl, min, max) {
    if (!inputEl) return;

    inputEl.addEventListener("keydown", (e) => {
      if (e.key === "." || e.key === "e" || e.key === "E" || e.key === "-" || e.key === "+") {
        e.preventDefault();
      }
    });

    inputEl.addEventListener("input", () => {
      let val = inputEl.value.replace(/\D/g, "");
      if (val !== "") {
        const num = parseInt(val, 10);
        if (num > max) val = String(max);
        if (num < min) val = String(min);
      }
      inputEl.value = val;
    });
  }

  /**
   * Configura campo de texto genérico con regex de filtro.
   */
  function setupTextField(inputEl, regex) {
    if (!inputEl) return;
    inputEl.addEventListener("input", () => {
      inputEl.value = filterText(inputEl.value, regex);
    });
  }

  // ─────────────────────────────────────────────────────────────────
  // CURP — formato + dígito verificador (espejo de validators.py)
  // ─────────────────────────────────────────────────────────────────

  const CURP_DICT = "0123456789ABCDEFGHIJKLMNÑOPQRSTUVWXYZ";

  /** Calcula el dígito verificador oficial a partir de los 17 primeros chars. */
  function curpDigitoVerificador(curp) {
    let suma = 0;
    for (let i = 0; i < 17; i++) {
      suma += CURP_DICT.indexOf(curp[i]) * (18 - i);
    }
    return String((10 - (suma % 10)) % 10);
  }

  /** Valida formato (18 chars) + dígito verificador. Devuelve true/false. */
  function isValidCurp(value) {
    if (!value) return false;
    const curp = value.trim().toUpperCase();
    if (curp.length !== 18) return false;
    if (!CURP_RE.test(curp)) return false;
    return curpDigitoVerificador(curp) === curp[17];
  }

  /** Configura un input de CURP: sólo A-Z/0-9, mayúsculas, máx 18 chars. */
  function setupCurpField(inputEl) {
    if (!inputEl) return;
    const sanitize = () => {
      inputEl.value = inputEl.value
        .toUpperCase()
        .replace(/[^A-Z0-9]/g, "")
        .slice(0, 18);
    };
    inputEl.addEventListener("input", sanitize);
    sanitize();
  }

  // ─────────────────────────────────────────────────────────────────
  // Validación de campos obligatorios
  // ─────────────────────────────────────────────────────────────────

  /**
   * Valida que los campos requeridos no estén vacíos.
   * Retorna array de {id, label} para los campos faltantes.
   */
  function validateRequired(formEl, requiredFields, options) {
    const status = options?.status || "completo";
    if (status !== "completo") return []; // borradores no requieren completar

    const missing = [];
    for (const { id, label } of requiredFields) {
      const input = formEl.querySelector(`[name="${id}"]`);
      if (!input || !input.value.trim()) {
        missing.push({ id, label });
      }
    }
    return missing;
  }

  // ─────────────────────────────────────────────────────────────────
  // Validación de constraints HTML5 (minlength, pattern)
  // Reemplaza la validación nativa del navegador desactivada por novalidate
  // ─────────────────────────────────────────────────────────────────

  function validateHTML5Constraints(formEl) {
    const errors = [];
    const inputs = formEl.querySelectorAll(
      'input:not([type="radio"]):not([type="checkbox"]), select, textarea'
    );

    for (const input of inputs) {
      const name = input.name;
      if (!name) continue;

      const value = input.value.trim();
      if (!value) continue; // Vacíos los maneja validateRequired
      if (input.disabled || input.readOnly) continue;

      const label = _getFieldLabel(input, name);
      let fieldHasError = false;

      // maxlength (aplica a text, textarea, etc.)
      const maxlength = input.getAttribute("maxlength");
      if (maxlength) {
        const max = parseInt(maxlength, 10);
        if (value.length > max) {
          errors.push({
            id: name,
            message: `${label} debe tener máximo ${max} caracteres`,
          });
          fieldHasError = true;
        }
      }

      // minlength
      const minlength = input.getAttribute("minlength");
      if (!fieldHasError && minlength) {
        const min = parseInt(minlength, 10);
        if (value.length < min) {
          errors.push({
            id: name,
            message: `${label} debe tener al menos ${min} caracteres`,
          });
          fieldHasError = true;
        }
      }

      // pattern
      if (!fieldHasError) {
        const pattern = input.getAttribute("pattern");
        if (pattern) {
          try {
            const regex = new RegExp(`^(?:${pattern})$`);
            if (!regex.test(value)) {
              errors.push({
                id: name,
                message: `${label} contiene caracteres o formato no permitido`,
              });
              fieldHasError = true;
            }
          } catch (e) {
            console.warn(`Patrón inválido para ${name}:`, pattern);
          }
        }
      }

      // min/max para number inputs
      if (!fieldHasError && input.type === "number") {
        const numValue = parseFloat(value);
        if (!isNaN(numValue)) {
          const min = input.getAttribute("min");
          if (min !== null && numValue < parseFloat(min)) {
            errors.push({
              id: name,
              message: `${label} debe ser mayor o igual a ${min}`,
            });
            fieldHasError = true;
          }

          const max = input.getAttribute("max");
          if (!fieldHasError && max !== null && numValue > parseFloat(max)) {
            errors.push({
              id: name,
              message: `${label} debe ser menor o igual a ${max}`,
            });
            fieldHasError = true;
          }
        }
      }
    }

    return errors;
  }

  function _getFieldLabel(inputEl, fallbackName) {
    let label = "";
    const container = inputEl.closest(".space-y-2, [class*='grid'], div");
    if (container) {
      const labelEl = container.querySelector("label");
      if (labelEl) {
        label = labelEl.textContent.trim();
        // Limpiar texto de checkbox si está presente
        label = label.replace(/Agregar.*/i, "").trim();
      }
    }

    if (!label) {
      label = fallbackName
        .replace(/_/g, " ")
        .replace(/tutor1_/g, "Tutor 1 ")
        .replace(/tutor2_/g, "Tutor 2 ")
        .replace(/^./, (str) => str.toUpperCase());
    }

    return label;
  }

  // ─────────────────────────────────────────────────────────────────
  // Errores visuales inline
  // ─────────────────────────────────────────────────────────────────

  function showFieldError(fieldName, message) {
    const input = document.querySelector(`[name="${fieldName}"]`);
    const error = document.querySelector(`[data-error-for="${fieldName}"]`);
    if (input) {
      input.classList.add("ring-1", "ring-red-400");
      input.setAttribute("aria-invalid", "true");
    }
    if (error) {
      error.textContent = message;
      error.classList.remove("hidden");
    }
  }

  function clearFieldError(fieldName) {
    const input = document.querySelector(`[name="${fieldName}"]`);
    const error = document.querySelector(`[data-error-for="${fieldName}"]`);
    if (input) {
      input.classList.remove("ring-1", "ring-red-400");
      input.removeAttribute("aria-invalid");
    }
    if (error) {
      error.textContent = "";
      error.classList.add("hidden");
    }
  }

  // Real-time required validation: text-like fields show an inline error below
  // the field on blur when required+empty, and clear it as the user types.
  // Checks `.required` at blur time so dynamically-required fields are covered.
  function setupLiveRequired(formEl) {
    if (!formEl) return;
    const fields = formEl.querySelectorAll(
      'input:not([type="radio"]):not([type="checkbox"]):not([type="hidden"]):not([type="file"]), textarea'
    );
    fields.forEach((field) => {
      const name = field.getAttribute("name");
      if (!name) return;
      field.addEventListener("blur", () => {
        if (field.required && !(field.value || "").trim()) {
          showFieldError(name, "Este campo es obligatorio");
        } else {
          clearFieldError(name);
        }
      });
      field.addEventListener("input", () => {
        if ((field.value || "").trim()) clearFieldError(name);
      });
    });
  }

  function clearAllFieldErrors(formEl) {
    formEl.querySelectorAll(".field-error").forEach((el) => {
      el.classList.add("hidden");
      el.textContent = "";
    });
    formEl.querySelectorAll(".ring-red-400").forEach((el) => {
      el.classList.remove("ring-1", "ring-red-400");
      el.removeAttribute("aria-invalid");
    });
  }

  // ─────────────────────────────────────────────────────────────────
  // Resaltado de campos al redirigir entre formularios (Issue #123)
  //
  // El backend/validaciones locales producen errores identificados por
  // {form, field}. Al pulsar "Ir al formulario" el usuario navega a otra
  // página, por lo que los errores se persisten en sessionStorage y se
  // reaplican al cargar el destino. El mapa traduce (form, field) →
  // {page, name, kind} porque los nombres del backend NO coinciden con los
  // `name` de los inputs del frontend (p.ej. curp_benef → curp).
  // ─────────────────────────────────────────────────────────────────

  const FIELD_ERROR_STASH_KEY = "sr_pending_field_errors";

  const _KNOWN_PAGES = new Set(["socioeconomico", "tecnica", "gestion"]);

  /**
   * Deriva la clave de página ("socioeconomico"|"tecnica"|"gestion") desde una
   * URL de destino como "socioeconomico.html" o "../x/tecnica.html".
   */
  function pageFromUrl(url) {
    if (!url) return null;
    const file = String(url).split(/[?#]/)[0].split("/").pop() || "";
    const base = file.replace(/\.html$/i, "");
    return _KNOWN_PAGES.has(base) ? base : null;
  }

  // Evidencias (archivos): no tienen [data-error-for]; se resaltan por
  // contenedor + leyenda con selectores explícitos.
  // `legend` apunta a un <p> DEDICADO al error (no al `*-status`, que lo maneja la
  // maquinaria de subida de documentos y lo sobrescribiría). Así el mensaje persiste
  // sin depender del orden de inicialización.
  // `message` es el texto específico que se muestra en la leyenda roja cuando
  // falta el archivo. Debe mantener el MISMO patrón ("Adjunte … para finalizar")
  // en las tres evidencias para que credencial/comprobante coincidan con la foto
  // del paciente (Issue: mensajes de evidencia consistentes, no genéricos).
  const EVIDENCE_TARGETS = {
    credencial_url: {
      page: "socioeconomico",
      container: "#credencial-file",
      legend: "#credencial-error",
      message: "Adjunte la credencial (INE) para finalizar",
    },
    comprobante_domicilio_url: {
      page: "socioeconomico",
      container: "#comprobante-domicilio-file",
      legend: "#comprobante-domicilio-error",
      message: "Adjunte el comprobante de domicilio para finalizar",
    },
    foto_url: {
      page: "tecnica",
      container: "[data-purpose='patient-photo-upload']",
      legend: "#photo-error",
      message: "Adjunte la fotografía del paciente para finalizar",
    },
  };

  // Campos del formulario "estudio" que en realidad se capturan en gestion.html.
  const _ESTUDIO_GESTION_FIELDS = new Set([
    "fecha_estudio",
    "tuvo_silla_previa",
    "como_obtuvo_silla",
  ]);

  // form → página destino por defecto.
  const _FORM_PAGE = {
    beneficiario: "socioeconomico",
    estudio: "socioeconomico",
    socioeconomico: "socioeconomico",
    tutor1: "socioeconomico",
    tutor2: "socioeconomico",
    solicitud: "tecnica",
    tecnica: "tecnica",
    gestion: "gestion",
  };

  // Traducciones puntuales de nombre backend → name del input frontend.
  const _FIELD_NAME_OVERRIDES = {
    curp_benef: "curp",
    imss_estatus: "imss",
    infonavit_estatus: "infonavit",
    tuvo_silla_previa: "silla_previa",
  };

  // Campos cuyo formulario backend no coincide con la página donde vive el input.
  // `diagnostico` viaja en el formulario "beneficiario" pero se captura en la
  // vista Técnica, no en Socioeconómico.
  const _FIELD_PAGE_OVERRIDES = {
    diagnostico: "tecnica",
  };

  /**
   * Resuelve un error {form, field} al objetivo de resaltado en el frontend.
   * Devuelve {page, kind, name?, container?, legend?, field, form} o null.
   */
  function resolveFieldTarget(form, field) {
    if (!field) return null;

    // Evidencias (archivos)
    const evidence = EVIDENCE_TARGETS[field];
    if (evidence) {
      return {
        page: evidence.page,
        kind: "evidencia",
        container: evidence.container,
        legend: evidence.legend,
        message: evidence.message,
        field,
        form,
      };
    }

    // Página destino
    let page = _FORM_PAGE[form] || "socioeconomico";
    if (form === "estudio" && _ESTUDIO_GESTION_FIELDS.has(field)) {
      page = "gestion";
    }
    if (_FIELD_PAGE_OVERRIDES[field]) {
      page = _FIELD_PAGE_OVERRIDES[field];
    }

    // `numero_tutor` es la señal que emite el backend cuando el tutor completo
    // falta (no existe la fila): NO hay un input `tutorN_numero_tutor`, así que
    // apuntamos al primer campo real del bloque (`tutorN_nombres`) para que el
    // resaltado y el scroll lleven al usuario a completar ese tutor.
    const baseField = field === "numero_tutor" ? "nombres" : field;

    // name del input: overrides puntuales + prefijo de tutor
    let name = _FIELD_NAME_OVERRIDES[baseField] || baseField;
    if (form === "tutor1") name = `tutor1_${name}`;
    else if (form === "tutor2") name = `tutor2_${name}`;

    return { page, kind: "text", name, field, form };
  }

  /**
   * Persiste entradas de error YA resueltas en sessionStorage, agrupadas por
   * `page`. Cada entrada: {page, kind:'text'|'evidencia', message,
   * name? (text) | container?/legend? (evidencia)}. Se invoca justo antes de
   * redirigir con "Ir al formulario".
   */
  function persistStashEntries(entries) {
    if (!Array.isArray(entries) || entries.length === 0) return;
    let stash = {};
    try {
      stash = JSON.parse(sessionStorage.getItem(FIELD_ERROR_STASH_KEY) || "{}");
      if (!stash || typeof stash !== "object") stash = {};
    } catch (_e) {
      stash = {};
    }

    for (const entry of entries) {
      if (!entry || !entry.page) continue;
      const dupKey = entry.name || entry.container;
      if (!dupKey) continue;
      const stored =
        entry.kind === "evidencia"
          ? { kind: "evidencia", container: entry.container, legend: entry.legend, message: entry.message }
          : { kind: "text", name: entry.name, message: entry.message };
      stash[entry.page] = stash[entry.page] || [];
      if (!stash[entry.page].some((e) => (e.name || e.container) === dupKey)) {
        stash[entry.page].push(stored);
      }
    }

    try {
      sessionStorage.setItem(FIELD_ERROR_STASH_KEY, JSON.stringify(stash));
    } catch (_e) {
      /* sessionStorage no disponible: se degrada silenciosamente */
    }
  }

  /**
   * Persiste errores en forma backend {form, field, message}, traduciéndolos
   * a objetivos del frontend vía resolveFieldTarget.
   */
  function stashFieldErrors(items) {
    if (!Array.isArray(items) || items.length === 0) return;
    const entries = [];
    for (const item of items) {
      const target = resolveFieldTarget(item.form, item.field);
      if (!target) continue;
      const message =
        item.message || `${getFieldLabel(item.field)} es obligatorio`;
      entries.push({ ...target, message });
    }
    persistStashEntries(entries);
  }

  /**
   * Resalta una zona de subida de evidencia (archivo) reutilizando el estilo
   * visual de showFieldError y escribiendo la leyenda en el <p> asociado.
   */
  function showEvidenceError(containerSelector, legendSelector, message) {
    const container = containerSelector
      ? document.querySelector(containerSelector)
      : null;
    const legend = legendSelector
      ? document.querySelector(legendSelector)
      : null;
    if (container) {
      container.classList.add("ring-1", "ring-red-400", "rounded-lg");
      container.setAttribute("aria-invalid", "true");
    }
    if (legend) {
      legend.textContent = message;
      legend.classList.remove("hidden");
      legend.classList.add("text-red-600");
    }
  }

  function clearEvidenceError(containerSelector, legendSelector) {
    const container = containerSelector
      ? document.querySelector(containerSelector)
      : null;
    const legend = legendSelector
      ? document.querySelector(legendSelector)
      : null;
    if (container) {
      container.classList.remove("ring-1", "ring-red-400");
      container.removeAttribute("aria-invalid");
    }
    if (legend) {
      legend.textContent = "";
      legend.classList.add("hidden");
      legend.classList.remove("text-red-600");
    }
  }

  /**
   * Consume (una sola vez) los errores persistidos para `pageName`, los aplica
   * con showFieldError / showEvidenceError, y hace scroll + focus al primero.
   * Debe llamarse tras el prefill/resume de la página destino.
   */
  function applyStashedFieldErrors(pageName) {
    let stash = {};
    try {
      stash = JSON.parse(sessionStorage.getItem(FIELD_ERROR_STASH_KEY) || "{}");
    } catch (_e) {
      stash = {};
    }
    const entries = stash && stash[pageName];

    // Consumo único: eliminar el estado del destino antes de aplicar.
    if (stash && Object.prototype.hasOwnProperty.call(stash, pageName)) {
      delete stash[pageName];
      try {
        if (Object.keys(stash).length === 0) {
          sessionStorage.removeItem(FIELD_ERROR_STASH_KEY);
        } else {
          sessionStorage.setItem(FIELD_ERROR_STASH_KEY, JSON.stringify(stash));
        }
      } catch (_e) {
        /* noop */
      }
    }

    if (!Array.isArray(entries) || entries.length === 0) return;

    let firstEl = null;
    for (const entry of entries) {
      if (entry.kind === "evidencia") {
        showEvidenceError(entry.container, entry.legend, entry.message);
        if (!firstEl && entry.container) {
          firstEl = document.querySelector(entry.container);
        }
      } else if (entry.name) {
        showFieldError(entry.name, entry.message);
        if (!firstEl) {
          firstEl = document.querySelector(`[name="${entry.name}"]`);
        }
      }
    }

    if (firstEl) {
      if (typeof firstEl.scrollIntoView === "function") {
        try {
          firstEl.scrollIntoView({ behavior: "smooth", block: "center" });
        } catch (_e) {
          try { firstEl.scrollIntoView(); } catch (_e2) { /* noop */ }
        }
      }
      // focus tras el scroll; los inputs de archivo/contenedores pueden no
      // ser enfocables, se ignora el error.
      setTimeout(() => {
        try {
          firstEl.focus({ preventScroll: true });
        } catch (_e) {
          /* no enfocable */
        }
      }, 300);
    }
  }

  function clearStashedFieldErrors() {
    try {
      sessionStorage.removeItem(FIELD_ERROR_STASH_KEY);
    } catch (_e) {
      /* noop */
    }
  }

  // ─────────────────────────────────────────────────────────────────
  // Formateo de errores backend
  // ─────────────────────────────────────────────────────────────────

  function formatBackendError(errData, fallback) {
    const _fallback = fallback || "Error desconocido";
    if (!errData) return _fallback;

    if (typeof errData.detail === "string" && errData.detail.trim()) {
      return errData.detail;
    }

    if (Array.isArray(errData.detail) && errData.detail.length > 0) {
      const msgs = errData.detail
        .map((d) => {
          const path = Array.isArray(d?.loc) ? d.loc.slice(1).join(".") : null;
          const label = path ? getBackendPathLabel(path) : "Campo";
          const msg = d?.msg || "valor inválido";
          return `${label}: ${msg}`;
        })
        .filter(Boolean);
      if (msgs.length > 0) return msgs.join(" | ");
    }

    return _fallback;
  }

  // ─────────────────────────────────────────────────────────────────
  // Utilidades de formateo
  // ─────────────────────────────────────────────────────────────────

  function sanitizeMoneyInput(raw) {
    if (raw == null) return "";
    const cleaned = String(raw)
      .replace(/,/g, "")
      .replace(/[^\d.]/g, "");
    const firstDot = cleaned.indexOf(".");
    if (firstDot === -1) return cleaned;
    const intPart = cleaned.slice(0, firstDot);
    const decPart = cleaned.slice(firstDot + 1).replace(/\./g, "");
    return `${intPart}.${decPart}`;
  }

  function formatMoneyDisplay(raw) {
    const sanitized = sanitizeMoneyInput(raw);
    if (!sanitized) return "";
    const [intPart, decPart] = sanitized.split(".");
    const formattedInteger = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    return decPart != null ? `${formattedInteger}.${decPart}` : formattedInteger;
  }

  function toMoneyNumberOrNull(raw) {
    const sanitized = sanitizeMoneyInput(raw);
    if (!sanitized || sanitized === ".") return null;
    const num = Number(sanitized);
    return Number.isFinite(num) ? num : null;
  }

  function sanitizeIntegerInput(raw, maxDigits) {
    if (raw == null) return "";
    let cleaned = String(raw).replace(/,/g, "").replace(/\D/g, "");
    if (maxDigits != null && cleaned.length > maxDigits) {
      cleaned = cleaned.slice(0, maxDigits);
    }
    return cleaned;
  }

  function formatIntegerDisplay(raw, maxDigits) {
    const sanitized = sanitizeIntegerInput(raw, maxDigits);
    if (!sanitized) return "";
    return sanitized.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }

  function toIntegerOrNull(raw) {
    const sanitized = sanitizeIntegerInput(raw);
    if (!sanitized) return null;
    const num = Number(sanitized);
    return Number.isFinite(num) ? num : null;
  }

  /**
   * Habilita/deshabilita un campo con estilos visuales consistentes.
   */
  function setFieldDisabled(el, disabled) {
    if (!el) return;
    const disabledClasses = ["bg-slate-100", "text-slate-400", "cursor-not-allowed"];
    if (disabled) {
      el.disabled = true;
      disabledClasses.forEach(c => el.classList.add(c));
    } else {
      el.disabled = false;
      disabledClasses.forEach(c => el.classList.remove(c));
    }
  }

  // ─────────────────────────────────────────────────────────────────
  // Auto-uppercase: free-text inputs and textareas are uppercased as
  // the user types, mirroring the backend's normalize_text so data is
  // stored and displayed in a single canonical format.
  // Opt out per field with the data-no-uppercase attribute.
  // ─────────────────────────────────────────────────────────────────

  // Allowlist: only free-text controls. Radios/checkboxes are HTMLInputElements
  // too and fire "input" on selection — uppercasing their value would corrupt
  // catalog payloads (e.g. prioridad "Alta" -> "ALTA").
  const UPPERCASE_ALLOWED_TYPES = new Set(["text"]);
  const UPPERCASE_EXCLUDED_NAME_RE = /(email|password|contrasena|search|buscar)/i;

  function shouldAutoUppercase(el) {
    const isInput = el instanceof HTMLInputElement;
    const isTextarea = el instanceof HTMLTextAreaElement;
    if (!isInput && !isTextarea) return false;
    if (el.dataset && el.dataset.noUppercase !== undefined) return false;
    if (isInput && !UPPERCASE_ALLOWED_TYPES.has((el.type || "text").toLowerCase())) return false;
    if (UPPERCASE_EXCLUDED_NAME_RE.test(el.name || el.id || "")) return false;
    return true;
  }

  document.addEventListener("input", (event) => {
    const el = event.target;
    if (!shouldAutoUppercase(el)) return;
    const upper = el.value.toUpperCase();
    if (upper === el.value) return;
    const start = el.selectionStart;
    const end = el.selectionEnd;
    el.value = upper;
    if (start != null && end != null) {
      try {
        el.setSelectionRange(start, end);
      } catch (_err) {
        // Some input types do not support selection ranges
      }
    }
  });

  // ─────────────────────────────────────────────────────────────────
  // Export
  // ─────────────────────────────────────────────────────────────────

  global.SR_Validations = {
    // Regex
    NOMBRE_RE,
    DIAGNOSTICO_RE,
    CALLE_RE,
    COLONIA_RE,
    NUM_DOMICILIO_RE,
    TELEFONO_RE,
    CURP_RE,
    EMAIL_RE,
    OBS_WHITELIST_RE,
    ENTIDAD_WHITELIST_RE,
    MEASURE_PARTIAL_RE,
    MEASURE_FINAL_RE,

    // Límites
    LIMITS,

    // Catálogos
    ENTORNO_OPTIONS,
    CONTROL_TRONCO_OPTIONS,
    CONTROL_CABEZA_OPTIONS,
    CONTROL_PIERNAS_OPTIONS,
    PRIORIDAD_OPTIONS,
    COMO_OBTUVO_OPTIONS,
    SEX_OPTIONS,
    UNIDAD_MEDIDA_OPTIONS,
    STATUS_OPTIONS,

    // Funciones
    filterText,
    filterPaste,
    blockBeforeInput,
    catchIME,
    setupWhitelistField,
    setupMeasureField,
    setupNameField,
    setupTelefonoField,
    setupMoneyField,
    setupMoneyFieldWithFormatting,
    setupEmailField,
    setupIntegerField,
    setupTextField,
    setupCurpField,
    curpDigitoVerificador,
    isValidCurp,
    validateRequired,
    validateHTML5Constraints,
    showFieldError,
    clearFieldError,
    setupLiveRequired,
    clearAllFieldErrors,
    pageFromUrl,
    resolveFieldTarget,
    persistStashEntries,
    stashFieldErrors,
    applyStashedFieldErrors,
    clearStashedFieldErrors,
    showEvidenceError,
    clearEvidenceError,
    formatBackendError,
    FIELD_LABELS,
    getFieldLabel,
    getBackendPathLabel,
    sanitizeMoneyInput,
    formatMoneyDisplay,
    toMoneyNumberOrNull,
    sanitizeIntegerInput,
    formatIntegerDisplay,
    toIntegerOrNull,
    setFieldDisabled,
  };
})(window);
