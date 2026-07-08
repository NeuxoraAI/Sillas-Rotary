# FIXES — Issue #161: Persistencia de borradores (arquitectura local-first + botón maestro único)

## Problema

**Síntoma reportado:** la persistencia de datos fallaba en `tecnica.html` para **todos** los campos: el usuario llenaba el formulario, navegaba con CONTINUAR/REGRESAR y al volver el formulario aparecía vacío.

**Causa raíz (frontend):** en cuanto existía un `solicitud_id` en localStorage (creado al guardar borrador desde socioeconómico o gestión), la restauración de `tecnica.html` usaba *exclusivamente* `GET /solicitudes/{id}` e ignoraba el draft local `draft_tecnica` — el único lugar donde CONTINUAR/REGRESAR persisten los campos. El backend devolvía campos técnicos en `null` (o viejos) y el formulario quedaba vacío.

**Bugs adicionales confirmados en la auditoría extendida:**

1. `observaciones_posturales` **se perdía siempre**: la migración 0013 renombró la columna original a `padecimiento` (que hoy guarda el catálogo de padecimientos) y el textarea quedó sin columna; el campo ni siquiera existía en `GuardarBorradorRequest`.
2. `soporte_oxigeno` se forzaba a `FALSE` cuando no se respondía (`bool(None)` + columna `NOT NULL DEFAULT FALSE`), anulando la validación backend del issue #162 (`IS NULL` nunca disparaba).
3. `_update_borrador` descartaba **en silencio** todos los campos técnicos si el estudio no tenía solicitud, devolviendo `solicitud_id=0` (falsy → el frontend nunca lo guardaba) con toast de "guardado con éxito".
4. Tres builders de payload divergentes (uno por vista); el de gestión omitía `soporte_oxigeno`, `equipo_solicitado` y `observaciones_posturales`.
5. Restauración triple solapada en `socioeconomico.html` (GET /estudios + draft local + modo edición) con race conditions — el último en escribir ganaba.
6. Autosave roto en `socioeconomico.html`: usaba la constante inexistente `LOCAL_DRAFT_STORAGE_KEY` (ReferenceError al primer input) y nada leía su snapshot.
7. `test_all_complete_returns_empty_list` **ya fallaba en main**: el commit a49d916 agregó la validación de `soporte_oxigeno` a `finalizar.py` sin actualizar los fixtures.

## Solución: arquitectura local-first con botón maestro único

**Principio:** durante la captura, los 3 drafts de localStorage (`draft_socioeconomico`, `draft_tecnica`, `draft_gestion`) son la única fuente de verdad; cada vista restaura solo desde su draft, de forma síncrona. El backend interviene en dos puntos:

