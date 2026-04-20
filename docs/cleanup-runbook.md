# Cleanup Runbook — Plataforma Sillas Rotary v2

> **Propósito:** Checklist ejecutable PASS/FAIL + rollback por fase para el
> cambio `cleanup-plataforma-seguridad-estabilidad`.
>
> **Regla:** No avanzar a la siguiente fase sin PASS en todos los checks.
> Si un check falla, ejecutar rollback antes de continuar.

---

## Fase 0 — Contención Inmediata

**Objetivo:** Bloquear superficies de exposición en producción.

### Checklist

| # | Check | Comando | Resultado esperado | ☐ |
|---|---|---|---|---|
| 0.1 | `/docs` bloqueado en prod | `ENV=production pytest backend/tests/test_main.py -k docs` | PASS (3 passed) | ☐ |
| 0.2 | `migrate_v2.sql` marcado LEGACY | `grep -c "LEGACY" backend/migrate_v2.sql` | ≥ 1 coincidencia | ☐ |
| 0.3 | Script `migrate_v2.sql` no ejecutable | `head -3 backend/migrate_v2.sql` | Contiene `-- LEGACY` o `-- DO NOT EXECUTE` | ☐ |
| 0.4 | Regla incremental documentada | `test -f backend/migrations/README.md` | Archivo existe con reglas | ☐ |
| 0.5 | Tests abortan en DB no-test | `cd backend && unset TEST_DATABASE_URL && unset TEST_DB_SCHEMA && ./venv/bin/pytest tests/test_database_safety.py` | RuntimeError: "Unsafe test database target refused" | ☐ |

### Rollback Fase 0

```bash
# Revertir el commit de la fase 0
git log --oneline | grep -i "contención\|phase 0\|fase 0"
git revert <hash>

# Re-deploy
git push origin develop
```

**Impacto:** `/docs`, `/redoc`, `/openapi.json` vuelven accesibles en producción.
Riesgo bajo — solo documentación de API expuesta.

---

## Fase 1 — RBAC Backend

**Objetivo:** Autorización por rol en todos los endpoints protegidos.

### Checklist

| # | Check | Comando | Resultado esperado | ☐ |
|---|---|---|---|---|
| 1.1 | `require_roles()` existe en `auth.py` | `grep -c "def require_roles" backend/routers/auth.py` | ≥ 1 | ☐ |
| 1.2 | `assert_resource_owner()` existe en `auth.py` | `grep -c "def assert_resource_owner" backend/routers/auth.py` | ≥ 1 | ☐ |
| 1.3 | Socioeconómico rechaza `tecnico` | `pytest backend/tests/test_socioeconomico.py -k tecnico` | 403 | ☐ |
| 1.4 | Técnica rechaza `capturista` | `pytest backend/tests/test_tecnica.py -k capturista` | 403 | ☐ |
| 1.5 | Admin puede acceder a todo | `pytest backend/tests/test_auth_helpers.py` | 5 passed | ☐ |
| 1.6 | Ownership: no-admin no edita recurso ajeno | `pytest backend/tests/test_socioeconomico.py -k owner` | 403 | ☐ |

### Rollback Fase 1

```bash
git log --oneline | grep -i "rbac\|phase 1\|fase 1\|require_roles"
git revert <hash>
git push origin develop
```

**Impacto:** Endpoints vuelven a solo `require_auth` (sin restricción por rol).
Cualquier rol autenticado puede acceder a todos los endpoints. **RIESGO MEDIO.**

---

## Fase 2 — Seguridad DB/Storage

**Objetivo:** Bucket privado, `foto_path` canónico, endpoint autenticado de fotos.

### Checklist

| # | Check | Comando | Resultado esperado | ☐ |
|---|---|---|---|---|
| 2.1 | Migración `0002` existe | `test -f backend/migrations/0002_add_foto_path_to_solicitudes_tecnicas.sql` | Archivo existe | ☐ |
| 2.2 | Columna `foto_path` en DB | `psql ... -c "\d solicitudes_tecnicas" \| grep foto_path` | Columna presente | ☐ |
| 2.3 | Bucket `fotos-tecnica` privado | Supabase Dashboard → Storage → `fotos-tecnica` → Settings → Public = OFF | `public: false` | ☐ |
| 2.4 | Endpoint `/api/solicitudes/{id}/foto` existe | `grep "foto" backend/routers/tecnica.py` | Función `obtener_foto_solicitud` presente | ☐ |
| 2.5 | Endpoint rechaza `capturista` | `pytest backend/tests/test_tecnica_storage_security.py -k capturista` | 403 | ☐ |
| 2.6 | Endpoint retorna signed URL para owner técnico | `pytest backend/tests/test_tecnica_storage_security.py -k signed` | 200 con URL | ☐ |
| 2.7 | Backfill desde `foto_url` funciona | Registro con solo `foto_url` → endpoint retorna signed URL | PASS | ☐ |

