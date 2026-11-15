"""Prueba real de edición PyQGIS y propagación a los seis nodos.

Solo crea y elimina un edificio sintético identificado con un UUID.
Ejecutar con el Python incluido en QGIS y la infraestructura iniciada.
"""

import json
import subprocess
import time
import uuid

from qgis.core import (
    QgsApplication,
    QgsDataSourceUri,
    QgsGeometry,
    QgsVectorLayer,
    QgsVectorLayerUtils,
)

NODES = ("sancarlos", "central", "cartago", "sanjose", "alajuela", "limon")


def sql(node, query):
    return subprocess.run(
        ["docker", "exec", "-i", f"sigtec-{node}", "psql", "-U", "postgres", "-d", "sigtec", "-At", "-v", "ON_ERROR_STOP=1", "-c", query],
        check=True, capture_output=True, text=True, timeout=15,
    ).stdout.strip()


def esperar(query, expected):
    deadline = time.monotonic() + 45
    pending = set(NODES)
    while pending:
        for node in tuple(pending):
            if sql(node, query) == expected:
                pending.remove(node)
        if not pending:
            return
        if time.monotonic() >= deadline:
            raise AssertionError(f"Cambios pendientes de replicar en {sorted(pending)}")
        time.sleep(0.4)


def verificar():
    uri = QgsDataSourceUri()
    uri.setConnection("localhost", "5443", "sigtec", "postgres", "sigtec2026")
    uri.setDataSource("san_carlos", "edificios", "geom", "", "id")
    layer = QgsVectorLayer(uri.uri(False), "Prueba temporal", "postgres")
    if not layer.isValid():
        raise RuntimeError("No se pudo abrir la capa edificios.")
    name = "__PRUEBA_QGIS_" + uuid.uuid4().hex
    # Coordenadas sintéticas; el objeto se elimina al terminar.
    geometry = QgsGeometry.fromWkt(
        "POLYGON((480000 1145000,480020 1145000,480020 1145020,480000 1145020,480000 1145000))"
    )
    feature = QgsVectorLayerUtils.createFeature(
        layer, geometry, {layer.fields().indexFromName("nombre"): name}
    )
    object_id = None
    try:
        if not layer.startEditing() or not layer.addFeature(feature):
            raise RuntimeError("No se pudo insertar la entidad en el búfer de edición.")
        if not layer.commitChanges():
            raise RuntimeError(f"Falló INSERT: {layer.commitErrors()}")
        object_id = int(sql("sancarlos", f"SELECT id FROM san_carlos.edificios WHERE nombre = '{name}';"))
        esperar(f"SELECT nombre FROM san_carlos.edificios WHERE id = {object_id};", name)

        generated = json.loads(sql("sancarlos", f"SELECT json_build_object('id',id,'campus_id',campus_id,'srid',ST_SRID(geom)) FROM san_carlos.edificios WHERE id = {object_id};"))
        if generated["campus_id"] != 3 or generated["srid"] != 5367 or not 3000001 <= generated["id"] <= 3999999:
            raise AssertionError(f"Valores generados incorrectos: {generated}")
        print(f"INSERT PyQGIS + replicación 6/6: {generated}")

        saved = next(layer.getFeatures(f'"id" = {object_id}'))
        updated = name + "_EDITADO"
        if not layer.startEditing() or not layer.changeAttributeValue(saved.id(), layer.fields().indexFromName("nombre"), updated):
            raise RuntimeError("No se pudo modificar el atributo.")
        if not layer.commitChanges():
            raise RuntimeError(f"Falló UPDATE: {layer.commitErrors()}")
        esperar(f"SELECT nombre FROM san_carlos.edificios WHERE id = {object_id};", updated)
        print("UPDATE PyQGIS + replicación 6/6: OK")

        if not layer.startEditing() or not layer.deleteFeature(saved.id()):
            raise RuntimeError("No se pudo eliminar la entidad de prueba.")
        if not layer.commitChanges():
            raise RuntimeError(f"Falló DELETE: {layer.commitErrors()}")
        esperar(f"SELECT count(*) FROM san_carlos.edificios WHERE id = {object_id};", "0")
        print("DELETE PyQGIS + replicación 6/6: OK; sin objetos de prueba restantes")
    finally:
        if layer.isEditable():
            layer.rollBack()
        # Se limpia por UUID incluso si el proveedor no devolvió el id.
        sql("sancarlos", f"DELETE FROM san_carlos.edificios WHERE nombre IN ('{name}', '{name}_EDITADO');")


if __name__ == "__main__":
    app = QgsApplication([], False)
    app.initQgis()
    try:
        verificar()
    finally:
        app.exitQgis()
