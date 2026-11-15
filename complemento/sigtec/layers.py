"""Carga atómica de las ocho vistas y aplicación de estilos compartidos."""
from pathlib import Path

from qgis.PyQt.QtXml import QDomDocument
from qgis.PyQt.QtCore import QPointF, QSizeF
from qgis.PyQt.QtGui import QTextDocument
from qgis.core import (
    QgsCoordinateReferenceSystem, QgsCredentials, QgsDataSourceUri,
    QgsExpressionContextUtils, QgsProject, QgsRasterLayer, QgsTextAnnotation, QgsVectorLayer,
)

from .backend import AccessError
from .cartography import LABELS, ORDER, configure_forms, institutional_style, validate_required_fields


def managed_layers(project=None):
    project = project or QgsProject.instance()
    return [layer for layer in project.mapLayers().values() if layer.customProperty("sigtec/managed", False)]


def pending_edits(project=None):
    return [layer.name() for layer in managed_layers(project) if isinstance(layer, QgsVectorLayer) and layer.isModified()]


def create_layers(session, password, config):
    result = []
    credentials = QgsDataSourceUri()
    endpoint = session.endpoint
    credentials.setConnection(endpoint["host"], str(endpoint["port"]), endpoint["database"], session.username, "")
    ssl_modes = {"disable": QgsDataSourceUri.SslDisable, "allow": QgsDataSourceUri.SslAllow,
                 "prefer": QgsDataSourceUri.SslPrefer, "require": QgsDataSourceUri.SslRequire,
                 "verify-ca": QgsDataSourceUri.SslVerifyCa, "verify-full": QgsDataSourceUri.SslVerifyFull}
    credentials.setSslMode(ssl_modes[endpoint.get("sslmode", "prefer")])
    credentials.setParam("connect_timeout", str(config["timeout"]))
    QgsCredentials.instance().put(credentials.connectionInfo(), session.username, password)
    for theme in ORDER:
        uri = QgsDataSourceUri(credentials.uri(False))
        uri.setDataSource(config["view_schema"], config["views"][theme], config["geometry_column"], "", config["key_column"])
        layer = QgsVectorLayer(uri.uri(False), LABELS[theme], "postgres")
        if not layer.isValid():
            raise AccessError(f"No se pudo cargar la vista {config['views'][theme]}. No se agregó ninguna capa.")
        source = "archivo local"
        qml = session.styles.get(config["views"][theme])
        if qml:
            document = QDomDocument()
            parsed = document.setContent(qml)
            if not parsed[0]:
                raise AccessError(f"El estilo compartido de {LABELS[theme]} no es un XML válido.")
            ok, message = layer.importNamedStyle(document)
            if not ok:
                raise AccessError(f"No se pudo aplicar el estilo de {LABELS[theme]}: {message}")
            source = "base de datos"
        else:
            local_style = Path(__file__).parent / "styles" / f"{theme}.qml"
            if local_style.exists():
                message, ok = layer.loadNamedStyle(str(local_style))
                if not ok:
                    raise AccessError(f"No se pudo cargar el estilo local de {LABELS[theme]}: {message}")
            else:
                institutional_style(layer, theme)
        configure_forms(layer, session.campus_id)
        validate_required_fields(layer, theme)
        for key, value in {"managed": True, "theme": theme, "campus_id": session.campus_id, "username": session.username, "style_source": source}.items():
            layer.setCustomProperty(f"sigtec/{key}", value)
        result.append(layer)
    return result


def install_layers(layers, session, project=None):
    project = project or QgsProject.instance()
    if pending_edits(project):
        raise AccessError("Guardá o descartá las ediciones pendientes antes de cambiar de sesión.")
    remove_layers(project)
    group = project.layerTreeRoot().insertGroup(0, f"SIG-TEC · {session.campus_name}")
    group.setCustomProperty("sigtec/group", True)
    project.setCrs(QgsCoordinateReferenceSystem("EPSG:5367"))
    QgsExpressionContextUtils.setProjectVariable(project, "sigtec_campus_id", session.campus_id)
    for layer in layers:
        project.addMapLayer(layer, False)
        group.addLayer(layer)
    ensure_attribution(project)
    return group


def remove_layers(project=None):
    project = project or QgsProject.instance()
    if pending_edits(project):
        raise AccessError("Hay ediciones sin guardar. Guardalas o descartalas antes de cerrar la sesión.")
    project.removeMapLayers([layer.id() for layer in managed_layers(project)])
    root = project.layerTreeRoot()
    for group in list(root.children()):
        if group.customProperty("sigtec/group", False):
            if group.children():
                # El usuario puede haber agregado sus propias capas al grupo.
                group.setCustomProperty("sigtec/group", False)
                group.setName("Capas conservadas")
            else:
                root.removeChildNode(group)


def add_basemap(project=None):
    project = project or QgsProject.instance()
    for layer in project.mapLayers().values():
        if layer.customProperty("sigtec/basemap", False):
            return layer
    layer = QgsRasterLayer("type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png&zmin=0&zmax=19", "Referencia · © OpenStreetMap contributors", "wms")
    if not layer.isValid():
        raise AccessError("No se pudo crear el mapa de referencia.")
    layer.setCustomProperty("sigtec/basemap", True)
    layer.setAttribution("© OpenStreetMap contributors · ODbL")
    layer.setAttributionUrl("https://www.openstreetmap.org/copyright")
    project.addMapLayer(layer, False)
    project.layerTreeRoot().addLayer(layer)
    ensure_attribution(project)
    return layer


def ensure_attribution(project=None):
    project = project or QgsProject.instance()
    credit = "© OpenStreetMap contributors · ODbL"
    for annotation in project.annotationManager().annotations():
        if isinstance(annotation, QgsTextAnnotation) and credit in annotation.document().toPlainText():
            return
    annotation = QgsTextAnnotation()
    document = QTextDocument()
    document.setHtml('<div style="font-size:9pt;color:#243e47;background:white">© OpenStreetMap contributors · ODbL<br/>openstreetmap.org/copyright</div>')
    annotation.setDocument(document)
    annotation.setHasFixedMapPosition(False)
    annotation.setRelativePosition(QPointF(0.01, 0.88))
    annotation.setFrameSizeMm(QSizeF(86, 11))
    project.annotationManager().addAnnotation(annotation)
