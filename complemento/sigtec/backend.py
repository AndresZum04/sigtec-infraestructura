"""Autenticación contra PostgreSQL central y comprobación del nodo asignado."""
from dataclasses import dataclass
from contextlib import contextmanager

import psycopg2
from psycopg2 import sql

from .settings import THEMES


class AccessError(Exception):
    """Mensaje seguro para presentar en la interfaz."""


@dataclass(frozen=True)
class Session:
    username: str
    campus_id: int
    campus_name: str
    campus_schema: str
    endpoint: dict
    styles: dict


@contextmanager
def connect(endpoint, username, password, timeout=5):
    connection = psycopg2.connect(
        host=endpoint["host"], port=endpoint["port"], dbname=endpoint["database"],
        user=username, password=password, sslmode=endpoint.get("sslmode", "prefer"),
        connect_timeout=timeout, application_name="SIGTEC-QGIS",
        options="-c statement_timeout=10000 -c lock_timeout=3000",
    )
    try:
        yield connection
    finally:
        connection.close()


def authenticate(config, username, password):
    if not username.strip() or not password:
        raise AccessError("Ingresá el usuario y la contraseña.")
    phase = "central"
    try:
        with connect(config["central"], username, password, config["timeout"]) as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql.SQL("SELECT campus_id, nombre, esquema FROM {}.{}()").format(
                    sql.Identifier(config["auth_schema"]), sql.Identifier(config["auth_function"])
                ))
                rows = cursor.fetchall()
        if len(rows) != 1:
            raise AccessError("Tu usuario no tiene un campus activo asignado.")
        campus_id, name, schema = rows[0]
        endpoint = config["campuses"].get(str(campus_id))
        if endpoint is None:
            raise AccessError("El campus asignado no tiene una conexión configurada.")
        phase = "campus"
        with connect(endpoint, username, password, config["timeout"]) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT public.campus_local()")
                if cursor.fetchone()[0] != campus_id:
                    raise AccessError("La conexión configurada apunta a otro campus. Revisá los puertos.")
                cursor.execute("""SELECT c.relname, c.relkind FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                    WHERE n.nspname=%s AND c.relname = ANY(%s)""", (config["view_schema"], list(config["views"].values())))
                found = {table: kind for table, kind in cursor.fetchall()}
                missing = [table for table in config["views"].values() if found.get(table) != "v"]
                if missing:
                    raise AccessError("Faltan vistas globales: " + ", ".join(missing) + ". Revisá la integración SQL.")
                for theme in THEMES:
                    cursor.execute(sql.SQL("SELECT {}, campus_id, {} FROM {}.{} LIMIT 0").format(
                        sql.Identifier(config["key_column"]), sql.Identifier(config["geometry_column"]),
                        sql.Identifier(config["view_schema"]), sql.Identifier(config["views"][theme]),
                    ))
                    cursor.execute("SELECT public.Find_SRID(%s,%s,%s)", (config["view_schema"], config["views"][theme], config["geometry_column"]))
                    if cursor.fetchone()[0] != 5367:
                        raise AccessError("Las vistas deben declarar sus geometrías en EPSG:5367.")
                cursor.execute("SELECT to_regclass('public.layer_styles') IS NOT NULL")
                styles = {}
                if cursor.fetchone()[0]:
                    cursor.execute("""SELECT f_table_name, styleqml FROM public.layer_styles
                        WHERE f_table_schema=%s AND f_table_catalog=%s AND f_geometry_column=%s
                        AND useasdefault ORDER BY update_time, id""",
                        (config["view_schema"], endpoint["database"], config["geometry_column"]))
                    styles = {table: str(qml) for table, qml in cursor.fetchall()}
        return Session(username, int(campus_id), name, schema, dict(endpoint), styles)
    except AccessError:
        raise
    except psycopg2.Error as error:
        code = error.pgcode
        if code in ("28P01", "28000") or "password authentication failed" in str(error):
            raise AccessError("Usuario o contraseña incorrectos." if phase == "central" else "El central validó tu usuario, pero el nodo rechazó la conexión. Revisá el puerto y los permisos del campus.") from None
        if code in ("42883", "42P01", "3F000"):
            raise AccessError("La base todavía no tiene el contrato SQL de SIG-TEC configurado.") from None
        if code == "42501":
            raise AccessError("Tu usuario no tiene los permisos necesarios. Revisá la configuración de acceso.") from None
        raise AccessError("No se pudo conectar con el central o el nodo del campus. Revisá Docker y la configuración.") from None
