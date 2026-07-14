# Hoja de Ruta de Migración — Disparadores, Nube y CORS

> **Issue paraguas — no propone migrar ahora.** Este documento existe para que
> las decisiones de infraestructura dejen de tomarse ad-hoc: define la
> secuencia incremental, los disparadores reales que justificarían avanzar de
> fase, deja diferida (no decidida) la elección AWS vs GCP, y especifica cómo
> se configurará CORS de forma segura cuando aplique. Ningún issue de
> infraestructura debe nombrar un proveedor de nube como dependencia
> obligatoria — ver [Criterios AWS vs GCP](#evaluación-aws-vs-gcp-diferida).

---

## Estado actual

- **Compute:** Vercel serverless, vía el shim `api/index.py` (ver `vercel.json`).
  Desde el issue #84 existe también un `Dockerfile` standalone que corre la
  misma `backend/main.py` con uvicorn — Vercel sigue siendo el runtime activo;
  el Dockerfile es la puerta de salida cuando se decida moverse, no un cambio
  de runtime en sí.
- **Config/secretos:** centralizados en `backend/settings.py` (issue #83) — un
  solo lugar que cambiar si el origen de los secretos deja de ser variables de
  entorno.
- **Datos y blobs:** PostgreSQL directo vía `psycopg2` + Supabase Storage para
  imágenes/documentos (ver `CLAUDE.md`).
- **Frontend:** HTML/CSS/JS estático, servido por la **misma** app FastAPI
  (`StaticFiles` en `backend/main.py`) bajo el **mismo origen** que la API. Por
  eso hoy **no existe `CORSMiddleware`** en `main.py`: no hace falta cuando
  frontend y backend comparten dominio. La fila de la tabla de seguridad del
  `README.md` que decía "CORS configurado en `main.py`" era inexacta y quedó
  corregida para reflejar esto.

## Secuencia incremental (A → B → C)

No se salta de fase. Cada fase solo se activa si su disparador real ocurre
(ver siguiente sección) — no por anticipación.

| Fase | Descripción | Estado |
|---|---|---|
| **A — Hoy** | Vercel serverless + Supabase, frontend y API en el mismo origen. | ✅ actual |
| **B — Portabilidad de compute (preparación)** | Config centralizada (#83) + imagen Docker agnóstica de runtime (#84). Vercel sigue siendo el runtime activo; esto solo reduce el costo de moverse después. | ✅ hecho |
| **C — Separación de compute** | Mover el proceso backend de Vercel serverless a un runtime de contenedores administrado (AWS App Runner, Google Cloud Run, ECS, etc.), usando la misma imagen de `Dockerfile`. Supabase no cambia. | ⏳ diferida — requiere un disparador |
| **D — Separación de frontend / entrada de cliente móvil** | El frontend deja de compartir origen con la API (SPA separada, CDN propio, o app móvil nativa consumiendo la misma API REST). Aquí es donde `CORSMiddleware` deja de ser opcional. | ⏳ diferida — requiere un disparador |
| **E — Migración de datos/almacenamiento** | Solo si un disparador de residencia de datos u otro requisito regulatorio lo exige; hoy no hay ninguna señal de esto. | ⏳ no planeada |

## Disparadores reales

Estos son los **únicos** motivos válidos para avanzar de fase. "Se vería bien
tener más control", curiosidad tecnológica, o preocupación genérica de
escalabilidad sin un problema medido **no** son disparadores.

1. **Residencia de datos por ley** — un requisito regulatorio (de alguna
   jurisdicción donde opere Ecosistema VIDA UG) que obligue a alojar datos de
   beneficiarios en una región o proveedor específico que Supabase/Vercel no
   puedan garantizar hoy. → dispara Fase C y/o E.
2. **Costo medido** — cuando el tráfico o almacenamiento reales (no
   proyectados) hacen que el plan de Vercel y/o Supabase sea más caro que
   operar el mismo Docker en un runtime de contenedores administrado. →
   dispara Fase C.
3. **Lanzamiento de la app móvil** — en cuanto exista un cliente móvil nativo
   real consumiendo la API, el "mismo origen" deja de ser cierto por
   definición. → dispara Fase D (CORS).
4. **Límites técnicos medidos de Vercel serverless** — cold starts, timeouts o
   límites de tamaño de payload que afecten un SLA real observado (no
   hipotético). → dispara Fase C.

Si ninguno de estos ha ocurrido, la respuesta correcta ante "¿deberíamos
migrar a X?" es **no todavía**.

## Evaluación AWS vs GCP (diferida)

**No se decide en este documento.** Cuando un disparador de la Fase C ocurra,
evaluar contra estos criterios y registrar la decisión final (con fecha y
motivo) en una sección nueva de este mismo archivo:

- **Costo total** para el volumen real medido en ese momento (compute +
  transferencia + logging), no listas de precios genéricas.
- **Curva de adopción del equipo** — qué tan familiarizado está el equipo de
  NEUXORA con cada plataforma en el momento de decidir.
- **Compatibilidad sin cambios** — tanto AWS App Runner como Google Cloud Run
  aceptan la misma imagen del `Dockerfile` (#84) sin modificaciones; la
  conexión a Supabase (`psycopg2` directo + HTTPS a Supabase Storage) es
  agnóstica de nube, así que no hay lock-in de datos en esta decisión.
- **Residencia de datos**, si el disparador #1 de la sección anterior está
  activo.
- **Soporte/SLA en la región** donde estén los beneficiarios (México / USA,
  según `paises`/`regiones` — ver `CLAUDE.md`).

Ningún otro issue de infraestructura de este repo debe asumir AWS o GCP como
dependencia obligatoria mientras esta decisión siga diferida.

## CORS seguro — especificación para la Fase D

Hoy no hace falta `CORSMiddleware` porque front y API comparten origen. Esta
sección especifica cómo se configurará **cuando** la Fase D se active (app
móvil o frontend separado) — no se implementa todavía.

```python
# backend/main.py — SOLO cuando la Fase D esté activa
from fastapi.middleware.cors import CORSMiddleware

import settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins(),  # allowlist explícita — nunca "*"
    allow_credentials=False,   # el JWT viaja en el header Authorization, no en cookies
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

Reglas obligatorias cuando se implemente:

- **Allowlist explícita de orígenes**, nunca `"*"`. Se lee desde
  `backend/settings.py` (issue #83) vía una nueva función
  `cors_allowed_origins()` que parsee una variable `CORS_ALLOWED_ORIGINS`
  (orígenes separados por coma) — mismo patrón que el resto de la config
  centralizada, para no reintroducir lecturas de `os.environ` dispersas.
- **`allow_credentials=False`** mientras el JWT siga viajando en el header
  `Authorization` (ver `docs/JWT_STORAGE_SECURITY.md`). La especificación CORS
  prohíbe combinar `allow_origins=["*"]` con `allow_credentials=True`; si en
  el futuro se migra el JWT a cookies `httpOnly` (documentado como opción en
  `JWT_STORAGE_SECURITY.md`), esta sección debe actualizarse junto con esa
  migración.
- **Métodos y headers acotados** a lo que la API realmente expone — no usar
  `["*"]` en `allow_methods`/`allow_headers`.
- **Prueba obligatoria antes de mergear el cambio:** un test que confirme que
  un origen fuera de la allowlist no recibe los headers `Access-Control-*` (y
  que uno permitido sí los recibe). Este documento no crea ese test porque
  CORS no está implementado todavía (ver "Pruebas sugeridas" del issue #86).

## Qué NO hacer todavía

- No elegir AWS ni GCP.
- No agregar `CORSMiddleware` — agregaría superficie y complejidad sin un
  disparador real.
- No mover el compute fuera de Vercel sin que uno de los disparadores de
  arriba haya ocurrido y esté documentado.

## Referencias relacionadas

- Issue #83 / `backend/settings.py` — módulo único de configuración/secretos.
- Issue #84 / `Dockerfile` — misma imagen corre en cualquier runtime de
  contenedores.
- `docs/JWT_STORAGE_SECURITY.md` — decisión vigente sobre almacenamiento de
  JWT; relevante si `allow_credentials` cambia de valor en el futuro.
