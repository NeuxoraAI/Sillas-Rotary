# Reglas de Validación — Contrato Frontend/Backend

> **Fuente de verdad:** `backend/validators.py`  
> **Espejo frontend:** `front/assets/js/validations.js`

Este documento define TODAS las reglas de validación del sistema. Cualquier cambio debe reflejarse en ambos lados (backend primero, frontend después).

---

## Catálogos

| Campo | Valores permitidos | Obligatorio (completo) |
|---|---|---|
| `sexo` | M, F, NE | Sí |
| `estado_civil` | SOLTERO, CASADO, VIUDO, DIVORCIADO, UNION_LIBRE | No |
| `vivienda` | PROPIA, RENTADA, PRESTADA, FAMILIAR, INFORMAL, OTRA | No |
| `nivel_estudios` | NINGUNO, PRIMARIA, SECUNDARIA, BACHILLERATO, LICENCIATURA, MAESTRIA, DOCTORADO, TECNICO | No |
| `como_obtuvo_silla` | COMPRA, DONACION | Condicional* |
| `entorno` | Urbano / Interiores, Rural / Terreno irregular, Mixto | Sí |
| `control_tronco` | Completo, Parcial / Requiere apoyo lateral, Nulo / Requiere soporte total | Sí |
| `control_cabeza` | Independiente, No posee / Requiere cabezal | Sí |
| `prioridad` | Alta, Media | No |
| `unidad_medida` | in, cm | Sí |
| `status` | borrador, completo | Sí |
| `imss_estatus` / `infonavit_estatus` | SI, NO | Sí (para Tutor 1) |

*Condicional: obligatorio cuando `tuvo_silla_previa = true`.

---

## Regex

| Campo | Regex Backend | Regex Frontend | Coinciden |
|---|---|---|---|
| `nombres` | `^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ. ]+$` | idéntica | ✅ |
| `apellido_paterno` / `materno` | `^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ. ]+$` | idéntica | ✅ |
| `diagnostico` | `^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9\s\-().\/,]+$` | idéntica | ✅ |
| `calle` | `^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9.\- ]+$` | idéntica | ✅ |
| `colonia` | `^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9.\- ]+$` | idéntica | ✅ |
| `num_ext` / `num_int` | `^[A-Z0-9\-/]+$` (post-normalize) | `^[A-Za-z0-9\-/]+$` | ✅* |
| `telefonos` | `^[0-9]{10}$` | idéntica | ✅ |
| `observaciones_posturales` | `^[a-zA-ZáéíóúÁÉÍÓÚäëïöüÄËÏÖÜñÑ0-9 ()\/\-.,:;]*$` | idéntica | ✅ |
| `justificacion` | `^[a-zA-ZáéíóúÁÉÍÓÚäëïöüÄËÏÖÜñÑ0-9 ()\/\-.,:;]*$` | idéntica | ✅ |
| `entidad_solicitante` | `^[a-zA-ZáéíóúÁÉÍÓÚäëïöüÄËÏÖÜñÑ0-9 ()\/\-.,]*$` | idéntica | ✅ |
| `medida_*` | `^[0-9]+(\.[0-9]{1,3})?$` | idéntica | ✅ |

*Nota: El frontend permite minúsculas porque el backend normaliza a mayúsculas antes de validar.

---

## Límites de longitud / rango

| Campo | Mín | Máx | Tipo |
|---|---|---|---|
| `nombres` | 2 | 60 | longitud |
| `apellido_paterno` / `materno` | 2 | 40 | longitud |
| `diagnostico` | 3 | 160 | longitud |
| `calle` | 3 | 120 | longitud |
| `colonia` | 2 | 120 | longitud |
| `ciudad` | 2 | 80 | longitud |
| `num_ext` / `num_int` | 1 | 10 | longitud |
| `telefonos` | 10 | 10 | dígitos exactos |
| `observaciones_posturales` | 0 | 500 | longitud |
| `justificacion` | 0 | 500 | longitud |
| `entidad_solicitante` | 0 | 64 | longitud |
| `fuente_empleo` | 0 | 80 | longitud |
| `otras_fuentes_ingreso` | 0 | 100 | longitud |
| `ingreso_mensual` | 0 | 9,999,999 | entero |
| `monto_otras_fuentes` | 0 | 999,999 | decimal |
| `num_hijos` | 0 | 30 | entero |
| `edad` | 0 | 99 | entero |
| `antiguedad_anios` | 0 | 50 | entero |
| `antiguedad_meses_extra` | 0 | 11 | entero |
| `medida_*` (enteros) | 1 | 4 | dígitos enteros |
| `medida_*` (decimales) | 0 | 3 | dígitos decimales |

