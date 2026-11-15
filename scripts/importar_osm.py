"""Carga datos públicos OSM de San Carlos, sin inventar atributos desconocidos.

La fuente descargada se conserva en datos/fuentes. Repetir el script no duplica
objetos ni reemplaza las ediciones del usuario. Es una base de trabajo, no un
inventario oficial o verificado en campo.
"""
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import psycopg2
from psycopg2 import sql
from qgis.core import QgsApplication, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsGeometry, QgsPointXY, QgsProject

ROOT = Path(__file__).resolve().parents[1]


def shape(element, polygon=False):
    if element["type"] == "node":
        return None if polygon else QgsGeometry.fromPointXY(QgsPointXY(element["lon"], element["lat"]))
    coordinates = element.get("geometry", [])
    if element["type"] != "way" or len(coordinates) < 2:
        return None
    points = [QgsPointXY(item["lon"], item["lat"]) for item in coordinates]
    if polygon:
        if len(points) < 4 or points[0] != points[-1]:
            return None
        return QgsGeometry.fromPolygonXY([points])
    return QgsGeometry.fromPolylineXY(points)


def classify(element):
    tags = element.get("tags", {})
    identity = f"{element['type']}/{element['id']}"
    description = f"Fuente: OpenStreetMap {identity}. Datos comunitarios; verificar en campo."
    if tags.get("building") not in (None, "no"):
        polygon = shape(element, True)
        if polygon:
            levels = tags.get("building:levels", "")
            yield "edificios", polygon, {"codigo": f"OSM{element['id']}", "nombre": tags.get("name", f"Edificio OSM {element['id']}"), "pisos": int(levels) if levels.isdigit() and int(levels)>0 else None}
    highway = tags.get("highway")
    if highway in ("unclassified", "residential", "service", "track", "tertiary", "secondary", "primary", "living_street"):
        yield "carreteras", shape(element), {"nombre": tags.get("name"), "tipo": highway, "superficie": tags.get("surface")}
    if highway in ("footway", "pedestrian", "path", "steps", "corridor"):
        width = tags.get("width", "")
        try:
            width = float(width)
            width = width if width > 0 else None
        except ValueError:
            width = None
        yield "aceras", shape(element), {"material": tags.get("surface"), "ancho_m": width, "condicion": None}
    if tags.get("amenity") in ("parking", "motorcycle_parking"):
        polygon = shape(element, True)
        if polygon:
            capacity = tags.get("capacity", "")
            yield "parqueos", polygon, {"nombre": tags.get("name"), "capacidad": int(capacity) if capacity.isdigit() else None, "tipo": tags.get("parking", tags["amenity"]), "espacios_disponibles": None}
    green = tags.get("natural") in ("wood", "scrub", "grassland") or tags.get("landuse") in ("grass", "meadow", "forest") or tags.get("leisure") in ("park", "garden")
    if green:
        yield "zonas_verdes", shape(element, True), {"nombre": tags.get("name"), "tipo_vegetacion": tags.get("natural", tags.get("landuse", tags.get("leisure")))}
    if tags.get("amenity") and tags["amenity"] not in ("university", "parking", "motorcycle_parking"):
        geometry = shape(element, element["type"] == "way")
        if geometry:
            if element["type"] != "node":
                geometry = geometry.pointOnSurface()
                description += " Posición representativa calculada a partir del polígono."
            yield "puntos_interes", geometry, {"nombre": tags.get("name", f"{tags['amenity']} OSM {element['id']}"), "tipo": tags["amenity"], "descripcion": description}
    if highway == "street_lamp":
        yield "iluminacion", shape(element), {"codigo": f"OSM{element['id']}", "potencia_w": None, "estado": None}
    if highway and (tags.get("wheelchair") in ("yes", "designated") or tags.get("ramp") == "yes"):
        yield "accesibilidad", shape(element), {"tipo": "rampa" if tags.get("ramp") == "yes" else "ruta accesible OSM", "descripcion": description}


