# FIXES — Issue #162

**Título:** `fix(tecnica): reemplazar alert() de soporte de oxígeno por SR_Validations`

**Rama:** `fix-eramirezh-issue162`

## Problema

El campo `soporte_oxigeno` en el formulario de Técnica usaba un `alert()` nativo del navegador para validación al hacer clic en "Continuar", mientras que todos los demás campos usan `SR_Validations.showFieldError()`. Esto rompía la consistencia UX y creaba un caso particular en el flujo de navegación.

Además, el campo no se validaba como obligatorio al finalizar el registro (ni en frontend ni en backend), a pesar de ser un campo requerido según el modelo de negocio.

## Causa Raíz

| Capa | Problema |
|------|----------|
| HTML (`tecnica.html:258`) | Sin `required`, sin `aria-describedby`, sin párrafo de error |
| JS (`tecnica.html:2884`) | `alert()` en vez de `SR_Validations.showFieldError()` |
| Frontend finalizar | No validaba `soporte_oxigeno` en `collectGestionFinalErrors()` |
| Backend (`finalizar.py`) | No validaba `soporte_oxigeno` en `_validate_all_complete` |

## Solución Implementada

### 1. `front/Capturista-view/tecnica.html` — HTML

**Antes:**
```html
<input ... name="soporte_oxigeno" type="radio" value="true" />
```

**Después:**
```html
<input ... name="soporte_oxigeno" type="radio" value="true" required aria-describedby="soporte_oxigeno-error" />
```

Agregado párrafo de error después del `</fieldset>`:
```html
<p class="field-error hidden text-red-600 text-xs mt-1" id="soporte_oxigeno-error" data-error-for="soporte_oxigeno" role="alert"></p>
```

### 2. `front/Capturista-view/tecnica.html` — JS

Se eliminó la validación de `soporte_oxigeno` del botón "Continuar" para mantener consistencia con otros campos similares (`sexo`, `prioridad`, `imss`, `infonavit`), que NO se validan al navegar entre formularios.

**Antes:**
```javascript
// CONTINUAR button: validate + save to localStorage + navigate
document.getElementById("btn-continuar-tecnica")?.addEventListener("click", () => {
  const soporteOxigeno = document.querySelector('[name="soporte_oxigeno"]:checked');
  if (!soporteOxigeno) {
    alert("Debes indicar si requiere soporte para oxígeno.");
    // ... scroll + return
  }
  continuarSolicitudTecnica();
});
```

**Después:**
```javascript
// CONTINUAR button: validate + save to localStorage + navigate
document.getElementById("btn-continuar-tecnica")?.addEventListener("click", () => {
  continuarSolicitudTecnica();
});
```

La validación de `soporte_oxigeno` como obligatorio ocurre únicamente al finalizar el registro (en `collectGestionFinalErrors()` y `_validate_all_complete`).

### 3. `front/Capturista-view/gestion.html` — Validación en finalizar

Agregado en `collectGestionFinalErrors()` después de la validación de foto_url:

```javascript
// Soporte de oxígeno obligatorio (Issue #162).
if (typeof draftTecnica.soporte_oxigeno !== "boolean") {
  errors.push({ form: "Técnica", label: "Soporte de oxígeno", message: "Este campo es obligatorio", url: "tecnica.html", stashEntry: mkT("tecnica", "soporte_oxigeno", "Este campo es obligatorio") });
}
```

### 4. `backend/routers/finalizar.py` — Validación backend

Agregado en `_validate_all_complete()` después de la validación de foto_url:

```python
# Soporte de oxígeno obligatorio (Issue #162).
if solicitud_row.get("soporte_oxigeno") is None:
    missing.append({"form": "solicitud", "field": "soporte_oxigeno"})
```

## Comportamiento Resultante

| Flujo | Antes | Después |
|-------|-------|---------|
| Guardar borrador | No valida | No valida (correcto) |
| Continuar/Regresar | `alert()` bloquea | No valida (consistente con otros campos) |
| Finalizar registro | No valida | Valida frontend + backend |

## Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `front/Capturista-view/tecnica.html` | HTML: `required aria-describedby` + párrafo error. JS: `showFieldError()` |
| `front/Capturista-view/gestion.html` | Validación `soporte_oxigeno` en `collectGestionFinalErrors()` |
| `backend/routers/finalizar.py` | Validación `soporte_oxigeno` en `_validate_all_complete` |

## Criterios de Aceptación

- [x] Se eliminó el `alert()` del botón "Continuar"
- [x] El campo tiene `required` y `aria-describedby` en el HTML
- [x] Existe párrafo de error `soporte_oxigeno-error`
- [x] El campo se valida como obligatorio al finalizar el registro (frontend)
- [x] El campo se valida como obligatorio al finalizar el registro (backend)
- [x] El guardado de borrador NO valida este campo (opcional en borrador)
- [x] El botón "Continuar" NO valida este campo (consistente con otros campos)
- [x] El comportamiento es consistente con otros radio buttons (`sexo`, `prioridad`)
