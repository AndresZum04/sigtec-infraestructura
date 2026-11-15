"""Ciclo de vida del complemento SIG-TEC para QGIS 3."""
import copy
from pathlib import Path

from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtGui import QIcon
try:
    from qgis.PyQt.QtGui import QAction
except ImportError:
    from qgis.PyQt.QtWidgets import QAction
from qgis.core import (
    Qgis, QgsApplication, QgsFeatureRequest, QgsMessageLog, QgsProject,
    QgsRectangle, QgsTask,
)

from .backend import AccessError, authenticate
from .dialogs import ConfigurationDialog, LoginDialog
from .layers import add_basemap, create_layers, install_layers, managed_layers, pending_edits, remove_layers
from . import settings


class AuthenticationTask(QgsTask):
    def __init__(self, config, username, password, finished):
        super().__init__("SIG-TEC · Validar acceso", QgsTask.CanCancel)
        self.config = copy.deepcopy(config)
        self.username, self.password = username, password
        self.callback = finished
        self.session = None
        self.error = None

    def run(self):
        try:
            if self.isCanceled():
                return False
            self.session = authenticate(self.config, self.username, self.password)
            return not self.isCanceled()
        except AccessError as error:
            self.error = str(error)
            return False
        except Exception as error:
            self.error = "Ocurrió un error al validar el acceso. Revisá la integración y volvé a intentar."
            QgsMessageLog.logMessage(f"Acceso: {type(error).__name__}", "SIG-TEC", Qgis.Warning)
            return False

    def finished(self, result):
        try:
            self.callback(self.session if result else None, self.password, self.error or ("Ingreso cancelado." if not result else None))
        finally:
            self.password = ""


class SigtecPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.dialog = None
        self.action = None
        self.task = None
        self.session = None
        self._password = ""
        self._unloaded = False
        self.config_path = Path(QgsApplication.qgisSettingsDirPath()) / "sigtec" / "conexiones.json"
        self.config = settings.load(self.config_path)

    def initGui(self):
        self.action = QAction(QIcon(str(Path(__file__).with_name("icon.svg"))), "SIG-TEC · Ingresar", self.iface.mainWindow())
        self.action.setObjectName("sigtecAction")
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&SIG-TEC", self.action)

    def unload(self):
        self._unloaded = True
        if self.task:
            self.task.cancel()
        self._password = ""
        if self.action:
            self.iface.removeToolBarIcon(self.action)
            self.iface.removePluginMenu("&SIG-TEC", self.action)
            self.action.deleteLater()
        if self.dialog:
            self.dialog.close()
            self.dialog.deleteLater()
        # Las capas y las ediciones del usuario permanecen al desactivar el complemento.

    def run(self):
        if self.dialog is None:
            self.dialog = LoginDialog(self.iface.mainWindow())
            self.dialog.username.setText(QSettings().value("sigtec/last_username", ""))
            self.dialog.loginRequested.connect(self.login)
            self.dialog.logoutRequested.connect(self.logout)
            self.dialog.refreshRequested.connect(self.refresh)
            self.dialog.configureRequested.connect(self.configure)
            self.dialog.filterRequested.connect(self.filter_local)
            self.dialog.zoomRequested.connect(self.zoom_local)
            self.dialog.basemapRequested.connect(self.basemap)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

    def login(self, username, password):
        if self.task:
            return
        if pending_edits():
            self.dialog.show_message("Guardá o descartá las ediciones pendientes antes de iniciar otra sesión.", True)
            return
        if not username or not password:
            self.dialog.show_message("Ingresá el usuario y la contraseña.", True)
            return
        self.dialog.set_busy(True)
        self.task = AuthenticationTask(self.config, username, password, self._login_finished)
        QgsApplication.taskManager().addTask(self.task)

    def _login_finished(self, session, password, error):
        self.task = None
        if self._unloaded:
            return
        self.dialog.set_busy(False)
        self.dialog.password.clear()
        if error:
            self.dialog.show_message(error, True)
            return
        try:
            layers = create_layers(session, password, self.config)
            install_layers(layers, session)
        except Exception as error:
            self.dialog.show_message(str(error) if isinstance(error, AccessError) else "No se pudieron cargar las capas. Revisá la configuración.", True)
            QgsMessageLog.logMessage(f"Carga: {type(error).__name__}", "SIG-TEC", Qgis.Warning)
            return
        self.session, self._password = session, password
        self.dialog.set_session(session)
        QSettings().setValue("sigtec/last_username", session.username)
        self.iface.messageBar().pushSuccess("SIG-TEC", f"Conectado a {session.campus_name}. Se cargaron ocho vistas globales.")
        self.zoom_local()

    def logout(self):
        try:
            remove_layers()
        except AccessError as error:
            self.dialog.show_message(str(error), True)
            return
        self.session, self._password = None, ""
        self.dialog.set_session(None)
        self.iface.mapCanvas().refresh()

    def refresh(self):
        if self.session:
            self.login(self.session.username, self._password)

    def configure(self):
        dialog = ConfigurationDialog(self.config, self.dialog)
        if dialog.exec():
            settings.save(self.config_path, dialog.config)
            self.config = dialog.config
            self.dialog.show_message("Conexiones guardadas. Ingresá para probarlas.")

    def filter_local(self, enabled):
        if not self.session:
            return
        if pending_edits():
            self.dialog.only_local.blockSignals(True)
            self.dialog.only_local.setChecked(not enabled)
            self.dialog.only_local.blockSignals(False)
            self.dialog.show_message("Guardá o descartá las ediciones antes de cambiar el filtro.", True)
            return
        layers = managed_layers()
        previous = [(layer, layer.subsetString()) for layer in layers]
        for layer in layers:
            if not layer.setSubsetString(f'"campus_id" = {self.session.campus_id}' if enabled else ""):
                for original, subset in previous:
                    original.setSubsetString(subset)
                self.dialog.only_local.blockSignals(True)
                self.dialog.only_local.setChecked(not enabled)
                self.dialog.only_local.blockSignals(False)
                self.dialog.show_message("No se pudo aplicar el filtro a todas las capas.", True)
                return
        self.iface.mapCanvas().refresh()
        self.dialog.show_message("Mostrando tu campus." if enabled else "Mostrando todos los campus.")

    def zoom_local(self):
        if not self.session:
            return
        extent = QgsRectangle()
        layers = managed_layers()
        for layer in layers:
            request = QgsFeatureRequest().setFilterExpression(f'"campus_id" = {self.session.campus_id}').setSubsetOfAttributes([])
            for feature in layer.getFeatures(request):
                if feature.hasGeometry():
                    rectangle = feature.geometry().boundingBox()
                    if extent.isNull():
                        extent = QgsRectangle(rectangle)
                    else:
                        extent.combineExtentWith(rectangle)
        if extent.isNull():
            for layer in layers:
                rectangle = layer.extent()
                if not rectangle.isEmpty():
                    if extent.isNull():
                        extent = QgsRectangle(rectangle)
                    else:
                        extent.combineExtentWith(rectangle)
            if not extent.isNull():
                self.dialog.show_message("Tu campus todavía no tiene objetos propios. Se muestra la información institucional disponible.")
        if not extent.isNull():
            extent.grow(25)
            self.iface.mapCanvas().setExtent(extent)
            self.iface.mapCanvas().refresh()
        else:
            self.dialog.show_message("Todavía no hay objetos de tu campus. Podés agregar un mapa de referencia.")

    def basemap(self):
        try:
            add_basemap()
            self.iface.mapCanvas().refresh()
            self.dialog.show_message("Mapa de referencia agregado. © OpenStreetMap contributors.")
        except AccessError as error:
            self.dialog.show_message(str(error), True)
