# Issue: Errores de campo obligatorio no desaparecen para radio buttons, selects y checkboxes

## Pre-flight Checks
- [x] He buscado issues duplicados y este no es uno
- [x] Entiendo que este issue necesita aprobación antes de abrir un PR

## Descripción del Bug

Cuando un campo obligatorio de tipo **texto** (`<input type="text">`, `<textarea>`) se deja vacío y pierde el foco, aparece el mensaje "Este campo es obligatorio". Al escribir algo, el mensaje desaparece automáticamente.

Sin embargo, para **radio buttons**, **selects** y **checkboxes**, el mensaje de error aparece al validar el formulario, pero **no desaparece** cuando el usuario selecciona una opción. El error persiste visualmente hasta que se navega fuera del formulario o se recarga la página.

## Causa Raíz

La función `setupLiveRequired` en `front/assets/js/validations.js` (línea 691-710) **excluye explícitamente** radio buttons, checkboxes y selects:

```javascript
const fields = formEl.querySelectorAll(
  'input:not([type="radio"]):not([type="checkbox"]):not([type="hidden"]):not([type="file"]), textarea'
);
```

Los listeners `blur` e `input` solo se aplican a campos de texto. No hay un listener de evento `change` para radio buttons, selects o checkboxes que llame a `clearFieldError()`.

## Excepciones Parciales (limpieza manual puntual)

Algunos campos tienen limpieza manual hardcodeada, pero son la excepción, no la regla:

| Campo | Archivo | Línea | Mecanismo |
|-------|---------|-------|-----------|
| `como_obtuvo_silla` | gestion.html | 406 | `clearFieldError()` en listener de `silla_previa` |
| `justificacion` | gestion.html | 428 | `clearFieldError()` en listener de `tiene_justificacion` |
| `padecimiento` | tecnica.html | 1233 | `clearFieldError()` en listener de checkboxes |

## Campos Afectados

### Radio buttons obligatorios (error NO desaparece al seleccionar)

| Campo | Formulario | Archivo |
|-------|-----------|---------|
| `sexo` | Socioeconómico | socioeconomico.html:261 |
| `tutor1_imss` | Socioeconómico | socioeconomico.html:516 |
| `tutor1_infonavit` | Socioeconómico | socioeconomico.html:528 |
| `tutor2_imss` | Socioeconómico | socioeconomico.html:771 |
| `tutor2_infonavit` | Socioeconómico | socioeconomico.html:783 |
| `soporte_oxigeno` | Técnica | tecnica.html:258 |
| `prioridad` | Gestión | gestion.html:207 |

### Selects obligatorios (error NO desaparece al seleccionar)

| Campo | Formulario | Archivo |
|-------|-----------|---------|
| `estado_codigo` | Socioeconómico | socioeconomico.html:240 |
| `ciudad` | Socioeconómico | socioeconomico.html:245 |
| `tutor1_nivel_estudios` | Socioeconómico | socioeconomico.html:377 |
| `tutor1_estado_civil` | Socioeconómico | socioeconomico.html:401 |
| `tutor1_vivienda` | Socioeconómico | socioeconomico.html:435 |
| `tutor1_fuente_empleo` | Socioeconómico | socioeconomico.html:465 |
| `tutor2_nivel_estudios` | Socioeconómico | socioeconomico.html:636 |
| `tutor2_estado_civil` | Socioeconómico | socioeconomico.html:659 |
| `tutor2_vivienda` | Socioeconómico | socioeconomico.html:691 |
| `tutor2_fuente_empleo` | Socioeconómico | socioeconomico.html:720 |
| `equipo_solicitado` | Técnica | tecnica.html:111 |
| `entorno` | Técnica | tecnica.html:121 |
| `control_tronco` | Técnica | tecnica.html:167 |
| `control_cabeza` | Técnica | tecnica.html:184 |
| `control_de_piernas` | Técnica | tecnica.html:200 |
| `unidad_medida` | Técnica | tecnica.html:282 |
| `silla_previa` | Gestión | gestion.html:109 |
| `como_obtuvo_silla` | Gestión | gestion.html:120 |
| `entidad_solicitante` | Gestión | gestion.html:196 |

### Checkboxes/toggles (comportamiento variable)

Los checkboxes de toggle (`tiene_num_interior`, `agregar_tutor2`, `sin_empleo`, etc.) no son obligatorios per se, pero algunos campos dependientes sí lo son. La limpieza del error del campo dependiente debería ocurrir cuando se selecciona el toggle.

## Comportamiento Esperado

Al igual que con los campos de texto:
1. Cuando el usuario selecciona un radio button, select o checkbox obligatorio, el mensaje de error debe desaparecer inmediatamente.
2. El borde rojo (`ring-red-400`) debe removerse.
3. El atributo `aria-invalid` debe actualizarse.

## Comportamiento Actual

- Para campos de texto: el error desaparece al escribir ✅
- Para radio buttons: el error persiste después de seleccionar ❌
- Para selects: el error persiste después de seleccionar ❌
- Para checkboxes obligatorios: el error persiste después de marcar ❌

## Solución Sugerida

Ampliar `setupLiveRequired` para incluir listeners de evento `change` en radio buttons, selects y checkboxes:

```javascript
// Para radio buttons: listener en cada input del grupo
formEl.querySelectorAll('input[type="radio"]').forEach((radio) => {
  radio.addEventListener("change", () => {
    clearFieldError(radio.name);
  });
});

// Para selects: listener en cada select
formEl.querySelectorAll("select").forEach((select) => {
  select.addEventListener("change", () => {
    if (select.value) clearFieldError(select.name);
  });
});

// Para checkboxes obligatorios: listener en cada checkbox
formEl.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
  cb.addEventListener("change", () => {
    clearFieldError(cb.name);
  });
});
```

Alternativamente, se puede usar delegación de eventos en el formulario:

```javascript
formEl.addEventListener("change", (e) => {
  const el = e.target;
  if (el.name) clearFieldError(el.name);
});
```

## Archivos Afectados

- `front/assets/js/validations.js` — función `setupLiveRequired` (línea 691-710)

## Severidad

**Media** — El bug no bloquea la funcionalidad (el formulario se envía correctamente), pero genera confusión visual para el capturista, que ve un error persistente aunque ya corrigió el campo.

## Criterios de Aceptación

- [ ] Al seleccionar un radio button obligatorio, el mensaje de error desaparece inmediatamente.
- [ ] Al seleccionar una opción en un select obligatorio, el mensaje de error desaparece inmediatamente.
- [ ] Al marcar un checkbox obligatorio, el mensaje de error desaparece inmediatamente.
- [ ] El borde rojo (`ring-red-400`) se remueve del campo.
- [ ] El atributo `aria-invalid` se actualiza correctamente.
- [ ] El comportamiento existente para campos de texto no se ve afectado.
- [ ] La solución funciona en los 3 formularios (socioeconómico, técnica, gestión).