---

## Normalización

| Campo | Normalización | Notas |
|---|---|---|
| `nombres`, `apellidos` | MAYÚSCULAS, sin acentos, espacios colapsados | `normalize_text()` |
| `diagnostico`, `calle`, `colonia` | MAYÚSCULAS, sin acentos, espacios colapsados | `normalize_text()` |
| `observaciones_posturales` | Sin normalización | Preserva mayúsculas/minúsculas y acentos |
| `justificacion` | Sin normalización | Preserva mayúsculas/minúsculas y acentos |
| `entidad_solicitante` | Sin normalización | Preserva mayúsculas/minúsculas y acentos |
| `telefonos` | Solo dígitos | Strip de todo excepto 0-9 |
| `num_ext` / `num_int` | MAYÚSCULAS, sin acentos | `normalize_text()` antes de regex |

---

## Obligatoriedad por formulario

### socioeconomico.html (status=completo)

| Campo | Obligatorio | Frontend `required` |
|---|---|---|
| `nombres` | Sí | Sí |
| `apellido_paterno` | Sí | Sí |
| `apellido_materno` | Sí | Sí |
| `fecha_nacimiento` | Sí | Sí |
| `diagnostico` | Sí | Sí |
| `calle` | Sí | Sí |
| `num_ext` | Opcional | — |
| `colonia` | Sí | Sí |
| `ciudad` | Sí | Sí |
| `estado_codigo` | Sí | Sí |
| `sexo` | Sí | Sí |
| `telefonos` | Sí | **Sí** (corregido) |
| `tutor1_nombres` | Sí | Sí |
| `tutor1_apellido_paterno` | Sí | Sí |
| `tutor1_apellido_materno` | Sí | Sí |
| `tutor1_edad` | Sí | Sí |
| `tutor1_nivel_estudios` | Sí | Sí |
| `tutor1_estado_civil` | Sí | Sí |
| `tutor1_num_hijos` | Sí | Sí |
| `tutor1_vivienda` | Sí | Sí |
| `tutor1_imss` | Sí | Sí |
| `tutor1_infonavit` | Sí | Sí |
| `tutor1_fuente_empleo` | Condicional | Obligatorio cuando `sin_empleo = false` |
| `tutor1_ingreso_mensual` | Condicional | Obligatorio cuando `sin_empleo = false` |
| `tutor1_antiguedad_anios` | Condicional | Obligatorio cuando `sin_empleo = false` AND `antiguedad_aplica = true` |
| `tutor1_antiguedad_meses_extra` | Condicional | Obligatorio cuando `sin_empleo = false` AND `antiguedad_aplica = true` |
| `tutor1_otras_fuentes_ingreso` | Condicional | Obligatorio cuando `otras_fuentes_aplica = true` |
| `tutor1_monto_otras_fuentes` | Condicional | Obligatorio cuando `otras_fuentes_aplica = true` |
| `num_int` | Condicional | Dinámico (checkbox `tiene_num_interior`) | Obligatorio solo si checkbox marcado |
| `tutor2_nombres` | Condicional | `required` (dinámico) | Solo si "Agregar segundo tutor" marcado |
| `tutor2_apellido_paterno` | Condicional | `required` (dinámico) | Solo si "Agregar segundo tutor" marcado |
| `tutor2_apellido_materno` | Condicional | `required` (dinámico) | Solo si "Agregar segundo tutor" marcado |
| `tutor2_edad` | Condicional | `required` (dinámico) | Solo si "Agregar segundo tutor" marcado |
| `tutor2_nivel_estudios` | Condicional | `required` (dinámico) | Solo si "Agregar segundo tutor" marcado |
| `tutor2_estado_civil` | Condicional | `required` (dinámico) | Solo si "Agregar segundo tutor" marcado |
| `tutor2_num_hijos` | Condicional | `required` (dinámico) | Solo si "Agregar segundo tutor" marcado |
| `tutor2_vivienda` | Condicional | `required` (dinámico) | Solo si "Agregar segundo tutor" marcado |
| `tutor2_imss` | Condicional | `required` (dinámico) | Solo si "Agregar segundo tutor" marcado |
| `tutor2_infonavit` | Condicional | `required` (dinámico) | Solo si "Agregar segundo tutor" marcado |

### tecnica.html (status=completo)

