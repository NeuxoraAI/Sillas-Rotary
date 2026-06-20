-- ============================================================================
-- Migration: 0014_app_runtime_role.sql
-- Purpose:  Issue #73 — least-privilege runtime role (NOT superuser).
--           The app connects via a direct psycopg2 connection. Today the
--           default user is the superuser `postgres`, so any injection, leaked
--           credential, or authz bug has superuser reach (DROP, total R/W).
--           This creates a bounded `app_runtime` role: DML only, no DDL,
--           NOSUPERUSER / NOCREATEDB / NOCREATEROLE / NOBYPASSRLS. Production
--           DB_USER then points at this role instead of `postgres`.
--
-- RLS note: every public table already has RLS ENABLED but NOT FORCED, so the
--           table owner (`postgres`) silently bypasses it — that is why the app
--           works today as superuser. `app_runtime` is NOT the owner and is
--           NOBYPASSRLS, so RLS would otherwise deny it every row. We add a
--           permissive `app_runtime_all` policy per table: the FastAPI backend
--           is the trusted authz boundary, while the anon/authenticated
--           PostgREST roles stay restricted by the 0003 policies.
--
-- FOOTGUN:  Any NEW table needs its own `app_runtime_all` policy in the
--           migration that creates it, or the backend will be denied on it.
--           DML grants for future tables ARE auto-covered (ALTER DEFAULT
--           PRIVILEGES below); RLS policies are NOT — they must be added by hand.
--
-- Password: NOT committed. After applying, set it out-of-band from a secret:
--             ALTER ROLE app_runtime WITH PASSWORD '<from-secret-manager>';
--           then set production env: DB_USER=app_runtime, DB_PASSWORD=<secret>.
--           (CONNECT on the database is granted to PUBLIC by default on
--           Supabase; add an explicit GRANT CONNECT if your cluster revokes it.)
-- ============================================================================

-- 1. Role attributes (idempotent). No password is set here on purpose.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_runtime') THEN
    CREATE ROLE app_runtime LOGIN
      NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
  ELSE
    ALTER ROLE app_runtime LOGIN
      NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
  END IF;
END $$;

-- 2. Schema usage — required to reference any object in `public`.
GRANT USAGE ON SCHEMA public TO app_runtime;

-- 3. DML on all existing tables. No DDL and deliberately NO TRUNCATE
--    (TRUNCATE can wipe a whole table and is not part of normal app traffic).
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_runtime;

-- 4. Sequences — serial PKs need USAGE+SELECT for nextval()/currval().
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_runtime;

-- 5. Future objects created by `postgres` inherit the same minimal grants.
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO app_runtime;

-- 6. Permissive RLS policy per existing table so the NOBYPASSRLS role passes.
--    The backend is trusted; row-level filtering for it happens in FastAPI.
DO $$
DECLARE t text;
BEGIN
  FOR t IN
    SELECT tablename FROM pg_tables WHERE schemaname = 'public'
  LOOP
    EXECUTE format('DROP POLICY IF EXISTS app_runtime_all ON public.%I', t);
    EXECUTE format(
      'CREATE POLICY app_runtime_all ON public.%I '
      'FOR ALL TO app_runtime USING (true) WITH CHECK (true)',
      t
    );
  END LOOP;
END $$;
