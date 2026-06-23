"""Autenticação por token JWT (Aula 12) — implementada só com a stdlib.

POR QUÊ JWT "na mão" (sem biblioteca externa):
    o projeto evita dependências desnecessárias e, didaticamente, mostrar como um
    **JWT** é montado (header.payload.assinatura) ensina mais do que esconder
    tudo numa lib. Para produção real, prefira uma biblioteca consolidada
    (PyJWT / python-jose) e um provedor de identidade (OAuth/Cognito) — ver a
    nota em ``config.py``.

Fluxo:
    1. ``POST /auth/login`` confere usuário/senha (a conta admin do ``Settings``).
    2. Se OK, :func:`create_access_token` devolve um JWT assinado com
       ``settings.secret_key`` (HS256) e validade ``jwt_expire_minutes``.
    3. As rotas protegidas dependem de :func:`require_auth`, que lê o cabeçalho
       ``Authorization: Bearer <token>``, valida assinatura + expiração e libera.

RISCO/LIMITAÇÃO (consciente, por ser demo):
    * conta única fixa (``admin``/``admin#123``) — em produção, banco de usuários
      com senhas com hash (bcrypt/argon2) e MFA.
    * sem refresh token / revogação — o token vale até expirar.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

ALGORITHM = "HS256"

# Extrai o cabeçalho `Authorization: Bearer <token>`. auto_error=False para
# devolvermos uma mensagem própria quando faltar o token.
_bearer = HTTPBearer(auto_error=False)


def _b64u_encode(raw: bytes) -> str:
    """base64url SEM padding (formato dos segmentos JWT)."""
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64u_decode(seg: str) -> bytes:
    """Inverso de :func:`_b64u_encode` (recoloca o padding)."""
    return base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4))


def _sign(signing_input: str) -> str:
    """Assina ``header.payload`` com HMAC-SHA256 e a ``secret_key``."""
    digest = hmac.new(
        settings.secret_key.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return _b64u_encode(digest)


def create_access_token(subject: str) -> str:
    """Cria um JWT assinado para ``subject`` (o nome do usuário).

    Args:
        subject: identificador do usuário (vai no claim ``sub``).

    Returns:
        str: o token ``header.payload.assinatura``.
    """
    now = int(time.time())
    header = {"alg": ALGORITHM, "typ": "JWT"}
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + settings.jwt_expire_minutes * 60,
    }
    seg = (
        _b64u_encode(json.dumps(header, separators=(",", ":")).encode())
        + "."
        + _b64u_encode(json.dumps(payload, separators=(",", ":")).encode())
    )
    return f"{seg}.{_sign(seg)}"


def decode_token(token: str) -> dict:
    """Valida assinatura + expiração e devolve o payload.

    Raises:
        ValueError: se o formato, a assinatura ou a validade estiverem errados.
    """
    try:
        header_b64, payload_b64, sig = token.split(".")
    except ValueError as exc:  # número errado de segmentos
        raise ValueError("token malformado") from exc

    signing_input = f"{header_b64}.{payload_b64}"
    if not hmac.compare_digest(_sign(signing_input), sig):
        raise ValueError("assinatura inválida")

    payload = json.loads(_b64u_decode(payload_b64))
    if int(payload.get("exp", 0)) < int(time.time()):
        raise ValueError("token expirado")
    return payload


def authenticate(username: str, password: str) -> bool:
    """Confere as credenciais contra a conta admin do ``Settings``.

    Usa :func:`hmac.compare_digest` (comparação em tempo constante) para não
    vazar informação por tempo de resposta.
    """
    user_ok = hmac.compare_digest(username, settings.admin_username)
    pass_ok = hmac.compare_digest(password, settings.admin_password)
    return user_ok and pass_ok


def require_auth(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str:
    """Dependência do FastAPI que protege rotas: exige um Bearer token válido.

    Returns:
        str: o ``sub`` (usuário) do token.

    Raises:
        HTTPException: 401 se faltar o token ou ele for inválido/expirado.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado (envie Authorization: Bearer <token>).",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return str(payload.get("sub", ""))
