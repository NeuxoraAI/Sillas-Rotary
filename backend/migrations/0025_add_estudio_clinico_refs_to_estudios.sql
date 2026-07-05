-- 0025: Persist the clinical study document on estudios_socioeconomicos.
-- The tecnica UI captures this file, but it is a study document alongside
-- credencial and comprobante_domicilio, so drafts must survive reloads through
-- the estudio record as well.

ALTER TABLE public.estudios_socioeconomicos
    ADD COLUMN IF NOT EXISTS estudio_clinico_path text,
    ADD COLUMN IF NOT EXISTS estudio_clinico_url text;

-- Preserve any references already written by the interim implementation on
-- solicitudes_tecnicas.
UPDATE public.estudios_socioeconomicos e
SET
    estudio_clinico_path = COALESCE(e.estudio_clinico_path, st.estudio_clinico_path),
    estudio_clinico_url = COALESCE(e.estudio_clinico_url, st.estudio_clinico_url)
FROM public.solicitudes_tecnicas st
WHERE st.beneficiario_id = e.beneficiario_id
  AND (e.estudio_clinico_path IS NULL OR e.estudio_clinico_url IS NULL)
  AND (st.estudio_clinico_path IS NOT NULL OR st.estudio_clinico_url IS NOT NULL);
