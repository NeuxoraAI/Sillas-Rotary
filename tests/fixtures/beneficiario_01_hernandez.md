# Test de Llenado — Beneficiario Ficticio

## Datos del Beneficiario de Prueba

| Campo | Valor |
|-------|-------|
| **Nombre** | María Guadalupe |
| **Apellido Paterno** | Hernández |
| **Apellido Materno** | López |
| **CURP** | HELO850312MDFRPS09 |
| **Fecha de Nacimiento** | 12/03/1985 |
| **Sexo** | Femenino |
| **Teléfono** | 5512345678 |

---

## Formulario 1: Socioeconómico (`socioeconomico.html`)

### Datos del Beneficiario

| # | Campo | Tipo | Valor | Obligatorio |
|---|-------|------|-------|:-----------:|
| 1 | Nombre(s) | texto | `María Guadalupe` | ✅ |
| 2 | Apellido Paterno | texto | `Hernández` | ✅ |
| 3 | Apellido Materno | texto | `López` | ✅ |
| 4 | CURP | texto | `HELO850312MDFRPS09` | ✅ |
| 5 | Fecha de nacimiento | fecha | `1985-03-12` | ✅ |
| 6 | Calle | texto | `Av. Insurgentes Sur` | ✅ |
| 7 | Número exterior | texto | `1234` | ✅ |
| 8 | ¿Agregar número interior? | checkbox | ✅ Marcar | ❌ |
| 9 | Número interior | texto | `Depto 5B` | ❌ |
| 10 | Colonia | texto | `Del Valle Centro` | ✅ |
| 11 | Estado | select | `Ciudad de México` | ✅ |
| 12 | Ciudad / Municipio | select | `Benito Juárez` | ✅ |
| 13 | Sexo | radio | `Femenino` | ✅ |
| 14 | Teléfonos de contacto | texto | `5512345678` | ✅ |

### Tutor 1 (Responsable)

| # | Campo | Tipo | Valor | Obligatorio |
|---|-------|------|-------|:-----------:|
| 15 | Nombre(s) | texto | `Juan Carlos` | ✅ |
| 16 | Apellido Paterno | texto | `Hernández` | ✅ |
| 17 | Apellido Materno | texto | `García` | ✅ |
| 18 | Edad | número | `42` | ✅ |
| 19 | Nivel de estudios | select | `Licenciatura` | ✅ |
| 20 | Estado civil | select | `Casado` | ✅ |
| 21 | Número de hijos | número | `3` | ✅ |
| 22 | Tipo de vivienda | select | `Propia` | ✅ |
| 23 | Fuente de empleo | select | `Empleado` | ✅ |
| 24 | ¿Sin empleo? | checkbox | ❌ No marcar | ❌ |
| 25 | Antigüedad (años) | texto | `8` | ✅ |
| 26 | Antigüedad (meses extra) | texto | `6` | ❌ |
| 27 | ¿No aplica antigüedad? | checkbox | ❌ No marcar | ❌ |
| 28 | Ingreso mensual | texto | `15000` | ✅ |
| 29 | ¿Tiene otras fuentes? | checkbox | ✅ Marcar | ❌ |
| 30 | Otra fuente de ingreso | texto | `Trabajo independiente` | ✅ |
| 31 | Monto otras fuentes | texto | `5000` | ✅ |
| 32 | ¿Cuenta con IMSS? | radio | `Sí` | ✅ |
| 33 | ¿Cuenta con INFONAVIT? | radio | `No` | ✅ |
| 34 | ¿Tiene email? | checkbox | ✅ Marcar | ❌ |
| 35 | Email | texto | `juan.hernandez@correo.com` | ❌ |

### Tutor 2 (Opcional)

