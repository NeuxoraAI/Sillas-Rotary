# Migraciones incrementales (v2)

Este directorio es la única fuente válida para cambios de esquema.

## Reglas obligatorias

1. **Solo migraciones incrementales**: prohibidos scripts monolíticos o destructivos.
2. **Reversibles por lote**: cada migración debe poder revertirse de forma controlada.
3. **Sin big-bang**: cambios aditivos primero (compatibilidad temporal), limpieza después.
4. **Nombres ordenados**: usar prefijo secuencial (`0001_`, `0002_`, etc.).

## Orden canónico actual

Los prefijos deben ser únicos. Si una migración ya fue aplicada en un entorno
con un nombre anterior, validar primero el contenido de la tabla de control del
runner (`supabase_migrations` o equivalente) antes de renombrar el historial en
ese entorno.

| Prefijo | Migración |
| --- | --- |
| `0002` | `add_foto_path_to_solicitudes_tecnicas` |
| `0003` | `rls_policies` |
| `0004` | `add_documento_refs_to_estudios_socioeconomicos` |
| `0005` | `prd_ajustes_nombre_estructurado` |
| `0006` | `prd_ajustes_imss_infonavit_triestado` |
| `0007` | `medidas_decimal_7_3` |
| `0008` | `add_tutor_email` |
| `0009` | `prevent_duplicate_estudios_solicitudes` |
| `0010` | `add_avatar_url_to_usuarios` |
| `0011` | `make_draft_columns_nullable` |
| `0012` | `organizaciones_membership_voluntarios` |
| `0013` | `rename_observaciones_posturales_to_padecimiento` |
| `0014` | `app_runtime_role` |
| `0015` | `prd_opcion_b_fields` |
| `0016` | `add_unidad_peso_captura` |
| `0017` | `add_finalizado_at` |
| `0018` | `add_soporte_oxigeno_to_solicitudes_tecnicas` |
| `0019` | `fix_advisor_indexes` |
| `0020` | `drop_dead_schema_objects` |
| `0021` | `curp_natural_key` |
| `0022` | `unify_org_leadership_source` |
| `0023` | `normalize_ciudad_municipio` |
| `0024` | `password_tokens` |
| `0025` | `add_estudio_clinico_refs_to_estudios` |
| `0026` | `auditoria_eventos` |
| `0027` | `add_equipo_solicitado_estudio_clinico` |
| `0028` | `drop_dead_columns` |

## Deprecación de legado

`backend/migrate_v2.sql` queda marcado como **LEGACY / DO NOT EXECUTE**.
No debe usarse en ningún entorno.

## Backfill y compatibilidad de fotos técnicas

- Migración `0002_add_foto_path_to_solicitudes_tecnicas.sql` agrega `foto_path` como campo canónico.
- Durante la transición, la API mantiene **dual-write** (`foto_path` + `foto_url` derivada como `storage://fotos-tecnica/<path>`).
- El endpoint autenticado de foto técnica (`GET /api/solicitudes/{id}/foto`) realiza backfill oportunista si encuentra registros legacy con solo `foto_url`.

## Postura RLS y rol runtime

- La autorización de negocio se implementa en FastAPI (`require_roles`, `assert_resource_owner` y validaciones por endpoint).
- RLS restringe el acceso directo de roles PostgREST (`anon`/`authenticated`) a tablas de negocio; no modela permisos por usuario final.
- Producción debe usar `DB_USER=app_runtime`, creado por `0014_app_runtime_role.sql`, en lugar de `postgres`.
- `app_runtime` es `NOBYPASSRLS`, por lo que necesita una política permisiva `app_runtime_all` para cada tabla que use el backend.
- Al crear una tabla nueva, la migración debe agregar también su política `app_runtime_all`; los grants futuros se heredan por default privileges, pero las políticas RLS no.
