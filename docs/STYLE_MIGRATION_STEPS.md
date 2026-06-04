# Guía de pasos — migración de estilo al estado actual

Este documento resume ÚNICAMENTE los pasos de estilo aplicados desde que se pidió actualizar la rama y unificar la apariencia con la paleta morado/naranja.

## Objetivo visual

Unificar las páginas del sistema para que usen:

- color principal morado: `#51274b`
- variante morado sombra: `#3d1d39`
- variante morado profundo: `#2f162c`
- acento cálido/naranja: `#B9844D`
- variante cálida sombra: `#8f6338`

Y además:

- separar estilos inline a archivos CSS dedicados
- mantener `tailwind.config` inline cuando la página usa Tailwind por CDN
- usar sombras suaves en cards, inputs, badges, headers y footers
- mantener textos de inputs en colores oscuros sobre fondos claros

---

## Paso 1 — actualizar la rama antes de tocar estilos

1. Posicionarse en la rama de trabajo.
2. Actualizarla desde la rama base definida para ese momento.
3. Resolver conflictos priorizando la base elegida cuando el objetivo es alinear visualmente la rama.

> En este caso, la rama de trabajo quedó sincronizada y luego se continuó con la capa de estilo.

---

## Paso 2 — definir la paleta visual común

En cada página que se homogenice, definir o reutilizar estos tokens:

- `primary` / `ug-blue`: `#51274b`
- `ug-blue-shadow`: `#3d1d39`
- `ug-blue-deep`: `#2f162c`
- `secondary` / `ug-yellow`: `#B9844D`
- `ug-yellow-shadow`: `#8f6338`

Si la página tiene CSS dedicado, también crear variables CSS equivalentes, por ejemplo:

```css
:root {
  --page-primary: #51274b;
  --page-primary-shadow: #3d1d39;
  --page-primary-deep: #2f162c;
  --page-accent: #b9844d;
  --page-accent-shadow: #8f6338;
}
```

---

## Paso 3 — separar estilos inline a CSS dedicado

Para cada página:

1. Crear un archivo en `front/assets/css/`.
2. Mover ahí:
   - `body { font-family: ... }`
   - estilos de inputs/selects/textarea/button
   - animaciones
   - sombras
   - estilos de badges, sidebars, cards, etc.
3. Agregar el `<link rel="stylesheet">` al HTML.
4. Quitar el `<style>` inline del `<head>`.

### Archivos CSS creados

- `front/assets/css/login.css`
- `front/assets/css/seleccion-region.css`
- `front/assets/css/socioeconomico.css`
- `front/assets/css/tecnica.css`
- `front/assets/css/gestion.css`
- `front/assets/css/vista-tecnicos.css`
- `front/assets/css/admin-regiones.css`
- `front/assets/css/admin-usuarios.css`

---

## Paso 4 — mantener `tailwind.config` inline si la página usa CDN

NO mover `tailwind.config` al CSS.

Motivo:

- con Tailwind CDN, los tokens de color y tipografía viven en el `script` inline
- clases como `bg-ug-blue`, `text-ug-blue`, `bg-secondary`, etc. dependen de esa configuración

Por eso el patrón correcto es:

- `tailwind.config` inline
- CSS visual dedicado

---

## Paso 5 — aplicar el mismo lenguaje visual base

En todas las páginas homologadas, aplicar esta estructura visual:

### Header / Topbar
- header morado (`#51274b`)
- sombra suave debajo
- logos o identidad visual con tarjetas blancas y sombra

### Card principal
- fondo blanco
- sombra principal
- borde sutil o `inset` para profundidad

### Inputs
- fondo claro
- texto oscuro
- sombra suave
- borde con `focus` morado

### Botones principales
- fondo morado visible
- hover con morado sombra
- sombra suave (NO necesariamente 3D si compromete visibilidad)

### Footer / branding
- banda o bloque consistente
- sombra sutil o separación visual

---

## Paso 6 — tratar el login como referencia de sistema

### Cambios realizados en `login.html`

1. Se extrajeron estilos a `login.css`.
2. Se dejó la barra superior fija.
3. Se aplicaron sombras a:
   - header
   - tarjetas de logos
   - card principal
   - inputs
   - botón principal
   - badge de seguridad
   - footer
4. Se probó un botón 3D; como no quedó confiable visualmente, se volvió a una versión más simple:
   - fondo morado sólido
   - hover morado sombra
   - sombra visible

### Regla aprendida

Si el 3D hace que el botón pierda visibilidad, PREFERIR botón plano con sombra antes que insistir con un falso 3D roto.

---

## Paso 7 — aplicar el patrón a `seleccion-region.html`

### Cambios realizados

1. Crear `seleccion-region.css`.
2. Mover estilos inline al CSS.
3. Usar la misma paleta morado/naranja.
4. Ajustar:
   - header
   - cards de logos
   - indicador de paso
   - card principal
   - inputs/selects
   - botón principal
   - info box
   - footer
