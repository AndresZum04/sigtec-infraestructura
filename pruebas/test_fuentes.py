"""Comprobaciones de distribución que no necesitan QGIS ni bases activas."""
import configparser
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "complemento"))
from sigtec import settings


class SourceTests(unittest.TestCase):
    def test_version_y_metadatos_completos(self):
        metadata = configparser.ConfigParser()
        metadata.read(ROOT / "complemento/sigtec/metadata.txt", encoding="utf-8")
        for key in ("name", "version", "author", "email", "repository", "description", "qgisMinimumVersion"):
            self.assertTrue(metadata["general"][key].strip(), key)
        version = (ROOT / "VERSION").read_text().strip()
        self.assertEqual(metadata["general"]["version"], version)
        self.assertEqual(json.loads((ROOT / "integracion/contrato_v1.json").read_text())["version"], version)

    def test_configuracion_coincide_con_el_contrato(self):
        config = settings.defaults()
        contract = json.loads((ROOT / "integracion/contrato_v1.json").read_text())
        self.assertEqual(config["view_schema"], contract["esquema_vistas"])
        self.assertEqual(config["key_column"], contract["clave"])
        self.assertEqual(config["geometry_column"], contract["geometria"])
        self.assertEqual(set(config["views"]), set(contract["vistas"]))
        for campus in contract["campus"]:
            self.assertEqual(config["campuses"][str(campus["id"])]["port"], campus["puerto"])
        for theme, view in contract["vistas"].items():
            columns = {field["nombre"]: field["tipo"] for field in view["columnas"]}
            self.assertEqual(columns["id"], "bigint")
            self.assertEqual(columns["campus_id"], "smallint")
            self.assertIn(",5367)", columns["geom"])

    def test_vistas_distintas_y_sin_credenciales_guardadas(self):
        config = settings.defaults()
        config["views"]["edificios"] = config["views"]["parqueos"]
        with self.assertRaises(ValueError):
            settings.validate(config)
        config = settings.defaults()
        config["central"]["password"] = "NO_GUARDAR"
        with self.assertRaises(ValueError):
            settings.validate(config)

    def test_estilos_xml_y_sin_codigo_de_formulario(self):
        for theme in settings.THEMES:
            file = ROOT / "complemento/sigtec/styles" / f"{theme}.qml"
            with self.subTest(capa=theme):
                xml = ET.parse(file).getroot()
                self.assertEqual(xml.tag, "qgis")
                self.assertFalse((xml.findtext("editforminitcode") or "").strip())

    def test_procedencia_de_infraestructura_y_datos(self):
        origin = json.loads((ROOT / "docs/infraestructura_origen.json").read_text())
        for name, expected in origin["archivos_sha256"].items():
            current = origin.get("rutas_integradas", {}).get(name, name)
            self.assertEqual(hashlib.sha256((ROOT / current).read_bytes()).hexdigest(), expected, name)
        source = ROOT / "datos/fuentes/osm_objetos_san_carlos.json"
        provenance = json.loads((ROOT / "datos/procedencia_san_carlos.json").read_text())
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), provenance["sha256_fuente"])
        self.assertEqual(len(provenance["objetos"]), 358)
        self.assertEqual(provenance["licencia"], "ODbL-1.0")

    def test_zip_no_modifica_perfil(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory) / "perfil"
            subprocess.run([sys.executable, str(ROOT / "scripts/instalar_complemento.py"), "--solo-zip", "--profile", str(profile)], check=True, capture_output=True)
            self.assertFalse(profile.exists())
        with zipfile.ZipFile(ROOT / "dist/SIGTEC_QGIS.zip") as archive:
            self.assertIsNone(archive.testzip())
            self.assertIn("sigtec/metadata.txt", archive.namelist())
            self.assertFalse(any("__pycache__" in name or ".local/" in name for name in archive.namelist()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
