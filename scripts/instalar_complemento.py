"""Crea un ZIP instalable y copia el complemento al perfil de QGIS.

Admite --profile /ruta/al/perfil para perfiles distintos de default.
"""
import argparse
from datetime import datetime
import os
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    if sys.platform == "darwin":
        default = Path.home() / "Library/Application Support/QGIS/QGIS3/profiles/default"
    elif sys.platform == "win32":
        default = Path(os.environ["APPDATA"]) / "QGIS/QGIS3/profiles/default"
    else:
        default = Path.home() / ".local/share/QGIS/QGIS3/profiles/default"
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=Path, default=default)
    parser.add_argument("--solo-zip", action="store_true", help="Genera el instalable sin modificar un perfil QGIS")
    args = parser.parse_args()
    source = ROOT / "complemento/sigtec"
    distribution = ROOT / "dist"
    distribution.mkdir(exist_ok=True)
    archive = distribution / "SIGTEC_QGIS.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
        for file in sorted(source.rglob("*")):
            if file.is_file() and "__pycache__" not in file.parts and file.suffix != ".pyc":
                output.write(file, str(Path("sigtec") / file.relative_to(source)))
    if args.solo_zip:
        print(f"ZIP instalable: {archive}")
        return
    destination = args.profile / "python/plugins/sigtec"
    if destination.exists():
        backup = ROOT / ".local" / ("complemento_anterior_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
        backup.parent.mkdir(exist_ok=True)
        shutil.copytree(destination, backup)
    shutil.copytree(source, destination, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    print(f"Complemento instalado en {destination}")
    print(f"ZIP instalable: {archive}")
    print("Activar SIG-TEC desde Complementos > Administrar e instalar complementos.")


if __name__ == "__main__":
    main()
