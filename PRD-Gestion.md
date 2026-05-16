# PRD: Orquestación de `gestion.html`
## Resumen ejecutivo
Se requiere introducir una nueva pantalla `gestion.html` como tercer y último paso del flujo de captura del rol `capturista`, centralizando 9 campos que hoy están distribuidos entre `socioeconomico.html` y `tecnica.html`.
La implementación debe preservar íntegramente los contratos actuales del sistema: nombres de campos, atributos `name`, IDs, validaciones frontend/backend, comportamiento de borrador, endpoints y estilo visual existente.
El nuevo flujo objetivo será:
`seleccion-region.html -> socioeconomico.html -> tecnica.html -> gestion.html`
`gestion.html` será la pantalla final desde la que se guardará el cierre del registro completo.
---
## Objetivo
Crear `front/gestion.html` para centralizar los campos administrativos y de cierre del proceso, eliminándolos de sus ubicaciones actuales y manteniendo el comportamiento funcional existente.
---
## Objetivos específicos
1. Reubicar 6 campos desde `socioeconomico.html` hacia `gestion.html`.
2. Reubicar 3 campos desde `tecnica.html` hacia `gestion.html`.
3. Eliminar los campos de sus archivos originales para evitar duplicidad.
4. Mantener el patrón actual de navegación por guardado y redirección.
5. Convertir `gestion.html` en el último paso del flujo de captura.
6. Conservar los endpoints existentes sin crear contratos alternos.
7. Crear un menú nuevo específico para `gestion.html`.
---
## Alcance
### Incluye
- Creación de `front/gestion.html`
- Reubicación de 9 campos
- Reubicación de la lógica JS exclusiva asociada a esos campos
- Ajuste de navegación entre pantallas
- Ajuste del cierre del flujo
- Persistencia de borrador desde `gestion.html`
- Guardado definitivo desde `gestion.html`
- Creación de un menú nuevo local para `gestion.html`
### No incluye
- Refactor general de layouts
- Creación de un stepper nuevo
- Cambios de base de datos
- Cambios de endpoints
- Cambios de validaciones
- Cambios de RBAC backend
- Participación de `admin` o `tecnico` en este flujo
- Cambio de nombres de campos, IDs o `name`
---
## Usuarios involucrados
### Usuario principal
- `capturista`
### Usuarios fuera de este flujo
- `admin`
- `tecnico`
Regla confirmada: solo el `capturista` recorre el flujo completo de captura.
---
## Estado actual del sistema
### Flujo actual
- `seleccion-region.html` redirige a:
  - `socioeconomico.html` para `capturista`
  - `tecnica.html` para `tecnico`
- `socioeconomico.html` hoy:
  - captura datos del beneficiario y tutores
  - incluye 6 campos de cierre de estudio
  - guarda contra `/api/estudios`
  - al completar redirige a `tecnica.html`
- `tecnica.html` hoy:
  - captura datos técnicos
  - incluye 3 campos de gestión de donación
  - guarda contra `/api/solicitudes`
  - al completar redirige a `socioeconomico.html`
### Observaciones verificadas
- No existe `base.html` ni layout compartido.
- No existe stepper entre socioeconómico y técnica.
- No existe menú de navegación reutilizable en pantallas de captura.
- Los campos a mover pertenecen a dos contratos backend distintos:
  - `/api/estudios`
  - `/api/solicitudes`
---
## Nuevo flujo objetivo
### Flujo final deseado
`seleccion-region.html -> socioeconomico.html -> tecnica.html -> gestion.html`
### Comportamiento esperado
1. El capturista selecciona región.
2. Captura el estudio socioeconómico.
3. Avanza a técnica.
4. Captura la información técnica.
5. Avanza a gestión.
6. En gestión captura los campos finales reubicados.
7. Puede guardar borrador.
8. Puede guardar de forma definitiva.
9. Al guardar definitivamente:
   - se persisten datos de estudio
   - se persisten datos de solicitud
   - se marca cierre final
   - se limpia estado local operativo
   - se reinicia el flujo en `socioeconomico.html`
