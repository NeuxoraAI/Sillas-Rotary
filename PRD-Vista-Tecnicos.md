# PRD — Vista principal para usuarios técnicos

Este documento define la nueva vista `vista_tecnicos.html` como pantalla principal operativa para usuarios con rol `tecnico`.

## Resumen ejecutivo

Hoy `front/tecnica.html` funciona como **formulario de solicitud técnica individual**. No resuelve bien la necesidad operativa del equipo técnico de **consultar beneficiarios, revisar información clínica relevante y controlar el estado de cada silla**.

Se propone crear una nueva vista principal llamada `vista_tecnicos.html` que permita:

1. Buscar beneficiarios por múltiples criterios.
2. Ver un listado útil para trabajo diario.
3. Abrir el detalle completo de cada beneficiario con información relevante.
4. Marcar el estado del proceso técnico como `sin_iniciar`, `en_proceso` o `finalizada`.
5. Mantener `tecnica.html` como formulario técnico específico, no como tablero principal.

---

## 1. Objetivo

Construir una vista principal para técnicos que centralice la consulta y seguimiento de beneficiarios, permitiendo a los usuarios del rol `tecnico` trabajar sobre casos reales sin depender de recordar IDs, navegar a ciegas o usar el formulario técnico como pseudo-listado.

---

## 2. Problema actual

### Estado actual confirmado

- `front/tecnica.html` es un formulario de captura de solicitud técnica.
- `backend/routers/tecnica.py` YA expone endpoints para listar beneficiarios técnicos, ver detalle y operar estados de proceso técnico.
- El endpoint actual de listado (`GET /api/tecnica/beneficiarios`) todavía es limitado para la necesidad del negocio, porque hoy sólo contempla búsqueda general y filtros básicos (`q`, `sede`, `estado`, `revision_pendiente`).

### Dolor operativo

El técnico necesita una vista centrada en el beneficiario, no en la captura aislada del formulario. Hoy falta una pantalla que le permita:

- encontrar rápidamente a un beneficiario,
- ver medidas, peso, estatura, foto y contexto relevante,
- entender si la silla está pendiente, en proceso o finalizada,
- llevar control operativo del avance técnico.

---

## 3. Usuarios

### Usuario principal
- `tecnico`

### Usuario secundario
- `admin` con acceso de consulta, si se decide habilitarlo en la vista o reutilizar los endpoints de detalle.

---

## 4. Resultado esperado

Al iniciar sesión como técnico, el usuario debe poder llegar a una pantalla principal donde vea una bandeja/listado de beneficiarios y pueda operar su flujo diario desde ahí.

---

## 5. Alcance

### Incluido

- Nueva vista `front/vista_tecnicos.html`
- Listado de beneficiarios para trabajo técnico
- Buscador y filtros
- Vista de detalle por beneficiario
- Visualización de datos relevantes del estudio y solicitud técnica
- Visualización de foto del paciente cuando exista
- Acciones de estado:
  - iniciar proceso
  - marcar silla en proceso
  - marcar silla finalizada
- Indicadores visuales de estado
- Navegación desde login/selección de región hacia la nueva vista principal para rol `tecnico`

### Fuera de alcance en esta iteración

- Reemplazar o eliminar `tecnica.html`
- Generación real de PDF final con layout formal
- Edición completa del estudio socioeconómico desde la vista técnica
- Workflow multi-etapa complejo con auditoría avanzada
- Kanban, drag & drop o dashboard analítico

---

## 6. Requerimientos funcionales

### RF-01 — Acceso a vista principal de técnicos

Cuando el usuario autenticado tenga rol `tecnico`, el flujo principal debe llevarlo a `vista_tecnicos.html` como pantalla operativa principal.

Reglas:
- el acceso requiere sesión válida,
- si no hay sesión válida debe redirigir a `login.html`,
- la vista debe respetar el contexto seleccionado en `region_ctx` si ese dato participa en filtros o navegación.

---

### RF-02 — Listado de beneficiarios técnicos

La vista debe mostrar un listado de beneficiarios apto para operación diaria.

Cada fila o tarjeta debe incluir como mínimo:

- nombre del beneficiario,
- folio,
- país,
- región,
- ciudad,
- sede,
- peso,
- estatura,
- estado técnico actual,
- indicador de foto disponible/no disponible,
- acción para ver detalle.

Notas:
- si algún dato no existe, debe mostrarse como “No capturado” o equivalente legible,
- el listado debe priorizar legibilidad mobile-first.

---

### RF-03 — Búsqueda libre

La vista debe incluir una búsqueda libre por texto que permita localizar beneficiarios por coincidencia parcial en campos relevantes.

Campos mínimos incluidos en búsqueda libre:

- nombre,
- folio,
- sede,
- ciudad,
- región,
- país.

Comportamiento:
- debe tolerar mayúsculas/minúsculas,
- debe permitir coincidencias parciales,
- debe responder sin recargar toda la aplicación.

---

### RF-04 — Filtros estructurados

La vista debe permitir filtrar por atributos concretos.

