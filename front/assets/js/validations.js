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
  const PRIORIDAD_OPTIONS = ["Alta", "Media"];
  const COMO_OBTUVO_OPTIONS = ["COMPRA", "DONACION"];
  const SEX_OPTIONS = ["M", "F"];
  const UNIDAD_MEDIDA_OPTIONS = ["in", "cm"];
  const STATUS_OPTIONS = ["borrador", "completo"];

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
          const path = Array.isArray(d?.loc) ? d.loc.slice(1).join(".") : "campo";
          const msg = d?.msg || "valor inválido";
          return `${path}: ${msg}`;
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
    validateRequired,
    validateHTML5Constraints,
    showFieldError,
    clearFieldError,
    clearAllFieldErrors,
    formatBackendError,
    sanitizeMoneyInput,
    formatMoneyDisplay,
    toMoneyNumberOrNull,
    sanitizeIntegerInput,
    formatIntegerDisplay,
    toIntegerOrNull,
    setFieldDisabled,
  };
})(window);
