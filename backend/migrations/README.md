# Migraciones incrementales (v2)

Este directorio es la única fuente válida para cambios de esquema.

## Reglas obligatorias

1. **Solo migraciones incrementales**: prohibidos scripts monolíticos o destructivos.
2. **Reversibles por lote**: cada migración debe poder revertirse de forma controlada.
3. **Sin big-bang**: cambios aditivos primero (compatibilidad temporal), limpieza después.
4. **Nombres ordenados**: usar prefijo secuencial (`0001_`, `0002_`, etc.).

## Deprecación de legado

`backend/migrate_v2.sql` queda marcado como **LEGACY / DO NOT EXECUTE**.
No debe usarse en ningún entorno.

## Backfill y compatibilidad de fotos técnicas

- Migración `0002_add_foto_path_to_solicitudes_tecnicas.sql` agrega `foto_path` como campo canónico.
- Durante la transición, la API mantiene **dual-write** (`foto_path` + `foto_url` derivada como `storage://fotos-tecnica/<path>`).
- El endpoint autenticado de foto técnica (`GET /api/solicitudes/{id}/foto`) realiza backfill oportunista si encuentra registros legacy con solo `foto_url`.