5. Corregir el alto del header para evitar que se viera negro detrás de logos pequeños.
6. Quitar franja oscura no deseada bajo el header.

---

## Paso 8 — aplicar el patrón a `socioeconomico.html`

### Cambios realizados

1. Crear `socioeconomico.css`.
2. Mover los estilos inline del `<head>`.
3. Aplicar clases propias a:
   - card principal
   - topbar
   - banner del título
   - tarjetas internas (tutores, documentos)
   - acciones primaria/secundaria
   - branding del footer
4. Mantener la lógica JS intacta mientras se cambia solo la capa visual.

### Corrección importante

Se reforzó el color del texto en inputs/selects/textarea para evitar que se escribiera en blanco sobre fondo blanco:

```css
color: #0f172a !important;
caret-color: #51274b;
-webkit-text-fill-color: #0f172a;
```

---

## Paso 9 — aplicar el patrón a `tecnica.html`

### Cambios realizados

1. Crear `tecnica.css`.
2. Mover estilos inline del `<head>`.
3. Cambiar la paleta azul/amarillo a morado/naranja.
4. Aplicar el patrón a:
   - topbar
   - banner principal
   - card principal
   - bloques suaves (por ejemplo multimedia)
   - acción principal
   - footer branding

### Ajuste puntual

El banner donde dice:

- `SOLICITUD TÉCNICA - SILLAS DE RUEDAS`

terminó fijándose directamente en HTML con:

```html
style="background-color: #51274b;"
```

cuando el CSS no estaba reflejando el color esperado.

---

## Paso 10 — aplicar el patrón a `gestion.html`

### Cambios realizados

1. Crear `gestion.css`.
2. Mover estilos inline.
3. Cambiar la paleta a morado/naranja.
4. Aplicar el patrón a:
   - topbar
   - menú local
   - banner principal
   - card principal
   - inputs
   - acción principal
   - footer branding

### Ajuste puntual

Las zonas:

- `Gestión`
- `GESTIÓN DE DONACIÓN`

se fijaron directamente en HTML con:

```html
style="background-color: #51274b;"
```

para asegurar el color exacto cuando el CSS no lo mostraba correctamente.

---

## Paso 11 — aplicar el patrón a páginas restantes

### `vista_tecnicos.html`

1. Crear `vista-tecnicos.css`.
2. Mover el bloque `<style>`.
3. Ajustar paleta:
   - `ug-blue` -> `#51274b`
   - `ug-yellow` -> `#B9844D`
4. Añadir sombras a:
   - header
   - barra sticky
   - cards/paneles
   - inputs/filtros

### `admin-regiones.html`

1. Crear `admin-regiones.css`.
2. Mover estilos inline.
3. Reemplazar azules de admin por morado.
4. Añadir sombras a:
   - sidebar
   - cards
   - iconografía de página
   - inputs
   - botones primarios

### `admin-usuarios.html`

1. Crear `admin-usuarios.css`.
2. Mover estilos inline.
3. Reemplazar azules/sidebar por morado.
4. Añadir sombras a:
   - sidebar
   - cards
   - iconografía de página
   - inputs
   - botones primarios

---

## Paso 12 — decidir cuándo usar HTML inline para color sólido

Usar color directo en HTML SOLO cuando:

- una franja visual crítica no está tomando el color correcto desde CSS
- el objetivo es fijar un color exacto sin ambigüedad
- se trata de un bloque muy específico como un banner principal

Ejemplo aplicado:

```html
style="background-color: #51274b;"
```

Evitar hacerlo en masa; debe ser excepción, no regla.

---

## Paso 13 — qué NO incluir en commits de estilo

Mantener fuera de los commits de estilo:

- PDFs fuente usados solo como referencia
- `.env`
- credenciales
- cambios de lógica no relacionados con apariencia

---

## Paso 14 — checklist de verificación final por página

Antes de dar por buena una página:

- [ ] ¿Usa CSS dedicado en `front/assets/css/`?
- [ ] ¿Quité estilos inline del `<head>`?
- [ ] ¿Mantiene `tailwind.config` inline si depende de CDN?
- [ ] ¿Usa morado `#51274b` como color principal visible?
- [ ] ¿Los textos en inputs se ven oscuros sobre fondo claro?
- [ ] ¿Los botones principales son visibles y consistentes?
- [ ] ¿Cards, banners y topbars tienen sombras suaves?
- [ ] ¿No rompí modales, toasts, validaciones ni JS existente?

---

## Páginas ya llevadas al patrón

- `front/login.html`
- `front/seleccion-region.html`
- `front/socioeconomico.html`
- `front/tecnica.html`
- `front/gestion.html`
- `front/vista_tecnicos.html`
- `front/admin-regiones.html`
- `front/admin-usuarios.html`

---

## Regla final de trabajo

Para futuras páginas, repetir siempre este patrón:

1. definir paleta morado/naranja
2. crear CSS dedicado
3. mover estilos inline
4. aplicar sombras a la capa visual
5. mantener la lógica JS intacta
6. corregir manualmente banners críticos si CSS no refleja el color exacto
