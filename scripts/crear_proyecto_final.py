"""Genera un proyecto con vistas, usuario de campus y datos reales de referencia.

No guarda contraseñas en el proyecto. Al reabrir, ingresar con el complemento.
"""
import json
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "complemento"))
from sigtec.backend import authenticate
from sigtec.layers import create_layers, install_layers, ensure_attribution
from sigtec.settings import defaults
from qgis.PyQt.QtCore import QSize, QRect
from qgis.PyQt.QtGui import QColor, QFont, QPainter
from qgis.PyQt.QtSvg import QSvgGenerator
from qgis.core import QgsApplication, QgsMapRendererParallelJob, QgsMapRendererCustomPainterJob, QgsMapSettings, QgsProject, QgsRectangle, QgsReferencedRectangle


def decorate(painter):
    painter.fillRect(0, 0, 1600, 90, QColor("#123449"))
    painter.setPen(QColor("#ffffff"))
    painter.setFont(QFont("Arial", 23, QFont.Bold))
    painter.drawText(35, 40, "SIG-TEC / SAN CARLOS")
    painter.setFont(QFont("Arial", 12))
    painter.drawText(35, 69, "Capas institucionales · EPSG:5367 · Referencia comunitaria")
    painter.fillRect(0, 1095, 1600, 55, QColor("#ffffff"))
    painter.setPen(QColor("#243e47"))
    painter.setFont(QFont("Arial", 11))
    painter.drawText(25, 1117, "© OpenStreetMap contributors · ODbL · openstreetmap.org/copyright")
    painter.drawText(25, 1138, "Datos de referencia. No es un inventario oficial ni una verificación de accesibilidad.")


def main():
    password = json.loads((ROOT / ".local/cuentas_demo.json").read_text())["kay"]
    session = authenticate(defaults(), "kay", password)
    layers = create_layers(session, password, defaults())
    project = QgsProject.instance()
    install_layers(layers, session, project)
    project.setTitle("SIG-TEC · San Carlos")
    project.setBackgroundColor(QColor("#f3f5ee"))
    ensure_attribution(project)
    extent = QgsRectangle()
    for layer in layers:
        if not layer.extent().isEmpty():
            if extent.isNull():
                extent = QgsRectangle(layer.extent())
            else:
                extent.combineExtentWith(layer.extent())
    extent.grow(60)
    project.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(extent, project.crs()))
    output = ROOT / "qgis/SIGTEC_San_Carlos.qgz"
    project.setFileName(str(output))
    if output.exists():
        backup = ROOT / ".local/SIGTEC_San_Carlos_previo.qgz"
        if not backup.exists():
            shutil.copy2(output, backup)
    if not project.write(str(output)):
        raise RuntimeError("No se pudo guardar el proyecto final.")
    with zipfile.ZipFile(output) as archive:
        name = next(name for name in archive.namelist() if name.endswith(".qgs"))
        (ROOT / "qgis/SIGTEC_San_Carlos.qgs").write_bytes(archive.read(name))

    settings = QgsMapSettings()
    settings.setDestinationCrs(project.crs())
    settings.setLayers(layers)
    settings.setExtent(extent)
    settings.setOutputSize(QSize(1600, 1150))
    settings.setBackgroundColor(QColor("#f3f5ee"))
    job = QgsMapRendererParallelJob(settings)
    job.start()
    job.waitForFinished()
    image = job.renderedImage()
    painter = QPainter(image)
    decorate(painter)
    painter.end()
    if not image.save(str(ROOT / "docs/mapa_san_carlos.png")):
        raise RuntimeError("No se pudo exportar la vista de referencia.")
    generator = QSvgGenerator()
    generator.setFileName(str(ROOT / "docs/mapa_san_carlos.svg"))
    generator.setSize(QSize(1600, 1150))
    generator.setViewBox(QRect(0, 0, 1600, 1150))
    generator.setResolution(96)
    generator.setTitle("SIG-TEC · San Carlos")
    generator.setDescription("Referencia geográfica: © OpenStreetMap contributors · ODbL. EPSG:5367.")
    painter = QPainter(generator)
    renderer = QgsMapRendererCustomPainterJob(settings, painter)
    renderer.renderSynchronously()
    decorate(painter)
    painter.end()
    print("Proyecto con ocho vistas guardado sin contraseñas.")
    print("Vista de referencia: docs/mapa_san_carlos.png")
    print("Fuentes versionables: qgis/SIGTEC_San_Carlos.qgs y docs/mapa_san_carlos.svg")
    project.clear()


if __name__ == "__main__":
    app = QgsApplication([], False)
    app.initQgis()
    try:
        main()
    finally:
        app.exitQgis()
