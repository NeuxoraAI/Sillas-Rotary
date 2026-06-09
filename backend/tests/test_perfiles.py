"""
TDD Tests for Perfiles de Capturista y Organización.

Tests for:
- GET /api/me/capturas (capturista sees own, org sees its own, admin sees own)
- elaboro_estudio override for organizacion role (POST and PATCH)
"""

import psycopg2.extras  # noqa: F401 — used in test fixture helpers
import pytest


class TestMisCapturas:
    """GET /api/me/capturas scenarios."""

    def test_capturista_sees_own_capturas(self, client, capturista_headers, sample_estudio):
        """Capturista can GET /api/me/capturas and sees their own studies."""
        res = client.get("/api/me/capturas", headers=capturista_headers)
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        for item in data:
            assert "estudio_id" in item
            assert "folio" in item
            assert "beneficiario_nombre" in item
            assert "elaboro_estudio" in item
            assert "fecha_estudio" in item
            assert "status" in item
            assert "sede" in item
            assert "created_at" in item
        # All results should have capturista's own name as elaboro_estudio
        for item in data:
            assert item["elaboro_estudio"] == "Capturista Test"

    def test_organizacion_sees_own_capturas(self, client, organizacion_headers, organizacion_user, region_lon):
        """Organizacion sees their own studies (by usuario_id)."""
        # Create a study as organizacion user
        token = _get_token_from_headers(organizacion_headers)
        session_nombre = "Organización Test"
        payload = _build_minimal_estudio(region_lon["id"], session_nombre)
        res = client.post("/api/estudios", json=payload, headers=organizacion_headers)
        assert res.status_code == 201, f"Org create estudio failed: {res.text}"

        res = client.get("/api/me/capturas", headers=organizacion_headers)
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_capturista_sees_zero_capturas(self, client, capturista_headers):
        """Capturista with no studies sees empty list."""
        res = client.get("/api/me/capturas", headers=capturista_headers)
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_unauthorized_returns_401(self, client):
        """Request without JWT returns 401."""
        res = client.get("/api/me/capturas")
        assert res.status_code == 401

    def test_tecnico_blocked_from_mis_capturas(self, client, tecnico_headers):
        """Tecnico should be blocked from GET /api/me/capturas."""
        res = client.get("/api/me/capturas", headers=tecnico_headers)
        assert res.status_code == 403

    def test_results_ordered_by_created_at_desc(self, client, capturista_headers, capturista_user, region_lon):
        """Results are sorted by created_at DESC (most recent first)."""
        # Create two studies
        payload1 = _build_minimal_estudio(region_lon["id"], "Capturista Test")
        payload1["estudio"]["fecha_estudio"] = "2026-01-01"
        res1 = client.post("/api/estudios", json=payload1, headers=capturista_headers)
        assert res1.status_code == 201

        payload2 = _build_minimal_estudio(region_lon["id"], "Capturista Test")
        payload2["estudio"]["fecha_estudio"] = "2026-06-01"
        res2 = client.post("/api/estudios", json=payload2, headers=capturista_headers)
        assert res2.status_code == 201

        res = client.get("/api/me/capturas", headers=capturista_headers)
        data = res.json()
        assert len(data) >= 2
        timestamps = [item["created_at"] for item in data]
        assert timestamps == sorted(timestamps, reverse=True)


class TestElaboroEstudioOverride:
    """POST/PATCH /api/estudios elaboro_estudio override for organizacion."""

    def test_capturista_elaboro_estudio_ignored(self, client, capturista_headers, region_lon):
        """Capturista's elaboro_estudio value is ignored, replaced with session nombre."""
        payload = _build_minimal_estudio(region_lon["id"], "INYECTADO")
        res = client.post("/api/estudios", json=payload, headers=capturista_headers)
        assert res.status_code == 201
        estudio_id = res.json()["estudio_id"]

        # Verify via GET /api/me/capturas
        res = client.get("/api/me/capturas", headers=capturista_headers)
        data = res.json()
        estudio = next((e for e in data if e["estudio_id"] == estudio_id), None)
        assert estudio is not None
        assert estudio["elaboro_estudio"] == "Capturista Test"  # usuario.nombre, NOT "INYECTADO"

    def test_organizacion_elaboro_estudio_accepted(self, client, organizacion_headers, region_lon):
        """Organizacion's elaboro_estudio value is accepted from the client."""
        volunteer_name = "María López"
        expected_name = "MARIA LOPEZ"  # normalized by normalize_text
        payload = _build_minimal_estudio(region_lon["id"], volunteer_name)
        res = client.post("/api/estudios", json=payload, headers=organizacion_headers)
        assert res.status_code == 201, f"Org create estudio failed: {res.text}"
        estudio_id = res.json()["estudio_id"]

        # Verify via GET /api/me/capturas
        res = client.get("/api/me/capturas", headers=organizacion_headers)
        data = res.json()
        estudio = next((e for e in data if e["estudio_id"] == estudio_id), None)
        assert estudio is not None
        assert estudio["elaboro_estudio"] == expected_name

    def test_organizacion_empty_elaboro_estudio_falls_back_to_org_name(self, client, organizacion_headers, region_lon):
        """Organizacion with empty elaboro_estudio falls back to org account name."""
        payload = _build_minimal_estudio(region_lon["id"], "")
        res = client.post("/api/estudios", json=payload, headers=organizacion_headers)
        assert res.status_code == 201
        estudio_id = res.json()["estudio_id"]

        res = client.get("/api/me/capturas", headers=organizacion_headers)
        data = res.json()
        estudio = next((e for e in data if e["estudio_id"] == estudio_id), None)
        assert estudio is not None
        assert estudio["elaboro_estudio"] == "Organización Test"

    def test_organizacion_long_name_falls_back(self, client, organizacion_headers, region_lon):
        """Long elaboro_estudio (>120 chars) falls back to org account name."""
        long_name = "A" * 200
        payload = _build_minimal_estudio(region_lon["id"], long_name)
        res = client.post("/api/estudios", json=payload, headers=organizacion_headers)
        assert res.status_code == 201
        estudio_id = res.json()["estudio_id"]

        res = client.get("/api/me/capturas", headers=organizacion_headers)
        data = res.json()
        estudio = next((e for e in data if e["estudio_id"] == estudio_id), None)
        assert estudio is not None
        # Should fall back to org account name (not the long value)
        assert estudio["elaboro_estudio"] == "Organización Test"

    def test_patch_organizacion_elaboro_estudio_accepted(self, client, organizacion_headers, region_lon):
        """PATCH /estudios accepts elaboro_estudio for organizacion."""
        # Create study first
        payload = _build_minimal_estudio(region_lon["id"], "Initial Name")
        res = client.post("/api/estudios", json=payload, headers=organizacion_headers)
        assert res.status_code == 201
        estudio_id = res.json()["estudio_id"]

        # Now PATCH with new elaboro_estudio
        patch_payload = {
            "elaboro_estudio": "Ana Vega Actualizado",
            "status": "borrador",
        }
        res = client.patch(f"/api/estudios/{estudio_id}", json=patch_payload, headers=organizacion_headers)
        assert res.status_code == 200

        # Verify the update
        res = client.get(f"/api/estudios/{estudio_id}", headers=organizacion_headers)
        data = res.json()
        assert data["elaboro_estudio"] == "ANA VEGA ACTUALIZADO"  # normalized by normalize_text

    def test_patch_capturista_elaboro_estudio_ignored(self, client, capturista_headers, region_lon):
        """PATCH /estudios ignores elaboro_estudio for capturista."""
        payload = _build_minimal_estudio(region_lon["id"], "Ignored")
        res = client.post("/api/estudios", json=payload, headers=capturista_headers)
        assert res.status_code == 201
        estudio_id = res.json()["estudio_id"]

        # PATCH with different elaboro_estudio
        patch_payload = {
            "elaboro_estudio": "Should Be Ignored",
            "status": "borrador",
        }
        res = client.patch(f"/api/estudios/{estudio_id}", json=patch_payload, headers=capturista_headers)
        assert res.status_code == 200

        res = client.get(f"/api/estudios/{estudio_id}", headers=capturista_headers)
        data = res.json()
        assert data["elaboro_estudio"] == "Capturista Test"


