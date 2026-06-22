"""CloudTask AI SaaS — pacote principal da aplicação.

Este pacote concentra todo o código de servidor: ponto de entrada
(:mod:`app.main`), camada HTTP (:mod:`app.api`), modelos e schemas
compartilhados (:mod:`app.schemas`).

A variável :data:`__version__` é a fonte única de verdade para a versão
exposta no Swagger (``/docs``) e no endpoint raiz (``GET /``).

Política de versionamento
-------------------------

A versão é incrementada **a cada nova semana** (branch ``semana-0N-...``)
no formato ``0.N.0``:

* Semana 1 → ``0.1.0``
* Semana 2 → ``0.2.0``
* Semana 3 → ``0.3.0``
* Semana 4 → ``0.4.0`` *(estado atual)*
* Semana 5 → ``0.5.0``
* Semana 6 → ``0.6.0`` *(versão final da disciplina)*

A versão não muda entre aulas da mesma semana (Aula 1 e Aula 2 ambas
em ``0.1.0``, por exemplo).

Aulas futuras vão expandir este pacote com:

* ``app.core`` — configuração via ``.env`` (Aula 4)
* ``app.db`` — SQLAlchemy + modelos (Aula 3)
* ``app.services`` — integrações S3 / DynamoDB (Aulas 5 e 10)

Attributes:
    __version__ (str): Versão semântica da aplicação (``0.N.0``, onde
        ``N`` é o número da semana corrente).
"""

# Atualize SOMENTE ao criar uma nova branch de semana. Aulas dentro da
# mesma semana mantêm a versão.
__version__: str = "0.5.0"
