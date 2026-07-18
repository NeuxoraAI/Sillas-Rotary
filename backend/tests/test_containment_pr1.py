"""PR 1 containment tests for correlated case writes.

These tests use FastAPI's real routing/dependency graph with an in-memory DB
adapter. They intentionally avoid the external PostgreSQL test harness so the
authorization boundary remains executable without production credentials.
"""

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from database import get_db
from routers import guardar_borrador, tecnica
from routers.auth import CurrentUser, require_auth


OWNER_ID = 10
LEADER_ID = 20
MEMBER_ID = 30
OUTSIDER_ID = 40


class Result:
    def __init__(self, row=None):
        self.row = row

    def fetchone(self):
        return self.row


class CaseDB:
    """Small stateful adapter implementing only the PR 1 SQL contract."""

    def __init__(self):
        self.estudios = {
            101: {"id": 101, "usuario_id": OWNER_ID, "beneficiario_id": 501},
            102: {"id": 102, "usuario_id": OUTSIDER_ID, "beneficiario_id": 502},
            103: {"id": 103, "usuario_id": OWNER_ID, "beneficiario_id": 503},
        }
        self.solicitudes = {
            201: self._solicitud(201, OWNER_ID, 501),
            202: self._solicitud(202, OUTSIDER_ID, 502),
        }
        self.beneficiarios = {
            501: {"id": 501, "diagnostico": "ORIGINAL", "curp_benef": None},
            502: {"id": 502, "diagnostico": "OTRO", "curp_benef": None},
            503: {"id": 503, "diagnostico": "ORIGINAL", "curp_benef": None},
        }
        self.leader_pairs = {(LEADER_ID, OWNER_ID)}
        self.next_solicitud_id = 300
        self.mutations: list[tuple[str, tuple]] = []

    @staticmethod
    def _solicitud(solicitud_id: int, user_id: int, beneficiario_id: int) -> dict:
        return {
            "id": solicitud_id,
            "usuario_id": user_id,
            "beneficiario_id": beneficiario_id,
            "unidad_captura": "in",
            "unidad_peso_captura": "kg",
            "altura_total_in": None,
            "peso_kg": None,
            "medida_cabeza_asiento": None,
            "medida_hombro_asiento": None,
            "medida_prof_asiento": None,
            "medida_rodilla_talon": None,
            "medida_ancho_cadera": None,
            "status": "borrador",
            "updated_at": datetime(2026, 7, 10, tzinfo=timezone.utc),
        }

    def execute(self, sql: str, params=()):
        normalized = " ".join(sql.split()).lower()
        params = tuple(params)

        if "select 1 from organizaciones" in normalized:
            return Result({"?column?": 1} if (params[0], params[2]) in self.leader_pairs else None)

        if "from estudios_socioeconomicos" in normalized:
            if "where id = %s" in normalized:
                return Result(self.estudios.get(params[0]))
            if "where beneficiario_id = %s" in normalized:
                row = next(
                    (row for row in self.estudios.values() if row["beneficiario_id"] == params[0]),
                    None,
                )
                return Result(row)

        if "from solicitudes_tecnicas" in normalized:
            if "where id = %s" in normalized:
                return Result(self.solicitudes.get(params[0]))
            if "where beneficiario_id = %s and usuario_id = %s" in normalized:
                row = next(
                    (
                        row
                        for row in self.solicitudes.values()
                        if row["beneficiario_id"] == params[0] and row["usuario_id"] == params[1]
                    ),
                    None,
                )
                return Result(row)
            if "where beneficiario_id = %s" in normalized:
                row = next(
                    (row for row in self.solicitudes.values() if row["beneficiario_id"] == params[0]),
                    None,
                )
                return Result(row)

        if normalized.startswith("insert into solicitudes_tecnicas"):
            solicitud_id = self.next_solicitud_id
            self.next_solicitud_id += 1
            self.solicitudes[solicitud_id] = self._solicitud(solicitud_id, params[1], params[0])
            self.mutations.append(("insert_solicitud", params))
            return Result({"id": solicitud_id})

        if normalized.startswith("update beneficiarios set diagnostico"):
            self.beneficiarios[params[1]]["diagnostico"] = params[0]
            self.mutations.append(("update_diagnostico", params))
            return Result()

        if normalized.startswith("update solicitudes_tecnicas set"):
            solicitud_id = params[-1]
            if "prioridad = %s" in normalized:
                self.solicitudes[solicitud_id]["prioridad"] = params[0]
            self.solicitudes[solicitud_id]["updated_at"] = datetime.now(timezone.utc)
            self.mutations.append(("update_solicitud", params))
            return Result()

        if "select curp_benef from beneficiarios" in normalized:
            return Result(self.beneficiarios.get(params[0]))

        raise AssertionError(f"Unexpected SQL in PR 1 test adapter: {normalized}")

    def rollback(self):
        return None


def _user(user_id: int, role: str = "capturista") -> CurrentUser:
    return CurrentUser(
        usuario_id=user_id,
        nombre=f"User {user_id}",
        email=f"user{user_id}@example.test",
        rol=role,
    )


@pytest.fixture
def case_db():
    return CaseDB()


