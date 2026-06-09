-- 0010_add_avatar_url_to_usuarios.sql
-- Objective: Add optional avatar_url column to usuarios for profile avatars.
-- Backward-compatible: NULL by default, existing rows unaffected.

ALTER TABLE public.usuarios
ADD COLUMN IF NOT EXISTS avatar_url TEXT;