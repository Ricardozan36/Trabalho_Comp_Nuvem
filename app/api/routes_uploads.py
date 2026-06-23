"""
Rotas de upload de arquivos (``/uploads``) — Aula 5.

Endpoints:
    * ``POST /uploads``              — recebe um arquivo, persiste e devolve
      ``UploadResponse`` com o nome final e a URL de download.
    * ``GET  /uploads/{filename}``  — baixa o arquivo (modo local) ou redireciona
      para a URL pré-assinada (modo S3).

A escolha entre backend local e S3 é feita por
:func:`app.services.s3_service.get_storage`, que lê ``settings.storage_mode``.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from fastapi.responses import (
    FileResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)

from app.core.config import settings
from app.schemas import DownloadUrlResponse, UploadResponse
from app.services.s3_service import (
    LocalStorage,
    S3Storage,
    StorageError,
    get_storage,
)

router = APIRouter(prefix="/uploads", tags=["uploads"])


# Limite de tamanho por arquivo (10 MB). POR QUÊ: evitar que um upload enorme
# trave o processo. Ajustável em produção via env, se necessário.
_MAX_BYTES = 10 * 1024 * 1024


CREATE_DESCRIPTION = """\
Recebe um arquivo via `multipart/form-data` e o salva no storage configurado.

| Modo (`STORAGE_MODE`) | Onde grava | URL devolvida |
| --- | --- | --- |
| `local` | pasta `LOCAL_UPLOADS_DIR` no container | `/uploads/<nome>` (servido pela própria API) |
| `s3` | bucket `S3_BUCKET_NAME` | URL **pré-assinada** com expiração |

Trocar de modo NÃO exige mexer no código — só mudar a variável de ambiente.

> <kbd>Limite</kbd> arquivos acima de **10 MB** são rejeitados (`413`).

### Exemplo de chamada

```bash
curl -F "file=@./tarefa.pdf" http://localhost:8000/uploads
```
"""


@router.post(
    "",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enviar arquivo (multipart/form-data)",
    description=CREATE_DESCRIPTION,
    responses={
        201: {"description": "Arquivo salvo com sucesso."},
        413: {"description": "Arquivo excede o limite (10 MB)."},
        500: {"description": "Falha ao salvar (disco cheio, S3 indisponível, etc.)."},
    },
)
async def create_upload(file: UploadFile = File(...)) -> UploadResponse:
    """Persiste o arquivo recebido no backend configurado.

    Args:
        file: Arquivo enviado pelo cliente (multipart).

    Returns:
        UploadResponse: nome final, URL de download e backend usado.

    Raises:
        HTTPException: 413 se o tamanho ultrapassar o limite; 500 em falhas de I/O.
    """
    # Lê em pedaços para controlar o tamanho total e não estourar memória.
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > _MAX_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Arquivo excede {_MAX_BYTES // (1024 * 1024)} MB.",
            )
        chunks.append(chunk)
    await file.close()

    # Repassa o conteúdo já lido como bytes para o backend.
    import io

    buffer = io.BytesIO(b"".join(chunks))
    storage = get_storage()
    try:
        stored_name = storage.save(
            filename=file.filename or "anexo.bin",
            content_type=file.content_type,
            file_obj=buffer,
        )
    except StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc

    return UploadResponse(
        filename=stored_name,
        url=storage.get_download_url(stored_name),
        storage_mode=settings.storage_mode,
    )


GET_DESCRIPTION = """\
Baixa o arquivo previamente enviado. O parâmetro `via` escolhe **como** o
download acontece — os três modos existem para ilustrar os padrões de entrega
de arquivos na nuvem.

| `via` | Modo `s3` | Modo `local` | Quando usar |
| --- | --- | --- | --- |
| `redirect` *(default)* | `307` → URL pré-assinada | serve o arquivo do disco | **padrão de produção**: o S3 entrega direto ao cliente |
| `url` | `200` JSON `{url, expires_in}` | `200` JSON (`url` = rota da API) | frontend baixa em **1 clique** (ver snippet abaixo) |
| `stream` | `200` com os **bytes** (proxy) | serve o arquivo do disco | funciona no **Swagger**; veja a ressalva abaixo |

### ⚠️ Por que NÃO baixar pela API (`via=stream`) em produção?

No modo `stream` (proxy) o arquivo trafega **`S3 → API → cliente`**. Isso:

* **dobra a banda** (paga-se egress ~2x) e satura a rede da API;
* **prende um worker** da API durante toda a transferência;
* **não escala barato** — para servir downloads pesados você teria que crescer a
  API só para empurrar bytes;