| # | Campo | Tipo | Valor | Obligatorio |
|---|-------|------|-------|:-----------:|
| 36 | ¿Agregar Tutor 2? | checkbox | ✅ Marcar | ❌ |
| 37 | Nombre(s) | texto | `Ana María` | ✅ |
| 38 | Apellido Paterno | texto | `López` | ✅ |
| 39 | Apellido Materno | texto | `Ramírez` | ✅ |
| 40 | Edad | número | `39` | ✅ |
| 41 | Nivel de estudios | select | `Preparatoria` | ✅ |
| 42 | Estado civil | select | `Casado` | ✅ |
| 43 | Número de hijos | número | `3` | ✅ |
| 44 | Tipo de vivienda | select | `Propia` | ✅ |
| 45 | Fuente de empleo | select | `Empleado` | ✅ |
| 46 | ¿Sin empleo? | checkbox | ❌ No marcar | ❌ |
| 47 | Antigüedad (años) | texto | `5` | ✅ |
| 48 | Antigüedad (meses extra) | texto | `3` | ❌ |
| 49 | ¿No aplica antigüedad? | checkbox | ❌ No marcar | ❌ |
| 50 | Ingreso mensual | texto | `12000` | ✅ |
| 51 | ¿Tiene otras fuentes? | checkbox | ❌ No marcar | ❌ |
| 52 | Otra fuente de ingreso | texto | *(vacío)* | ❌ |
| 53 | Monto otras fuentes | texto | *(vacío)* | ❌ |
| 54 | ¿Cuenta con IMSS? | radio | `No` | ✅ |
| 55 | ¿Cuenta con INFONAVIT? | radio | `No` | ✅ |
| 56 | ¿Tiene email? | checkbox | ❌ No marcar | ❌ |
| 57 | Email | texto | *(vacío)* | ❌ |

### Documentos (NO incluir en este test)

| Campo | Estado |
|-------|--------|
| Credencial (INE) | ⬜ Pendiente de captura |
| Comprobante de domicilio | ⬜ Pendiente de captura |

**Acción:** Guardar borrador y continuar a Técnica.

---

## Formulario 2: Técnica (`tecnica.html`)

### Especificaciones de Uso

| # | Campo | Tipo | Valor | Obligatorio |
|---|-------|------|-------|:-----------:|
| 58 | Equipo Solicitado | select | `Silla de ruedas neurológica PCI` | ❌ |
| 59 | Entorno de Uso Principal | select | `Urbano / Interiores` | ✅ |

### Capacidad Postural y Diagnóstico

| # | Campo | Tipo | Valor | Obligatorio |
|---|-------|------|-------|:-----------:|
| 60 | Diagnóstico Médico | texto | `Parálisis cerebral infantil tetraparesia espástica` | ✅ |
| 61 | Control de Tronco | select | `Parcial / Requiere apoyo lateral` | ✅ |
| 62 | Control de Cabeza | select | `Independiente` | ✅ |
| 63 | Control de Piernas | select | `Nulo` | ✅ |
| 64 | Padecimientos | checkboxes | ✅ Distonía, ✅ Escoliosis | ❌ |
| 65 | Padecimiento adicional (Otra) | texto | `Espasticidad severa` | ❌ |
| 66 | ¿Requiere soporte para oxígeno? | radio | `No` | ✅ |

### Medidas Técnicas

| # | Campo | Tipo | Valor | Obligatorio |
|---|-------|------|-------|:-----------:|
| 67 | Sistema de medición | select | `Centímetros / Kilogramos` | ❌ |
| 68 | Altura total | texto | `120` | ✅ |
| 69 | Peso | texto | `25` | ✅ |
| 70 | Medida cabeza-asiento | texto | `32` | ✅ |
| 71 | Medida hombro-asiento | texto | `28` | ✅ |
| 72 | Medida prof. asiento | texto | `35` | ✅ |
| 73 | Medida rodilla-talón | texto | `38` | ✅ |
| 74 | Medida ancho cadera | texto | `28` | ✅ |

### Multimedia (NO incluir en este test)

| Campo | Estado |
|-------|--------|
| Fotografía del paciente | ⬜ Pendiente de captura |
| Estudio clínico | ⬜ Pendiente de captura (opcional) |

**Acción:** Guardar borrador y continuar a Gestión.

---

## Formulario 3: Gestión (`gestion.html`)

### Información del Estudio

