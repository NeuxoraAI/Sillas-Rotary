-- 0019: Resolve Supabase advisor index findings.
-- - Drop duplicate organizaciones_miembros(usuario_id) index.
-- - Add missing coverage indexes for procesos_tecnicos user foreign keys.

DROP INDEX IF EXISTS public.idx_org_miembros_user;

CREATE INDEX IF NOT EXISTS idx_procesos_tecnicos_responsable_actual_usuario
ON public.procesos_tecnicos(responsable_actual_usuario_id);

CREATE INDEX IF NOT EXISTS idx_procesos_tecnicos_tecnico_inicio_usuario
ON public.procesos_tecnicos(tecnico_inicio_usuario_id);
