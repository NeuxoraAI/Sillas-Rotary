-- ============================================================================
-- Migration: 0003_rls_policies.sql
-- Purpose:  Create RLS policies for all public tables.
--           The backend operates via SUPABASE_SERVICE_KEY (bypasses RLS).
--           These policies enforce defense-in-depth: deny anonymous access,
--           allow authenticated access for catalog reads, and restrict
--           write access to the service role only.
--
-- Pattern:
--   - service role:  bypasses RLS entirely (no policy needed)
--   - anon role:     denied everywhere (no policies = deny when RLS enabled)
--   - authenticated: read-only on catalogs (paises, regiones);
--                    denied on all other tables
-- ============================================================================

-- ============================================================================
-- Catalog tables: authenticated users can READ (needed for seleccion-region)
-- ============================================================================
CREATE POLICY "Authenticated users can read paises"
  ON public.paises FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Authenticated users can read regiones"
  ON public.regiones FOR SELECT
  TO authenticated
  USING (true);

-- ============================================================================
-- Region counters: only service role needs access
--   (no policies = default deny for anon/authenticated)
--   The service role bypasses RLS, so no policy needed here.
-- ============================================================================

-- ============================================================================
-- Core business tables: deny direct access from PostgREST.
--   The backend uses the service key which bypasses RLS.
--   No SELECT/INSERT/UPDATE/DELETE policies = total deny for
--   anon and authenticated roles via PostgREST.
-- ============================================================================
-- usuarios          — no policies needed (service key only)
-- capturistas      — no policies needed (service key only; legacy table)
-- beneficiarios    — no policies needed (service key only)
-- tutores          — no policies needed (service key only)
-- estudios_socioeconomicos — no policies needed (service key only)
-- solicitudes_tecnicas     — no policies needed (service key only)
-- historial_estados         — no policies needed (service key only)
-- region_counters          — no policies needed (service key only)

-- ============================================================================
-- Storage: restrict access to fotos-tecnica bucket
--   The bucket is now private (public=false).
--   Only the backend (service key) can upload and generate signed URLs.
--   No storage policies needed because the service key bypasses storage RLS.
--   This policy allows authenticated users to READ objects in fotos-tecnica,
--   which is only useful if the frontend ever needs direct access (currently
--   it doesn't — all access goes through the signed URL endpoint).
--   We keep it explicit for defense-in-depth: deny by default.
-- ============================================================================
-- Storage policies are separate from table RLS. Since we serve all photos
-- via the authenticated endpoint GET /api/solicitudes/{id}/foto with
-- signed URLs, there is NO need for any storage policy that allows
-- direct public access. The service key handles all uploads and
-- signed URL generation.

-- ============================================================================
-- CRITICAL: Remove any pre-existing dangerous policies
-- ============================================================================
-- A previous policy "Enable read access for all users" on public.usuarios
-- allowed unauthenticated access to the entire usuarios table (including
-- password_hash). This migration removes it.
DROP POLICY IF EXISTS "Enable read access for all users" ON public.usuarios;