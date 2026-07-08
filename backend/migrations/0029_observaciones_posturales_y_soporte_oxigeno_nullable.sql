-- 0029_observaciones_posturales_y_soporte_oxigeno_nullable.sql
-- Issue #161 (reestructuración de borradores):
--   * observaciones_posturales: el textarea de tecnica.html se perdía SIEMPRE —
--     la migración 0013 renombró la columna original a `padecimiento` (que hoy
--     guarda el catálogo de padecimientos) y el texto libre quedó sin columna.
--   * soporte_oxigeno: era NOT NULL DEFAULT FALSE (0018) y el backend forzaba
--     bool(None) → FALSE, por lo que un borrador sin respuesta quedaba como un
--     "No" real y la validación de completitud de /finalizar-registro
--     (soporte_oxigeno IS NULL, issue #162) nunca podía disparar. Se permite
--     NULL para distinguir "sin responder" de "No".
--     Nota: filas existentes conservan FALSE (indistinguible de un "No" real);
--     aceptable porque el dato nunca se capturó como NULL.

ALTER TABLE public.solicitudes_tecnicas
    ADD COLUMN IF NOT EXISTS observaciones_posturales TEXT NULL;

ALTER TABLE public.solicitudes_tecnicas
    ALTER COLUMN soporte_oxigeno DROP NOT NULL,
    ALTER COLUMN soporte_oxigeno DROP DEFAULT;