### Rollback Fase 2

```bash
# 1. Revertir código
git log --oneline | grep -i "storage\|foto_path\|phase 2\|fase 2"
git revert <hash>
git push origin develop

# 2. Revertir migración (manual en Supabase SQL editor)
ALTER TABLE public.solicitudes_tecnicas DROP COLUMN IF EXISTS foto_path;

# 3. Hacer bucket público de nuevo (si es necesario para frontend legacy)
# Supabase Dashboard → Storage → fotos-tecnica → Settings → Public = ON
```

**Impacto:** Bucket vuelve a público; columna `foto_path` se elimina.
Si `foto_url` aún tiene valores válidos, las fotos siguen accesibles.
**RIESGO ALTO** — verificar que `foto_url` tiene datos antes de revertir.

---

## Fase 3 — Hardening de Despliegue

**Objetivo:** Security headers, health endpoint, bloqueo de rutas internas.

### Checklist

| # | Check | Comando | Resultado esperado | ☐ |
|---|---|---|---|---|
| 3.1 | `X-Frame-Options` presente | `curl -sI https://<tu-dominio>/ \| grep X-Frame-Options` | `DENY` | ☐ |
| 3.2 | `X-Content-Type-Options` presente | `curl -sI https://<tu-dominio>/ \| grep X-Content-Type` | `nosniff` | ☐ |
| 3.3 | `Referrer-Policy` presente | `curl -sI https://<tu-dominio>/ \| grep Referrer-Policy` | `strict-origin-when-cross-origin` | ☐ |
| 3.4 | `GET /api/health` funciona | `curl -s https://<tu-dominio>/api/health` | `{"status":"ok"}` | ☐ |
| 3.5 | Rutas internas bloqueadas | `curl -sI https://<tu-dominio>/backend/main.py` | 404 | ☐ |
| 3.6 | `.sql` bloqueado | `curl -sI https://<tu-dominio>/migrate_v2.sql` | 404 | ☐ |
| 3.7 | `.py` bloqueado | `curl -sI https://<tu-dominio>/api/index.py` | 404 | ☐ |
| 3.8 | `vercel.json` válido | `python -m json.tool vercel.json > /dev/null` | Sin error | ☐ |

### Rollback Fase 3

```bash
git log --oneline | grep -i "hardening\|headers\|phase 3\|fase 3\|vercel"
git revert <hash>
git push origin develop
```

**Impacto:** Headers de seguridad se eliminan; rutas internas vuelven accesibles.
`/api/health` se elimina. **RIESGO MEDIO.**

---

## Fase 4 — Cleanup v1/v2

**Objetivo:** Eliminar referencias v1 activas sin romper v2.

### Checklist

| # | Check | Comando | Resultado esperado | ☐ |
|---|---|---|---|---|
| 4.1 | Sin tabla `capturistas` en `init_db.py` | `grep -c "capturistas" backend/init_db.py` | 0 (solo en comentarios) | ☐ |
| 4.2 | Sin `capturista_id` activo en routers | `grep "capturista_id" backend/routers/*.py` | Solo en comentarios `# DEPRECATED` | ☐ |
| 4.3 | Sin badge SQLite en README | `grep -i sqlite README.md` | 0 coincidencias | ☐ |
| 4.4 | Sin endpoint `/api/login` en README | `grep "/api/login" README.md` | 0 coincidencias activas | ☐ |
| 4.5 | Suite v2 endpoints pasa | `pytest backend/tests/test_v1_legacy_cleanup.py` | 13 passed | ☐ |
| 4.6 | Auth v2 funciona | `pytest backend/tests/test_auth.py` | PASS | ☐ |
| 4.7 | Estudios v2 funcionan | `pytest backend/tests/test_socioeconomico.py` | PASS | ☐ |
| 4.8 | Solicitudes v2 funcionan | `pytest backend/tests/test_tecnica.py` | PASS | ☐ |

### Rollback Fase 4

```bash
git log --oneline | grep -i "cleanup v1\|legacy\|phase 4\|fase 4"
git revert <hash>
git push origin develop
```

**Impacto:** Referencias v1 se restauran (comentadas). Sin impacto funcional
en producción — solo código/documentación. **RIESGO BAJO.**

---

## Fase 5 — Tests Aislados

**Objetivo:** Suite confiable con cleanup por scope, sin TRUNCATE global.

### Checklist