Filtros requeridos para esta iniciativa:

- país,
- región,
- ciudad,
- sede,
- estado técnico,
- rango de peso,
- rango de estatura,
- con foto / sin foto.

Notas:
- país/región/ciudad/sede pueden convivir con la búsqueda libre,
- peso y estatura deben manejarse como rangos, no como texto exacto,
- el estado técnico mínimo esperado es:
  - `sin_iniciar`
  - `en_proceso`
  - `finalizada`

---

### RF-05 — Detalle de beneficiario

Al abrir un beneficiario, la vista debe mostrar una ficha completa con información relevante para la operación técnica.

Contenido mínimo del detalle:

#### Identificación
- nombre completo,
- folio,
- país,
- región,
- ciudad,
- sede,
- diagnóstico si existe.

#### Datos físicos / clínicos relevantes
- peso,
- estatura,
- medidas técnicas capturadas,
- control de tronco,
- control de cabeza,
- observaciones posturales.

#### Evidencia visual
- foto del paciente si existe,
- indicador claro cuando no exista foto.

#### Contexto social útil
- tutores o responsables principales,
- teléfono(s) de contacto si están disponibles,
- entidad solicitante si existe.

#### Estado del proceso técnico
- estado actual,
- responsable actual si existe,
- fecha de inicio si existe,
- fecha de último movimiento si existe,
- historial básico de participantes si ya está disponible.

---

### RF-06 — Cambio de estado técnico

Desde la vista de detalle, el técnico debe poder operar el estado del caso.

Acciones requeridas:

1. **Iniciar proceso**
   - aplica cuando el estado es `sin_iniciar`
   - resultado: pasa a `en_proceso`

2. **Marcar en proceso**
   - si ya existe proceso iniciado, debe permitir continuar o reafirmar el trabajo activo sin romper el flujo
   - resultado esperado: mantener `en_proceso`

3. **Marcar finalizada**
   - aplica cuando el caso está siendo trabajado
   - resultado: pasa a `finalizada`

Reglas:
- sólo usuarios con rol `tecnico` pueden ejecutar estas acciones,
- la UI debe confirmar visualmente el cambio,
- tras la acción, el listado y el detalle deben reflejar el nuevo estado sin inconsistencias.

---

### RF-07 — Vista sólo lectura de base documental

La información socioeconómica y técnica histórica mostrada al técnico debe tratarse como **consulta** en esta iteración.

Reglas:
- no se edita directamente desde `vista_tecnicos.html`,
- si luego se requiere edición, se definirá como cambio aparte,
- el técnico sí puede usar esta vista para decidir si inicia o finaliza el proceso.

---

### RF-08 — Relación con `tecnica.html`

`tecnica.html` permanecerá como formulario técnico especializado o de captura puntual.

Regla de producto:
- `vista_tecnicos.html` = bandeja principal / seguimiento / consulta
- `tecnica.html` = formulario técnico específico

---

## 7. Requerimientos de datos y backend

### Estado actual confirmado del backend

Ya existen estos endpoints:

- `GET /api/tecnica/beneficiarios`
- `GET /api/tecnica/beneficiarios/{beneficiario_id}`
- `POST /api/tecnica/beneficiarios/{beneficiario_id}/iniciar`
- `POST /api/tecnica/procesos/{proceso_id}/continuar`
- `POST /api/tecnica/procesos/{proceso_id}/finalizar`

El detalle actual ya arma un snapshot con:

- `beneficiario`
- `tutores`
- `estudio`
- `solicitud`
- `proceso_tecnico`
- `participantes`

### Gap confirmado

El listado actual NO cubre todavía todos los filtros/datos que el negocio necesita.

### RB-01 — Ampliar el endpoint de listado técnico

El backend debe ampliar `GET /api/tecnica/beneficiarios` para soportar al menos:

- búsqueda libre robusta,
- filtro por país,
- filtro por región,
- filtro por ciudad,
- filtro por sede,
- filtro por estado técnico,
- filtro por rango de peso,
- filtro por rango de estatura,
- filtro por presencia de foto.

Además, la respuesta del listado debe incluir datos suficientes para no obligar a abrir cada detalle solo para triage.

Campos mínimos recomendados en cada item:

- `beneficiario_id`
- `nombre`
- `folio`
- `pais_nombre`
- `region_nombre`
- `ciudad`
- `sede`
- `peso_kg`
- `altura_total`
- `unidad_medida`
- `foto_url` o `tiene_foto`
- `estado`
- `revision_pendiente`
- `proceso_id`

---

### RB-02 — Reutilizar el detalle técnico existente

Siempre que sea posible, se debe reutilizar `GET /api/tecnica/beneficiarios/{beneficiario_id}` como fuente principal del panel detalle.

Si faltan campos para la UI definida, el endpoint debe extenderse sin romper compatibilidad.

---

### RB-03 — Normalización de “estatura”

El negocio pide búsqueda por estatura, pero el modelo actual técnico parece usar `altura_total_in` y `unidad_medida`.

