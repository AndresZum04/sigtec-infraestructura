#!/usr/bin/env bash
set -euo pipefail
export MSYS_NO_PATHCONV=1
N=${1:?uso: restaurar_pitr.sh <nodo> <base_XXXX> "<YYYY-MM-DD HH:MM:SS+00>"}
BASE=${2:?falta carpeta base}
T=${3:?falta instante}
RAIZ=$(pwd -W 2>/dev/null || pwd)

cat > "respaldos/$N/recuperacion.conf" <<EOF
restore_command = 'cp /wal_archive/%f %p'
recovery_target_time = '$T'
recovery_target_action = 'promote'
EOF

docker compose stop "$N"

docker run --rm \
  -v "sigtec_pg_$N:/data" \
  -v "$RAIZ/respaldos/$N:/respaldos" \
  postgis/postgis:16-3.4 bash -c "
    rm -rf /data/* &&
    cp -a /respaldos/$BASE/. /data/ &&
    cat /respaldos/recuperacion.conf >> /data/postgresql.auto.conf &&
    touch /data/recovery.signal &&
    chown -R postgres:postgres /data && chmod 700 /data"

docker compose start "$N"
sleep 5
docker logs "sigtec-$N" --tail 20