@pytest.fixture
def api_client(case_db, request):
    app = FastAPI()
    app.include_router(tecnica.router, prefix="/api")
    app.include_router(guardar_borrador.router, prefix="/api")
    current_user = getattr(request, "param", _user(OWNER_ID))
    app.dependency_overrides[get_db] = lambda: case_db
    app.dependency_overrides[require_auth] = lambda: current_user
    with TestClient(app) as client:
        yield client


def _create_payload(beneficiario_id: int, *, diagnostico: str | None = None) -> dict:
    payload = {
        "beneficiario_id": beneficiario_id,
        "entorno": "Urbano / Interiores",
        "control_tronco": "Completo",
        "control_cabeza": "Independiente",
        "control_de_piernas": "Parcial",
        "status": "borrador",
    }
    if diagnostico is not None:
        payload["diagnostico"] = diagnostico
    return payload


def test_owner_correlated_post_write_201(api_client, case_db):
    response = api_client.post("/api/solicitudes", json=_create_payload(503))

    assert response.status_code == 201, response.text
    assert response.json()["beneficiario_id"] == 503
    assert any(kind == "insert_solicitud" for kind, _ in case_db.mutations)


@pytest.mark.parametrize("api_client", [_user(OUTSIDER_ID)], indirect=True)
def test_cross_user_post_write_403_without_mutation(api_client, case_db):
    response = api_client.post("/api/solicitudes", json=_create_payload(503))

    assert response.status_code == 403
    assert case_db.mutations == []


@pytest.mark.parametrize(
    ("api_client", "expected"),
    [(_user(LEADER_ID, "organizacion"), 201), (_user(MEMBER_ID, "organizacion"), 403)],
    indirect=["api_client"],
)
def test_org_leader_allowed_plain_member_denied_on_post(api_client, expected):
    response = api_client.post("/api/solicitudes", json=_create_payload(503))

    assert response.status_code == expected, response.text


def test_owner_correlated_patch_write_200(api_client, case_db):
    response = api_client.patch("/api/solicitudes/201", json={"prioridad": "Alta"})

    assert response.status_code == 200, response.text
    assert case_db.solicitudes[201]["prioridad"] == "Alta"


@pytest.mark.parametrize("api_client", [_user(OUTSIDER_ID)], indirect=True)
def test_cross_user_patch_write_403_without_mutation(api_client, case_db):
    response = api_client.patch("/api/solicitudes/201", json={"prioridad": "Alta"})

    assert response.status_code == 403
    assert case_db.mutations == []


@pytest.mark.parametrize(
    ("api_client", "expected"),
    [(_user(LEADER_ID, "organizacion"), 200), (_user(MEMBER_ID, "organizacion"), 403)],
    indirect=["api_client"],
)
def test_org_leader_allowed_plain_member_denied_on_patch(api_client, expected):
    response = api_client.patch("/api/solicitudes/201", json={"prioridad": "Media"})

    assert response.status_code == expected, response.text


def test_mismatched_beneficiary_and_solicitud_returns_422(api_client, case_db):
    response = api_client.post(
        "/api/guardar-borrador",
        json={"estudio_id": 101, "solicitud_id": 202, "beneficiario_id": 501},
    )

    assert response.status_code == 422, response.text
    assert case_db.mutations == []


def test_unknown_explicit_solicitud_id_returns_404_without_fallback(api_client, case_db):
    response = api_client.post(
        "/api/guardar-borrador",
        json={"estudio_id": 101, "solicitud_id": 999, "beneficiario_id": 501},
    )

    assert response.status_code == 404, response.text
    assert case_db.solicitudes[201]["updated_at"] == datetime(2026, 7, 10, tzinfo=timezone.utc)
    assert case_db.mutations == []


def test_owner_diagnostico_post_mutates_authorized_beneficiary(api_client, case_db):
    response = api_client.post(
        "/api/solicitudes",
        json=_create_payload(503, diagnostico="Lesión medular"),
    )

    assert response.status_code == 201, response.text
    assert case_db.beneficiarios[503]["diagnostico"] == "LESION MEDULAR"


@pytest.mark.parametrize("api_client", [_user(OUTSIDER_ID)], indirect=True)
def test_diagnostico_post_requires_beneficiary_estudio_authorization(api_client, case_db):
    response = api_client.post(
        "/api/solicitudes",
        json=_create_payload(503, diagnostico="No autorizado"),
    )

    assert response.status_code == 403
    assert case_db.beneficiarios[503]["diagnostico"] == "ORIGINAL"


def test_owner_diagnostico_patch_mutates_authorized_beneficiary(api_client, case_db):
    response = api_client.patch(
        "/api/solicitudes/201",
        json={"diagnostico": "Lesión medular"},
    )

    assert response.status_code == 200, response.text
    assert case_db.beneficiarios[501]["diagnostico"] == "LESION MEDULAR"


def test_diagnostico_patch_requires_matching_estudio_authorization(api_client, case_db):
    case_db.estudios[101]["usuario_id"] = OUTSIDER_ID

    response = api_client.patch(
        "/api/solicitudes/201",
        json={"diagnostico": "No autorizado"},
    )

    assert response.status_code == 403
    assert case_db.beneficiarios[501]["diagnostico"] == "ORIGINAL"
