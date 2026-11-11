-- Al montar ./init sobre /docker-entrypoint-initdb.d se tapa el 10_postgis.sh
-- que trae la imagen, así que la extensión se crea aquí.
CREATE EXTENSION IF NOT EXISTS postgis;

-- Catálogo de campus (igual en todos los nodos, no se replica)
CREATE TABLE IF NOT EXISTS public.campus (
  campus_id smallint PRIMARY KEY,
  esquema   text NOT NULL UNIQUE,
  nombre    text NOT NULL
);

INSERT INTO public.campus (campus_id, esquema, nombre) VALUES
  (1, 'cartago',    'Campus Tecnológico Central Cartago'),
  (2, 'san_jose',   'Campus Tecnológico Local San José'),
  (3, 'san_carlos', 'Campus Tecnológico Local San Carlos'),
  (4, 'alajuela',   'Campus Tecnológico Local Alajuela'),
  (5, 'limon',      'Campus Tecnológico Local Limón')
ON CONFLICT DO NOTHING;

-- Crea el esquema de un campus con sus 8 capas
CREATE OR REPLACE FUNCTION public.crear_capas(p_esquema text, p_campus smallint)
RETURNS void
LANGUAGE plpgsql
AS $f$
DECLARE
  s    text   := quote_ident(p_esquema);
  ini  bigint := p_campus * 1000000::bigint + 1;
  fin  bigint := p_campus * 1000000::bigint + 999999;
  base text;
  t    text;
BEGIN
  EXECUTE format('CREATE SCHEMA IF NOT EXISTS %s', s);
  EXECUTE format(
    'CREATE SEQUENCE IF NOT EXISTS %s.seq_id_global MINVALUE %s MAXVALUE %s START WITH %s',
    s, ini, fin, ini);

  -- columnas que llevan todas las capas
  base := format(
    'id bigint PRIMARY KEY DEFAULT nextval(%L) CHECK (id BETWEEN %s AND %s),
     campus_id smallint NOT NULL DEFAULT %s CHECK (campus_id = %s),
     creado_en timestamptz NOT NULL DEFAULT now(),
     modificado_en timestamptz NOT NULL DEFAULT now()',
    p_esquema || '.seq_id_global', ini, fin, p_campus, p_campus);

  EXECUTE format('CREATE TABLE IF NOT EXISTS %s.edificios (%s,
      codigo varchar(20),
      nombre varchar(120) NOT NULL,
      area_m2 numeric(12,2),
      pisos smallint CHECK (pisos > 0),
      geom geometry(Polygon, 5367) NOT NULL)', s, base);

  EXECUTE format('CREATE TABLE IF NOT EXISTS %s.carreteras (%s,
      nombre varchar(120),
      tipo varchar(40),
      superficie varchar(40),
      geom geometry(LineString, 5367) NOT NULL)', s, base);

  EXECUTE format('CREATE TABLE IF NOT EXISTS %s.aceras (%s,
      material varchar(40),
      ancho_m numeric(5,2),
      condicion varchar(20),
      geom geometry(LineString, 5367) NOT NULL)', s, base);

  EXECUTE format('CREATE TABLE IF NOT EXISTS %s.parqueos (%s,
      nombre varchar(120),
      capacidad integer CHECK (capacidad >= 0),
      tipo varchar(40),
      espacios_disponibles integer CHECK (espacios_disponibles >= 0),
      geom geometry(Polygon, 5367) NOT NULL)', s, base);

  EXECUTE format('CREATE TABLE IF NOT EXISTS %s.zonas_verdes (%s,
      nombre varchar(120),
      area_m2 numeric(12,2),
      tipo_vegetacion varchar(60),
      geom geometry(Polygon, 5367) NOT NULL)', s, base);

  EXECUTE format('CREATE TABLE IF NOT EXISTS %s.puntos_interes (%s,
      nombre varchar(120) NOT NULL,
      tipo varchar(40),
      descripcion text,
      geom geometry(Point, 5367) NOT NULL)', s, base);

  EXECUTE format('CREATE TABLE IF NOT EXISTS %s.iluminacion (%s,
      codigo varchar(20),
      potencia_w integer,
      estado varchar(20),
      geom geometry(Point, 5367) NOT NULL)', s, base);

  EXECUTE format('CREATE TABLE IF NOT EXISTS %s.accesibilidad (%s,
      tipo varchar(40),
      descripcion text,
      geom geometry(LineString, 5367) NOT NULL)', s, base);

  FOREACH t IN ARRAY ARRAY['edificios','carreteras','aceras','parqueos',
                           'zonas_verdes','puntos_interes','iluminacion','accesibilidad']
  LOOP
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %s.%I USING gist (geom)',
                   t || '_geom_gix', s, t);
  END LOOP;
END;
$f$;

-- Los 5 esquemas existen en todos los nodos
SELECT public.crear_capas(esquema, campus_id) FROM public.campus ORDER BY campus_id;
