"""Regresión de permisos de escritura por rol — Issue #130.

Modelo de roles sobre registros (socioeconómico / técnica / gestión):

    * capturista / organizacion → CREAN y editan registros (captura).
    * tecnico                   → SOLO lectura/descarga (nunca escribe).
    * admin                     → NO captura; edita/elimina solo por las rutas
                                  dedicadas /admin/beneficiarios/*.

Las aserciones se hacen sobre la *compuerta de rol* (`require_roles`), que
responde 403 ANTES de tocar la base de datos o validar el cuerpo. Por eso estas
pruebas son deterministas e independientes del estado del esquema de la BD:
verificamos 403 para los roles vetados y "no-403" (la compuerta admite; el
resto del flujo puede devolver 404/422) para los roles autorizados.
"""

import pytest


# --- Helpers de invocación por endpoint -----------------------------------
# Cada entrada: (id, fn(client, headers) -> Response). Se usa cuerpo mínimo;
# el 403 de la dependencia gana sobre cualquier 422 de validación de cuerpo.

def _post_estudios(client, headers):
    return client.post("/api/estudios", headers=headers, json={})


def _patch_estudios(client, headers):
    return client.patch("/api/estudios/999999", headers=headers, json={})


def _post_upload_documento(client, headers):
    return client.post(
        "/api/upload-documento",
        headers=headers,
        data={"tipo": "credencial"},
        files={"archivo": ("x.jpg", b"data", "image/jpeg")},
    )


def _post_upload_foto(client, headers):
    return client.post(
        "/api/upload-foto",
        headers=headers,
        files={"foto": ("x.jpg", b"data", "image/jpeg")},
    )


def _post_upload_estudio_clinico(client, headers):
    return client.post(
        "/api/upload-estudio-clinico",
        headers=headers,
        files={"archivo": ("x.pdf", b"data", "application/pdf")},
    )


def _post_solicitudes(client, headers):
    return client.post("/api/solicitudes", headers=headers, json={})


def _patch_solicitudes(client, headers):
    return client.patch("/api/solicitudes/999999", headers=headers, json={})


def _post_guardar_borrador(client, headers):
    return client.post("/api/guardar-borrador", headers=headers, json={})


def _post_finalizar_registro(client, headers):
    return client.post("/api/finalizar-registro", headers=headers, json={})


# Los 9 endpoints de escritura/captura cerrados a capturista+organizacion.
WRITE_ENDPOINTS = [
    ("POST /estudios", _post_estudios),
    ("PATCH /estudios/{id}", _patch_estudios),
    ("POST /upload-documento", _post_upload_documento),
    ("POST /upload-foto", _post_upload_foto),
    ("POST /upload-estudio-clinico", _post_upload_estudio_clinico),
    ("POST /solicitudes", _post_solicitudes),
    ("PATCH /solicitudes/{id}", _patch_solicitudes),
    ("POST /guardar-borrador", _post_guardar_borrador),
    ("POST /finalizar-registro", _post_finalizar_registro),
]

_WRITE_IDS = [name for name, _ in WRITE_ENDPOINTS]


# --- Roles vetados en escritura: técnico y admin → 403 --------------------

@pytest.mark.parametrize("endpoint", WRITE_ENDPOINTS, ids=_WRITE_IDS)
def test_tecnico_no_puede_escribir(client, tecnico_headers, endpoint):
    _name, fn = endpoint
    assert fn(client, tecnico_headers).status_code == 403


@pytest.mark.parametrize("endpoint", WRITE_ENDPOINTS, ids=_WRITE_IDS)
def test_admin_no_puede_capturar(client, admin_headers, endpoint):
    _name, fn = endpoint
    assert fn(client, admin_headers).status_code == 403


# --- Roles autorizados en escritura: capturista / organizacion → no 403 ---

@pytest.mark.parametrize("endpoint", WRITE_ENDPOINTS, ids=_WRITE_IDS)
def test_capturista_conserva_escritura(client, capturista_headers, endpoint):
    _name, fn = endpoint
    # La compuerta admite al capturista; el flujo posterior puede devolver
    # 404/422, pero nunca 403.
    assert fn(client, capturista_headers).status_code != 403


@pytest.mark.parametrize("endpoint", WRITE_ENDPOINTS, ids=_WRITE_IDS)
def test_organizacion_conserva_escritura(client, organizacion_headers, endpoint):
    _name, fn = endpoint
    assert fn(client, organizacion_headers).status_code != 403


# --- Rutas dedicadas del admin: solo admin pasa la compuerta --------------

def _patch_admin_estudio(client, headers):
    return client.patch("/api/admin/beneficiarios/999999/estudio", headers=headers, json={})


def _post_admin_upload_documento(client, headers):
    return client.post(
        "/api/admin/upload-documento",
        headers=headers,
        data={"tipo": "credencial"},
        files={"archivo": ("x.jpg", b"data", "image/jpeg")},
    )


ADMIN_ROUTES = [
    ("PATCH /admin/beneficiarios/{id}/estudio", _patch_admin_estudio),
    ("POST /admin/upload-documento", _post_admin_upload_documento),
]

_ADMIN_IDS = [name for name, _ in ADMIN_ROUTES]


@pytest.mark.parametrize("route", ADMIN_ROUTES, ids=_ADMIN_IDS)
def test_admin_conserva_rutas_dedicadas(client, admin_headers, route):
    _name, fn = route
    assert fn(client, admin_headers).status_code != 403


@pytest.mark.parametrize("route", ADMIN_ROUTES, ids=_ADMIN_IDS)
def test_no_admin_bloqueado_en_rutas_admin(
    client, capturista_headers, tecnico_headers, organizacion_headers, route
):
    _name, fn = route
    assert fn(client, capturista_headers).status_code == 403
    assert fn(client, tecnico_headers).status_code == 403
    assert fn(client, organizacion_headers).status_code == 403
