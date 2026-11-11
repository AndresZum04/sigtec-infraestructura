#!/usr/bin/env bash
set -e
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<EOSQL
CREATE TABLE IF NOT EXISTS public.nodo_local (
  unico     boolean PRIMARY KEY DEFAULT true CHECK (unico),
  campus_id smallint REFERENCES public.campus(campus_id),
  rol       text NOT NULL CHECK (rol IN ('central','campus'))
);

INSERT INTO public.nodo_local (campus_id, rol)
VALUES (NULLIF('${CAMPUS_ID}', '0')::smallint, '${ROL_NODO}')
ON CONFLICT (unico) DO NOTHING;

CREATE OR REPLACE FUNCTION public.campus_local() RETURNS smallint
LANGUAGE sql STABLE AS 'SELECT campus_id FROM public.nodo_local';
EOSQL
