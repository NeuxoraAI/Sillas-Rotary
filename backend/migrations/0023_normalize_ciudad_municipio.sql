-- ============================================================================
-- Migration: 0023_normalize_ciudad_municipio.sql
-- Purpose:  Issue #67 — backfill beneficiarios.ciudad to the canonical form
--           introduced in the frontend normalization PR (#91, issue #67).
--
--           The frontend now normalises ciudad on every write:
--             1. Collapse internal whitespace runs to a single space
--             2. Trim leading/trailing whitespace
--             3. Uppercase, accent-preserving (JS toLocaleUpperCase("es-MX"))
--
--           Before that PR landed, rows accumulated mixed-case values
--           (e.g. "Mérida", "MERIDA", "mérida ", "Guadalajara"). The
--           admin list/export endpoint groups by ciudad, so those variants
--           produced duplicate buckets in reports.
--
--           This UPDATE normalises every existing row to the same canonical
--           form so that old and new records match when grouped.
--
-- SQL vs. JS equivalence:
--           Postgres upper() is Unicode-aware and preserves accent marks
--           exactly as JS toLocaleUpperCase("es-MX") does for Spanish
--           characters (á→Á, é→É, í→Í, ó→Ó, ú→Ú, ñ→Ñ, ü→Ü).
--           regexp_replace(ciudad, '\s+', ' ', 'g') collapses whitespace
--           runs to a single space; btrim() removes leading/trailing spaces.
--           This is a faithful server-side replica of the frontend rule.
--
-- Idempotency: the WHERE clause skips rows that are already normalised, so
--           re-running this migration is safe and produces no spurious writes.
--
-- Scope:    Only beneficiarios.ciudad. ciudad_registro and other columns are
--           NOT touched.
-- ============================================================================

UPDATE beneficiarios
SET    ciudad = upper(btrim(regexp_replace(ciudad, '\s+', ' ', 'g')))
WHERE  ciudad IS NOT NULL
  AND  ciudad <> upper(btrim(regexp_replace(ciudad, '\s+', ' ', 'g')));