- **Hidratación única** al reanudar un borrador: `GET /borrador/{estudio_id}` siembra los 3 drafts + IDs (con overlay de carga — el pedido original del issue #161).
- **Guardado explícito único** desde `gestion.html`: el botón "Guardar Borrador" (junto a "Finalizar Registro") envía `POST /guardar-borrador` con un payload construido por un único builder. Los botones "Guardar Borrador" de socioeconómico y técnica se eliminaron.

### Backend

| Archivo | Cambio |
| --- | --- |
| `backend/migrations/0029_observaciones_posturales_y_soporte_oxigeno_nullable.sql` | **Nueva.** `ADD COLUMN observaciones_posturales TEXT NULL` + `soporte_oxigeno DROP NOT NULL / DROP DEFAULT` en `solicitudes_tecnicas`. Aplicada a `testschema`; **pendiente de aplicar a `public` (BD real) vía el workflow de migraciones de Supabase**. |
| `backend/routers/guardar_borrador.py` | Campo `observaciones_posturales` en el modelo (normalización + validador `validate_padecimiento`), en el INSERT y en `_patch_solicitud`. `bool(body.soporte_oxigeno)` → `body.soporte_oxigeno` (None→NULL). Helper `_insert_solicitud()` extraído; `_update_borrador` ahora **inserta** la solicitud si no existe (elimina el descarte silencioso y el `solicitud_id or 0`). `GET /borrador` resuelve `foto_url_resolved` y `estudio_clinico_url_resolved` en `solicitud` para los previews post-hidratación. |
| `backend/migrations/README.md` | Registro de la 0029 en el orden canónico. |

### Frontend

| Archivo | Cambio |
| --- | --- |
| `front/assets/js/draft-store.js` | **Nuevo.** `window.DraftStore`: `getDraft/setDraft`, `getIds/setIds`, `clearAll`, `hydrateIfNeeded({urlEstudioId})` (regla única de hidratación + overlay #161 + 404→limpia IDs), `seedFromBorrador` (normaliza tutores —split de `nombre` compuesto, `antiguedad_meses`→años+meses—, `curp_benef`→`curp`, reconstruye `region_ctx`) y `buildMasterPayload` (único builder, ahora con `soporte_oxigeno`, `equipo_solicitado` y `observaciones_posturales`). |
| `front/Capturista-view/gestion.html` | `guardarBorradorDesdeGestion` y `finalizarRegistro` usan `DraftStore` (setDraft → buildMasterPayload → setIds/clearAll). El IIFE ya no hace GET a `/estudios` ni `/solicitudes`: hidrata una vez y pinta desde `draft_gestion`. Eliminados `buildGuardarBorradorPayload`, `submitGestion` y `validarFormularioGestion` (legacy sin llamadores). |
| `front/Capturista-view/tecnica.html` | Restauración **siempre** desde `draft_tecnica` (fix del bug crítico — se quitó la condición `!solicitudId` y la rama `GET /solicitudes/{id}` completa). Botón "Guardar Borrador" + `guardarBorradorDesdeTecnica` eliminados. `submitSolicitud` (POST/PATCH directo con status `completo` desde el Enter del form) eliminado; el submit siempre rutea a CONTINUAR. |
| `front/Capturista-view/socioeconomico.html` | Restauración triple colapsada: el IIFE hidrata (`hydrateIfNeeded({urlEstudioId})`, cubre el modo edición `?estudio_id=` con banner) y `restoreLocalStorageDraft()` es el **único** pintado, encadenado tras catálogos + hidratación (`draftInitReady`). Eliminados: botón "Guardar Borrador" + `guardarBorradorMaster`, autosave roto (`LOCAL_DRAFT_STORAGE_KEY`), `populateFormWithData`, `cacheLoadedDraftForContinuation`, `loadExistingEstudio`, override `submitEstudio`/`_patchEstudio`, `submitEstudio` y `persistDraftRemotely` (todos sin llamadores tras el rediseño). |
| `front/assets/js/confirmation-modal.js` | `confirmUnsavedNavigation(opts)` acepta mensaje custom; en pasos 1-2 el aviso de salida aclara: *"El borrador se guarda en el servidor al llegar al paso 3 (Gestión); hasta entonces, los datos capturados viven solo en este dispositivo."* |

### Flujos resultantes

- **Captura nueva:** paso 1 → CONTINUAR (draft local) → paso 2 → CONTINUAR (draft local) → paso 3 → "Guardar Borrador" (CREATE backend) o "Finalizar Registro" (consolida + finaliza + limpia las 6 claves).
- **Navegación ida/vuelta:** cada vista restaura su draft local síncronamente — sin red, sin race, sin sobrescrituras.
- **Reanudar borrador** (perfil → `socioeconomico.html?estudio_id=N`, o entrada directa a cualquier paso con `estudio_id` local sin drafts): hidratación única desde `GET /borrador` con overlay; después todo es local.

## Tests

- `backend/tests/test_guardar_borrador.py`: nueva clase `TestPersistenciaTecnicaBorrador` (6 tests): roundtrip de `observaciones_posturales` en CREATE y UPDATE, `soporte_oxigeno` None→NULL y False explícito, INSERT fallback con estudio sin solicitud, URLs resueltas en `GET /borrador`.
- `backend/tests/test_finalizar.py`: `soporte_oxigeno=None` → aparece en `missing` (la validación #162 vive por fin en backend); `False` explícito no bloquea. Fixtures corregidos (`_complete_rows` y el seeder ahora responden `soporte_oxigeno` — el test de "todo completo" llevaba roto desde a49d916).
- **Resultado:** suite backend completa en verde (ver nota de verificación al final).

## Riesgos y decisiones documentadas

- **Abandono en paso 1-2 (decisión aceptada):** el borrador no llega al backend hasta pisar gestión — no aparece en "Mis capturas" ni es recuperable desde otro dispositivo. Mitigación: los drafts locales sobreviven al cierre del navegador + aviso explícito al salir del wizard.
- **Dos dispositivos:** si hay draft local, no se hidrata aunque el backend tenga datos más nuevos (last-writer-wins). Sin resolución de conflictos.
- **Filas legacy** con `soporte_oxigeno=FALSE` sintético: indistinguibles de un "No" real (el dato nunca se capturó como NULL).
- **Split heurístico del nombre del tutor** al hidratar: ~~preexistente, fuera de alcance~~ **RESUELTO en el follow-up de QA** (ver sección al final): migración 0030 agrega columnas estructuradas a `tutores`; la heurística queda solo como fallback de lectura para filas legacy.
- **PATCH parcial no vacía campos** (None = no tocar): comportamiento preexistente, sin cambio.

## Pendientes para despliegue

1. ~~Aplicar la migración 0029 a la BD real (`public`)~~ **APLICADA** (2026-07-07, verificada: `observaciones_posturales` existe y `soporte_oxigeno` es nullable sin default).
2. ~~QA manual en dispositivo real~~ **REALIZADO** (2026-07-07): captura nueva y reanudación funcionando; el único hallazgo (nombre de tutor sin dividir) se corrigió con el follow-up de abajo.

## Follow-up de QA (2026-07-07): nombre estructurado del tutor

**Hallazgo del QA manual:** al reanudar un borrador, el nombre del tutor se cargaba mal repartido entre los campos Nombre(s) / Apellido Paterno / Apellido Materno (o completo en un solo campo con drafts sembrados por versiones previas), a diferencia del beneficiario.

**Causa raíz:** la tabla `tutores` solo tenía la columna `nombre` (compuesta). Los INSERT concatenaban los 3 campos capturados y `GET /borrador` devolvía solo el compuesto; `_normalizeTutor` (draft-store.js) adivinaba la división por espacios — imposible de acertar con apellidos compuestos ("De la Cruz", "San Juan") o nombres de 2 palabras.

**Fix (espejo de `0005_prd_ajustes_nombre_estructurado` para beneficiarios):**

| Archivo | Cambio |
| --- | --- |
| `backend/migrations/0030_tutores_nombre_estructurado.sql` | **Nueva.** `ADD COLUMN nombres / apellido_paterno / apellido_materno TEXT NULL` en `tutores`. `nombre` compuesto se conserva (export admin, filas legacy). **Aplicada a `public` y `testschema`** (2026-07-07). |
| `backend/routers/guardar_borrador.py` | `_build_tutor_params` + los 2 INSERT de tutores (create/update) hacen dual-write: compuesto + 3 campos estructurados. |
| `backend/routers/socioeconomico.py` | `_insertar_tutores` (usado por POST y PATCH /estudios) hace el mismo dual-write. |
| `front/assets/js/draft-store.js` | Sin cambio funcional: `_normalizeTutor` ya prefería `t.nombres` del backend; la heurística queda documentada como fallback solo-legacy (filas pre-0030 se autocorrigen al siguiente guardado). |
| `backend/tests/test_guardar_borrador.py` | Nuevo `test_tutor_nombre_estructurado_round_trip`: create + update con apellidos compuestos → GET devuelve los 3 campos exactos y el compuesto. |

**Verificación:** `test_guardar_borrador.py` + `test_socioeconomico.py` + `test_finalizar.py` → 116 passed. `node --check` OK en draft-store.js.

## Follow-up 2 (2026-07-07): el pedido literal del issue #161 + auditoría global de races de UI

El issue #161 pide textualmente **bloquear la UI mientras cargan los datos persistidos**. El rediseño local-first ya lo resolvía en tecnica/gestion (pintado síncrono tras `hydrateIfNeeded`), pero en socioeconomico el pintado espera el catálogo de municipios (red, `cache:"no-store"`) sin bloqueo: el usuario podía teclear y `restoreLocalStorageDraft()` lo sobrescribía. Además, una auditoría global del frontend (alcance "todo lo de riesgo real" aprobado por el usuario) encontró cascadas país→región fuera de orden y guardados sin bloqueo anti doble-click. Todo frontend-only.

| Fix | Archivo(s) | Cambio |
| --- | --- | --- |
| A1 · overlay #161 (crítico) | `draft-store.js`, `socioeconomico.html` | Overlay **ref-counted** y expuesto (`DraftStore.showOverlay/hideOverlay`); socioeconomico lo sostiene desde el primer frame cuando hay borrador que restaurar (draft local, `?estudio_id=` o `estudio_id` en localStorage) y lo libera en el `finally` de la cadena catálogo→hidratación→pintado (`return restoreLocalStorageDraft()` + `catch` que además corrige una rejection sin manejar cuando el catálogo falla). Captura nueva NO se bloquea. tecnica/gestion sin cambios. |
| C1 · org duplicada | `admin-usuarios.html` | `btn-guardar-org`: doble click con `_manageOrgId` vacío creaba DOS organizaciones (POST antes de asignar el id). Guard `disabled` + `finally`. |
| B1 · region_ctx envenenado | `seleccion-region.html` | Token monotónico en `loadRegiones`: respuestas fuera de orden al cambiar país rápido dejaban regiones del país anterior y se persistía `region_ctx` cruzado para toda la sesión (afecta folio). |
| A2 · catálogo en edición admin | `admin-beneficiarios.html` | `_setupMunicipiosCatalog`: `estado` se deshabilita síncrono mientras baja el catálogo (el listener de change se conectaba tras el await y los cambios se perdían); `try/catch/finally` exception-safe. |
| C2 · re-subida de documentos | `admin-beneficiarios.html` | `_runGlobalSave` single-flight (`_globalSaveInFlight`): mientras un guardado con uploads vuela, `btn-save-all` era clickeable de nuevo → guardado concurrente re-subía documentos. `btn-confirm-save` con `disabled`+`btn-loading` (el doble-click directo ya lo cubría `_hideSaveWarningModal` anulando `pendingSave`). |
| C3 · PATCH perfil duplicado | `perfil-capturista.html` | `btn-guardar-edit`: `disabled` + `finally`. |
| C4 ×5 · doble-submit | `admin-usuarios.html` (edit-user, agregar-lider, agregar-miembro), `admin-regiones.html` (edit-pais, edit-region) | Mismo patrón de 2 líneas, disable tras validaciones sync. |
| B2 · filtro técnico | `vista_tecnicos.html` | Token en `loadRegionesDropdown` (solo gatea el write al DOM; el cache queda incondicional). |
| Banner de edición persistente | `socioeconomico.html` | El banner "Editando estudio #N" (+ título y label del botón) ahora se muestra también cuando hay `estudio_id` en localStorage, no solo con `?estudio_id=` en la URL — al navegar entre pasos el parámetro se pierde pero se sigue editando el mismo borrador. La verificación de persistencia en navegación (captura y edición) confirmó que todos los CONTINUAR/REGRESAR guardan su draft local antes de navegar; este banner era el único hallazgo (cosmético). |

**Verificación:** `node --check` OK en draft-store.js y en los 14 bloques `<script>` inline de los 7 HTML modificados. QA manual pendiente con throttle (Slow 3G): captura nueva sin overlay / borrador con overlay continuo sin flicker / bloquear el JSON de municipios no congela la UI; doble click en cada guardado = un solo request en Network; cambio rápido de país = regiones consistentes.
