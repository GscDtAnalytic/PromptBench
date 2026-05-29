FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependências de sistema mínimas (postgres client para alembic via psycopg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instala uv (gerenciador rápido)
RUN pip install uv==0.5.13

# Copia metadata primeiro pra cachear a layer de deps
COPY pyproject.toml /app/
RUN uv pip install --system -e .

# Copia o restante (em dev, o volume sobrescreve)
COPY . /app

EXPOSE 8000
