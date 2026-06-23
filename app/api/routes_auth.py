"""Rotas de autenticação (``/auth``) — Aula 12.

* ``POST /auth/login`` — recebe usuário/senha, devolve um token JWT.
* ``GET  /auth/me``    — devolve quem é o portador do token (rota protegida).

O frontend guarda o token e o envia em ``Authorization: Bearer <token>`` nas
chamadas às rotas de dados (``/tasks``, ``/uploads``, ``/events``).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.security import authenticate, create_access_token, require_auth

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Credenciais enviadas pelo frontend na tela de login."""

    username: str = Field(..., examples=["admin"])
    password: str = Field(..., examples=["admin#123"])


class TokenResponse(BaseModel):
    """Token devolvido após login bem-sucedido."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Validade do token em segundos.")


LOGIN_DESCRIPTION = """\
Autentica a conta administrativa e devolve um **token JWT**.

| Campo | Valor (demo) |
| --- | --- |
| `username` | `admin` |
| `password` | `admin#123` |

Use o `access_token` retornado no cabeçalho das próximas chamadas:
`Authorization: Bearer <access_token>`.
"""


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login (devolve JWT)",
    description=LOGIN_DESCRIPTION,
    responses={401: {"description": "Usuário ou senha inválidos."}},
)
def login(body: LoginRequest) -> TokenResponse:
    """Confere as credenciais e emite um token JWT."""
    if not authenticate(body.username, body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha inválidos.",
        )
    token = create_access_token(subject=body.username)
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.get(
    "/me",
    summary="Quem sou eu (rota protegida)",
    responses={401: {"description": "Token ausente ou inválido."}},
)
def me(user: Annotated[str, Depends(require_auth)]) -> dict:
    """Devolve o usuário do token — útil para o frontend validar a sessão."""
    return {"username": user}
