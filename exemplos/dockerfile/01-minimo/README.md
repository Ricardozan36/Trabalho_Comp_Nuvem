# Dockerfile mínimo

A versão **mais curta possível** que ainda é funcional. Cada linha tem exatamente um propósito:

| Linha                    | Função                                                     |
| ------------------------ | ---------------------------------------------------------- |
| `FROM public.ecr.aws/docker/library/python:3.11-slim`  | Imagem base enxuta com Python pré-instalado.               |
| `WORKDIR /app`           | Define `/app` como pasta de trabalho dentro do container.  |
| `COPY requirements.txt .`| Copia só o arquivo de dependências primeiro.               |
| `RUN pip install ...`    | Instala as dependências (sem cache do pip).                |
| `COPY . .`               | Copia o resto do projeto.                                  |
| `EXPOSE 8000`            | Documenta a porta usada (não publica sozinho).             |
| `CMD [...]`              | Comando padrão executado quando o container sobe.          |

## Como rodar

```bash
docker build -t exemplo-minimo .
docker run --rm -p 8000:8000 exemplo-minimo
curl http://localhost:8000/health
```

## O que **falta** aqui (e existe no `02-completo`)

- `.dockerignore` para evitar copiar `.git`, `.venv`, etc.
- Usuário não-root (segurança).
- Healthcheck.
- Multi-stage build (imagem final menor).
- Variáveis de ambiente bem definidas.