---
## Campos a reubicar
## Sección A: Información del Estudio
Origen: `front/socioeconomico.html`
1. Elaboró el estudio
2. Fecha del estudio
3. Sede
4. Ciudad del registro
5. ¿El paciente ha tenido silla previamente?
6. ¿Cómo la obtuvo?
### Nombres de campo implicados
- `elaboro_estudio`
- `fecha_estudio`
- `sede`
- `ciudad_registro`
- `silla_previa`
- `como_obtuvo_silla`
---
## Sección B: Información de la Solicitud
Origen: `front/tecnica.html`
1. Entidad Solicitante
2. Prioridad
3. Justificación para silla de ruedas
### Nombres de campo implicados
- `entidad_solicitante`
- `prioridad`
- `justificacion`
---
## Reglas funcionales obligatorias
1. Los campos deben moverse, no copiarse.
2. Al finalizar, cada campo debe existir únicamente en `gestion.html`.
3. No se pueden cambiar:
   - `name`
   - `id`
   - validaciones HTML
   - comportamiento JS asociado
   - contratos del backend
4. No se deben introducir nuevas validaciones.
5. No se deben cambiar endpoints.
6. No se deben alterar reglas actuales de `borrador` y `completo`.
7. No se debe introducir stepper visual nuevo.
8. Debe mantenerse el patrón actual de navegación por botones y redirecciones.
---
## Estructura requerida para `gestion.html`
## Sección A — Información del Estudio
Debe contener exactamente los 6 campos provenientes de `socioeconomico.html`.
### Requisitos
- Conservar bloque HTML exacto
- Conservar clases
- Conservar readonly/disabled si aplica
- Conservar reglas condicionales
- Mantener la misma jerarquía visual y grid del origen
## Sección B — Información de la Solicitud
Debe contener exactamente los 3 campos provenientes de `tecnica.html`.
### Requisitos
- Conservar bloque HTML exacto
- Conservar clases
- Conservar radios/textarea/inputs sin cambios
- Mantener la misma jerarquía visual y grid del origen
---
## Navegación requerida
## Entre pantallas
### `socioeconomico.html`
- Al completar, sigue redirigiendo a `tecnica.html`
### `tecnica.html`
- Debe dejar de redirigir a `socioeconomico.html`
- Debe redirigir a `gestion.html`
### `gestion.html`
- Debe incluir acción de retroceso a `tecnica.html`
- Debe ser el último paso del flujo
---
## Botones requeridos en `gestion.html`
Orden visual requerido:
`[Anterior]   [Guardar borrador]   [Guardar datos de gestión]`
## 1. Botón "Anterior"
### Comportamiento
- Redirige a `tecnica.html`
## 2. Botón "Guardar borrador"
### Comportamiento
- Persiste la información actual sin exigir obligatorios
- Mantiene el patrón existente del proyecto
- Debe guardar tanto datos de estudio como de solicitud
## 3. Botón "Guardar datos de gestión"
### Comportamiento
- Acción principal de la página
- Valida obligatorios usando el mismo mecanismo existente
- Persiste ambos grupos de datos
- Cierra el registro completo
- Limpia estado local operativo
- Redirige a `socioeconomico.html` con flujo reiniciado
---
## Menú requerido
Se debe crear un menú nuevo específico para `gestion.html`.
### Requisitos del menú
- Debe incluir el ítem `Gestión`
- Debe respetar la estética del sistema existente
- No debe implicar refactorización global del resto de pantallas
- Su objetivo es dar contexto local al usuario dentro del último paso
### Restricción
No existe hoy un menú compartido en pantallas de captura, por lo tanto este menú será local a `gestion.html`.
---
## Orquestación técnica requerida
## Principio central
`gestion.html` no será una pantalla meramente visual; será un orquestador final que coordina dos contratos ya existentes:
- `/api/estudios`
- `/api/solicitudes`
---
## Persistencia de estudio
Los 6 campos del bloque “Información del Estudio” pertenecen a la lógica de estudio y deben seguir persistiendo mediante `/api/estudios`.
### Operaciones esperadas
- Rehidratación de borrador desde `/api/estudios/{id}`
- PATCH del estudio desde `gestion.html`
- Conservación de la lógica de:
  - `elaboro_estudio`
  - `sede`
  - `ciudad_registro`
  - `silla_previa`
  - `como_obtuvo_silla`
  - `fecha_estudio`
---
## Persistencia de solicitud
Los 3 campos del bloque “Información de la Solicitud” pertenecen a la lógica de solicitud técnica y deben seguir persistiendo mediante `/api/solicitudes`.
### Operaciones esperadas
- Rehidratación de borrador desde `/api/solicitudes/{id}`
- PATCH de la solicitud desde `gestion.html`
- Conservación de la lógica de:
  - `entidad_solicitante`
  - `prioridad`
  - `justificacion`
