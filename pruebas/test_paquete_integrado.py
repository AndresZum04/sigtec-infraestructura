"""Comprueba que la entrega conjunta contiene y conecta ambas partes.

Solo extrae el ZIP e inspecciona la configuración; no crea contenedores.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="sigtec paquete ")
        cls.root = Path(cls.temp.name)
        with zipfile.ZipFile(ROOT / "dist/SIGTEC_proyecto.zip") as archive:
            cls.names = archive.namelist()
            archive.extractall(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_fuentes_de_andres_incluidas_y_sin_cambios(self):
        manifest = json.loads((self.root / "docs/infraestructura_origen.json").read_text())
        self.assertEqual(manifest["url"], "https://github.com/AndresZum04/sigtec-infraestructura.git")
        self.assertFalse(manifest["cambios_locales"])
        for name, expected in manifest["archivos_sha256"].items():
            with self.subTest(archivo=name):
                current = manifest.get("rutas_integradas", {}).get(name, name)
                self.assertEqual(hashlib.sha256((self.root / current).read_bytes()).hexdigest(), expected)

    def test_fuentes_de_kay_y_arranque_unico_incluidos(self):
        for name in ("sigtec.sh", "scripts/sistema.py", "integracion/01_central.sql", "integracion/02_vistas.sql", "complemento/sigtec/plugin.py", "dist/SIGTEC_QGIS.zip"):
            self.assertIn(name, self.names)
        result = subprocess.run(["bash", str(self.root / "sigtec.sh"), "--help"], cwd=self.root, capture_output=True, text=True, check=True)
        self.assertIn("preparar", result.stdout)
        self.assertIn("respaldar", result.stdout)

    def test_archivos_privados_y_de_ejecucion_excluidos(self):
        forbidden = {".git", ".local", "wal", "respaldos", "__pycache__", "infraestructura"}
        self.assertFalse(any(forbidden.intersection(Path(name).parts) for name in self.names))
        self.assertFalse(any("cuentas_demo" in name or "acceso_qgis.txt" in name for name in self.names))

    def test_compose_extraido_resuelve_rutas_dentro_del_paquete(self):
        result = subprocess.run(["docker", "compose", "-f", str(self.root / "docker-compose.yml"), "-f", str(self.root / "config/compose.macos.yml"), "config", "--format", "json"], capture_output=True, text=True, check=True)
        config = json.loads(result.stdout)
        self.assertEqual(len(config["services"]), 6)
        for name, service in config["services"].items():
            self.assertEqual(service["container_name"], f"sigtec-{name}")
            self.assertEqual(service["platform"], "linux/amd64")
            mounts = {mount["target"]: mount for mount in service["volumes"]}
            self.assertEqual(Path(mounts["/docker-entrypoint-initdb.d"]["source"]), self.root / ".local/init")
            self.assertEqual(Path(mounts["/wal_archive"]["source"]), self.root / f"wal/{name}")
            self.assertEqual(Path(mounts["/respaldos"]["source"]), self.root / f"respaldos/{name}")
            self.assertEqual(mounts["/var/lib/postgresql/data"]["type"], "volume")


if __name__ == "__main__":
    unittest.main(verbosity=2)
