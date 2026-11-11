#!/usr/bin/env bash
set -euo pipefail
export MSYS_NO_PATHCONV=1
N=${1:?uso: resincronizar.sh <nodo>}
PASS=sigtec2026
declare -A ESQ=( [cartago]=cartago [sanjose]=san_jose [sancarlos]=san_carlos [alajuela]=alajuela [limon]=limon )
E=${ESQ[$N]}

psqlc() { docker exec -i "sigtec-$1" psql -U postgres -d sigtec -v ON_ERROR_STOP=1 -q; }
sql()   { docker exec -i "sigtec-$1" psql -U postgres -d sigtec -v ON_ERROR_STOP=1 -q -At -c "$2"; }

echo "== Central: vaciar $E y volver a copiarlo desde $N"
psqlc central <<EOSQL
ALTER SUBSCRIPTION sub_desde_$E DISABLE;
ALTER SUBSCRIPTION sub_desde_$E SET (slot_name = NONE);
DROP SUBSCRIPTION sub_desde_$E;
DO \$\$
DECLARE r record;
BEGIN
  FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = '$E' LOOP
    EXECUTE format('TRUNCATE %I.%I', '$E', r.tablename);
  END LOOP;
END \$\$;
EOSQL
sql central "CREATE SUBSCRIPTION sub_desde_$E CONNECTION 'host=$N port=5432 dbname=sigtec user=postgres password=$PASS' PUBLICATION pub_$E;"

echo "== $N: quitar la suscripción global vieja"
# Se suelta el slot antes del DROP, así no falla si el slot ya no existe en el central
psqlc "$N" <<EOSQL
ALTER SUBSCRIPTION sub_global_$E DISABLE;
ALTER SUBSCRIPTION sub_global_$E SET (slot_name = NONE);
DROP SUBSCRIPTION sub_global_$E;
EOSQL

# Esperar a que el slot quede libre y borrarlo en el central
for _ in $(seq 1 15); do
  activo=$(sql central "SELECT coalesce(bool_or(active), false) FROM pg_replication_slots WHERE slot_name = 'sub_global_$E';")
  [[ "$activo" == "f" ]] && break
  sleep 1
done
sql central "SELECT pg_drop_replication_slot(slot_name) FROM pg_replication_slots WHERE slot_name = 'sub_global_$E';" >/dev/null

echo "== $N: volver a copiar los datos globales desde el central"
psqlc "$N" <<EOSQL
DO \$\$
DECLARE r record;
BEGIN
  FOR r IN SELECT schemaname, tablename FROM pg_tables
           WHERE schemaname IN (SELECT esquema FROM public.campus WHERE esquema <> '$E') LOOP
    EXECUTE format('TRUNCATE %I.%I', r.schemaname, r.tablename);
  END LOOP;
END \$\$;
EOSQL
sql "$N" "CREATE SUBSCRIPTION sub_global_$E CONNECTION 'host=central port=5432 dbname=sigtec user=postgres password=$PASS' PUBLICATION pub_global_para_$E;"

echo "== Esperando la copia inicial"
sleep 10
bash scripts/conteos.sh edificios
