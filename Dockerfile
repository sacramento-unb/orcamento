# syntax=docker/dockerfile:1

FROM node:26-alpine AS frontend-build

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM python:3.14-slim AS runtime

ARG APP_UID=1000
ARG APP_GID=1000

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=America/Sao_Paulo

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && existing_group="$(getent group "${APP_GID}" | cut -d: -f1)" \
    && if [ -n "${existing_group}" ]; then groupmod --new-name appgroup "${existing_group}"; else groupadd --gid "${APP_GID}" appgroup; fi \
    && useradd --uid "${APP_UID}" --gid appgroup --create-home appuser

COPY backend/requirements.txt /app/backend/requirements.txt
RUN python -m pip install --requirement /app/backend/requirements.txt

COPY --chown=appuser:appgroup backend/ /app/backend/
COPY --chown=appuser:appgroup gunicorn.conf.py /app/gunicorn.conf.py
COPY --from=frontend-build --chown=appuser:appgroup /build/frontend/dist /app/frontend/dist

RUN mkdir -p /app/data /app/exports \
    && chown -R appuser:appgroup /app/data /app/exports

USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/api/health', timeout=2)" || exit 1

CMD ["gunicorn", "--config", "gunicorn.conf.py", "backend.app:app"]
