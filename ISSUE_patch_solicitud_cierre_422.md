<!--
GitHub issue metadata — usar al crear el issue (gh issue create):

title:     fix(tecnica): cerrar una solicitud por PATCH /solicitudes/{id} con cuerpo parcial devuelve 422 (validador exige medidas en el body)
labels:    backend, type:bug, Alta
assignees: eramirezh10
state:     OPEN (propuesto)
-->

# fix(tecnica): cerrar una solicitud por `PATCH /solicitudes/{id}` con cuerpo parcial devuelve 422

| Campo | Valor |
| --- | --- |
| **Título** | `fix(tecnica): cerrar una solicitud por PATCH /solicitudes/{id} con cuerpo parcial devuelve 422 (validador exige medidas en el body)` |
| **Labels** | `backend`, `type:bug`, `Alta` |
| **Assignees** | `eramirezh10` |
| **Estado** | Propuesta (borrador) — pendiente de aprobación antes de implementar |

> Comando de referencia (no ejecutado):
> ```bash
> gh issue create \
>   --title "fix(tecnica): cerrar una solicitud por PATCH /solicitudes/{id} con cuerpo parcial devuelve 422 (validador exige medidas en el body)" \
>   --label "backend,type:bug,Alta" \
>   --assignee "eramirezh10" \
>   --body-file ISSUE_patch_solicitud_cierre_422.md
> ```

## Pre-flight Checks
- [x] Searched existing issues for duplicates.
- [x] This issue must be approved before implementation work starts.

## Descripción del bug

El endpoint `PATCH /solicitudes/{id}` es una **actualización parcial**: el cliente
debería poder enviar solo los campos que cambia. Sin embargo, **no se puede cerrar
una solicitud** (transición a `status = "completo"`) enviando un cuerpo parcial:
el modelo Pydantic `SolicitudUpdateRequest` exige que **las 7 medidas vengan en el
cuerpo de la petición** cuando `status == "completo"`, aunque esas medidas ya estén
guardadas en la base de datos desde el borrador.

Como la validación ocurre en la capa Pydantic (que **no tiene acceso a la BD**),
una petición como `PATCH /solicitudes/{id}` con cuerpo `{"status": "completo"}`
siempre devuelve **422**, en lugar de cerrar el registro (200) o, en su caso,
aplicar primero la verificación de autorización (403).

## Causa raíz

`backend/routers/tecnica.py:663-688` — validador `_validar_completo_t2` del modelo
`SolicitudUpdateRequest`:

```python
@model_validator(mode="after")
def _validar_completo_t2(self):
    if self.status != "completo":
        return self
    missing = [campo for campo, valor in {
        "altura_total_in": self.altura_total_in,
        "peso_kg": self.peso_kg,
        "medida_cabeza_asiento": self.medida_cabeza_asiento,
        "medida_hombro_asiento": self.medida_hombro_asiento,
        "medida_prof_asiento": self.medida_prof_asiento,
        "medida_rodilla_talon": self.medida_rodilla_talon,
        "medida_ancho_cadera": self.medida_ancho_cadera,
    }.items() if valor is None]
    if missing:
        raise ValueError(f"{', '.join(missing)} es obligatorio cuando status es completo")
    return self
```

El validador asume que el cuerpo del PATCH es **completo** (como un POST de
creación), pero en un PATCH parcial esos campos llegan en `None` porque ya
fueron persistidos en el borrador. No puede consultar la BD para verificar el
estado **fusionado** (lo enviado + lo ya guardado).

Comportamiento reproducido:

```python
SolicitudUpdateRequest(status="completo")                  # -> 422
SolicitudUpdateRequest(status="completo", prioridad="Alta")# -> 422
SolicitudUpdateRequest(status="borrador")                  # -> OK
SolicitudUpdateRequest(prioridad="Alta")                   # -> OK
```

## Evidencia (tests en rojo)

`backend/tests/test_tecnica.py::TestTecnicaRbac` — **4 tests** fallan por esta causa
(todos hacen PATCH con `status=completo` y cuerpo parcial):

| Test | Esperado | Obtenido |
| --- | --- | --- |
| `test_tecnico_owner_can_patch_borrador` | 200 | **422** |
| `test_admin_can_patch_foreign_solicitud` | 200 | **422** |
| `test_non_owner_tecnico_patch_forbidden` | 403 | **422** |
| `test_capturista_cannot_close_existing_solicitud` | 403 | **422** |

