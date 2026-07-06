# Guía de Estilo de Idioma — Ecosistema VIDA UG

## Registro Oficial

**Español neutro latinoamericano con tratamiento de usted (formal).**

La interfaz utiliza exclusivamente el registro formal (usted) para mantener consistencia y profesionalismo dirigido a trabajadores de campo y personal administrativo.

---

## Reglas Fundamentales

### 1. Tratamiento de Usted

Todo texto dirigido al usuario debe usar conjugaciones de usted, nunca de tú ni de voseo.

| ❌ Incorrecto (tú) | ❌ Incorrecto (voseo) | ✅ Correcto (usted) |
|---------------------|----------------------|---------------------|
| Tienes cambios | Tenés cambios | Tiene cambios |
| Perderás los datos | Perderás los datos | Perderá los datos |
| Podrás continuar | Podés continuar | Podrá continuar |
| No puedes hacer eso | No podés hacer eso | No puede hacer eso |

### 2. Conjugaciones de Verbos Comunes

| Infinitivo | ❌ Voseo | ❌ Tú | ✅ Usted |
|------------|---------|-------|---------|
| Revisar | revisá | revisa | revise |
| Corregir | corregí | corrige | corrija |
| Ir | andá | ve | vaya |
| Poder | podés | puedes | puede |
| Iniciar | iniciá | inicia | inicie |
| Volver | volvé | vuelve | vuelva |
| Intentar | intentá | intenta | intente |
| Completar | completalos | complétalos | complételos |
| Acomodar | acomodá | acomoda | acomode |
| Tomar | tomá | toma | tome |
| Perder | perdés | pierdes | pierde |
| Tener | tenés | tienes | tiene |

### 3. Pronombres y Posesivos

| ❌ Incorrecto | ✅ Correcto |
|---------------|------------|
| tu conexión | su conexión |
| tus datos | sus datos |
| tu contraseña | su contraseña |
| contigo | con usted |

### 4. Imperativos

Los imperativos deben conjugarse en forma de usted:

| ❌ Voseo | ❌ Tú | ✅ Usted |
|---------|-------|---------|
| Corregila | Corrígela | Corríjala |
| Completalos | Complétalos | Complételos |
| Revisalo | Revísalo | Revíselo |

---

## Excepciones Permitidas

### Textos de Sistema (no visibles al usuario)

- Nombres de variables, funciones y clases en código
- Comentarios técnicos en código
- Mensajes de log y depuración
- Nombres de archivos y directorios

### Textos Legales o Institucionales

- Nombres de organizaciones o instituciones
- Textos legales que provengan de fuentes oficiales
- Citas o referencias externas

---

## Checklist para Nuevos Textos

Antes de agregar cualquier texto visible al usuario en la interfaz:

- [ ] ¿Usa conjugaciones de usted?
- [ ] ¿Evita voseo (revisá, corregí, andá, podés)?
- [ ] ¿Evita tú informal (tienes, perderás, puedes)?
- [ ] ¿Usa "su" en vez de "tu"?
- [ ] ¿Los imperativos están en forma de usted?

---

## Ejemplos en Contexto

### Mensajes de Error

| ❌ Incorrecto | ✅ Correcto |
|---------------|------------|
| Revisá los campos | Revise los campos |
| Corregí los errores | Corrija los errores |
| No tienes permisos | No tiene permisos |

### Mensajes de Éxito

| ❌ Incorrecto | ✅ Correcto |
|---------------|------------|
| Ya podés iniciar sesión | Ya puede iniciar sesión |
| Los datos se guardaron, podés continuar | Los datos se guardaron, puede continuar |

### Mensajes de Confirmación

| ❌ Incorrecto | ✅ Correcto |
|---------------|------------|
| Tienes cambios pendientes | Tiene cambios pendientes |
| Si cierras, perderás los datos | Si cierra, perderá los datos |
| Podrás volver después | Podrá volver después |

### Instrucciones

| ❌ Incorrecto | ✅ Correcto |
|---------------|------------|
| Andá al formulario | Vaya al formulario |
| Acomodá el documento | Acomode el documento |
| Tomá la foto | Tome la foto |

---

## Archivos de Interfaz

Los siguientes archivos contienen texto visible al usuario y deben seguir esta guía:

| Archivo | Contenido |
|---------|-----------|
| `front/login.html` | Pantalla de inicio de sesión |
| `front/seleccion-region.html` | Selección de país/región/sede |
| `front/Capturista-view/socioeconomico.html` | Formulario socioeconómico |
| `front/Capturista-view/tecnica.html` | Formulario técnico |
| `front/Capturista-view/gestion.html` | Formulario de gestión |
| `front/Capturista-view/perfil-capturista.html` | Perfil del capturista |
| `front/admin-beneficiarios.html` | Panel de administración |
| `front/Admin-view/admin-usuarios.html` | Gestión de usuarios |
| `front/Admin-view/admin-regiones.html` | Gestión de regiones |
| `front/reset-password.html` | Restablecer contraseña |
| `front/set-password.html` | Establecer contraseña |
| `front/forgot-password.html` | Olvidé contraseña |

---

## Referencia Rápida

```
REGISTRO: Usted (formal)
EVITAR:   Voseo (argentino), Tú (informal)
EJEMPLO:  "Revise los campos e intente de nuevo."
NO:       "Revisá los campos e intentá de nuevo."
NO:       "Revisa los campos e intenta de nuevo."
```