| # | Check | Comando | Resultado esperado | ☐ |
|---|---|---|---|---|
| 5.1 | Sin TRUNCATE en `conftest.py` | `grep -c "TRUNCATE" backend/tests/conftest.py` | 0 | ☐ |
| 5.2 | `_scoped_cleanup` existe | `grep -c "_scoped_cleanup" backend/tests/conftest.py` | ≥ 1 | ☐ |
| 5.3 | `_track` helper existe | `grep -c "def _track" backend/tests/conftest.py` | ≥ 1 | ☐ |
| 5.4 | Contrato 4xx para estudios | `pytest backend/tests/test_estudio_error_contract.py` | 5 passed | ☐ |
| 5.5 | Contrato 4xx para solicitudes | `pytest backend/tests/test_solicitud_error_contract.py` | PASS | ☐ |
| 5.6 | Suite mínima sin DB pasa | `cd backend && unset TEST_DATABASE_URL && ./venv/bin/pytest tests/test_main.py tests/test_folio.py tests/test_v1_legacy_cleanup.py tests/test_vercel_config.py tests/test_migration_deprecation.py tests/test_auth_helpers.py tests/test_cleanup_scope.py tests/test_database_safety.py tests/test_storage_security_migration.py tests/test_tecnica_storage_security.py` | 57 passed | ☐ |
| 5.7 | Tests DB fallan sin env seguro | Mismo comando sin `TEST_DATABASE_URL` | RuntimeError aborta antes de mutar | ☐ |

### Rollback Fase 5

```bash
git log --oneline | grep -i "test.*isolat\|conftest\|phase 5\|fase 5\|cleanup.*scope"
git revert <hash>
git push origin develop
```

**Impacto:** Tests vuelven a TRUNCATE global. **Solo afecta CI/local,
NO producción.** Riesgo operacional nulo. **RIESGO BAJO.**

---

## Fase 6 — Documentación Operativa

**Objetivo:** README con gates/rollback + runbook ejecutable.

### Checklist

| # | Check | Comando | Resultado esperado | ☐ |
|---|---|---|---|---|
| 6.1 | Sección "Gates por Fase" en README | `grep -c "Gates por Fase" README.md` | ≥ 1 | ☐ |
| 6.2 | Sección "Rollback por Lote" en README | `grep -c "Rollback por Lote" README.md` | ≥ 1 | ☐ |
| 6.3 | Runbook existe | `test -f docs/cleanup-runbook.md` | Archivo existe | ☐ |
| 6.4 | Runbook tiene checklist por fase 0→5 | `grep -c "Fase 0\|Fase 1\|Fase 2\|Fase 3\|Fase 4\|Fase 5" docs/cleanup-runbook.md` | ≥ 6 | ☐ |
| 6.5 | Runbook tiene rollback por fase | `grep -c "Rollback Fase" docs/cleanup-runbook.md` | ≥ 6 | ☐ |
| 6.6 | Gates en README coinciden con implementación real | Revisar manualmente cada gate vs código | Consistente | ☐ |

### Rollback Fase 6

```bash
git log --oneline | grep -i "documentación\|runbook\|phase 6\|fase 6"
git revert <hash>
git push origin develop
```

**Impacto:** Solo archivos de documentación. Cero impacto operacional.
**RIESGO NULO.**

---

## Procedimiento de Rollback General

### Reglas

1. **Orden inverso:** Si la Fase N falla, revertir primero las fases N+1, N+2, ...
   que ya se hayan deployado, luego revertir la Fase N.
2. **Migraciones SQL:** Las migraciones aditivas (ALTER TABLE ADD COLUMN) se
   revierten manualmente con `DROP COLUMN IF EXISTS`.
3. **Commits atómicos:** Cada fase debe tener su propio commit. Si hay múltiples
   commits por fase, revertir en orden inverso (último primero).
4. **Verificar después de rollback:** Ejecutar los checks de la fase anterior
   al rollback para confirmar que el sistema quedó en estado conocido.

### Secuencia de emergencia

```bash
# 1. Detener despliegue automático (si aplica)
# Vercel Dashboard → Project Settings → Git → Disconnect Git

# 2. Identificar último commit bueno
git log --oneline -20

# 3. Revertir en orden inverso (última fase primero)
git revert <hash-fase-mas-reciente>
git revert <hash-fase-anterior>
# ... repetir hasta la fase problemática

# 4. Push
git push origin develop

# 5. Re-deploy manual
# Vercel Dashboard → Deployments → Redeploy del último bueno
# O: vercel deploy --prod

# 6. Verificar
curl -s https://<tu-dominio>/api/health
curl -sI https://<tu-dominio>/ | head -20
```

---

## Referencias

| Artefacto | Ubicación |
|---|---|
| Spec del cambio | Engram: `sdd/cleanup-plataforma-seguridad-estabilidad/spec` |
| Design | Engram: `sdd/cleanup-plataforma-seguridad-estabilidad/design` |
| Tasks | Engram: `sdd/cleanup-plataforma-seguridad-estabilidad/tasks` |
| Apply Progress | Engram: `sdd/cleanup-plataforma-seguridad-estabilidad/apply-progress` |
| Migraciones | `backend/migrations/` |
| Tests | `backend/tests/` |
