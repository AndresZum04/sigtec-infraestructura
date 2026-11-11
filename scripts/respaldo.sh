#!/usr/bin/env bash
set -euo pipefail
export MSYS_NO_PATHCONV=1
N=${1:?uso: respaldo.sh <nodo>}
TS=$(date +%Y%m%d_%H%M%S)
declare -A ESQ=( [cartago]=cartago [sanjose]=san_jose [sancarlos]=san_carlos [alajuela]=alajuela [limon]=limon )

echo "== Respaldo lógico completo"
docker exec -u postgres "sigtec-$N" pg_dump -d sigtec -Fc -f "/respaldos/logico_sigtec_$TS.dump"

if [[ -n "${ESQ[$N]:-}" ]]; then
  echo "== Respaldo lógico del esquema ${ESQ[$N]}"
  docker exec -u postgres "sigtec-$N" pg_dump -d sigtec -Fc -n "${ESQ[$N]}" \
    -f "/respaldos/logico_${ESQ[$N]}_$TS.dump"
fi

echo "== Respaldo físico (pg_basebackup)"
docker exec -u postgres "sigtec-$N" pg_basebackup -D "/respaldos/base_$TS" -Fp -Xs -P

echo "Respaldos en respaldos/$N/  (base_$TS)"
