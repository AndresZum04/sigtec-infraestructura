#!/usr/bin/env bash
set -euo pipefail
export MSYS_NO_PATHCONV=1
TABLA=${1:-edificios}
for n in central cartago sanjose sancarlos alajuela limon; do
  printf '%-10s ' "$n"
  docker exec -i "sigtec-$n" psql -U postgres -d sigtec -At -c "
    SELECT string_agg(format('%s=%s', esquema, n), '  ' ORDER BY campus_id)
    FROM (
      SELECT c.campus_id, c.esquema,
             (xpath('/row/n/text()', query_to_xml(
                format('SELECT count(*) AS n FROM %I.%I', c.esquema, '$TABLA'),
                false, true, '')))[1]::text::int AS n
      FROM public.campus c
    ) x;"
done
