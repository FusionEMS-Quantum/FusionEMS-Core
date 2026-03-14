FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV UVICORN_WORKERS=2

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 10001 fusionems && useradd --system --uid 10001 --gid 10001 fusionems

COPY pyproject.toml /app/pyproject.toml

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir uv \
    && python3 -c "import tomllib; deps=tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']; open('/tmp/deps.txt','w').write('\n'.join(deps))" \
    && uv pip install --system --no-cache -r /tmp/deps.txt

COPY . /app

RUN chown -R fusionems:fusionems /app

USER fusionems

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/healthz || exit 1

CMD ["uvicorn", "core_app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
