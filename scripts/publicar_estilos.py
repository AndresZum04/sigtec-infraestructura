"""Publica la simbología institucional y replica layer_styles a los campus.

Ejecutar con el Python de QGIS. Solo el administrador local publica estilos.
"""
from pathlib import Path
import argparse
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "complemento"))
from sigtec.cartography import institutional_style, configure_forms, validate_required_fields
from sigtec.settings import THEMES
from qgis.core import QgsApplication, QgsDataSourceUri, QgsVectorLayer

NODES = ("cartago", "sanjose", "sancarlos", "alajuela", "limon")
USERS = ("demo_cartago", "demo_san_jose", "kay", "demo_alajuela", "demo_limon")


def sql(node, statement):
    result = subprocess.run(["docker", "exec", "-i", f"sigtec-{node}", "psql", "-U", "postgres", "-d", "sigtec", "-At", "-v", "ON_ERROR_STOP=1"], input=statement, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"{node}: {result.stderr}")
    return result.stdout.strip()


def main(conservar=False):
    existing = set()
    if conservar and sql("central", "SELECT to_regclass('public.layer_styles') IS NOT NULL;") == "t":
        existing = set(sql("central", "SELECT f_table_name FROM public.layer_styles WHERE f_table_schema='sigtec_qgis' AND f_table_catalog='sigtec' AND useasdefault;").splitlines())
    for theme in THEMES:
        if theme in existing:
            print(f"Central: estilo {theme} existente conservado")
            continue
        uri = QgsDataSourceUri()
        uri.setConnection("localhost", "5440", "sigtec", "postgres", "sigtec2026")
        uri.setDataSource("sigtec_qgis", theme, "geom", "", "id")
        layer = QgsVectorLayer(uri.uri(False), theme, "postgres")
        if not layer.isValid():
            raise RuntimeError(f"No se pudo abrir la vista central {theme}.")
        institutional_style(layer, theme)
        configure_forms(layer, 3)
        validate_required_fields(layer, theme)
        for directory in (ROOT / "qgis/estilos", ROOT / "complemento/sigtec/styles"):
            directory.mkdir(parents=True, exist_ok=True)
            message, ok = layer.saveNamedStyle(str(directory / f"{theme}.qml"))
            if not ok:
                raise RuntimeError(message)
        error = layer.saveStyleToDatabase(f"SIGTEC_{theme}_v1", "Simbología institucional v1; formularios y etiquetas comunes.", True, "")
        if error:
            raise RuntimeError(error)
        print(f"Central: estilo {theme} guardado")
        del layer

    structure = subprocess.run(["docker", "exec", "sigtec-central", "pg_dump", "-U", "postgres", "-d", "sigtec", "-s", "-t", "public.layer_styles"], capture_output=True, text=True, check=True).stdout
    if sql("central", "SELECT count(*) FROM pg_publication WHERE pubname='pub_sigtec_qgis_estilos';") == "0":
        sql("central", "CREATE PUBLICATION pub_sigtec_qgis_estilos FOR TABLE public.layer_styles;")
    for node, user in zip(NODES, USERS):
        if sql(node, "SELECT to_regclass('public.layer_styles') IS NOT NULL;") == "f":
            sql(node, structure)
        sql(node, f'GRANT SELECT ON public.layer_styles TO "{user}";')
        if sql(node, "SELECT count(*) FROM pg_subscription WHERE subname='sub_sigtec_qgis_estilos';") == "0":
            if sql(node, "SELECT count(*) FROM public.layer_styles;") != "0":
                raise RuntimeError(f"{node}: hay estilos previos; revisar la migración antes de suscribir.")
            sql(node, f"CREATE SUBSCRIPTION sub_sigtec_qgis_estilos CONNECTION 'host=central port=5432 dbname=sigtec user=postgres password=sigtec2026' PUBLICATION pub_sigtec_qgis_estilos WITH (slot_name='sub_sigtec_estilos_{node}');")
    deadline = time.monotonic() + 45
    expected = sql("central", "SELECT count(*) FROM public.layer_styles;")
    while True:
        counts = {node: sql(node, "SELECT count(*) FROM public.layer_styles;") for node in NODES}
        if all(count == expected for count in counts.values()):
            print(f"Estilos distribuidos a 5/5 campus: {expected} por nodo")
            return
        if time.monotonic() > deadline:
            raise RuntimeError(f"La distribución de estilos no terminó: {counts}")
        time.sleep(0.5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--conservar", action="store_true", help="Conserva los estilos predeterminados que ya existen en la base")
    args = parser.parse_args()
    app = QgsApplication([], False)
    app.initQgis()
    try:
        main(args.conservar)
    finally:
        app.exitQgis()
