"""Ventanas Qt nativas de acceso y configuración."""
import copy

from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QApplication, QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox,
    QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from .settings import THEMES, validate
from .cartography import LABELS


class LoginDialog(QDialog):
    loginRequested = pyqtSignal(str, str)
    logoutRequested = pyqtSignal()
    refreshRequested = pyqtSignal()
    configureRequested = pyqtSignal()
    filterRequested = pyqtSignal(bool)
    zoomRequested = pyqtSignal()
    basemapRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SIG-TEC · Información geográfica")
        self.setMinimumWidth(410)
        self.dark = QApplication.palette().window().color().lightness() < 128
        layout = QVBoxLayout(self)
        title = QLabel("SIG-TEC")
        title_color = "#86d8d5" if self.dark else "#15576a"
        title.setStyleSheet(f"font-size: 27px; font-weight: 700; color: {title_color}; margin-bottom: 4px;")
        layout.addWidget(title)
        self.intro = QLabel("Ingresá con tu usuario para consultar todos los campus y editar los objetos de tu sede.")
        self.intro.setWordWrap(True)
        layout.addWidget(self.intro)
        self.login_box = QGroupBox("Ingresar")
        form = QFormLayout(self.login_box)
        self.username = QLineEdit()
        self.username.setPlaceholderText("Nombre de usuario")
        self.username.setObjectName("sigtecUsername")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setObjectName("sigtecPassword")
        form.addRow("Usuario", self.username)
        form.addRow("Contraseña", self.password)
        show = QCheckBox("Mostrar contraseña")
        show.toggled.connect(lambda checked: self.password.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password))
        form.addRow("", show)
        self.login_button = QPushButton("Ingresar")
        self.login_button.setObjectName("sigtecLogin")
        self.login_button.clicked.connect(self.request_login)
        self.password.returnPressed.connect(self.request_login)
        form.addRow(self.login_button)
        layout.addWidget(self.login_box)

        self.session_box = QGroupBox("Sesión activa")
        active = QVBoxLayout(self.session_box)
        self.identity = QLabel()
        self.identity.setWordWrap(True)
        self.identity.setTextFormat(Qt.PlainText)
        active.addWidget(self.identity)
        self.only_local = QCheckBox("Mostrar solo los objetos de mi campus")
        self.only_local.toggled.connect(self.filterRequested)
        active.addWidget(self.only_local)
        buttons = QHBoxLayout()
        for label, signal in (("Actualizar capas", self.refreshRequested), ("Ir a mi campus", self.zoomRequested)):
            button = QPushButton(label)
            button.clicked.connect(signal)
            buttons.addWidget(button)
        active.addLayout(buttons)
        background = QPushButton("Agregar mapa de referencia")
        background.clicked.connect(self.basemapRequested)
        active.addWidget(background)
        logout = QPushButton("Cerrar sesión")
        logout.clicked.connect(self.logoutRequested)
        active.addWidget(logout)
        self.session_box.hide()
        layout.addWidget(self.session_box)
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.message.setTextFormat(Qt.PlainText)
        self.message.setObjectName("sigtecMessage")
        layout.addWidget(self.message)
        self.configure_button = QPushButton("Configurar conexiones…")
        self.configure_button.clicked.connect(self.configureRequested)
        layout.addWidget(self.configure_button)

    def request_login(self):
        if self.login_button.isEnabled():
            self.loginRequested.emit(self.username.text().strip(), self.password.text())

    def show_message(self, text, error=False):
        color = ("#ff9e95" if self.dark else "#bd423a") if error else ("#8cdcd4" if self.dark else "#27757b")
        self.message.setStyleSheet(f"color: {color};")
        self.message.setText(text)

    def set_busy(self, busy):
        self.login_button.setEnabled(not busy)
        self.configure_button.setEnabled(not busy)
        self.username.setEnabled(not busy)
        self.password.setEnabled(not busy)
        self.session_box.setEnabled(not busy)
        if busy:
            self.show_message("Validando acceso y conectando con tu campus…")

    def set_session(self, session):
        self.login_box.setVisible(session is None)
        self.session_box.setVisible(session is not None)
        self.password.clear()
        self.only_local.blockSignals(True)
        self.only_local.setChecked(False)
        self.only_local.blockSignals(False)
        self.configure_button.setVisible(session is None)
        if session:
            self.intro.setText("Información institucional disponible. Trabajá desde las capas de tu proyecto QGIS.")
            self.identity.setText(f"{session.username}\n{session.campus_name}\n8 capas institucionales · EPSG:5367")
            self.identity.setMinimumHeight(self.identity.sizeHint().height())
            self.show_message("Podés consultar todos los campus. La base restringe la edición a tu sede.")
        else:
            self.intro.setText("Ingresá con tu usuario para consultar todos los campus y editar los objetos de tu sede.")
            self.show_message("Sesión cerrada. Ingresá para conectar nuevamente.")
        self.adjustSize()


class ConfigurationDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = copy.deepcopy(config)
        self.setWindowTitle("SIG-TEC · Configuración de integración")
        self.resize(680, 580)
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        endpoints = QWidget()
        form = QFormLayout(endpoints)
        self.host = QLineEdit(config["central"]["host"])
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(config["central"]["port"])
        self.database = QLineEdit(config["central"]["database"])
        form.addRow("Host del central", self.host)
        form.addRow("Puerto del central", self.port)
        form.addRow("Base de datos central", self.database)
        form.addRow(QLabel("Nodos de campus (host, puerto y base de datos):"))
        self.nodes = QTableWidget(5, 3)
        self.nodes.setHorizontalHeaderLabels(["Host", "Puerto", "Base de datos"])
        self.nodes.setVerticalHeaderLabels(["Cartago", "San José", "San Carlos", "Alajuela", "Limón"])
        for row in range(5):
            node = config["campuses"][str(row + 1)]
            for column, key in enumerate(("host", "port", "database")):
                self.nodes.setItem(row, column, QTableWidgetItem(str(node[key])))
        self.nodes.horizontalHeader().setStretchLastSection(True)
        form.addRow(self.nodes)
        tabs.addTab(endpoints, "Conexiones")
        contract = QWidget()
        form = QFormLayout(contract)
        self.names = {}
        for key, label in (("auth_schema", "Esquema de autenticación"), ("auth_function", "Función de perfil"), ("view_schema", "Esquema de vistas"), ("geometry_column", "Columna geométrica"), ("key_column", "Identificador único")):
            self.names[key] = QLineEdit(config[key])
            form.addRow(label, self.names[key])
        self.views = QTableWidget(8, 1)
        self.views.setHorizontalHeaderLabels(["Nombre de la vista"])
        self.views.setVerticalHeaderLabels([LABELS[theme] for theme in THEMES])
        for row, theme in enumerate(THEMES):
            self.views.setItem(row, 0, QTableWidgetItem(config["views"][theme]))
        self.views.horizontalHeader().setStretchLastSection(True)
        form.addRow(self.views)
        tabs.addTab(contract, "Contrato SQL")
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.setStyleSheet("color: #bd423a;")
        layout.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        try:
            value = copy.deepcopy(self.config)
            value["central"].update(host=self.host.text().strip(), port=self.port.value(), database=self.database.text().strip())
            for row in range(5):
                value["campuses"][str(row + 1)].update({key: self.nodes.item(row, column).text().strip() for column, key in enumerate(("host", "port", "database"))})
            value.update({key: field.text().strip() for key, field in self.names.items()})
            value["views"] = {theme: self.views.item(row, 0).text().strip() for row, theme in enumerate(THEMES)}
            self.config = validate(value)
        except (ValueError, TypeError, AttributeError) as error:
            self.error.setText(str(error))
            return
        super().accept()
