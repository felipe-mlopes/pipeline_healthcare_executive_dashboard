# ---- Stage 1: build das dependências ----
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --user -r requirements.txt

# ---- Stage 2: imagem final, enxuta e sem root ----
FROM python:3.11-slim 

# Cria usuário/grupo não-root dedicados (não roda como root em produção)
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

# Copia apenas as dependências já instaladas (sem cache/lixo de build)
COPY --from=builder /root/.local /home/appuser/.local

# Copia somente o código necessário para rodar o pipeline
COPY config/ ./config/
COPY extract/ ./extract/
COPY load/ ./load/
COPY utils/ ./utils/
COPY main.py .

# Diretório de staging local, efêmero durante a execução do job
RUN mkdir -p /tmp/data && chown -R appuser:appuser /tmp/data /app 

ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_PATH=/tmp/data

USER appuser

# Cloud Run Jobs não expõe porta/HTTP — é execução batch (roda e termina).
ENTRYPOINT ["python", "main.py"]