"""Ejecutar desde la consola Python de QGIS; activa el complemento instalado."""
from pathlib import Path
import sys
import qgis.utils
from qgis.core import QgsApplication, QgsSettings

directory = str(Path(QgsApplication.qgisSettingsDirPath()) / "python/plugins")
if directory not in sys.path:
    sys.path.insert(0, directory)
if directory not in qgis.utils.plugin_paths:
    qgis.utils.plugin_paths.insert(0, directory)
qgis.utils.updateAvailablePlugins()
if not qgis.utils.isPluginLoaded("sigtec"):
    if not qgis.utils.loadPlugin("sigtec"):
        raise RuntimeError("QGIS no pudo cargar SIG-TEC.")
    if not qgis.utils.startPlugin("sigtec"):
        raise RuntimeError("QGIS no pudo iniciar SIG-TEC.")
QgsSettings().setValue("PythonPlugins/sigtec", True)
qgis.utils.plugins["sigtec"].run()
print("SIG-TEC activado. Usá las cuentas locales de .local/acceso_qgis.txt.")
