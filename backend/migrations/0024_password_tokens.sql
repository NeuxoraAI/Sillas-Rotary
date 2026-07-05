-- ============================================================================
-- Migration: 0024_password_tokens.sql
-- Purpose:  Add password_tokens table for invite-activation and forgot-password
--           reset flows. Tokens are stored as sha256 hex of the raw urlsafe
--           token (raw token travels only in the URL/email, never in the DB).
--           Also makes usuarios.password_hash NULLABLE so admin-created accounts
--           can exist without a password until the user activates via invite link.
--
-- Background: Moving from admin-sets-password to verification-by-delivery.
--             Account starts activo=FALSE with NULL password_hash; setting
--             password via invite link activates the account (proves email
--             ownership). Forgot-password uses tipo='reset', shorter TTL.
--
-- Environment variables consumed by the runtime (backend/utils/email.py):
--   RESEND_API_KEY   — Bearer token for https://api.resend.com (required to send)
--   EMAIL_FROM       — Sender address (default onboarding@resend.dev for dev)
--   APP_BASE_URL     — Base URL used to build activation/reset links in emails
--
-- This is ADDITIVE only (per migrations/README.md rule #3):
--   - New table: password_tokens
--   - ALTER TABLE usuarios: password_hash DROP NOT NULL
--   Both are safe for existing active users (all have non-null password_hash;
--   removing the constraint does not change existing data or behavior).
--
-- FOOTGUN: New table requires its own app_runtime_all RLS policy (app_runtime
--          is NOBYPASSRLS — see 0014). Included in this migration.
-- ============================================================================

BEGIN;

-- 1. Make password_hash nullable (additive — no existing data changes)
ALTER TABLE public.usuarios
    ALTER COLUMN password_hash DROP NOT NULL;

-- 2. Token store
CREATE TABLE IF NOT EXISTS public.password_tokens (
    id           BIGSERIAL PRIMARY KEY,
    usuario_id   INTEGER   NOT NULL
                           REFERENCES public.usuarios(id) ON DELETE CASCADE,
    token_hash   TEXT      NOT NULL UNIQUE,          -- sha256 hex of raw urlsafe token
    tipo         TEXT      NOT NULL
                           CHECK (tipo IN ('invite', 'reset')),
    expires_at   TIMESTAMPTZ NOT NULL,
    used_at      TIMESTAMPTZ,                        -- NULL = unused; set on redemption
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Indexes
--    Primary lookup: hash (always queried by exact hash)
CREATE INDEX IF NOT EXISTS idx_password_tokens_hash
    ON public.password_tokens (token_hash);

--    Compound: invalidate prior tokens of same (usuario_id, tipo) on resend
CREATE INDEX IF NOT EXISTS idx_password_tokens_user_tipo
    ON public.password_tokens (usuario_id, tipo);

-- 4. RLS (FOOTGUN — mandatory for app_runtime NOBYPASSRLS role)
ALTER TABLE public.password_tokens ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS app_runtime_all ON public.password_tokens;
CREATE POLICY app_runtime_all ON public.password_tokens
    FOR ALL TO app_runtime
    USING (true)
    WITH CHECK (true);

COMMIT;
