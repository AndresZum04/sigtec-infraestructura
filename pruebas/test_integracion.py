"""Pruebas reales sobre los nodos locales; eliminan sus objetos temporales."""
import copy
import json
from pathlib import Path
import sys
import time
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "complemento"))
import psycopg2
from qgis.PyQt.QtWidgets import QMainWindow
from qgis.core import QgsApplication, QgsFeatureRequest, QgsGeometry, QgsProject, QgsVectorLayer, QgsVectorLayerUtils
from sigtec.backend import AccessError, authenticate, connect
from sigtec.layers import create_layers, install_layers, managed_layers, pending_edits, remove_layers
from sigtec.plugin import SigtecPlugin
from sigtec.settings import defaults, validate

ACCOUNTS = json.loads((ROOT / ".local/cuentas_demo.json").read_text())
CONFIG = defaults()
NODES = [(1, "demo_cartago"), (2, "demo_san_jose"), (3, "kay"), (4, "demo_alajuela"), (5, "demo_limon")]
GEOMS = {
    "edificios": "POLYGON((480000 1145000,480020 1145000,480020 1145020,480000 1145020,480000 1145000))",
    "parqueos": "POLYGON((480000 1145000,480020 1145000,480020 1145020,480000 1145020,480000 1145000))",
    "zonas_verdes": "POLYGON((480000 1145000,480020 1145000,480020 1145020,480000 1145020,480000 1145000))",
    "carreteras": "LINESTRING(480000 1145000,480020 1145020)",
    "aceras": "LINESTRING(480000 1145000,480020 1145020)",
    "accesibilidad": "LINESTRING(480000 1145000,480020 1145020)",
    "puntos_interes": "POINT(480000 1145000)",
    "iluminacion": "POINT(480000 1145000)",
}


def execute(campus_id, username, query, args=None):
    with connect(CONFIG["campuses"][str(campus_id)], username, ACCOUNTS[username]) as connection:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(query, args)
            return cursor.fetchall() if cursor.description else None