| Campo | Obligatorio | Nota |
|---|---|---|
| `altura_total_in` | Sí | `required` + `field-error` |
| `peso_kg` | Sí | `required` + `field-error` |
| `medida_cabeza_asiento` | Sí | `required` + `field-error` |
| `medida_hombro_asiento` | Sí | `required` + `field-error` |
| `medida_prof_asiento` | Sí | `required` + `field-error` |
| `medida_rodilla_talon` | Sí | `required` + `field-error` |
| `medida_ancho_cadera` | Sí | `required` + `field-error` |
| `entorno` | Sí | `required` en select |
| `control_tronco` | Sí | `required` en select |
| `control_cabeza` | Sí | `required` en select |
| `observaciones_posturales` | No | Checkbox toggle "Agregar observaciones posturales" |

### gestion.html (status=completo)

| Campo | Obligatorio | Nota |
|---|---|---|
| `silla_previa` | Sí | `required` en select, placeholder "Selecciona una opción" |
| `como_obtuvo_silla` | Condicional | Solo si `silla_previa = "Sí"` |
| `fecha_estudio` | Sí | `required` en input |
| `elaboro_estudio` | Sí | Pre-llenado (readonly) |
| `sede` | Sí | Pre-llenado (readonly) |
| `ciudad_registro` | Sí | Pre-llenado (readonly) |
| `entidad_solicitante` | Sí | `required` + `field-error` |
| `prioridad` | Sí | `required` en radio + `field-error` |
| `justificacion` | No | Checkbox toggle "Agregar justificación" |

---

## Campos condicionales

| Campo | Condición | Obligatorio cuando |
|---|---|---|
| `num_int` | Checkbox "Agregar número interior" | Marcado |
| Tutor 2 (todos los campos) | Checkbox "Agregar segundo tutor" | Marcado |
| `fuente_empleo` (Tutor 1 y 2) | `sin_empleo` NO marcado | Empleado |
| `ingreso_mensual` (Tutor 1 y 2) | `sin_empleo` NO marcado | Empleado |
| `antiguedad_anios/meses` (Tutor 1 y 2) | `sin_empleo` NO y `antiguedad_no_aplica` NO | Empleado con antigüedad |
| `otras_fuentes_ingreso` (Tutor 1 y 2) | `otras_fuentes_aplica` SÍ | Con otras fuentes |
| `monto_otras_fuentes` (Tutor 1 y 2) | `otras_fuentes_aplica` SÍ | Con otras fuentes |
| `observaciones_posturales` | Checkbox `tiene_observaciones` | Cuando marcado, habilita textarea |
| `justificacion` | Checkbox `tiene_justificacion` | Cuando marcado, habilita textarea |

---

## Estilo visual de campos deshabilitados

> Los campos `disabled` dinámicamente usan la función `SR_Validations.setFieldDisabled(el, bool)` que agrega/remueve las clases `bg-slate-100 text-slate-400 cursor-not-allowed` junto con el atributo `disabled`. Campos `readonly` permanentes usan `bg-slate-100` en HTML estático.

---

## Bugs corregidos

| # | Bug | Corrección |
|---|---|---|
| 1 | `telefonos` sin `required` en frontend | Agregado `required` + validación JS |
| 2 | Límites monetarios desalineados (frontend 12 dígitos vs backend 7/6) | Sincronizados a `INGRESO_MENSUAL_MAX=9,999,999` y `MONTO_OTRAS_FUENTES_MAX=999,999` |
| 3 | `num_hijos` max=20 frontend vs max=30 backend | Sincronizado a **30** en ambos lados |
| 4 | `\s` en regex JS vs espacio literal en backend | Unificado a **espacio literal** en ambos lados |
| 5 | `entorno`, `control_tronco`, `control_cabeza` sin catálogo backend | Agregados catálogos `frozenset` en `validators.py` |
| 6 | `fecha_nacimiento` sin validación backend | Agregado `validate_fecha_nacimiento()` en `validators.py` |
| 7 | `LoginRequest.email` sin validación de formato | Agregado `validate_email_format()` en `validators.py` |

---

## Cómo agregar un nuevo campo

1. **Backend:** Agregar regex/validador a `backend/validators.py`
2. **Backend:** Usar el validador en el Pydantic model del router correspondiente
3. **Frontend:** Agregar regex/límite a `front/assets/js/validations.js`
4. **Frontend:** Agregar `setup*` function a `validations.js` si es un patrón nuevo
5. **Frontend:** Usar `SR_Validations.setupXxx()` en el HTML del formulario
6. **Documento:** Actualizar esta tabla
7. **Tests:** Agregar tests unitarios en `backend/tests/test_validators.py`
