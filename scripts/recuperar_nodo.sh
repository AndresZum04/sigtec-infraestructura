#!/usr/bin/env bash
set -euo pipefail
export MSYS_NO_PATHCONV=1
N=${1:?uso: recuperar_nodo.sh <nodo>}
PASS=sigtec2026
declare -A ESQ=( [cartago]=cartago [sanjose]=san_jose [sancarlos]=san_carlos [alajuela]=alajuela [limon]=limon )
E=${ESQ[$N]}

sql() { docker exec -i "sigtec-$1" psql -U postgres -d sigtec -v ON_ERROR_STOP=1 -q -c "$2"; }

echo "== Esperando que $N acepte conexiones"
until docker exec "sigtec-$N" pg_isready -U postgres -d sigtec >/dev/null 2>&1; do sleep 2; done
sleep 3

echo "== Apartar el WAL archivado del nodo anterior"
# El nodo nuevo vuelve a numerar su WAL desde 000000010000000000000001 y chocaría con
# los archivos viejos (el archive_command no sobrescribe), así que no podría archivar nada.
# Solo se aparta si el nodo nuevo todavía no ha archivado ningún segmento propio.
archivados=$(docker exec "sigtec-$N" psql -U postgres -d sigtec -At -c "SELECT archived_count FROM pg_stat_archiver;")
if [[ "$archivados" == "0" && -n "$(ls -A "wal/$N" 2>/dev/null)" ]]; then
  VIEJO="wal/${N}_anterior_$(date +%Y%m%d_%H%M%S)"
  mkdir -p "$VIEJO"
  mv "wal/$N"/* "$VIEJO"/
  echo "   WAL viejo movido a $VIEJO"
fi

echo "== Copiar los datos propios de $N desde el central"
docker exec -u postgres sigtec-central pg_dump -d sigtec -a -n "$E" \
  | docker exec -i "sigtec-$N" psql -U postgres -d sigtec -v ON_ERROR_STOP=1 -q

echo "== Ajustar la secuencia para no repetir ids"
docker exec -i "sigtec-$N" psql -U postgres -d sigtec -v ON_ERROR_STOP=1 -q <<EOSQL
DO \$\$
DECLARE r record; m bigint := 0; x bigint;
BEGIN
  FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = '$E' LOOP
    EXECUTE format('SELECT max(id) FROM %I.%I', '$E', r.tablename) INTO x;
    m := greatest(m, coalesce(x, 0));
  END LOOP;
  IF m > 0 THEN
    PERFORM setval('$E.seq_id_global', m);
  END IF;
END \$\$;
EOSQL

echo "== Volver a publicar y rehacer la suscripción en el central (sin recopiar)"
sql "$N" "CREATE PUBLICATION pub_$E FOR TABLES IN SCHEMA $E;"
sql central "ALTER SUBSCRIPTION sub_desde_$E DISABLE;"
sql central "ALTER SUBSCRIPTION sub_desde_$E SET (slot_name = NONE);"
sql central "DROP SUBSCRIPTION sub_desde_$E;"
sql central "CREATE SUBSCRIPTION sub_desde_$E CONNECTION 'host=$N port=5432 dbname=sigtec user=postgres password=$PASS' PUBLICATION pub_$E WITH (copy_data = false);"

echo "== Recibir otra vez los datos globales"
sql central "SELECT pg_drop_replication_slot('sub_global_$E') FROM pg_replication_slots WHERE slot_name = 'sub_global_$E';"
sql "$N" "CREATE SUBSCRIPTION sub_global_$E CONNECTION 'host=central port=5432 dbname=sigtec user=postgres password=$PASS' PUBLICATION pub_global_para_$E;"

sleep 10
bash scripts/conteos.sh edificios