> Nota de seguridad: en los dos casos que esperan **403**, el 422 de validación
> ocurre **antes** del check de autorización (`assert_resource_owner`), de modo que
> hoy es imposible verificar por test que la autorización del cierre funcione. El
> orden validación-antes-de-autorización es normal en FastAPI, pero deja la
> autorización del cierre sin cobertura efectiva hasta que se corrija el 422.

## Impacto en producción (alcance)

El defecto es principalmente de **contrato de API y de cobertura de tests**. Los
caminos principales de la UI lo esquivan, pero no todos:

- `front/Capturista-view/gestion.html:867-871` — el PATCH de la solicitud **no
  envía `status`**, solo `entidad_solicitante`, `prioridad`, `justificacion`; por
  eso el validador no se dispara en ese flujo. (El cierre real se apoya en
  `tecnica.html` y/o `POST /finalizar-registro`.)
- `front/admin-beneficiarios.html` — la edición admin usa las rutas dedicadas
  `PATCH /admin/beneficiarios/{id}/solicitud`, no el endpoint general.

Sin embargo, **cualquier cliente que use el contrato documentado** de
`PATCH /solicitudes/{id}` con cuerpo parcial (`{"status": "completo"}`) recibe 422
salvo que reenvíe las 7 medidas. El contrato de actualización parcial está roto.

## Comportamiento esperado

- `PATCH /solicitudes/{id}` con `{"status": "completo"}` cierra la solicitud (200)
  cuando las 7 medidas **ya están persistidas** en la BD, sin exigir reenviarlas.
- Si faltan medidas en el estado **fusionado** (cuerpo + BD), se devuelve 422 con el
  detalle de los campos faltantes.
- La verificación de autorización (`assert_resource_owner`) se evalúa para los
  casos correspondientes (dueño/líder/admin → 200; ajeno → 403).

## Solución sugerida

1. **Mover la verificación de completitud al endpoint** `actualizar_solicitud`
   (`tecnica.py:1507`), donde sí hay acceso a la BD, y validar contra el estado
   **fusionado** (valores del cuerpo + valores ya almacenados en
   `solicitudes_tecnicas`). Es el mismo enfoque que ya usa
   `backend/routers/finalizar.py::_validate_all_complete`.
2. **Quitar** (o relajar) el `model_validator` `_validar_completo_t2` de
   `SolicitudUpdateRequest`, dejando en el modelo solo validaciones que no
   dependan de la BD (rango/tipo/formato de cada campo, que ya existen).
3. Mantener el comportamiento estricto del **POST de creación**
   (`SolicitudCreateRequest._validar_completo_t2`, `tecnica.py:514-536`), donde sí
   es razonable exigir todo en el cuerpo (no hay estado previo en BD). *(Confirmar
   con negocio si la creación directa en `completo` debe seguir siendo posible.)*
4. Actualizar/restaurar los 4 tests para que verifiquen el contrato correcto
   (cierre con cuerpo parcial → 200; ajeno → 403; faltan medidas en estado
   fusionado → 422).

## Hallazgo secundario (relacionado, otra causa)

En la misma clase de tests falla además:

| Test | Esperado | Obtenido |
| --- | --- | --- |
| `test_capturista_cannot_create_solicitud` | 403 | **201** |

**No es el mismo bug.** Este test asume que el `capturista` **no** puede crear
solicitudes, pero el modelo de roles confirmado indica lo contrario: **el
capturista es quien crea los registros** (socioeconómico, técnica, gestión). El
comportamiento del backend (201) es **correcto**; el test está **obsoleto** y debe
actualizarse/eliminarse para reflejar el modelo. Esto se relaciona con
`ISSUE_permisos_roles_escritura.md` (matriz de permisos por rol). Se recomienda
corregir este test dentro de ese issue de permisos, no en este.

## Criterios de aceptación

- [ ] `PATCH /solicitudes/{id}` con `{"status": "completo"}` cierra la solicitud
      (200) cuando las medidas ya están en la BD.
- [ ] Si faltan medidas en el estado fusionado (cuerpo + BD) → 422 con detalle.
- [ ] La autorización del cierre se evalúa correctamente (dueño/líder/admin → 200;
      ajeno → 403) y queda cubierta por test.
- [ ] El POST de creación conserva su validación de completitud (o se ajusta según
      decisión de negocio).
- [ ] Los 4 tests de `TestTecnicaRbac` afectados por el 422 quedan en verde.
- [ ] El test `test_capturista_cannot_create_solicitud` se alinea con el modelo de
      roles (tratado en `ISSUE_permisos_roles_escritura.md`).