---
## Reglas de guardado en `gestion.html`
## Guardar borrador
Debe realizar:
1. Lectura de `estudio_id` desde `localStorage`
2. Lectura de `solicitud_id` desde `localStorage`
3. PATCH a `/api/estudios/{id}` con `status: "borrador"`
4. PATCH a `/api/solicitudes/{id}` con `status: "borrador"`
5. Persistencia parcial sin obligar completitud
## Guardado definitivo
Debe realizar:
1. Validación del formulario con el mismo mecanismo actual
2. PATCH a `/api/estudios/{id}` con:
   - datos del bloque de estudio
   - `status: "completo"`
3. PATCH a `/api/solicitudes/{id}` con:
   - datos del bloque de solicitud
   - `status: "completo"`
4. Confirmación de éxito en ambos endpoints
5. Limpieza del estado local operativo
6. Redirección a `socioeconomico.html`
---
## Regla de consistencia transaccional a nivel frontend
El cierre del flujo debe considerarse exitoso SOLO si ambos guardados finales terminan correctamente.
### Si un guardado falla
- No se debe limpiar `localStorage`
- No se debe redirigir
- Debe mostrarse error
- Debe preservarse la capacidad de reintento
---
## Limpieza requerida en archivos origen
## En `socioeconomico.html`
### Eliminar
- HTML de los 6 campos reubicados
- Mensajes y bloques asociados exclusivamente a esos campos
- Listeners exclusivos
- Inicialización exclusiva
- Referencias DOM que queden huérfanas
### Conservar
- lógica compartida del formulario
- validaciones de beneficiario
- validaciones de tutores
- integración general con estudio
- navegación a técnica
---
## En `tecnica.html`
### Eliminar
- HTML de `entidad_solicitante`
- HTML de `prioridad`
- HTML de `justificacion`
- Rehidratación exclusiva de esos campos
- Lectura de esos campos para payload si ya no viven ahí
- Referencias DOM exclusivas que queden huérfanas
### Conservar
- validaciones técnicas
- foto
- medidas
- persistencia de solicitud
- integración principal con `/api/solicitudes`
---
## Riesgos y consideraciones
## Riesgo 1: dependencia actual del contrato de estudio
Hoy algunos datos del estudio se preparan desde `socioeconomico.html`. Al mover campos al último paso, la implementación deberá conservar compatibilidad sin romper el guardado intermedio.
## Riesgo 2: semántica de `status`
Actualmente `tecnica.html` usa `status: "completo"` y reinicia flujo. Con `gestion.html`, el cierre real del caso se desplaza al nuevo último paso. La implementación debe alinear esa transición sin alterar el contrato backend.
## Riesgo 3: ausencia de menú existente
Como no existe menú reutilizable en las pantallas de captura, habrá que construir un menú local sin propagar una refactorización innecesaria.
---
## Criterios de aceptación
- [ ] Existe un nuevo archivo `front/gestion.html`
- [ ] `gestion.html` contiene dos secciones:
  - [ ] Información del Estudio
  - [ ] Información de la Solicitud
- [ ] Los 6 campos del estudio ya no aparecen en `socioeconomico.html`
- [ ] Los 3 campos de solicitud ya no aparecen en `tecnica.html`
- [ ] Los 9 campos existen únicamente en `gestion.html`
- [ ] Se conserva el mismo `name`, `id`, clases y validaciones de cada campo
- [ ] `socioeconomico.html` sigue avanzando a `tecnica.html`
- [ ] `tecnica.html` ahora avanza a `gestion.html`
- [ ] `gestion.html` permite volver a `tecnica.html`
- [ ] `gestion.html` guarda borrador usando ambos endpoints
- [ ] `gestion.html` guarda definitivo usando ambos endpoints
- [ ] El cierre exitoso limpia estado local y reinicia en `socioeconomico.html`
- [ ] No quedan referencias JS huérfanas en archivos origen
- [ ] No se cambian endpoints
- [ ] No se cambian validaciones
- [ ] No se crea stepper nuevo
- [ ] El flujo completo sigue siendo exclusivo de `capturista`
---
## Requerimientos técnicos inmutables
1. No cambiar nombres de campos.
2. No cambiar IDs.
3. No cambiar atributos `name`.
4. No cambiar endpoints.
5. No cambiar validaciones frontend.
6. No cambiar validaciones backend.
7. No crear estilos globales nuevos.
8. No dejar duplicidad de campos.
9. No eliminar lógica compartida que siga siendo usada por otros campos.
---
## Definición de éxito
La iniciativa se considerará exitosa cuando el capturista pueda completar el flujo:
`socioeconomico -> tecnica -> gestion`
y `gestion.html` se convierta en el único punto de captura de los 9 campos reubicados, manteniendo intacta la compatibilidad funcional y contractual del sistema existente.