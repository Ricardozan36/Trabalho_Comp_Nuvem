"""Testes da autenticação JWT (Aula 12).

Usa um ``TestClient`` PRÓPRIO (sem o override de ``require_auth`` do
``conftest.client``), para exercitar a guarda de verdade.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


@pytest.fixture
def raw_client() -> TestClient:
    """Cliente sem overrides — a autenticação real fica ativa."""
    app.dependency_overrides.clear()
    return TestClient(app)


def test_login_ok(raw_client: TestClient) -> None:
    r = raw_client.post(
        "/auth/login",
        json={"username": settings.admin_username, "password": settings.admin_password},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"].count(".") == 2  # header.payload.assinatura
    assert body["expires_in"] == settings.jwt_expire_minutes * 60


def test_login_senha_errada(raw_client: TestClient) -> None:
    r = raw_client.post(
        "/auth/login", json={"username": "admin", "password": "errada"}
    )
    assert r.status_code == 401


def test_rota_protegida_sem_token(raw_client: TestClient) -> None:
    # /tasks exige token; sem ele, 401 ANTES de tocar o banco.
    assert raw_client.get("/tasks").status_code == 401


def test_me_com_token(raw_client: TestClient) -> None:
    login = raw_client.post(
        "/auth/login",
        json={"username": settings.admin_username, "password": settings.admin_password},
    ).json()
    token = login["access_token"]
    r = raw_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["username"] == settings.admin_username


def test_token_invalido(raw_client: TestClient) -> None:
    r = raw_client.get("/auth/me", headers={"Authorization": "Bearer abc.def.ghi"})
    assert r.status_code == 401