| # | Campo | Tipo | Valor | Obligatorio |
|---|-------|------|-------|:-----------:|
| 75 | ¿Ha tenido silla previamente? | select | `No` | ✅ |
| 76 | ¿Cómo la obtuvo? | select | *(se habilita si elige "Sí")* | ❌ |
| 77 | Elaboró el estudio | texto | *(auto: nombre del capturista)* | ❌ |
| 78 | Fecha del estudio | fecha | `2025-07-05` | ✅ |
| 79 | Sede | texto | *(auto: de selección de región)* | ❌ |
| 80 | Ciudad del registro | texto | *(auto)* | ❌ |

### Información de la Solicitud

| # | Campo | Tipo | Valor | Obligatorio |
|---|-------|------|-------|:-----------:|
| 81 | Entidad Solicitante | texto | `Hospital Pediátrico de Especialidades` | ✅ |
| 82 | Prioridad | radio | `Media` | ✅ |
| 83 | ¿Agregar justificación? | checkbox | ✅ Marcar | ❌ |
| 84 | Justificación | texto | `Paciente requiere silla de ruedas para actividades diarias y rehabilitación` | ❌ |

**Acción:** Finalizar registro.

---

## Flujo de Prueba Completo

### Paso 1: Inicio de Sesión
1. Ir a `login.html`
2. Ingresar credenciales de capturista
3. Verificar redirección a `seleccion-region.html`

### Paso 2: Selección de Región
1. Seleccionar país: `México`
2. Seleccionar región: `Ciudad de México`
3. Ingresar sede: `Sede Central CDMX`
4. Continuar a `socioeconomico.html`

### Paso 3: Socioeconómico
1. Llenar campos 1-14 (Datos del Beneficiario)
2. Llenar campos 15-35 (Tutor 1)
3. Marcar "Agregar Tutor 2" (campo 36)
4. Llenar campos 37-57 (Tutor 2)
5. **NO** subir documentos (credencial, comprobante)
6. Hacer clic en "Guardar Borrador"
7. Verificar que el borrador se guardó correctamente
8. Continuar a Técnica

### Paso 4: Técnica
1. Llenar campos 58-59 (Especificaciones)
2. Llenar campos 60-66 (Capacidad Postural)
3. Llenar campos 67-74 (Medidas Técnicas)
4. **NO** subir fotos ni documentos
5. Hacer clic en "Guardar Borrador"
6. Verificar que el borrador se guardó correctamente
7. Continuar a Gestión

### Paso 5: Gestión
1. Llenar campos 75-80 (Información del Estudio)
2. Llenar campos 81-84 (Información de la Solicitud)
3. Hacer clic en "Finalizar Registro"
4. Verificar que se muestra el modal de confirmación

### Paso 6: Verificación
1. Ir a `admin-beneficiarios.html` (como admin)
2. Buscar al beneficiario por nombre o CURP
3. Verificar que todos los campos se guardaron correctamente
4. Verificar que el estado es "completo"

---

## Notas de Prueba

### Errores Esperados (si no se llenan campos obligatorios)
- Al intentar finalizar sin llenar todos los campos obligatorios, el sistema debe mostrar errores inline con borde rojo y mensaje descriptivo.
- Los errores deben desaparecer al completar el campo correspondiente.

### Casos Especiales a Verificar
1. **CURP inválida**: Ingresar una CURP con dígito verificador incorrecto → debe mostrar error al finalizar
2. **Teléfono inválido**: Ingresar menos de 10 dígitos → debe mostrar error
3. **Tutor 2 condicional**: Los campos del Tutor 2 solo son obligatorios si se marca "Agregar Tutor 2"
4. **Silla previa condicional**: "¿Cómo la obtuvo?" solo es obligatorio si se selecciona "Sí" en "¿Ha tenido silla previamente?"
5. **Justificación condicional**: El campo de justificación se habilita al marcar "Agregar justificación"

---

## Datos del Beneficiario para Búsqueda

| Campo | Valor |
|-------|-------|
| Nombre completo | María Guadalupe Hernández López |
| CURP | HELO850312MDFRPS09 |
| Folio | *(se genera automáticamente al finalizar)* |
| Región | Ciudad de México |
| Sede | Sede Central CDMX |