def wait_for(query, args, expected):
    deadline = time.monotonic() + 40
    while True:
        rows = execute(3, "kay", query, args)
        if rows == expected:
            return
        if time.monotonic() > deadline:
            raise AssertionError(f"Replicación pendiente; esperado {expected}, recibido {rows}")
        time.sleep(0.25)


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = authenticate(CONFIG, "kay", ACCOUNTS["kay"])

    def tearDown(self):
        project = QgsProject.instance()
        for layer in managed_layers(project):
            if layer.isEditable():
                layer.rollBack()
        project.clear()

    def test_01_autenticacion_real_y_campus(self):
        for campus, username in NODES:
            with self.subTest(campus=campus):
                session = authenticate(CONFIG, username, ACCOUNTS[username])
                self.assertEqual(session.campus_id, campus)
                self.assertEqual(len(session.styles), 8)
                layers = create_layers(session, ACCOUNTS[username], CONFIG)
                self.assertEqual(len(layers), 8)
                for layer in layers:
                    feature = QgsVectorLayerUtils.createFeature(layer)
                    # El proveedor puede representar el valor predeterminado
                    # smallint como literal de texto hasta guardar la entidad.
                    self.assertEqual(int(feature["campus_id"]), campus)
        with self.assertRaisesRegex(AccessError, "incorrectos"):
            authenticate(CONFIG, "kay", "CONTRASENA_INCORRECTA")
        with self.assertRaisesRegex(AccessError, "Ingresá"):
            authenticate(CONFIG, "", "")

    def test_02_configuracion_y_vistas_ausentes(self):
        config = copy.deepcopy(CONFIG)
        config["views"]["edificios"] = "vista_no_instalada"
        with self.assertRaisesRegex(AccessError, "Faltan vistas"):
            authenticate(config, "kay", ACCOUNTS["kay"])
        config = copy.deepcopy(CONFIG)
        config["campuses"]["3"]["port"] = 5441
        with self.assertRaisesRegex(AccessError, "nodo rechazó"):
            authenticate(config, "kay", ACCOUNTS["kay"])
        config = copy.deepcopy(CONFIG)
        config["view_schema"] = 'public; DROP SCHEMA public'
        with self.assertRaises(ValueError):
            validate(config)
        config = copy.deepcopy(CONFIG)
        config["central"]["port"] = 9
        config["timeout"] = 2
        with self.assertRaisesRegex(AccessError, "No se pudo conectar"):
            authenticate(config, "kay", ACCOUNTS["kay"])

    def test_03_capas_estilos_formularios_y_proyecto_sin_claves(self):
        layers = create_layers(self.session, ACCOUNTS["kay"], CONFIG)
        self.assertEqual(len(layers), 8)
        install_layers(layers, self.session)
        project = QgsProject.instance()
        self.assertEqual(project.crs().authid(), "EPSG:5367")
        for layer in layers:
            self.assertEqual(layer.customProperty("sigtec/style_source"), "base de datos")
            self.assertNotIn("password=", layer.source())
            self.assertTrue(layer.editFormConfig().readOnly(layer.fields().indexFromName("campus_id")))
            self.assertEqual(layer.defaultValueDefinition(layer.fields().indexFromName("campus_id")).expression(), "@sigtec_campus_id")
        destination = ROOT / ".local/prueba_proyecto.qgs"
        self.assertTrue(project.write(str(destination)))
        self.assertNotIn(ACCOUNTS["kay"], destination.read_text())

    def test_04_crud_pyqgis_ocho_vistas_y_replicacion(self):
        layers = create_layers(self.session, ACCOUNTS["kay"], CONFIG)
        for layer in layers:
            theme = layer.customProperty("sigtec/theme")
            marker = "T_" + uuid.uuid4().hex[:8]
            field = "nombre" if layer.fields().indexFromName("nombre") >= 0 else ("codigo" if theme == "iluminacion" else "descripcion" if theme == "accesibilidad" else "material")
            attrs = {layer.fields().indexFromName(field): marker}
            feature = QgsVectorLayerUtils.createFeature(layer, QgsGeometry.fromWkt(GEOMS[theme]), attrs)
            object_id = None
            with self.subTest(capa=theme):
                try:
                    self.assertTrue(layer.startEditing())
                    self.assertTrue(layer.addFeature(feature))
                    self.assertTrue(layer.commitChanges(), layer.commitErrors())
                    object_id, campus = execute(3, "kay", f'SELECT id,campus_id FROM sigtec_qgis.{theme} WHERE "{field}"=%s', (marker,))[0]
                    self.assertEqual(campus, 3)
                    self.assertTrue(3000001 <= object_id <= 3999999)
                    saved = next(layer.getFeatures(QgsFeatureRequest().setFilterExpression(f'"id"={object_id}')))
                    self.assertTrue(layer.startEditing())
                    self.assertTrue(layer.changeAttributeValue(saved.id(), layer.fields().indexFromName(field), marker + "_EDIT"))
                    self.assertTrue(layer.commitChanges(), layer.commitErrors())
                    for campus_id, username in NODES:
                        deadline = time.monotonic() + 30
                        while execute(campus_id, username, f'SELECT "{field}" FROM sigtec_qgis.{theme} WHERE id=%s', (object_id,)) != [(marker + "_EDIT",)]:
                            if time.monotonic() > deadline:
                                self.fail(f"{theme} no llegó al campus {campus_id}")
                            time.sleep(0.2)
                    self.assertTrue(layer.startEditing())
                    self.assertTrue(layer.deleteFeature(saved.id()))
                    self.assertTrue(layer.commitChanges(), layer.commitErrors())
                finally:
                    if layer.isEditable():
                        layer.rollBack()
                    if object_id:
                        execute(3, "kay", f"DELETE FROM sigtec_qgis.{theme} WHERE id=%s", (object_id,))

    def test_05_prohibicion_escritura_ajena_y_cambio_identidad(self):
        marker = "__TEST_AJENO_" + uuid.uuid4().hex[:12]
        foreign = execute(1, "demo_cartago", "INSERT INTO sigtec_qgis.edificios(nombre,geom) VALUES(%s,ST_GeomFromText(%s,5367)) RETURNING id", (marker, GEOMS["edificios"]))[0][0]
        own = execute(3, "kay", "INSERT INTO sigtec_qgis.edificios(nombre,geom) VALUES(%s,ST_GeomFromText(%s,5367)) RETURNING id", (marker, GEOMS["edificios"]))[0][0]
        try:
            wait_for("SELECT id FROM sigtec_qgis.edificios WHERE id=%s", (foreign,), [(foreign,)])
            statements = [
                ("UPDATE sigtec_qgis.edificios SET nombre='NO' WHERE id=%s", (foreign,)),
                ("DELETE FROM sigtec_qgis.edificios WHERE id=%s", (foreign,)),
                ("UPDATE sigtec_qgis.edificios SET campus_id=1 WHERE id=%s", (own,)),
                ("UPDATE sigtec_qgis.edificios SET id=id+1 WHERE id=%s", (own,)),
                ("INSERT INTO sigtec_qgis.edificios(campus_id,nombre,geom) VALUES(1,'NO',ST_GeomFromText(%s,5367))", (GEOMS["edificios"],)),
                ("INSERT INTO cartago.edificios(nombre,geom) VALUES('NO',ST_GeomFromText(%s,5367))", (GEOMS["edificios"],)),
            ]
            for statement, args in statements:
                with self.assertRaises(psycopg2.Error) as error:
                    execute(3, "kay", statement, args)
                self.assertEqual(error.exception.pgcode, "42501")
            self.assertEqual(execute(3, "kay", "SELECT nombre FROM sigtec_qgis.edificios WHERE id=%s", (foreign,)), [(marker,)])
        finally:
            execute(3, "kay", "DELETE FROM sigtec_qgis.edificios WHERE id=%s", (own,))
            execute(1, "demo_cartago", "DELETE FROM sigtec_qgis.edificios WHERE id=%s", (foreign,))

    def test_06_geometria_invalida_rechazada(self):
        invalid = "POLYGON((480000 1145000,480020 1145020,480020 1145000,480000 1145020,480000 1145000))"
        with self.assertRaises(psycopg2.Error) as error:
            execute(3, "kay", "INSERT INTO sigtec_qgis.edificios(nombre,geom) VALUES('NO',ST_GeomFromText(%s,5367))", (invalid,))
        self.assertEqual(error.exception.pgcode, "23514")
        with self.assertRaises(psycopg2.Error) as empty_error:
            execute(3, "kay", "INSERT INTO sigtec_qgis.edificios(nombre,geom) VALUES('NO',ST_GeomFromText('POLYGON EMPTY',5367))")
        self.assertEqual(empty_error.exception.pgcode, "23514")

    def test_07_sesion_conserva_ediciones_y_capas_ajenas(self):
        project = QgsProject.instance()
        unrelated = QgsVectorLayer("Point?crs=EPSG:5367", "Mi capa independiente", "memory")
        project.addMapLayer(unrelated)
        install_layers(create_layers(self.session, ACCOUNTS["kay"], CONFIG), self.session)
        layer = next(layer for layer in managed_layers() if layer.customProperty("sigtec/theme") == "puntos_interes")
        feature = QgsVectorLayerUtils.createFeature(layer, QgsGeometry.fromWkt(GEOMS["puntos_interes"]), {layer.fields().indexFromName("nombre"): "SIN_GUARDAR"})
        layer.startEditing()
        layer.addFeature(feature)
        self.assertTrue(pending_edits())
        with self.assertRaises(AccessError):
            remove_layers()
        self.assertEqual(len(managed_layers()), 8)
        layer.rollBack()
        remove_layers()
        self.assertEqual(len(project.mapLayers()), 1)
        self.assertIn(unrelated.id(), project.mapLayers())

        # Una capa ajena agregada dentro del grupo de SIG-TEC también se conserva.
        group = install_layers(create_layers(self.session, ACCOUNTS["kay"], CONFIG), self.session)
        nested = QgsVectorLayer("Point?crs=EPSG:5367", "Capa propia dentro del grupo", "memory")
        project.addMapLayer(nested, False)
        group.addLayer(nested)
        remove_layers()
        self.assertIn(nested.id(), project.mapLayers())
        self.assertIsNotNone(project.layerTreeRoot().findLayer(nested.id()))

    def test_08_interfaz_y_tarea_asincrona(self):
        class Canvas:
            def setExtent(self, extent): pass
            def refresh(self): pass
        class Messages:
            def pushSuccess(self, *args): pass
        class Iface:
            def __init__(self): self.window = QMainWindow()
            def mainWindow(self): return self.window
            def addToolBarIcon(self, action): pass
            def addPluginToMenu(self, menu, action): pass
            def removeToolBarIcon(self, action): pass
            def removePluginMenu(self, menu, action): pass
            def mapCanvas(self): return Canvas()
            def messageBar(self): return Messages()
        iface = Iface()
        plugin = SigtecPlugin(iface)
        try:
            plugin.initGui()
            plugin.run()
            plugin.login("kay", "INCORRECTA")
            self.await_task(plugin)
            self.assertIsNone(plugin.session)
            self.assertIn("incorrectos", plugin.dialog.message.text())
            self.assertTrue(plugin.dialog.login_button.isEnabled())
            plugin.login("kay", ACCOUNTS["kay"])
            self.await_task(plugin)
            self.assertEqual(plugin.session.campus_id, 3, plugin.dialog.message.text())
            self.assertEqual(len(managed_layers()), 8)
            plugin.filter_local(True)
            self.assertTrue(all(layer.subsetString() == '"campus_id" = 3' for layer in managed_layers()))
            plugin.filter_local(False)
            plugin.refresh()
            self.await_task(plugin)
            self.assertEqual(len(managed_layers()), 8)
            plugin.logout()
            self.assertEqual(len(managed_layers()), 0)
            plugin.login("demo_cartago", ACCOUNTS["demo_cartago"])
            self.await_task(plugin)
            self.assertEqual(plugin.session.campus_id, 1)
            self.assertEqual(len(managed_layers()), 8)
            self.assertIn("información institucional", plugin.dialog.message.text())
            plugin.logout()
        finally:
            plugin.unload()
            iface.window.close()

    def test_09_estilos_identicos_y_solo_lectura(self):
        hashes = []
        for campus_id, username in NODES:
            hashes.append(execute(campus_id, username, "SELECT md5(string_agg(styleqml::text,'|' ORDER BY f_table_name)) FROM public.layer_styles WHERE useasdefault")[0][0])
        self.assertEqual(len(set(hashes)), 1)
        with self.assertRaises(psycopg2.Error) as error:
            execute(3, "kay", "DELETE FROM public.layer_styles WHERE false")
        self.assertEqual(error.exception.pgcode, "42501")

    def test_10_central_no_expone_catalogo_usuarios(self):
        with connect(CONFIG["central"], "kay", ACCOUNTS["kay"]) as connection:
            with connection.cursor() as cursor:
                with self.assertRaises(psycopg2.Error) as error:
                    cursor.execute("SELECT * FROM sigtec_auth.usuarios")
                self.assertEqual(error.exception.pgcode, "42501")

    def test_11_usuario_inactivo_no_ingresa(self):
        from contextlib import closing
        from psycopg2 import sql
        username = "sigtec_test_" + uuid.uuid4().hex[:10]
        password = uuid.uuid4().hex
        with closing(psycopg2.connect(host="localhost", port=5440, dbname="sigtec", user="postgres", password="sigtec2026")) as admin:
            admin.autocommit = True
            with admin.cursor() as cursor:
                cursor.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD %s").format(sql.Identifier(username)), (password,))
                try:
                    cursor.execute("INSERT INTO sigtec_auth.usuarios(usuario,campus_id,activo) VALUES(%s,3,false)", (username,))
                    cursor.execute(sql.SQL("GRANT USAGE ON SCHEMA sigtec_auth TO {}").format(sql.Identifier(username)))
                    cursor.execute(sql.SQL("GRANT EXECUTE ON FUNCTION sigtec_auth.perfil_actual() TO {}").format(sql.Identifier(username)))
                    with self.assertRaisesRegex(AccessError, "campus activo"):
                        authenticate(CONFIG, username, password)
                finally:
                    cursor.execute("DELETE FROM sigtec_auth.usuarios WHERE usuario=%s", (username,))
                    cursor.execute(sql.SQL("DROP OWNED BY {}").format(sql.Identifier(username)))
                    cursor.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(username)))

    def await_task(self, plugin):
        deadline = time.monotonic() + 35
        while plugin.task is not None:
            QgsApplication.processEvents()
            if time.monotonic() > deadline:
                self.fail("La tarea de acceso no terminó.")
            time.sleep(0.01)


if __name__ == "__main__":
    app = QgsApplication([], True)
    app.initQgis()
    try:
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(IntegrationTests))
    finally:
        QgsProject.instance().clear()
        app.exitQgis()
    sys.exit(0 if result.wasSuccessful() else 1)
