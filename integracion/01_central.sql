-- Contrato de integración de Kay. Acordar este contrato con Brady.
-- Autenticación real de PostgreSQL: no se guardan contraseñas en esta tabla.
BEGIN;
CREATE SCHEMA IF NOT EXISTS sigtec_auth;
REVOKE ALL ON SCHEMA sigtec_auth FROM PUBLIC;
CREATE TABLE IF NOT EXISTS sigtec_auth.usuarios (
    usuario name PRIMARY KEY,
    campus_id smallint NOT NULL REFERENCES public.campus,
    activo boolean NOT NULL DEFAULT true
);
REVOKE ALL ON sigtec_auth.usuarios FROM PUBLIC;

CREATE OR REPLACE FUNCTION sigtec_auth.perfil_actual()
RETURNS TABLE(campus_id smallint, nombre text, esquema text)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
    SELECT c.campus_id, c.nombre, c.esquema
    FROM sigtec_auth.usuarios u
    JOIN public.campus c USING (campus_id)
    WHERE u.usuario = session_user AND u.activo
$$;
REVOKE ALL ON FUNCTION sigtec_auth.perfil_actual() FROM PUBLIC;
COMMENT ON FUNCTION sigtec_auth.perfil_actual() IS
    'Contrato QGIS v1: campus del usuario autenticado por PostgreSQL central; solo lectura.';
COMMIT;