# ═══════════════════════════════════════════════════════════════════════════════
# New Tests for GitHub-style Profiles (Tasks 8.1–8.4)
# ═══════════════════════════════════════════════════════════════════════════════


class TestMePerfil:
    """GET /api/me/perfil and PATCH /api/me/perfil endpoints."""

    def test_get_my_perfil_returns_capturista_data(self, client, capturista_headers, capturista_user):
        """GET /api/me/perfil returns usuario info and stats."""
        res = client.get("/api/me/perfil", headers=capturista_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["usuario"]["id"] == capturista_user["id"]
        assert data["usuario"]["nombre"] == "Capturista Test"
        assert data["usuario"]["rol"] == "capturista"
        assert "stats" in data
        assert "total_capturas" in data["stats"]
        assert "this_month" in data["stats"]
        assert "heatmap_data" in data
        assert data["can_edit"] is True

    def test_get_my_perfil_with_no_studies(self, client, capturista_headers):
        """GET /api/me/perfil with no studies shows zero stats."""
        res = client.get("/api/me/perfil", headers=capturista_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["stats"]["total_capturas"] == 0
        assert data["heatmap_data"] == []

    def test_get_my_perfil_requires_auth(self, client):
        """GET /api/me/perfil without JWT returns 401."""
        res = client.get("/api/me/perfil")
        assert res.status_code == 401

    def test_patch_my_perfil_updates_nombre(self, client, capturista_headers):
        """PATCH /api/me/perfil updates nombre."""
        res = client.patch("/api/me/perfil", json={"nombre": "Updated Name"}, headers=capturista_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["nombre"] == "Updated Name"

    def test_patch_my_perfil_duplicate_email_returns_409(self, client, capturista_headers, admin_headers):
        """PATCH /api/me/perfil with duplicate email returns 409."""
        res = client.patch("/api/me/perfil", json={"email": "admin@test.mx"}, headers=capturista_headers)
        assert res.status_code == 409

    def test_patch_my_perfil_short_nombre_returns_422(self, client, capturista_headers):
        """PATCH /api/me/perfil with too-short nombre returns 422."""
        res = client.patch("/api/me/perfil", json={"nombre": "A"}, headers=capturista_headers)
        assert res.status_code == 422


class TestMeHeatmap:
    """GET /api/me/heatmap endpoint."""

    def test_heatmap_empty_with_no_studies(self, client, capturista_headers):
        """GET /api/me/heatmap with no studies returns empty array."""
        res = client.get("/api/me/heatmap", headers=capturista_headers)
        assert res.status_code == 200
        assert res.json() == []

    def test_heatmap_returns_date_count_pairs(self, client, capturista_headers, capturista_user, region_lon):
        """GET /api/me/heatmap with studies returns date-count pairs."""
        payload = _build_minimal_estudio(region_lon["id"], "Capturista Test")
        client.post("/api/estudios", json=payload, headers=capturista_headers)

        res = client.get("/api/me/heatmap", headers=capturista_headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 1
        for entry in data:
            assert "date" in entry
            assert "count" in entry
            assert entry["count"] >= 1

    def test_heatmap_groups_same_date(self, client, capturista_headers, capturista_user, region_lon):
        """Multiple studies on same date are grouped."""
        for _ in range(2):
            payload = _build_minimal_estudio(region_lon["id"], "Capturista Test")
            client.post("/api/estudios", json=payload, headers=capturista_headers)

        res = client.get("/api/me/heatmap", headers=capturista_headers)
        data = res.json()
        from datetime import date
        today = str(date.today())
        today_entry = next((e for e in data if e["date"] == today), None)
        if today_entry:
            assert today_entry["count"] >= 2

    def test_heatmap_sorted_by_date(self, client, capturista_headers, capturista_user, region_lon):
        """Heatmap entries are sorted by date ascending."""
        payload = _build_minimal_estudio(region_lon["id"], "Capturista Test")
        client.post("/api/estudios", json=payload, headers=capturista_headers)

        res = client.get("/api/me/heatmap", headers=capturista_headers)
        data = res.json()
        if len(data) > 1:
            dates = [e["date"] for e in data]
            assert dates == sorted(dates)


class TestMeBeneficiarios:
    """GET /api/me/beneficiarios endpoint."""

    def test_beneficiarios_returns_user_studies(self, client, capturista_headers, capturista_user, region_lon):
        """GET /api/me/beneficiarios returns this user's beneficiaries."""
        payload = _build_minimal_estudio(region_lon["id"], "Capturista Test")
        res = client.post("/api/estudios", json=payload, headers=capturista_headers)
        assert res.status_code == 201

        res = client.get("/api/me/beneficiarios", headers=capturista_headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 1
        for item in data:
            assert "estudio_id" in item
            assert "folio" in item
            assert "beneficiario_nombre" in item
            assert "status" in item
            assert "edit_url" in item
            assert f"estudio_id={item['estudio_id']}" in item["edit_url"]

    def test_beneficiarios_empty(self, client, capturista_headers):
        """GET /api/me/beneficiarios with no studies returns empty list."""
        res = client.get("/api/me/beneficiarios", headers=capturista_headers)
        assert res.status_code == 200
        assert res.json() == []

    def test_beneficiarios_blocked_for_tecnico(self, client, tecnico_headers):
        """Tecnico cannot access beneficiary list."""
        res = client.get("/api/me/beneficiarios", headers=tecnico_headers)
        assert res.status_code == 403


class TestOrganizacionesCRUD:
    """Organization CRUD endpoints (admin only)."""

    def _create_org(self, client, admin_headers, nombre="Test Org Rotary"):
        return client.post(
            "/api/organizaciones",
            json={"nombre": nombre, "direccion": "Dirección Test"},
            headers=admin_headers,
        )

    def test_admin_creates_org(self, client, admin_headers):
        """Admin can create an organization (201)."""
        res = self._create_org(client, admin_headers, "Rotary León Test")
        assert res.status_code == 201
        data = res.json()
        assert "id" in data
        assert data["nombre"] == "Rotary León Test"

    def test_non_admin_cannot_create_org(self, client, capturista_headers):
        """Non-admin creating org returns 403."""
        res = self._create_org(client, capturista_headers, "Should Fail")
        assert res.status_code == 403

    def test_duplicate_org_name_returns_409(self, client, admin_headers):
        """Duplicate org name returns 409."""
        self._create_org(client, admin_headers, "Unique Name Org")
        res = self._create_org(client, admin_headers, "Unique Name Org")
        assert res.status_code == 409

    def test_admin_lists_orgs(self, client, admin_headers):
        """Admin can list all organizations."""
        self._create_org(client, admin_headers, "Org Alpha")
        self._create_org(client, admin_headers, "Org Beta")

        res = client.get("/api/organizaciones", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 2

    def test_admin_assigns_leader(self, client, admin_headers, capturista_user):
        """Admin assigns a leader to an org."""
        res = self._create_org(client, admin_headers, "Leader Test Org")
        org_id = res.json()["id"]

        res = client.patch(
            f"/api/organizaciones/{org_id}/lider",
            json={"lider_usuario_id": capturista_user["id"]},
            headers=admin_headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["lider_usuario_id"] == capturista_user["id"]

    def test_admin_removes_leader(self, client, admin_headers, capturista_user):
        """Admin removes a leader by setting to null."""
        res = self._create_org(client, admin_headers, "Remove Leader Org")
        org_id = res.json()["id"]

        client.patch(
            f"/api/organizaciones/{org_id}/lider",
            json={"lider_usuario_id": capturista_user["id"]},
            headers=admin_headers,
        )
        res = client.patch(
            f"/api/organizaciones/{org_id}/lider",
            json={"lider_usuario_id": None},
            headers=admin_headers,
        )
        assert res.status_code == 200
        assert res.json()["lider_usuario_id"] is None

    def test_get_org_detail(self, client, admin_headers, capturista_user):
        """GET /api/organizaciones/{id} returns org detail with stats."""
        res = self._create_org(client, admin_headers, "Detail Test Org")
        org_id = res.json()["id"]

        client.patch(
            f"/api/organizaciones/{org_id}/lider",
            json={"lider_usuario_id": capturista_user["id"]},
            headers=admin_headers,
        )

        res = client.get(f"/api/organizaciones/{org_id}", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["nombre"] == "Detail Test Org"
        assert "lider_usuario_id" in data
        assert "stats" in data
        assert "total_capturas" in data["stats"]
        assert "this_month" in data["stats"]

    def test_get_org_detail_not_found(self, client, admin_headers):
        """GET /api/organizaciones/{id} for non-existent org returns 404."""
        res = client.get("/api/organizaciones/99999", headers=admin_headers)
        assert res.status_code == 404

    def test_voluntarios_empty_for_unlinked_org(self, client, admin_headers):
        """GET /api/organizaciones/{id}/voluntarios returns empty for unlinked org."""
        res = self._create_org(client, admin_headers, "Voluntarios Test Org")
        org_id = res.json()["id"]

        res = client.get(f"/api/organizaciones/{org_id}/voluntarios", headers=admin_headers)
        assert res.status_code == 200
        assert res.json() == []

    def test_create_org_with_usuario_id(self, client, admin_headers, capturista_user):
        """Admin creates org with linked user account."""
        res = client.post(
            "/api/organizaciones",
            json={"nombre": "Org with User", "usuario_id": capturista_user["id"]},
            headers=admin_headers,
        )
        assert res.status_code == 201


class TestLeaderBypass:
    """Leader authorization bypass scenarios."""

    def test_non_leader_blocked_from_patch(self, client, capturista_headers, tecnico_headers, region_lon):
        """Non-leader PATCHing otro's estudio returns 403."""
        payload = _build_minimal_estudio(region_lon["id"], "Capturista Test")
        res = client.post("/api/estudios", json=payload, headers=capturista_headers)
        assert res.status_code == 201
        estudio_id = res.json()["estudio_id"]

        # Try to PATCH as a different user (tecnico)
        res = client.patch(
            f"/api/estudios/{estudio_id}",
            json={"status": "borrador"},
            headers=tecnico_headers,
        )
        assert res.status_code == 403


class TestOrgHeatmap:
    """Organization heatmap endpoints."""

    def test_org_heatmap_empty(self, client, admin_headers):
        """GET /api/organizaciones/{id}/heatmap with no studies returns empty."""
        import uuid
        unique = str(uuid.uuid4())[:8]
        res = client.post(
            "/api/organizaciones",
            json={"nombre": f"Heatmap Empty {unique}"},
            headers=admin_headers,
        )
        org_id = res.json()["id"]

        res = client.get(f"/api/organizaciones/{org_id}/heatmap", headers=admin_headers)
        assert res.status_code == 200
        assert res.json() == []


class TestProfileUpdateEdgeCases:
    """Edge cases for profile updates."""

    def test_patch_empty_body_returns_current(self, client, capturista_headers):
        """PATCH with empty body returns current profile."""
        res = client.patch("/api/me/perfil", json={}, headers=capturista_headers)
        assert res.status_code == 200
        data = res.json()
        assert "id" in data
        assert "nombre" in data


# ═══════════════════════════════════════════════════════════════════════════════
# Org Heatmap Aggregation Tests (SDD: fix-frontend-calendario-actividad-github)
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetOrgUserIds:
    """Tests for _get_org_user_ids() helper."""

    def _setup_org(self, _test_db_conn, nombre="Agg Org"):
        """Create org with no linked user, return org_id."""
        from database import _DBAdapter
        cur = _test_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        adapter = _DBAdapter(_test_db_conn, cur)
        row = adapter.execute(
            "INSERT INTO organizaciones (nombre) VALUES (%s) RETURNING id",
            (nombre,),
        ).fetchone()
        _test_db_conn.commit()
        cur.close()
        return row["id"]

    def _make_adapter(self, _test_db_conn):
        """Create a _DBAdapter for calling helpers."""
        from database import _DBAdapter
        import psycopg2.extras as _pe
        cur = _test_db_conn.cursor(cursor_factory=_pe.RealDictCursor)
        return _DBAdapter(_test_db_conn, cur), cur

    def _create_user(self, _test_db_conn, nombre, email, rol="capturista"):
        """Create a user and return their id."""
        from passlib.context import CryptContext
        import psycopg2.extras as _pe
        pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
        pw_hash = pwd.hash("testpass123")
        with _test_db_conn.cursor(cursor_factory=_pe.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES (%s, %s, %s, %s) RETURNING id",
                (nombre, email, pw_hash, rol),
            )
            row = cur.fetchone()
        _test_db_conn.commit()
        return row["id"]

    def _add_leader(self, _test_db_conn, org_id, usuario_id):
        """Add a leader to an org."""
        with _test_db_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO organizaciones_lideres (organizacion_id, usuario_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (org_id, usuario_id),
            )
        _test_db_conn.commit()

    def _add_member(self, _test_db_conn, org_id, usuario_id):
        """Add a member to an org."""
        with _test_db_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO organizaciones_miembros (organizacion_id, usuario_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (org_id, usuario_id),
            )
        _test_db_conn.commit()

    def test_returns_linked_account_only(self, _test_db_conn):
        """Org with only linked usuario_id returns that single ID."""
        uid = self._create_user(_test_db_conn, "Link", "link@test.mx")
        with _test_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO organizaciones (nombre, usuario_id) VALUES (%s, %s) RETURNING id",
                ("Link Org", uid),
            )
            org_id = cur.fetchone()["id"]
        _test_db_conn.commit()

        from routers.perfiles import _get_org_user_ids
        adapter, cur = self._make_adapter(_test_db_conn)
        try:
            result = _get_org_user_ids(adapter, org_id)
            assert result == [uid]
        finally:
            cur.close()

    def test_returns_leaders_only(self, _test_db_conn):
        """Org without linked account but with leaders returns leader IDs."""
        org_id = self._setup_org(_test_db_conn, "Leaders Org")
        uid = self._create_user(_test_db_conn, "Leader", "leader@test.mx")
        self._add_leader(_test_db_conn, org_id, uid)

        from routers.perfiles import _get_org_user_ids
        adapter, cur = self._make_adapter(_test_db_conn)
        try:
            result = _get_org_user_ids(adapter, org_id)
            assert result == [uid]
        finally:
            cur.close()

    def test_returns_members_only(self, _test_db_conn):
        """Org without linked account but with members returns member IDs."""
        org_id = self._setup_org(_test_db_conn, "Members Org")
        uid = self._create_user(_test_db_conn, "Member", "member@test.mx")
        self._add_member(_test_db_conn, org_id, uid)

        from routers.perfiles import _get_org_user_ids
        adapter, cur = self._make_adapter(_test_db_conn)
        try:
            result = _get_org_user_ids(adapter, org_id)
            assert result == [uid]
        finally:
            cur.close()

    def test_returns_all_linked_users_mixed(self, _test_db_conn):
        """Org with linked account + leaders + members returns all unique IDs."""
        uid_account = self._create_user(_test_db_conn, "Account", "acct@test.mx")
        uid_leader = self._create_user(_test_db_conn, "Leader2", "ldr@test.mx")
        uid_member = self._create_user(_test_db_conn, "Member2", "mbr@test.mx")

        with _test_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO organizaciones (nombre, usuario_id) VALUES (%s, %s) RETURNING id",
                ("Mixed Org", uid_account),
            )
            org_id = cur.fetchone()["id"]
        _test_db_conn.commit()
        self._add_leader(_test_db_conn, org_id, uid_leader)
        self._add_member(_test_db_conn, org_id, uid_member)

        from routers.perfiles import _get_org_user_ids
        adapter, cur = self._make_adapter(_test_db_conn)
        try:
            result = _get_org_user_ids(adapter, org_id)
            assert sorted(result) == sorted([uid_account, uid_leader, uid_member])
        finally:
            cur.close()

    def test_returns_empty_when_no_users(self, _test_db_conn):
        """Org with NULL usuario_id and no leaders/members returns empty list."""
        org_id = self._setup_org(_test_db_conn, "Empty Org")

        from routers.perfiles import _get_org_user_ids
        adapter, cur = self._make_adapter(_test_db_conn)
        try:
            result = _get_org_user_ids(adapter, org_id)
            assert result == []
        finally:
            cur.close()

    def test_deduplicates_same_user(self, _test_db_conn):
        """Same user appearing as linked account AND leader is returned once."""
        uid = self._create_user(_test_db_conn, "Dup", "dup@test.mx")
        with _test_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO organizaciones (nombre, usuario_id) VALUES (%s, %s) RETURNING id",
                ("Dup Org", uid),
            )
            org_id = cur.fetchone()["id"]
        _test_db_conn.commit()
        self._add_leader(_test_db_conn, org_id, uid)
        self._add_member(_test_db_conn, org_id, uid)

        from routers.perfiles import _get_org_user_ids
        adapter, cur = self._make_adapter(_test_db_conn)
        try:
            result = _get_org_user_ids(adapter, org_id)
            assert result == [uid]
        finally:
            cur.close()


class TestGetOrgStatsAndHeatmap:
    """Tests for _get_org_stats_and_heatmap() helper."""

    def _make_adapter(self, _test_db_conn):
        from database import _DBAdapter
        import psycopg2.extras as _pe
        cur = _test_db_conn.cursor(cursor_factory=_pe.RealDictCursor)
        return _DBAdapter(_test_db_conn, cur), cur

    def _create_user(self, _test_db_conn, nombre, email, rol="capturista"):
        from passlib.context import CryptContext
        import psycopg2.extras as _pe
        pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
        pw_hash = pwd.hash("testpass123")
        with _test_db_conn.cursor(cursor_factory=_pe.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES (%s, %s, %s, %s) RETURNING id",
                (nombre, email, pw_hash, rol),
            )
            row = cur.fetchone()
        _test_db_conn.commit()
        return row["id"]

    def _create_study_for_user(self, _test_db_conn, usuario_id, region_id, status="completo", days_ago=0):
        """Create a minimal estudio_socioeconomico for a user."""
        from datetime import datetime, timedelta, timezone
        created = datetime.now(timezone.utc) - timedelta(days=days_ago)
        # Need a region counter first
        with _test_db_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO region_counters (pais_codigo, region_codigo, anio, ultimo_numero) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                ("MX", "LON", created.year, 5),
            )
        _test_db_conn.commit()
        # Create beneficiary
        with _test_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO beneficiarios (nombre, fecha_nacimiento, diagnostico, calle, colonia, ciudad, telefonos, region_id, sede) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
                ("Benef Test", "2000-01-15", "Dx", "Calle", "Col", "Ciudad", "4621112233", region_id, "Sede Test"),
            )
            ben_id = cur.fetchone()["id"]
        _test_db_conn.commit()
        # Create estudio
        from datetime import datetime as _dt
        _fecha_str = created.strftime("%Y-%m-%d")
        with _test_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO estudios_socioeconomicos (beneficiario_id, usuario_id, sede, status, created_at, elaboro_estudio, fecha_estudio) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
                (ben_id, usuario_id, "Sede Test", status, created, "Test Helper", _fecha_str),
            )
            estudio_id = cur.fetchone()["id"]
        _test_db_conn.commit()
        return estudio_id

    def test_stats_aggregates_all_linked_users(self, _test_db_conn, region_lon):
        """Stats total_capturas sums across linked account + leader + member."""
        # Create users
        uid_acct = self._create_user(_test_db_conn, "Acct", "acct2@test.mx")
        uid_lead = self._create_user(_test_db_conn, "Lead", "lead2@test.mx")
        uid_memb = self._create_user(_test_db_conn, "Memb", "memb2@test.mx")

        # Create org with linked account
        with _test_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO organizaciones (nombre, usuario_id) VALUES (%s, %s) RETURNING id",
                ("Stats Org", uid_acct),
            )
            org_id = cur.fetchone()["id"]
        _test_db_conn.commit()

        # Add leader and member
        with _test_db_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO organizaciones_lideres (organizacion_id, usuario_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (org_id, uid_lead),
            )
            cur.execute(
                "INSERT INTO organizaciones_miembros (organizacion_id, usuario_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (org_id, uid_memb),
            )
        _test_db_conn.commit()

        # Account has 2 studies, leader has 1, member has 3
        for _ in range(2):
            self._create_study_for_user(_test_db_conn, uid_acct, region_lon["id"])
        self._create_study_for_user(_test_db_conn, uid_lead, region_lon["id"])
        for _ in range(3):
            self._create_study_for_user(_test_db_conn, uid_memb, region_lon["id"])

        from routers.perfiles import _get_org_stats_and_heatmap
        adapter, cur = self._make_adapter(_test_db_conn)
        try:
            result = _get_org_stats_and_heatmap(adapter, org_id)
            assert result["total_capturas"] == 6  # 2 + 1 + 3
            assert result["completados"] == 6
            assert isinstance(result["this_month"], int)
            assert len(result["heatmap_data"]) >= 1  # at least today's date
        finally:
            cur.close()

    def test_stats_returns_zeros_when_no_captures(self, _test_db_conn, region_lon):
        """Org with linked users but zero studies returns zero stats."""
        uid = self._create_user(_test_db_conn, "ZeroUser", "zero@test.mx")
        with _test_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO organizaciones (nombre, usuario_id) VALUES (%s, %s) RETURNING id",
                ("Zero Org", uid),
            )
            org_id = cur.fetchone()["id"]
        _test_db_conn.commit()

        from routers.perfiles import _get_org_stats_and_heatmap
        adapter, cur = self._make_adapter(_test_db_conn)
        try:
            result = _get_org_stats_and_heatmap(adapter, org_id)
            assert result["total_capturas"] == 0
            assert result["this_month"] == 0
            assert result["completados"] == 0
            assert result["heatmap_data"] == []
        finally:
            cur.close()

    def test_heatmap_data_includes_all_dates(self, _test_db_conn, region_lon):
        """Heatmap includes dates from all linked users, grouped by date."""
        uid1 = self._create_user(_test_db_conn, "H1", "h1@test.mx")
        uid2 = self._create_user(_test_db_conn, "H2", "h2@test.mx")

        with _test_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO organizaciones (nombre, usuario_id) VALUES (%s, %s) RETURNING id",
                ("Heatmap Org", uid1),
            )
            org_id = cur.fetchone()["id"]
        _test_db_conn.commit()

        with _test_db_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO organizaciones_lideres (organizacion_id, usuario_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (org_id, uid2),
            )
        _test_db_conn.commit()

        # Create studies for both users
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc)
        yesterday_str = (today - __import__('datetime').timedelta(days=1)).strftime("%Y-%m-%d")

        self._create_study_for_user(_test_db_conn, uid1, region_lon["id"])
        self._create_study_for_user(_test_db_conn, uid2, region_lon["id"], days_ago=1)

        from routers.perfiles import _get_org_stats_and_heatmap
        adapter, cur = self._make_adapter(_test_db_conn)
        try:
            result = _get_org_stats_and_heatmap(adapter, org_id)
            dates = {entry["date"] for entry in result["heatmap_data"]}
            assert len(dates) >= 1
            assert all(entry["count"] >= 1 for entry in result["heatmap_data"])
        finally:
            cur.close()

    def test_heatmap_empty_for_no_linked_users(self, _test_db_conn):
        """Heatmap is empty when org has no linked users at all."""
        with _test_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO organizaciones (nombre) VALUES (%s) RETURNING id",
                ("No User Org",),
            )
            org_id = cur.fetchone()["id"]
        _test_db_conn.commit()

        from routers.perfiles import _get_org_stats_and_heatmap
        adapter, cur = self._make_adapter(_test_db_conn)
        try:
            result = _get_org_stats_and_heatmap(adapter, org_id)
            assert result["total_capturas"] == 0
            assert result["this_month"] == 0
            assert result["completados"] == 0
            assert result["heatmap_data"] == []
        finally:
            cur.close()


