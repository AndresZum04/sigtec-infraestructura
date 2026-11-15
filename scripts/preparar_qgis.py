"""Genera el proyecto inicial y los estilos usando el Python de QGIS."""

from pathlib import Path

from qgis.PyQt.QtGui import QColor

from qgis.core import (
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsDataSourceUri,
    QgsFillSymbol,
    QgsLineSymbol,
    QgsMarkerSymbol,
    QgsProject,
    QgsRectangle,
    QgsVectorLayer,
)

ROOT = Path(__file__).resolve().parents[1]
LAYERS = (
    ("zonas_verdes", "Zonas verdes", "polygon", "#b8d49b"),
    ("parqueos", "Parqueos", "polygon", "#cbd5e1"),
    ("edificios", "Edificios", "polygon", "#db9975"),
    ("carreteras", "Carreteras", "line", "#566477"),
    ("aceras", "Aceras", "line", "#cfb78a"),
    ("accesibilidad", "Accesibilidad", "line", "#007f86"),
    ("puntos_interes", "Puntos de interés", "point", "#3169a8"),
    ("iluminacion", "Iluminación", "point", "#edc348"),
)


def crear_proyecto():
    output = ROOT / "qgis"
    destination = output / "SIGTEC_San_Carlos.qgz"
    if destination.exists():
        raise FileExistsError(f"El proyecto ya existe; no se sobrescribe: {destination}")
    project = QgsProject()
    project.setTitle("SIG-TEC · San Carlos · Preparación")
    project.setCrs(QgsCoordinateReferenceSystem("EPSG:5367"))
    project.setBackgroundColor(QColor("#f4f5f0"))
    group = project.layerTreeRoot().addGroup("San Carlos · tablas de trabajo")
    styles = output / "estilos"
    styles.mkdir(parents=True, exist_ok=True)

    for table, label, kind, color in LAYERS:
        uri = QgsDataSourceUri()
        uri.setConnection("localhost", "5443", "sigtec", "postgres", "sigtec2026")
        uri.setDataSource("san_carlos", table, "geom", "", "id")
        layer = QgsVectorLayer(uri.uri(False), label, "postgres")
        if not layer.isValid():
            raise RuntimeError(f"No se pudo cargar san_carlos.{table}: {layer.error().summary()}")

        if kind == "polygon":
            symbol = QgsFillSymbol.createSimple({"color": color, "outline_color": "#52606b", "outline_width": "0.25"})
        elif kind == "line":
            symbol = QgsLineSymbol.createSimple({"line_color": color, "line_width": "0.7"})
        else:
            symbol = QgsMarkerSymbol.createSimple({"name": "circle", "color": color, "size": "2.6", "outline_color": "#ffffff"})
        layer.renderer().setSymbol(symbol)

        # Estos valores los genera y valida PostgreSQL.
        form = layer.editFormConfig()
        for name in ("id", "campus_id", "creado_en", "modificado_en"):
            index = layer.fields().indexFromName(name)
            if index >= 0:
                form.setReadOnly(index, True)
        layer.setEditFormConfig(form)
        project.addMapLayer(layer, False)
        group.insertLayer(0, layer)
        message, ok = layer.saveNamedStyle(str(styles / f"{table}.qml"))
        if not ok:
            raise RuntimeError(f"No se pudo guardar el estilo de {table}: {message}")

    # Vista regional inicial. No representa límites ni objetos del campus.
    from qgis.core import QgsReferencedRectangle
    project.viewSettings().setDefaultViewExtent(
        QgsReferencedRectangle(QgsRectangle(450000, 1100000, 500000, 1170000), project.crs())
    )
    if not project.write(str(destination)):
        raise RuntimeError("No se pudo guardar el proyecto QGIS.")
    print(f"Proyecto creado: {destination}")
    print(f"Capas válidas: {len(project.mapLayers())}; CRS: {project.crs().authid()}")
    project.clear()


if __name__ == "__main__":
    app = QgsApplication([], False)
    app.initQgis()
    try:
        crear_proyecto()
    finally:
        app.exitQgis()