Decisión funcional:
- para esta iniciativa, “estatura” se interpretará como la medida técnica de altura total del beneficiario,
- backend y frontend deben mostrarla con su unidad,
- los filtros por rango deben operar sobre un valor normalizado o sobre una convención única definida por backend.

Recomendación:
- normalizar internamente a una unidad base para filtrar consistentemente.

---

## 8. UX / UI esperada

## Quick path

1. El técnico entra a `vista_tecnicos.html`.
2. Ve buscador, filtros y listado.
3. Selecciona un beneficiario.
4. Revisa ficha completa, foto, medidas y estado.
5. Marca el caso como `en_proceso` o `finalizada`.

### Estructura recomendada de la pantalla

#### Zona superior
- título de la vista,
- nombre del técnico autenticado,
- botón de cerrar sesión,
- resumen rápido de conteos por estado.

#### Zona de filtros
- input de búsqueda libre,
- selects para país, región, ciudad, sede, estado,
- inputs para rangos de peso y estatura,
- toggle con foto / sin foto,
- botón limpiar filtros.

#### Zona de resultados
- listado en tabla o tarjetas,
- estado visible con badge,
- acceso rápido a detalle.

#### Zona de detalle
- panel lateral o bloque expandido,
- secciones agrupadas:
  - identificación
  - contacto
  - datos socioeconómicos clave
  - datos técnicos
  - fotografía
  - estado del proceso
  - acciones.

---

## 9. Requerimientos no funcionales

### RNF-01 — Mobile-first
- la vista debe funcionar en teléfono y tablet,
- filtros y tarjetas deben seguir siendo operables en pantallas pequeñas.

### RNF-02 — Velocidad percibida
- la búsqueda y filtrado deben sentirse ágiles,
- la UI debe mostrar estados de carga y vacío.

### RNF-03 — Claridad operacional
- el técnico debe entender el estado de un caso sin abrir múltiples pantallas,
- los badges y acciones deben evitar ambigüedad.

### RNF-04 — Seguridad
- todas las llamadas deben usar `Authorization: Bearer {token}`,
- acciones de cambio de estado restringidas a rol `tecnico`.

---

## 10. Reglas de negocio

### RN-01
Un beneficiario puede existir en la bandeja técnica aunque todavía no tenga proceso técnico iniciado.

### RN-02
Si no existe proceso técnico, el estado visible debe tratarse como `sin_iniciar`.

### RN-03
El técnico puede iniciar un proceso una sola vez por beneficiario, salvo que el backend ya contemple una transición explícita distinta en el futuro.

### RN-04
Finalizar un caso debe dejarlo claramente marcado como `finalizada` en el listado y en el detalle.

### RN-05
La foto del paciente NO es obligatoria para mostrar el caso, pero sí debe señalarse claramente si no existe.

---

## 11. Criterios de aceptación

### Checklist funcional

- [ ] Un técnico autenticado entra a una vista principal distinta de `tecnica.html`.
- [ ] La vista muestra un listado de beneficiarios útil para operación real.
- [ ] Se puede buscar por nombre, folio, país, región, ciudad y sede.
- [ ] Se puede filtrar por estado técnico.
- [ ] Se puede filtrar por rangos de peso y estatura.
- [ ] Se puede distinguir si existe foto del paciente.
- [ ] Al abrir un beneficiario se ven medidas, peso, estatura, foto y datos relevantes.
- [ ] El técnico puede cambiar el estado a `en_proceso`.
- [ ] El técnico puede cambiar el estado a `finalizada`.
- [ ] El listado refleja los cambios de estado sin inconsistencias.

---

## 12. Dependencias técnicas

- `front/login.html` y/o `front/seleccion-region.html` deben redirigir correctamente al rol `tecnico`
- `backend/routers/tecnica.py` debe ampliar el contrato del listado
- puede requerirse ampliar joins con:
  - `beneficiarios`
  - `estudios_socioeconomicos`
  - `solicitudes_tecnicas`
  - `procesos_tecnicos`
  - `regiones`
  - `paises`

---

## 13. Riesgos y consideraciones

| Riesgo | Impacto | Mitigación |
|-------|---------|------------|
| El listado actual no trae todos los campos necesarios | La UI queda pobre o fuerza demasiadas consultas | Ampliar contrato del endpoint antes de cerrar frontend |
| Peso/estatura pueden venir de distintas fuentes o unidades | Filtros inconsistentes | Normalizar unidad en backend |
| País/región/ciudad pueden estar repartidos entre tablas distintas | Filtros incompletos | Definir joins y fuente de verdad por campo |
| Reutilizar `tecnica.html` como detalle podría mezclar conceptos | Confusión de UX | Mantener clara separación entre vista principal y formulario |

---

## 14. Siguiente paso recomendado

Con este PRD, el siguiente entregable correcto NO es escribir código directo a ciegas. El siguiente paso sano es:

1. diseñar contrato de datos de `vista_tecnicos`,
2. validar qué campos ya entrega backend y cuáles faltan,
3. partir la implementación en backend + frontend.
