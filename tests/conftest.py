"""
Fixtures compartilhadas pelos testes (pytest).

Estratégia de banco para os testes de integração:
    * Reutilizamos o **mesmo banco da aplicação** (``settings.database_url``,
      em geral ``cloudtask``) — NÃO criamos um banco ``cloudtask_test``
      separado.
    * Cada teste roda dentro de uma TRANSAÇÃO + SAVEPOINT que é desfeita
      (``rollback``) no final. POR QUÊ: garante isolamento sem precisar
      apagar/criar bancos e funciona mesmo quando as rotas chamam
      ``db.commit()`` (graças ao ``join_transaction_mode="create_savepoint"``).
    * As tabelas são criadas uma vez por sessão de testes.

POR QUÊ não usamos um banco ``_test`` separado: em alguns ambientes (imagens
do PostgreSQL com inicialização específica), bancos criados depois do startup
recusavam autenticação para o mesmo usuário, embora o banco padrão aceitasse.
O padrão de rollback é mais simples, robusto e cross-environment.

EFEITO: os testes NÃO deixam dados no banco ``cloudtask`` (tudo é desfeito).
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.security import require_auth
from app.db.database import Base, get_db
from app.main import app


@pytest.fixture(autouse=True)
def _isolate_event_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Isola o event store (Aula 10) num arquivo temporário por teste.

    POR QUÊ autouse: o CRUD de tarefas passou a **emitir eventos**
    (create/update/delete). Sem este isolamento, os testes gravariam no
    ``./local_events/events.json`` real (poluição). Aqui forçamos o modo
    ``local`` e um arquivo temporário descartável a cada teste.
    """
    monkeypatch.setattr(settings, "event_store_mode", "local", raising=False)
    monkeypatch.setattr(
        settings, "local_events_file", str(tmp_path / "events.json"), raising=False
    )


@pytest.fixture(scope="session")
def engine() -> Generator[Engine, None, None]:
    """Engine SQLAlchemy ligada ao banco da aplicação (escopo de sessão).

    Cria todas as tabelas uma única vez. Não precisa de banco separado: o
    isolamento por teste é feito via transação na fixture ``db_session``.
    """
    eng = create_engine(settings.database_url, pool_pre_ping=True, future=True)
    Base.metadata.create_all(bind=eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Generator[Session, None, None]:
    """Sessão isolada por teste — tudo é desfeito ao fim com ``rollback``.

    Como funciona:
        1. Abrimos uma conexão e iniciamos uma transação externa.
        2. Criamos a sessão presa a essa conexão, com
           ``join_transaction_mode="create_savepoint"``: quando a rota chamar
           ``session.commit()``, na verdade só o SAVEPOINT interno é "liberado"
           — a transação externa continua aberta.
        3. Ao final do teste, o ``transaction.rollback()`` desfaz TUDO
           (incluindo o que o ``commit`` da rota gravou). O banco volta ao
           estado anterior, sem precisar deletar registros manualmente.
    """
    connection: Connection = engine.connect()
    transaction = connection.begin()

    # TRUNCATE dentro da transação externa: o teste passa a ver as tabelas
    # VAZIAS independentemente do que o aluno tenha criado pelo Swagger durante
    # o desenvolvimento. POR QUÊ funciona sem afetar dev: o `rollback` no
    # `finally` desfaz ESTE truncate junto com tudo o que o teste inseriu, então
    # os dados de desenvolvimento permanecem intactos no banco.
    # `RESTART IDENTITY` reinicia a sequência do id (cosmético; testes não
    # dependem de id específico).
    connection.execute(text("TRUNCATE TABLE tasks RESTART IDENTITY CASCADE"))

    SessionTesting = sessionmaker(
        bind=connection,
        expire_on_commit=False,
        class_=Session,
        join_transaction_mode="create_savepoint",
    )
    session = SessionTesting()
    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Cliente HTTP de teste do FastAPI usando a sessão isolada acima."""

    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    # Aula 12: as rotas de dados passaram a exigir token JWT. Os testes de CRUD/
    # uploads/eventos NÃO mandam token — então aqui desligamos a guarda (fingimos
    # um admin autenticado). A autenticação em si é testada em test_auth.py, que
    # usa um client SEM esse override.
    app.dependency_overrides[require_auth] = lambda: "admin"
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
