#!/usr/bin/env bash
set -euo pipefail
export MSYS_NO_PATHCONV=1   # evita que Git Bash cambie las rutas

PASS=sigtec2026
CAMPUS=(cartago sanjose sancarlos alajuela limon)
declare -A ESQ=( [cartago]=cartago [sanjose]=san_jose [sancarlos]=san_carlos [alajuela]=alajuela [limon]=limon )

sql() { docker exec -i "sigtec-$1" psql -U postgres -d sigtec -v ON_ERROR_STOP=1 -q -c "$2"; }
conn() { echo "host=$1 port=5432 dbname=sigtec user=postgres password=$PASS"; }

echo "== Nivel 1: cada campus publica su esquema y el central se suscribe"
for c in "${CAMPUS[@]}"; do
  e=${ESQ[$c]}
  sql "$c" "CREATE PUBLICATION pub_$e FOR TABLES IN SCHEMA $e;"
  sql central "CREATE SUBSCRIPTION sub_desde_$e CONNECTION '$(conn "$c")' PUBLICATION pub_$e;"
  echo "   $c -> central listo"
done

echo "== Nivel 2: el central publica a cada campus los otros cuatro esquemas"
for c in "${CAMPUS[@]}"; do
  e=${ESQ[$c]}
  otros=""
  for o in "${CAMPUS[@]}"; do
    if [[ "$o" != "$c" ]]; then otros+="${ESQ[$o]},"; fi
  done
  otros=${otros%,}
  sql central "CREATE PUBLICATION pub_global_para_$e FOR TABLES IN SCHEMA $otros;"
  sql "$c" "CREATE SUBSCRIPTION sub_global_$e CONNECTION '$(conn central)' PUBLICATION pub_global_para_$e;"
  echo "   central -> $c listo ($otros)"
done

echo "== Listo. Revisar con scripts/conteos.sh"
