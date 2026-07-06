# FIXES — Issue #163

**Título:** `docs(validators): documentar reglas de validación para soporte_oxigeno y padecimiento`

**Rama:** `fix-eramirezh-issue162` (resuelto junto con #162)

## Problema

Los campos `soporte_oxigeno` y `padecimiento` no tenían reglas de validación documentadas en `docs/VALIDATION_RULES.md`, lo que dificultaba el mantenimiento y la verificación de consistencia frontend/backend.

## Estado Anterior

| Campo | VALIDATION_RULES.md | validators.py | Backend valida |
|-------|:------------------:|:-------------:|:--------------:|
| `soporte_oxigeno` | ❌ No existía | ❌ No existía | ❌ No validaba |
| `padecimiento` | ❌ No existía | ✅ Existía | ✅ Solo formato |

## Solución Implementada

### 1. `docs/VALIDATION_RULES.md` — Tabla de Catálogos

Agregados dos campos:

```markdown
| `soporte_oxigeno` | true, false | Sí |
| `padecimiento` | Lista separada por comas (máx 500 chars) | No |
```

### 2. `docs/VALIDATION_RULES.md` — Tabla de Regex

Agregado `padecimiento`:

```markdown
| `padecimiento` | `^[a-zA-ZáéíóúÁÉÍÓÚäëïöüÄËÏÖÜñÑ0-9 ()\-/.,:;]*$` | idéntica | ✅ |
```

### 3. `docs/VALIDATION_RULES.md` — Tabla de Límites

Agregado `padecimiento`:

```markdown
| `padecimiento` | 0 | 500 | longitud |
```

### 4. Implementación de `soporte_oxigeno` (Issue #162)

Dado que `soporte_oxigeno` debe ser obligatorio, se implementó la validación completa:

- **Frontend**: Validación en `collectGestionFinalErrors()` (solo al finalizar)
- **Backend**: Validación en `_validate_allComplete()` de `finalizar.py`
- **HTML**: `required aria-describedby` + párrafo de error
- **JS**: Se eliminó la validación del botón "Continuar" para consistencia con otros campos

Ver `FIXES_Issue_162.md` para los detalles de implementación.

## Estado Resultante

| Campo | VALIDATION_RULES.md | validators.py | Frontend valida | Backend valida | Obligatorio |
|-------|:------------------:|:-------------:|:--------------:|:--------------:|:-----------:|
| `soporte_oxigeno` | ✅ Documentado | N/A (booleano) | ✅ Finalizar | ✅ Finalizar | ✅ Sí |
| `padecimiento` | ✅ Documentado | ✅ Formato | ❌ No (opcional) | ❌ No (opcional) | ❌ No |

### Compatibilidad de `soporte_oxigeno` con otros campos

| Flujo | soporte_oxigeno | sexo | prioridad | imss/infonavit |
|-------|:---------------:|:----:|:---------:|:--------------:|
| Guardar borrador | No valida | No valida | No valida | No valida |
| Continuar/Regresar | No valida | No valida | No valida | No valida |
| Finalizar registro | ✅ Valida | ✅ Valida | ✅ Valida | ✅ Valida |

## Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `docs/VALIDATION_RULES.md` | Agregados `soporte_oxigeno` y `padecimiento` en catálogos, regex y límites |

## Criterios de Aceptación

- [x] `soporte_oxigeno` documentado como obligatorio en catálogos
- [x] `padecimiento` documentado como opcional en catálogos
- [x] `padecimiento` documentado en tabla de regex
- [x] `padecimiento` documentado en tabla de límites de longitud
- [x] `soporte_oxigeno` implementado como obligatorio (frontend + backend)