def main():
    source = ROOT / "datos/fuentes/osm_objetos_san_carlos.json"
    raw = source.read_bytes()
    data = json.loads(raw)
    campus_data = json.loads((ROOT / "datos/fuentes/osm_campus_san_carlos.json").read_text())
    campus = shape(campus_data["elements"][0], True)
    credentials = json.loads((ROOT / ".local/cuentas_demo.json").read_text())
    # La procedencia se guarda fuera de los esquemas que replica Andrés.
    with closing(psycopg2.connect(host="localhost", port=5443, dbname="sigtec", user="postgres", password="sigtec2026")) as admin:
        with admin, admin.cursor() as cursor:
            cursor.execute('''CREATE SCHEMA IF NOT EXISTS sigtec_importacion;
                CREATE TABLE IF NOT EXISTS sigtec_importacion.origen (
                    capa text NOT NULL, osm_tipo text NOT NULL, osm_id bigint NOT NULL,
                    objeto_id bigint NOT NULL, version_osm integer, fecha_osm timestamptz,
                    importado_en timestamptz NOT NULL DEFAULT now(),
                    PRIMARY KEY(capa,osm_tipo,osm_id));
                GRANT USAGE ON SCHEMA sigtec_importacion TO kay;
                GRANT SELECT,INSERT ON sigtec_importacion.origen TO kay;''')
    transform = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:4326"), QgsCoordinateReferenceSystem("EPSG:5367"), QgsProject.instance())
    added, skipped = Counter(), Counter()
    manifest = []
    with closing(psycopg2.connect(host="localhost", port=5443, dbname="sigtec", user="kay", password=credentials["kay"])) as connection:
        with connection, connection.cursor() as cursor:
            for element in data["elements"]:
                for theme, geometry, attributes in classify(element):
                    if geometry is None or geometry.isEmpty() or not geometry.isGeosValid() or not geometry.intersects(campus):
                        skipped["geometría no compatible o fuera del campus"] += 1
                        continue
                    key = (theme, element["type"], element["id"])
                    cursor.execute("SELECT objeto_id FROM sigtec_importacion.origen WHERE capa=%s AND osm_tipo=%s AND osm_id=%s", key)
                    previous = cursor.fetchone()
                    if previous:
                        manifest.append({"capa": theme, "osm": f"{element['type']}/{element['id']}", "id": previous[0]})
                        skipped["ya importado"] += 1
                        continue
                    geometry.transform(transform)
                    fields = list(attributes)
                    query = sql.SQL("INSERT INTO sigtec_qgis.{} ({},geom) VALUES ({},ST_GeomFromWKB(%s,5367)) RETURNING id").format(
                        sql.Identifier(theme), sql.SQL(",").join(map(sql.Identifier, fields)), sql.SQL(",").join(sql.Placeholder() for _ in fields))
                    cursor.execute(query, [*attributes.values(), psycopg2.Binary(bytes(geometry.asWkb()))])
                    object_id = cursor.fetchone()[0]
                    cursor.execute("INSERT INTO sigtec_importacion.origen(capa,osm_tipo,osm_id,objeto_id,version_osm,fecha_osm) VALUES(%s,%s,%s,%s,%s,%s)", (*key, object_id, element.get("version"), element.get("timestamp")))
                    manifest.append({"capa": theme, "osm": f"{element['type']}/{element['id']}", "id": object_id})
                    added[theme] += 1
    report = {"fuente": "© OpenStreetMap contributors", "licencia": "ODbL-1.0", "licencia_url": "https://www.openstreetmap.org/copyright", "campus_osm": "way/351554216", "sha256_fuente": hashlib.sha256(raw).hexdigest(), "fecha_snapshot_osm": data.get("osm3s", {}).get("timestamp_osm_base"), "actualizado_en_utc": datetime.now(timezone.utc).isoformat(), "objetos": manifest, "nota": "Base comunitaria de trabajo, no inventario institucional. No se deducen luminarias, rampas, capacidad, disponibilidad, pisos ni condición cuando la fuente no lo indica."}
    (ROOT / "datos/procedencia_san_carlos.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print("Objetos nuevos:", dict(added))
    print("Omitidos:", dict(skipped))
    print("Procedencia:", ROOT / "datos/procedencia_san_carlos.json")


if __name__ == "__main__":
    app = QgsApplication([], False)
    app.initQgis()
    try:
        main()
    finally:
        app.exitQgis()
