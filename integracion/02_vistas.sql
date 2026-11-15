-- Implementación del contrato SIG-TEC v1.0.0 para el complemento QGIS.
-- PostgreSQL 16. No cambia las tablas ni publicaciones originales de Andrés.
BEGIN;
CREATE SCHEMA IF NOT EXISTS sigtec_qgis;
REVOKE CREATE ON SCHEMA sigtec_qgis FROM PUBLIC;

CREATE OR REPLACE FUNCTION sigtec_qgis.editar_local()
RETURNS trigger LANGUAGE plpgsql
SET search_path = pg_catalog, public, pg_temp
AS $$
DECLARE
    local_id smallint := public.campus_local();
    local_schema text;
    payload jsonb;
    cols text;
    vals text;
    affected bigint;
BEGIN
    IF local_id IS NULL THEN
        RAISE EXCEPTION 'El nodo central es de consulta.' USING ERRCODE = '42501';
    END IF;
    SELECT esquema INTO STRICT local_schema FROM public.campus WHERE campus_id = local_id;
    IF TG_OP IN ('UPDATE', 'DELETE') AND OLD.campus_id IS DISTINCT FROM local_id THEN
        RAISE EXCEPTION 'Solo se pueden editar objetos del campus local (%).', local_id USING ERRCODE = '42501';
    END IF;
    IF TG_OP <> 'DELETE' THEN
        IF NEW.campus_id IS NOT NULL AND NEW.campus_id IS DISTINCT FROM local_id THEN
            RAISE EXCEPTION 'No se pueden crear ni trasladar objetos a otro campus.' USING ERRCODE = '42501';
        END IF;
        IF TG_OP = 'UPDATE' AND (NEW.id IS DISTINCT FROM OLD.id OR NEW.campus_id IS DISTINCT FROM OLD.campus_id) THEN
            RAISE EXCEPTION 'El identificador y el campus no se pueden cambiar.' USING ERRCODE = '42501';
        END IF;
        IF NEW.geom IS NULL OR public.ST_IsEmpty(NEW.geom) OR public.ST_SRID(NEW.geom) <> 5367 OR NOT public.ST_IsValid(NEW.geom) THEN
            RAISE EXCEPTION 'La geometría debe ser válida y usar EPSG:5367.' USING ERRCODE = '23514';
        END IF;
        NEW.campus_id := local_id;
        NEW.modificado_en := clock_timestamp();
        IF TG_OP = 'INSERT' THEN
            NEW.id := coalesce(NEW.id, nextval(format('%I.seq_id_global', local_schema)::regclass));
            NEW.creado_en := clock_timestamp();
        ELSE
            NEW.creado_en := OLD.creado_en;
        END IF;
        payload := to_jsonb(NEW);
        IF TG_TABLE_NAME IN ('edificios', 'zonas_verdes') THEN
            payload := payload || jsonb_build_object('area_m2', round(public.ST_Area(NEW.geom)::numeric, 2));
        END IF;
    END IF;

    IF TG_OP = 'INSERT' THEN
        EXECUTE format('INSERT INTO %I.%I SELECT r.* FROM jsonb_populate_record(NULL::%I.%I, $1) r RETURNING *',
            local_schema, TG_TABLE_NAME, local_schema, TG_TABLE_NAME) INTO NEW USING payload;
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        SELECT string_agg(format('%I', attname), ', ' ORDER BY attnum),
               string_agg(format('r.%I', attname), ', ' ORDER BY attnum)
        INTO cols, vals FROM pg_attribute
        WHERE attrelid = format('%I.%I', local_schema, TG_TABLE_NAME)::regclass
        AND attnum > 0 AND NOT attisdropped AND attname NOT IN ('id', 'campus_id', 'creado_en');
        EXECUTE format('UPDATE %I.%I SET (%s) = (SELECT %s FROM jsonb_populate_record(NULL::%I.%I, $1) r) WHERE id=$2 RETURNING *',
            local_schema, TG_TABLE_NAME, cols, vals, local_schema, TG_TABLE_NAME) INTO NEW USING payload, OLD.id;
        GET DIAGNOSTICS affected = ROW_COUNT;
        IF affected <> 1 THEN
            RAISE EXCEPTION 'El objeto cambió o fue eliminado. Actualizá la capa e intentá otra vez.' USING ERRCODE = '40001';
        END IF;
        RETURN NEW;
    ELSE
        EXECUTE format('DELETE FROM %I.%I WHERE id=$1 RETURNING *', local_schema, TG_TABLE_NAME) INTO OLD USING OLD.id;
        GET DIAGNOSTICS affected = ROW_COUNT;
        IF affected <> 1 THEN
            RAISE EXCEPTION 'El objeto ya no existe. Actualizá la capa.' USING ERRCODE = '40001';
        END IF;
        RETURN OLD;
    END IF;
END;
$$;

DO $$
DECLARE
    theme text;
    geom_type text;
    all_cols text;
    body text;
    c record;
    local_id smallint := public.campus_local();
    local_schema text;
BEGIN
    SELECT esquema INTO local_schema FROM public.campus WHERE campus_id = local_id;
    FOREACH theme IN ARRAY ARRAY['edificios','carreteras','aceras','parqueos','zonas_verdes','puntos_interes','iluminacion','accesibilidad'] LOOP
        geom_type := CASE WHEN theme IN ('edificios','parqueos','zonas_verdes') THEN 'Polygon'
                          WHEN theme IN ('puntos_interes','iluminacion') THEN 'Point' ELSE 'LineString' END;
        SELECT string_agg(format('%I', attname), ', ' ORDER BY attnum) INTO all_cols
        FROM pg_attribute WHERE attrelid=format('cartago.%I',theme)::regclass
            AND attnum>0 AND NOT attisdropped AND attname <> 'geom';
        body := '';
        FOR c IN SELECT esquema FROM public.campus ORDER BY campus_id LOOP
            IF body <> '' THEN body := body || ' UNION ALL '; END IF;
            body := body || format('SELECT %s, geom FROM %I.%I', all_cols, c.esquema, theme);
        END LOOP;
        EXECUTE format('CREATE OR REPLACE VIEW sigtec_qgis.%I WITH (security_invoker=true) AS SELECT %s, geom::public.geometry(%s,5367) AS geom FROM (%s) datos',
            theme, all_cols, geom_type, body);
        EXECUTE format('COMMENT ON VIEW sigtec_qgis.%I IS %L', theme,
            'Vista global de referencia para QGIS. Cada campus escribe solamente sus objetos mediante INSTEAD OF.');
        IF local_id IS NOT NULL THEN
            EXECUTE format('ALTER VIEW sigtec_qgis.%I ALTER COLUMN id SET DEFAULT nextval(%L::regclass)',
                theme, local_schema || '.seq_id_global');
            EXECUTE format('ALTER VIEW sigtec_qgis.%I ALTER COLUMN campus_id SET DEFAULT %s', theme, local_id);
            EXECUTE format('DROP TRIGGER IF EXISTS editar_local ON sigtec_qgis.%I', theme);
            EXECUTE format('CREATE TRIGGER editar_local INSTEAD OF INSERT OR UPDATE OR DELETE ON sigtec_qgis.%I FOR EACH ROW EXECUTE FUNCTION sigtec_qgis.editar_local()', theme);
        END IF;
    END LOOP;
END;
$$;
COMMIT;
