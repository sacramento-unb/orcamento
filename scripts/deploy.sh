#!/usr/bin/env bash
set -Eeuo pipefail

source_dir="${1:-${GITHUB_WORKSPACE:-}}"
deploy_dir="${2:-${HOME}/apps/orcamento}"

if [[ -z "${source_dir}" || ! -f "${source_dir}/compose.yaml" ]]; then
  echo "Diretorio de origem invalido: ${source_dir:-<vazio>}" >&2
  exit 1
fi

for command_name in docker rsync; do
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "Comando obrigatorio ausente: ${command_name}" >&2
    exit 1
  fi
done

mkdir -p "${deploy_dir}" "${deploy_dir}/data" "${deploy_dir}/exports"

if [[ ! -f "${deploy_dir}/.env" ]]; then
  umask 077
  {
    printf 'APP_BIND_IP=127.0.0.1\n'
    printf 'APP_PORT=5050\n'
    printf 'APP_UID=%s\n' "$(id -u)"
    printf 'APP_GID=%s\n' "$(id -g)"
  } >"${deploy_dir}/.env"
fi

rsync --archive --delete \
  --exclude '/.env' \
  --exclude '/.git/' \
  --exclude '/data/' \
  --exclude '/exports/' \
  "${source_dir}/" "${deploy_dir}/"

cd "${deploy_dir}"
docker compose --env-file .env config --quiet
docker compose --env-file .env up --build --detach --remove-orphans

for attempt in {1..30}; do
  if docker compose --env-file .env exec --no-TTY app \
    python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/api/health', timeout=2)"; then
    docker compose --env-file .env ps
    exit 0
  fi
  sleep 2
done

docker compose --env-file .env logs --tail=100 app >&2
echo "A aplicacao nao ficou saudavel dentro do prazo." >&2
exit 1
