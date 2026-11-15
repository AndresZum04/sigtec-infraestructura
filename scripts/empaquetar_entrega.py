"""Construye un único paquete del proyecto y el instalable QGIS."""
import hashlib
from io import BytesIO
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    project = ROOT / "qgis/SIGTEC_San_Carlos.qgs"
    compact = project.with_suffix(".qgz")
    if project.exists() and not compact.exists():
        with zipfile.ZipFile(compact, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.write(project, project.name)
    names = ("README.md", ".gitignore", ".gitattributes", "VERSION", "CHANGELOG.md",
             "CONTRIBUTING.md", "THIRD_PARTY_NOTICES.md", "sigtec.sh", "docker-compose.yml",
             "dist/SIGTEC_QGIS.zip")
    files = [ROOT / name for name in names]
    for folder in (".github", "complemento", "config", "datos", "docs", "init", "integracion", "pruebas", "qgis", "scripts"):
        files.extend(file for file in (ROOT / folder).rglob("*")
                     if file.is_file() and "__pycache__" not in file.parts
                     and file.suffix != ".pyc" and not file.name.endswith("~"))
    accounts = ROOT / ".local/cuentas_demo.json"
    encoded = [password.encode() for password in json.loads(accounts.read_text()).values()] if accounts.exists() else []

    def inspect(data, name):
        if any(password in data for password in encoded):
            raise RuntimeError(f"Se encontró una contraseña local en {name}.")
        if name.endswith((".zip", ".qgz")):
            with zipfile.ZipFile(BytesIO(data)) as nested:
                for entry in nested.namelist():
                    inspect(nested.read(entry), f"{name}/{entry}")

    output = ROOT / "dist/SIGTEC_proyecto.zip"
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(set(files)):
            data = file.read_bytes()
            inspect(data, str(file.relative_to(ROOT)))
            archive.write(file, str(file.relative_to(ROOT)))
    with zipfile.ZipFile(output) as archive:
        forbidden = {".local", ".git", "wal", "respaldos", "__pycache__", "infraestructura"}
        if archive.testzip() is not None or any(forbidden.intersection(Path(entry).parts) for entry in archive.namelist()):
            raise RuntimeError("El ZIP contiene estado local, un repositorio anidado o archivos inválidos.")
    sums = []
    for artifact in (ROOT / "dist/SIGTEC_QGIS.zip", output):
        sums.append(f"{hashlib.sha256(artifact.read_bytes()).hexdigest()}  {artifact.name}\n")
    (ROOT / "dist/SHA256SUMS.txt").write_text("".join(sums), encoding="utf-8")
    print(f"Proyecto único: {output.name}; {len(set(files))} archivos; {output.stat().st_size:,} bytes")
    print("ZIP verificado; credenciales, repositorios internos, WAL y respaldos excluidos.")


if __name__ == "__main__":
    main()
