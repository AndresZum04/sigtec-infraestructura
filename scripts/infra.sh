#!/usr/bin/env bash
# Compatible con el Bash 3.2 de macOS; los scripts originales usan Bash 4+.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

compose() {
  if [[ "$(uname -s)" == Darwin && "$(uname -m)" == arm64 ]]; then
    docker compose -f docker-compose.yml -f "$ROOT/config/compose.macos.yml" "$@"
  else
    docker compose -f docker-compose.yml "$@"
  fi
}

modern_bash() {
  local candidate
  for candidate in /opt/homebrew/bin/bash /usr/local/bin/bash "$(command -v bash)"; do
    if [[ -x "$candidate" ]] && "$candidate" -c '(( BASH_VERSINFO[0] >= 4 ))'; then
      "$candidate" "$@"
      return
    fi
  done
  echo 'Se necesita Bash 4 o posterior para los scripts de infraestructura.' >&2
  return 1
}

sql() {
  docker exec -i "sigtec-$1" psql -U postgres -d sigtec -At -v ON_ERROR_STOP=1 -c "$2"
}

case "${1:-status}" in
  up)
    if [[ "$(uname -s)" == Darwin && "$(uname -m)" == arm64 ]]; then
      # Docker Desktop puede montar archivos del host sin permiso de ejecución.
      # Postgres hace source de los .sh sin +x; no se cambia el repositorio original.
      mkdir -p "$ROOT/.local/init"
      cp init/20_capas.sql init/30_nodo.sh "$ROOT/.local/init/"
      chmod a-x "$ROOT/.local/init/30_nodo.sh"
    fi
    compose up -d --wait --wait-timeout 240
    for node in central cartago sanjose sancarlos alajuela limon; do
      # Completa también una inicialización anterior que se interrumpió en el .sh.
      if [[ "$(sql "$node" "SELECT to_regprocedure('public.campus_local()') IS NOT NULL;")" != t ]]; then
        docker exec "sigtec-$node" bash /docker-entrypoint-initdb.d/30_nodo.sh
      fi
    done
    existing=$(sql central "SELECT count(*) FROM pg_subscription WHERE subname IN ('sub_desde_cartago','sub_desde_san_jose','sub_desde_san_carlos','sub_desde_alajuela','sub_desde_limon');")
    campus_total=0
    for node in cartago sanjose sancarlos alajuela limon; do
      count=$(sql "$node" "SELECT count(*) FROM pg_subscription WHERE subname LIKE 'sub_global_%';")
      campus_total=$((campus_total + count))
    done
    if [[ "$existing" == 0 && "$campus_total" == 0 ]]; then
      modern_bash scripts/replicacion.sh
    elif [[ "$existing" == 5 && "$campus_total" == 5 ]]; then
      echo 'Las suscripciones ya existen; no se vuelven a crear.'
    else
      echo 'La replicación está parcialmente configurada. Revisar antes de continuar.' >&2
      exit 1
    fi
    ;;
  status) compose ps ;;
  counts) modern_bash scripts/conteos.sh "${2:-edificios}" ;;
  stop) compose stop ;;
  *) echo 'Uso: bash scripts/infra.sh {up|status|counts [tabla]|stop}' >&2; exit 2 ;;
esac
