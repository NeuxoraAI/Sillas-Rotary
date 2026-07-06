# FIXES — Issue #164

**Título:** `fix(frontend): unificar idioma de interfaz a español neutro (usted)`

**Rama:** `fix-eramirezh-issue164`

## Problema

La interfaz mezclaba 3 registros de español distintos:

| Registro | Ocurrencias | Archivos afectados |
|----------|:-----------:|-------------------|
| **Usted** (formal) | 52 | login, seleccion-region, admin-* (correcto) |
| **Voseo** (argentino) | 12 | socioeconomico, tecnica, gestion, reset-password |
| **Tú** (informal) | 4 | admin-beneficiarios, socioeconomico |

## Solución Implementada

### Correcciones de Voseo → Usted (12 casos)

| Archivo | Línea | Antes | Después |
|---------|-------|-------|---------|
| `gestion.html` | 568-569 | "Revisá el formato... Podés guardar... corregí" | "Revise el formato... Puede guardar... corrija" |
| `gestion.html` | 742 | "revisá el formato... Corregila" | "revise el formato... Corríjala" |
| `gestion.html` | 1087 | "Corregí estos puntos y volvé a intentar" | "Corrija estos puntos y vuelva a intentar" |
| `gestion.html` | 1137 | "Andá al formulario... corregí la CURP" | "Vaya al formulario... corrija la CURP" |
| `gestion.html` | 1212 | "Andá al formulario... completalos" | "Vaya al formulario... complételos" |
| `socioeconomico.html` | 926 | "Acomodá el documento... tomá la foto" | "Acomode el documento... tome la foto" |
| `socioeconomico.html` | 2553-2554 | "Revisá el formato... Podés guardar... corregí" | "Revise el formato... Puede guardar... corrija" |
| `socioeconomico.html` | 3220 | "Revisá tu conexión e intentá de nuevo" | "Revise su conexión e intente de nuevo" |
| `tecnica.html` | 693 | "Acomodá al paciente... tomá la foto" | "Acomode al paciente... tome la foto" |
| `tecnica.html` | 2155 | "Revisá tu conexión e intentá de nuevo" | "Revise su conexión e intente de nuevo" |
| `tecnica.html` | 2206-2207 | "Revisá el formato... Podés guardar... corregí" | "Revise el formato... Puede guardar... corrija" |
| `reset-password.html` | 77 | "Ya podés iniciar sesión" | "Ya puede iniciar sesión" |

### Correcciones de Tú → Usted (4 casos)

| Archivo | Línea | Antes | Después |
|---------|-------|-------|---------|
| `admin-beneficiarios.html` | 381 | "Tienes cambios pendientes" | "Tiene cambios pendientes" |
| `admin-beneficiarios.html` | 383 | "Si cierras ahora, perderás" | "Si cierra ahora, perderá" |
| `admin-beneficiarios.html` | 422 | "Podrás volver a agregar" | "Podrá volver a agregar" |
| `socioeconomico.html` | 4033 | "No tienes permisos" | "No tiene permisos" |

## Documentación Creada

### `docs/LANGUAGE_STYLE_GUIDE.md`

Guía de estilo de idioma para prevenir futuros traslapes. Incluye:

1. **Registro oficial**: Español neutro latinoamericano con usted formal
2. **Tabla de conjugaciones**: Verbos comunes en voseo/tú vs usted
3. **Pronombres y posesivos**: tu→su, tus→sus
4. **Imperativos**: Formas correctas de usted
5. **Excepciones permitidas**: Textos de sistema, códigos, logs
6. **Checklist para nuevos textos**: Verificación antes de agregar UI
7. **Ejemplos en contexto**: Mensajes de error, éxito, confirmación, instrucciones
8. **Archivos de interfaz**: Lista de archivos que contienen UI text

## Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `front/Capturista-view/gestion.html` | 5 correcciones de voseo |
| `front/Capturista-view/socioeconomico.html` | 3 voseo + 1 tú |
| `front/Capturista-view/tecnica.html` | 3 correcciones de voseo |
| `front/reset-password.html` | 1 corrección de voseo |
| `front/admin-beneficiarios.html` | 3 correcciones de tú |
| `docs/LANGUAGE_STYLE_GUIDE.md` | **NUEVO** — Guía de estilo |

## Verificación

- Todos los textos visibles al usuario ahora usan usted formal
- No quedan formas de voseo ni tú informal en la interfaz
- La guía de estilo previene futuros traslapes

## Criterios de Aceptación

- [x] No existen formas de voseo en la interfaz
- [x] No existen formas de tú informal en la interfaz
- [x] Todos los textos usan conjugaciones de usted
- [x] Existe documentación para prevenir futuros traslapes
