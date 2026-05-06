import asyncio
from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers

from routers.auth import CurrentUser
from routers import socioeconomico


class _FakeStorage:
    def __init__(self):
        self.uploads: list[tuple[str, bytes, dict]] = []

    def upload(self, *, path: str, file: bytes, file_options: dict):
        self.uploads.append((path, file, file_options))


def _user() -> CurrentUser:
    return CurrentUser(
        usuario_id=7,
        nombre="Cap",
        email="cap@test.mx",
        rol="capturista",
    )


def _upload_file(filename: str, content_type: str, content: bytes) -> UploadFile:
    return UploadFile(
        file=BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


def test_extract_document_path_from_storage_scheme_url() -> None:
    result = socioeconomico.extract_document_path(
        "storage://documentos-estudio/credencial/archivo.pdf"
    )

    assert result == "credencial/archivo.pdf"


def test_extract_document_path_from_public_url() -> None:
    result = socioeconomico.extract_document_path(
        "https://abc.supabase.co/storage/v1/object/public/documentos-estudio/comprobante_domicilio/doc.png"
    )

    assert result == "comprobante_domicilio/doc.png"


def test_upload_documento_estudio_accepts_pdf(monkeypatch) -> None:
    storage = _FakeStorage()
    monkeypatch.setattr(socioeconomico, "_storage", lambda: storage)

    response = asyncio.run(
        socioeconomico.upload_documento_estudio(
            tipo="credencial",
            archivo=_upload_file("credencial.pdf", "application/pdf", b"pdf-bytes"),
            _usuario=_user(),
        )
    )

    assert response["tipo"] == "credencial"
    assert response["documento_path"].startswith("credencial/")
    assert response["documento_url"].startswith("storage://documentos-estudio/credencial/")
    assert storage.uploads[0][2]["content-type"] == "application/pdf"


def test_upload_documento_estudio_rejects_invalid_tipo() -> None:
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            socioeconomico.upload_documento_estudio(
                tipo="pasaporte",
                archivo=_upload_file("archivo.pdf", "application/pdf", b"pdf-bytes"),
                _usuario=_user(),
            )
        )

    assert exc.value.status_code == 422


def test_upload_documento_estudio_rejects_invalid_content_type() -> None:
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            socioeconomico.upload_documento_estudio(
                tipo="comprobante_domicilio",
                archivo=_upload_file("archivo.txt", "text/plain", b"hola"),
                _usuario=_user(),
            )
        )

    assert exc.value.status_code == 400
    assert "Tipo de archivo" in exc.value.detail
