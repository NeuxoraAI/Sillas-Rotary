-- ============================================================================
-- Migration: 0003_rls_policies.sql
-- Purpose:  Define the direct-access RLS posture for Supabase/PostgREST roles.
--           Business authorization is enforced by FastAPI. Direct table access
--           through anon/authenticated PostgREST roles is denied except for
--           explicit catalog reads needed by the frontend.
--
-- Pattern:
--   - backend runtime: connects directly through psycopg2; see
--                      0014_app_runtime_role.sql for the bounded runtime role
--                      and its explicit app_runtime_all policy.
--   - service role:    bypasses RLS entirely; used only for Supabase Storage.
--   - anon role:       denied everywhere (no policies = deny when RLS enabled).
--   - authenticated:   read-only on catalogs (paises, regiones);
--                      denied on all other business tables.
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
-- Region counters: only the trusted backend runtime needs access
--   (no policies here = default deny for anon/authenticated).
-- ============================================================================

-- ============================================================================
-- Core business tables: deny direct access from PostgREST.
--   The backend enforces RBAC/resource ownership in FastAPI and uses the
--   app_runtime policy from 0014_app_runtime_role.sql for direct DB access.
--   No SELECT/INSERT/UPDATE/DELETE policies = total deny for
--   anon and authenticated roles via PostgREST.
-- ============================================================================
-- usuarios          — no direct PostgREST policies needed
-- beneficiarios    — no direct PostgREST policies needed
-- tutores          — no direct PostgREST policies needed
-- estudios_socioeconomicos — no direct PostgREST policies needed
-- solicitudes_tecnicas     — no direct PostgREST policies needed
-- region_counters          — no direct PostgREST policies needed

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