* **perde features do S3/CDN** (CloudFront, *range requests* / pausar-e-retomar).

> **Regra de ouro:** a **API autoriza** (gera a URL pré-assinada que expira) e o
> **S3/CDN entrega** os bytes. O `stream` existe aqui só porque o **Swagger UI**
> (rodando no browser) não consegue seguir o redirect `307` até o S3 sem CORS.

### Frontend de 1 clique (modo `url`)

```js
const { url } = await fetch(`/uploads/${name}?via=url`).then(r => r.json());
window.location = url;   // baixa direto do S3 — 1 clique do usuário
```
"""


@router.get(
    "/{filename}",
    summary="Baixar arquivo",
    description=GET_DESCRIPTION,
    responses={
        200: {"description": "Bytes do arquivo (`via=stream`/local) **ou** JSON `DownloadUrlResponse` (`via=url`)."},
        307: {"description": "Redirect para URL pré-assinada do S3 (`via=redirect`, modo S3)."},
        404: {"description": "Arquivo não encontrado."},
    },
)
async def get_upload(
    filename: str,
    via: Literal["stream", "url", "redirect"] = Query(
        "redirect",
        description=(
            "Como entregar o download: `redirect` (307 → S3, padrão de produção), "
            "`url` (JSON com a URL pré-assinada, ideal p/ frontend) ou "
            "`stream` (API faz proxy dos bytes — funciona no Swagger, mas é "
            "anti-padrão em produção)."
        ),
    ),
) -> Response:
    """Devolve o arquivo conforme o modo de entrega escolhido em ``via``.

    Args:
        filename: Nome armazenado (devolvido pelo `POST /uploads`).
        via: Estratégia de download (`redirect` | `url` | `stream`). Veja a
            descrição do endpoint para o trade-off de cada uma.

    Returns:
        Response: `RedirectResponse` (307), `DownloadUrlResponse` (JSON 200),
        `StreamingResponse`/`FileResponse` (bytes 200), conforme ``via`` e o
        ``storage_mode`` configurado.

    Raises:
        HTTPException: 404 se o arquivo não existir.
    """
    storage = get_storage()
    if not storage.exists(filename):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arquivo {filename!r} não encontrado.",
        )

    # via=url: devolve a URL de download (não os bytes). Mesmo formato nos dois
    # backends — só muda a URL e se ela expira.
    if via == "url":
        return DownloadUrlResponse(
            url=storage.get_download_url(filename),
            expires_in=(
                settings.s3_presigned_url_expires
                if settings.storage_mode == "s3"
                else None
            ),
            storage_mode=settings.storage_mode,
        )

    if settings.storage_mode == "s3":
        assert isinstance(storage, S3Storage)
        if via == "stream":
            # PROXY: a API baixa do S3 e repassa os bytes. Anti-padrão em prod
            # (banda dobra), mas é o único modo que funciona dentro do Swagger.
            body, meta = storage.open_stream(filename)
            return StreamingResponse(
                body.iter_chunks(),
                media_type=meta["content_type"] or "application/octet-stream",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        # via=redirect: devolve 307 para a URL pré-assinada — o cliente baixa
        # direto do bucket (padrão de produção: API autoriza, S3 entrega).
        url = storage.get_download_url(filename)
        return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    # Modo local: não há S3 para redirecionar; serve sempre o arquivo do disco
    # (vale tanto para via=stream quanto via=redirect). FileResponse cuida do
    # streaming e dos headers.
    assert isinstance(storage, LocalStorage)
    path = storage.base_dir / filename
    return FileResponse(path=str(path), filename=filename)


@router.delete(
    "/{filename}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Apagar arquivo",
    responses={
        204: {"description": "Arquivo apagado."},
        404: {"description": "Arquivo não encontrado."},
    },
)
async def delete_upload(filename: str) -> Response:
    """Apaga um arquivo do storage (local ou S3).

    Usado pelo frontend no botão "apagar anexo" (Aula 12). Idempotente do ponto
    de vista do cliente: se o arquivo não existe, devolve 404.

    Args:
        filename: Nome armazenado (o mesmo devolvido pelo `POST /uploads`).

    Raises:
        HTTPException: 404 se o arquivo não existir.
    """
    storage = get_storage()
    if not storage.exists(filename):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arquivo {filename!r} não encontrado.",
        )
    try:
        storage.delete(filename)
    except StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao apagar: {exc}",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