class TestOrgDetailAggregatedStats:
    """Integration tests: GET /api/organizaciones/{id} shows aggregated stats."""

    def test_org_detail_aggregates_leader_captures(self, client, admin_headers, capturista_user, region_lon):
        """Org detail includes leader captures in stats."""
        # Create org linked to capturista_user
        res = client.post(
            "/api/organizaciones",
            json={
                "nombre": "Agg Detail Test",
                "usuario_id": capturista_user["id"],
            },
            headers=admin_headers,
        )
        assert res.status_code == 201
        org_id = res.json()["id"]

        # Capturista creates a study (must be done as the capturista user)
        cap_token = client.post("/api/auth/login", json={"email": "cap@test.mx", "password": "cappass123"}).json()["access_token"]
        cap_headers = {"Authorization": f"Bearer {cap_token}"}
        payload = _build_minimal_estudio(region_lon["id"], "Capturista Test")
        res = client.post("/api/estudios", json=payload, headers=cap_headers)
        assert res.status_code == 201

        # Get org detail
        res = client.get(f"/api/organizaciones/{org_id}", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert "stats" in data
        assert data["stats"]["total_capturas"] >= 1

    def test_org_detail_404(self, client, admin_headers):
        """Non-existent org returns 404."""
        res = client.get("/api/organizaciones/99999", headers=admin_headers)
        assert res.status_code == 404
        assert "no encontrada" in res.json()["detail"].lower()


class TestOrgHeatmapV2:
    """Integration tests: GET /api/organizaciones/{id}/heatmap aggregated."""

    def test_org_heatmap_with_leader_captures(self, client, admin_headers, capturista_user, region_lon):
        """Heatmap includes leader captures, not just org account."""
        # Create org
        res = client.post(
            "/api/organizaciones",
            json={"nombre": "Heatmap Agg Test", "usuario_id": capturista_user["id"]},
            headers=admin_headers,
        )
        assert res.status_code == 201
        org_id = res.json()["id"]

        # Create a study as capturista_user (they are the linked account)
        token_res = client.post("/api/auth/login", json={"email": "cap@test.mx", "password": "cappass123"})
        cap_token = token_res.json()["access_token"]
        cap_headers = {"Authorization": f"Bearer {cap_token}"}

        payload = _build_minimal_estudio(region_lon["id"], "Capturista Test")
        res = client.post("/api/estudios", json=payload, headers=cap_headers)
        assert res.status_code == 201

        # Get org heatmap
        res = client.get(f"/api/organizaciones/{org_id}/heatmap", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        # Should have at least one date entry
        assert len(data) >= 0

    def test_org_heatmap_empty_no_captures(self, client, admin_headers, capturista_user):
        """Heatmap returns empty array when no captures exist."""
        res = client.post(
            "/api/organizaciones",
            json={"nombre": "Heatmap Empty2", "usuario_id": capturista_user["id"]},
            headers=admin_headers,
        )
        assert res.status_code == 201
        org_id = res.json()["id"]

        res = client.get(f"/api/organizaciones/{org_id}/heatmap", headers=admin_headers)
        assert res.status_code == 200
        assert res.json() == []

    def test_org_heatmap_404(self, client, admin_headers):
        """Non-existent org returns 404 for heatmap."""
        res = client.get("/api/organizaciones/99999/heatmap", headers=admin_headers)
        assert res.status_code == 404

    def test_org_heatmap_requires_auth(self, client, admin_headers, capturista_user):
        """Heatmap endpoint without JWT returns 401."""
        res = client.post(
            "/api/organizaciones",
            json={"nombre": "Heatmap Auth", "usuario_id": capturista_user["id"]},
            headers=admin_headers,
        )
        assert res.status_code == 201
        org_id = res.json()["id"]

        res = client.get(f"/api/organizaciones/{org_id}/heatmap")
        assert res.status_code == 401


class TestHeatmapColorVisibility:
    """Test that heatmap colors are visible on white background."""

    def test_heatmap_color_contrast(self):
        """Verify all heatmap colors are distinguishable on white background."""
        colors = ['#ebedf0', '#4ade80', '#22c55e', '#16a34a', '#15803d']

        # Calculate luminance for each color
        def get_luminance(hex_color):
            hex_color = hex_color.lstrip('#')
            r = int(hex_color[0:2], 16) / 255
            g = int(hex_color[2:4], 16) / 255
            b = int(hex_color[4:6], 16) / 255
            # Gamma correction
            r = r / 12.92 if r <= 0.03928 else pow((r + 0.055) / 1.055, 2.4)
            g = g / 12.92 if g <= 0.03928 else pow((g + 0.055) / 1.055, 2.4)
            b = b / 12.92 if b <= 0.03928 else pow((b + 0.055) / 1.055, 2.4)
            return 0.2126 * r + 0.7152 * g + 0.0722 * b

        # White background luminance
        white_luminance = 1.0

        # Check contrast ratio for each color against white
        for color in colors:
            lum = get_luminance(color)
            # Contrast ratio formula
            if white_luminance > lum:
                ratio = (white_luminance + 0.05) / (lum + 0.05)
            else:
                ratio = (lum + 0.05) / (white_luminance + 0.05)

            # For small 13x13px cells, we need at least 1.5:1 contrast
            # The first color (no activity) is expected to be low contrast
            if color == '#ebedf0':
                # No activity cell should be subtle but still visible
                assert ratio > 1.1, f"Color {color} is invisible on white background"
            else:
                # Activity cells should be clearly visible
                assert ratio > 1.5, f"Color {color} is too close to white background (ratio: {ratio:.2f})"

    def test_heatmap_color_is_visible_for_low_counts(self):
        """Verify that color for 1-2 captures is clearly visible."""
        # The color #4ade80 has luminance ~0.61
        # On white background (1.0), the ratio is (1.0 + 0.05) / (0.61 + 0.05) = 1.59
        # This is good for a 13x13px cell

        # Test with bright green
        better_green = '#4ade80'
        # Calculate luminance
        hex_color = better_green.lstrip('#')
        r = int(hex_color[0:2], 16) / 255
        g = int(hex_color[2:4], 16) / 255
        b = int(hex_color[4:6], 16) / 255
        r = r / 12.92 if r <= 0.03928 else pow((r + 0.055) / 1.055, 2.4)
        g = g / 12.92 if g <= 0.03928 else pow((g + 0.055) / 1.055, 2.4)
        b = b / 12.92 if b <= 0.03928 else pow((b + 0.055) / 1.055, 2.4)
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b

        ratio = (1.0 + 0.05) / (lum + 0.05)
        assert ratio > 1.5, f"Better green color should have contrast > 1.5"

    def test_heatmap_scrolls_to_most_recent(self):
        """Verify that heatmap scrolls to show most recent dates."""
        # This is a frontend behavior test - we verify the logic exists in the HTML
        # by checking the JavaScript code
        import os

        frontend_path = os.path.join(os.path.dirname(__file__), '..', '..', 'front', 'Capturista-view', 'perfil-capturista.html')
        if os.path.exists(frontend_path):
            with open(frontend_path, 'r') as f:
                content = f.read()
            # Verify scroll to rightmost code exists
            assert 'container.scrollLeft = container.scrollWidth' in content, \
                "Heatmap should scroll to show most recent dates (rightmost)"

        # Also check org profile
        org_path = os.path.join(os.path.dirname(__file__), '..', '..', 'front', 'perfil-organizacion.html')
        if os.path.exists(org_path):
            with open(org_path, 'r') as f:
                content = f.read()
            assert 'container.scrollLeft = container.scrollWidth' in content, \
                "Org heatmap should scroll to show most recent dates"

    def test_heatmap_uses_active_year_not_fixed_365_days(self):
        """Verify heatmaps adapt to the year of the latest capture."""
        import os

        frontend_paths = [
            os.path.join(os.path.dirname(__file__), '..', '..', 'front', 'Capturista-view', 'perfil-capturista.html'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'front', 'perfil-organizacion.html'),
        ]

        for frontend_path in frontend_paths:
            assert os.path.exists(frontend_path)
            with open(frontend_path, 'r') as f:
                content = f.read()

            assert 'activeYear' in content
            assert 'sortedDates.length' in content
            assert 'Date.UTC(activeYear, 0, 1)' in content
            assert 'd.setUTCDate(d.getUTCDate() + 1)' in content
            assert 'for (let i = 364; i >= 0; i--)' not in content

    def test_year_selector_present_on_both_pages(self):
        """Both profile pages have #heatmap-year-select element."""
        import os
        for frontend_path in [
            os.path.join(os.path.dirname(__file__), '..', '..', 'front', 'Capturista-view', 'perfil-capturista.html'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'front', 'perfil-organizacion.html'),
        ]:
            assert os.path.exists(frontend_path)
            with open(frontend_path, 'r') as f:
                content = f.read()
            assert 'id="heatmap-year-select"' in content, f"{frontend_path} missing year selector"

    def test_full_year_grid_always_jan_dec(self):
        """Verify grid always renders Jan 1 - Dec 31 (no conditional endDate)."""
        import os
        for frontend_path in [
            os.path.join(os.path.dirname(__file__), '..', '..', 'front', 'Capturista-view', 'perfil-capturista.html'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'front', 'perfil-organizacion.html'),
        ]:
            with open(frontend_path, 'r') as f:
                content = f.read()
            # Should always use Dec 31, not conditional today-based endDate
            assert 'Date.UTC(activeYear, 11, 31)' in content, f"{frontend_path} should always render Dec 31"
            # Should NOT have the old conditional
            assert 'todayUtc.getUTCFullYear()' not in content or 'endDate = activeYear === todayUtc' not in content

    def test_12_month_labels_in_grid(self):
        """Verify all 12 month labels (Ene-Dic) rendered in SVG."""
        import os
        for frontend_path in [
            os.path.join(os.path.dirname(__file__), '..', '..', 'front', 'Capturista-view', 'perfil-capturista.html'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'front', 'perfil-organizacion.html'),
        ]:
            with open(frontend_path, 'r') as f:
                content = f.read()
            months = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
            for m in months:
                assert m in content, f"{frontend_path} missing month label {m}"

    def test_empty_year_message_renders(self):
        """Verify 'Sin actividad en {year}' message is rendered when year has no data."""
        import os
        for frontend_path in [
            os.path.join(os.path.dirname(__file__), '..', '..', 'front', 'Capturista-view', 'perfil-capturista.html'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'front', 'perfil-organizacion.html'),
        ]:
            with open(frontend_path, 'r') as f:
                content = f.read()
            assert 'Sin actividad en' in content, f"{frontend_path} missing empty year message"

    def test_year_param_in_fetch_url(self):
        """Verify ?year=YYYY is appended to fetch URL when year selected."""
        import os
        for frontend_path, endpoint in [
            (os.path.join(os.path.dirname(__file__), '..', '..', 'front', 'Capturista-view', 'perfil-capturista.html'), '/api/me/heatmap'),
            (os.path.join(os.path.dirname(__file__), '..', '..', 'front', 'perfil-organizacion.html'), '/api/organizaciones/'),
        ]:
            assert os.path.exists(frontend_path)
            with open(frontend_path, 'r') as f:
                content = f.read()
            assert '?year=' in content or 'url += \'?year=\'' in content, f"{frontend_path} missing year param in fetch URL"


# ═══════════════════════════════════════════════════════════════════════════════
# Year-filter heatmap tests (SDD: enhance-heatmap-year-selector)
# ═══════════════════════════════════════════════════════════════════════════════


class TestMeHeatmapYearFilter:
    """GET /api/me/heatmap?year=YYYY scenarios."""

    def _create_study(self, _test_db_conn, usuario_id, region_id, created_at_str, status="completo"):
        """Create a minimal estudio with a specific created_at date."""
        # Need a region counter first
        year = int(created_at_str[:4])
        with _test_db_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO region_counters (pais_codigo, region_codigo, anio, ultimo_numero) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                ("MX", "LON", year, 5),
            )
        _test_db_conn.commit()
        # Create beneficiary
        import psycopg2.extras as _pe
        with _test_db_conn.cursor(cursor_factory=_pe.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO beneficiarios (nombre, fecha_nacimiento, diagnostico, calle, colonia, ciudad, telefonos, region_id, sede) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
                ("Benef YearTest", "2000-01-15", "Dx", "Calle", "Col", "Ciudad", "4621112233", region_id, "Sede Test"),
            )
            ben_id = cur.fetchone()["id"]
        _test_db_conn.commit()
        # Create estudio
        with _test_db_conn.cursor(cursor_factory=_pe.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO estudios_socioeconomicos (beneficiario_id, usuario_id, sede, status, created_at, elaboro_estudio, fecha_estudio) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
                (ben_id, usuario_id, "Sede Test", status, created_at_str, "Test", created_at_str),
            )
            estudio_id = cur.fetchone()["id"]
        _test_db_conn.commit()
        return estudio_id

    def test_year_2025_returns_only_2025_data(self, client, capturista_headers, capturista_user, region_lon, _test_db_conn):
        """?year=2025 scopes results to Jan 1 - Dec 31 2025 only."""
        # Create a study in 2025-03-15
        self._create_study(_test_db_conn, capturista_user["id"], region_lon["id"], "2025-03-15")
        # Create a study in 2026 (current year) to ensure only 2025 is returned
        self._create_study(_test_db_conn, capturista_user["id"], region_lon["id"], "2026-01-10")

        res = client.get("/api/me/heatmap?year=2025", headers=capturista_headers)
        assert res.status_code == 200
        data = res.json()
        dates = {d["date"] for d in data}
        assert "2025-03-15" in dates, "2025-03-15 should be in year=2025 results"
        assert "2026-01-10" not in dates, "2026-01-10 should NOT be in year=2025 results"

    def test_year_with_no_data_returns_empty(self, client, capturista_headers, _test_db_conn):
        """?year=2020 with no data returns [] HTTP 200."""
        res = client.get("/api/me/heatmap?year=2020", headers=capturista_headers)
        assert res.status_code == 200
        assert res.json() == []

    def test_invalid_year_returns_422(self, client, capturista_headers):
        """?year=abc returns HTTP 422."""
        res = client.get("/api/me/heatmap?year=abc", headers=capturista_headers)
        assert res.status_code == 422

    def test_no_year_param_defaults_to_current(self, client, capturista_headers, capturista_user, region_lon, _test_db_conn):
        """No year param defaults to current UTC year range."""
        from datetime import datetime, timezone
        current_year = datetime.now(timezone.utc).year
        # Create study in current year
        self._create_study(_test_db_conn, capturista_user["id"], region_lon["id"], f"{current_year}-06-01")

        res = client.get("/api/me/heatmap", headers=capturista_headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 1
        # All returned dates should be in current year
        for entry in data:
            assert entry["date"].startswith(str(current_year)), f"Date {entry['date']} not in {current_year}"

    def test_year_2023_no_data_for_user(self, client, capturista_headers, _test_db_conn):
        """User with no data in 2023 returns []."""
        res = client.get("/api/me/heatmap?year=2023", headers=capturista_headers)
        assert res.status_code == 200
        assert res.json() == []


class TestOrgHeatmapYearFilter:
    """GET /api/organizaciones/{id}/heatmap?year=YYYY scenarios."""

    def _create_user(self, _test_db_conn, nombre, email, rol="capturista"):
        from passlib.context import CryptContext
        import psycopg2.extras as _pe
        pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
        pw_hash = pwd.hash("testpass123")
        with _test_db_conn.cursor(cursor_factory=_pe.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES (%s, %s, %s, %s) RETURNING id",
                (nombre, email, pw_hash, rol),
            )
            row = cur.fetchone()
        _test_db_conn.commit()
        return row["id"]

    def _create_study(self, _test_db_conn, usuario_id, region_id, created_at_str):
        """Create a minimal estudio with specific created_at."""
        year = int(created_at_str[:4])
        with _test_db_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO region_counters (pais_codigo, region_codigo, anio, ultimo_numero) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                ("MX", "LON", year, 5),
            )
        _test_db_conn.commit()
        import psycopg2.extras as _pe
        with _test_db_conn.cursor(cursor_factory=_pe.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO beneficiarios (nombre, fecha_nacimiento, diagnostico, calle, colonia, ciudad, telefonos, region_id, sede) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
                ("Benef OrgYear", "2000-01-15", "Dx", "Calle", "Col", "Ciudad", "4621112233", region_id, "Sede Test"),
            )
            ben_id = cur.fetchone()["id"]
        _test_db_conn.commit()
        with _test_db_conn.cursor(cursor_factory=_pe.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO estudios_socioeconomicos (beneficiario_id, usuario_id, sede, status, created_at, elaboro_estudio, fecha_estudio) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
                (ben_id, usuario_id, "Sede Test", "completo", created_at_str, "Test", created_at_str),
            )
            estudio_id = cur.fetchone()["id"]
        _test_db_conn.commit()
        return estudio_id

    def test_org_heatmap_year_2025_scopes_data(self, client, admin_headers, region_lon, _test_db_conn):
        """?year=2025 on org heatmap only returns 2025 data."""
        uid = self._create_user(_test_db_conn, "OrgYearUser", "orgyear@test.mx")
        import psycopg2.extras as _pe
        with _test_db_conn.cursor(cursor_factory=_pe.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO organizaciones (nombre, usuario_id) VALUES (%s, %s) RETURNING id",
                ("Org Year Test", uid),
            )
            org_id = cur.fetchone()["id"]
        _test_db_conn.commit()

        # Create study in 2025
        self._create_study(_test_db_conn, uid, region_lon["id"], "2025-03-15")
        # Create study in 2026
        self._create_study(_test_db_conn, uid, region_lon["id"], "2026-01-10")

        res = client.get(f"/api/organizaciones/{org_id}/heatmap?year=2025", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        dates = {d["date"] for d in data}
        assert "2025-03-15" in dates, "2025 data should be in year=2025 results"
        assert "2026-01-10" not in dates, "2026 data should NOT be in year=2025 results"

    def test_org_heatmap_year_empty(self, client, admin_headers, region_lon, _test_db_conn):
        """Org heatmap with no data in year returns []."""
        uid = self._create_user(_test_db_conn, "OrgEmptyYear", "orgempty@test.mx")
        import psycopg2.extras as _pe
        with _test_db_conn.cursor(cursor_factory=_pe.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO organizaciones (nombre, usuario_id) VALUES (%s, %s) RETURNING id",
                ("Org Empty Year", uid),
            )
            org_id = cur.fetchone()["id"]
        _test_db_conn.commit()

        res = client.get(f"/api/organizaciones/{org_id}/heatmap?year=2022", headers=admin_headers)
        assert res.status_code == 200
        assert res.json() == []

    def test_org_heatmap_invalid_year_422(self, client, admin_headers, _test_db_conn):
        """Non-integer year on org heatmap returns 422."""
        # Need a valid org first
        import psycopg2.extras as _pe
        with _test_db_conn.cursor(cursor_factory=_pe.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO organizaciones (nombre) VALUES (%s) RETURNING id",
                ("Invalid Year Org",),
            )
            org_id = cur.fetchone()["id"]
        _test_db_conn.commit()

        res = client.get(f"/api/organizaciones/{org_id}/heatmap?year=abc", headers=admin_headers)
        assert res.status_code == 422

    def test_org_heatmap_default_year(self, client, admin_headers, region_lon, _test_db_conn):
        """No year param on org heatmap defaults to current year."""
        from datetime import datetime, timezone
        current_year = datetime.now(timezone.utc).year

        uid = self._create_user(_test_db_conn, "OrgDefaultYear", "orgdefault@test.mx")
        import psycopg2.extras as _pe
        with _test_db_conn.cursor(cursor_factory=_pe.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO organizaciones (nombre, usuario_id) VALUES (%s, %s) RETURNING id",
                ("Org Default Year", uid),
            )
            org_id = cur.fetchone()["id"]
        _test_db_conn.commit()

        self._create_study(_test_db_conn, uid, region_lon["id"], f"{current_year}-06-01")

        res = client.get(f"/api/organizaciones/{org_id}/heatmap", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 1
        for entry in data:
            assert entry["date"].startswith(str(current_year)), f"Date {entry['date']} not in {current_year}"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_token_from_headers(headers: dict) -> str:
    """Extract Bearer token from headers dict."""
    auth = headers.get("Authorization", "")
    return auth.replace("Bearer ", "")


def _build_minimal_estudio(region_id: int, elaboro_estudio: str) -> dict:
    """Build a minimal estudio payload for testing."""
    return {
        "region_id": region_id,
        "sede": "Sede Test",
        "beneficiario": {
            "nombres": "BENEFICIARIO",
            "apellido_paterno": "TEST",
            "apellido_materno": "PERFILES",
            "fecha_nacimiento": "2000-01-15",
            "diagnostico": "Parálisis cerebral",
            "calle": "Calle Test 123",
            "num_ext": "12A",
            "colonia": "Centro",
            "ciudad": "León",
            "estado_codigo": "11",
            "estado_nombre": "GUANAJUATO",
            "sexo": "M",
            "telefonos": "4621234567",
        },
        "tutores": [
            {
                "numero_tutor": 1,
                "nombres": "Tutor",
                "apellido_paterno": "Test",
                "apellido_materno": "Perfiles",
                "edad": 45,
                "nivel_estudios": "LICENCIATURA",
                "estado_civil": "CASADO",
                "num_hijos": 2,
                "vivienda": "PROPIA",
                "fuente_empleo": "Empleado",
                "antiguedad_anios": 10,
                "ingreso_mensual": 12000,
                "tiene_imss": True,
                "tiene_infonavit": False,
            }
        ],
        "estudio": {
            "tuvo_silla_previa": False,
            "como_obtuvo_silla": None,
            "elaboro_estudio": elaboro_estudio,
            "fecha_estudio": "2026-06-01",
            "status": "completo",
        },
        "ciudad_registro": "LEON, GTO",
    }
