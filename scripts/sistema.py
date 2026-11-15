"""Operación conjunta de la infraestructura de Andrés y QGIS de Kay.

Solo usa la biblioteca estándar; invoca el Python de QGIS cuando es necesario.
No elimina volúmenes ni ejecuta recuperaciones destructivas.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
NODES = {"central": 0, "cartago": 1, "sanjose": 2, "sancarlos": 3, "alajuela": 4, "limon": 5}
SCHEMAS = {"cartago": "cartago", "sanjose": "san_jose", "sancarlos": "san_carlos", "alajuela": "alajuela", "limon": "limon"}
THEMES = ("edificios", "carreteras", "aceras", "parqueos", "zonas_verdes", "puntos_interes", "iluminacion", "accesibilidad")


def run(command, cwd=ROOT, env=None):
    subprocess.run([str(value) for value in command], cwd=cwd, env=env, check=True)


def sql(node, statement):
    result = subprocess.run(["docker", "exec", "-i", f"sigtec-{node}", "psql", "-U", "postgres", "-d", "sigtec", "-At", "-v", "ON_ERROR_STOP=1"], input=statement, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"{node}: no se pudo inspeccionar la base. {result.stderr.strip()}")
    return result.stdout.strip()


def qgis_python(explicit=None):
    if explicit:
        candidates = [explicit]
    elif os.environ.get("QGIS_PYTHON"):
        candidates = [os.environ["QGIS_PYTHON"]]
    else:
        candidates = ["/Applications/QGIS-LTR.app/Contents/MacOS/python", "/Applications/QGIS.app/Contents/MacOS/python", sys.executable]
    for candidate in candidates:
        if not Path(candidate).is_file():
            continue
        try:
            result = subprocess.run([candidate, "-c", "import qgis.core, psycopg2"], capture_output=True, timeout=25)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0:
            return str(candidate)
    raise RuntimeError("No se encontró un Python con PyQGIS y psycopg2. Instalá QGIS o indicá --qgis-python /ruta/al/python-de-QGIS.")


def qgis_run(python, script, *args):
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONUNBUFFERED="1")
    run([python, ROOT / "scripts" / script, *args], env=env)


def modern_bash():
    for candidate in ("/opt/homebrew/bin/bash", "/usr/local/bin/bash", shutil.which("bash")):
        if candidate and Path(candidate).is_file():
            result = subprocess.run([candidate, "-c", "(( BASH_VERSINFO[0] >= 4 ))"], capture_output=True)
            if result.returncode == 0:
                return candidate
    raise RuntimeError("Los scripts originales de Andrés requieren Bash 4 o posterior.")


def inspect_node(node):
    profile = json.loads(sql(node, """SELECT json_build_object(
        'campus_id',public.campus_local(),
        'tablas', (SELECT count(*) FROM pg_tables WHERE schemaname IN ('cartago','san_jose','san_carlos','alajuela','limon')),
        'vistas',(SELECT count(*) FROM pg_views WHERE schemaname='sigtec_qgis'),
        'autenticacion',to_regprocedure('sigtec_auth.perfil_actual()') IS NOT NULL,
        'tiene_estilos',to_regclass('public.layer_styles') IS NOT NULL,
        'suscripciones',(SELECT coalesce(json_object_agg(subname,subenabled),'{}'::json) FROM pg_subscription),
        'tablas_sincronizadas',(SELECT coalesce(bool_and(srsubstate='r'),false) FROM pg_subscription_rel),
        'prepared_transactions',current_setting('max_prepared_transactions')::integer
    );"""))
    if profile["tiene_estilos"]:
        profile["estilos"] = json.loads(sql(node, """SELECT json_build_object(
            'cantidad',count(*),'firma',md5(string_agg(f_table_schema||'.'||f_table_name||styleqml::text,'|' ORDER BY f_table_schema,f_table_name,id)))
            FROM public.layer_styles WHERE useasdefault;"""))
    else:
        profile["estilos"] = {"cantidad": 0, "firma": None}
    if profile["vistas"] == 8:
        query = " UNION ALL ".join(f"SELECT '{theme}' AS capa,count(*) AS n FROM sigtec_qgis.{theme}" for theme in THEMES)
        profile["conteos"] = json.loads(sql(node, f"SELECT json_object_agg(capa,n) FROM ({query}) datos;"))
    else:
        profile["conteos"] = {}
    return profile


def check_cluster(wait=0, save=None):
    deadline = time.monotonic() + wait
    while True:
        report, problems = {}, []
        for node, campus_id in NODES.items():
            try:
                status = inspect_node(node)
                report[node] = status
                if status["campus_id"] != (campus_id or None):
                    problems.append(f"{node}: identidad de campus incorrecta")
                if status["tablas"] != 40 or status["vistas"] != 8:
                    problems.append(f"{node}: se requieren 40 tablas y ocho vistas")
                if status["estilos"]["cantidad"] != 8:
                    problems.append(f"{node}: faltan estilos predeterminados")
                expected = [f"sub_desde_{schema}" for schema in SCHEMAS.values()] if node == "central" else [f"sub_global_{SCHEMAS[node]}", "sub_sigtec_qgis_estilos"]
                if any(not status["suscripciones"].get(name) for name in expected):
                    problems.append(f"{node}: falta una suscripción habilitada")
                if not status["tablas_sincronizadas"]:
                    problems.append(f"{node}: hay tablas sin sincronizar")
                if node == "central" and not status["autenticacion"]:
                    problems.append("central: falta el perfil de autenticación")
            except (RuntimeError, json.JSONDecodeError) as error:
                problems.append(str(error))
        if len(report) == 6:
            baseline = report["central"]
            for node, status in report.items():
                if status["conteos"] != baseline["conteos"]:
                    problems.append(f"{node}: los conteos todavía no coinciden con el central")
                if status["estilos"]["firma"] != baseline["estilos"]["firma"]:
                    problems.append(f"{node}: los estilos todavía no coinciden con el central")
        if not problems or time.monotonic() >= deadline:
            break
        time.sleep(0.5)
    for node, status in report.items():
        print(f"{node:10} campus={status['campus_id']} tablas={status['tablas']} vistas={status['vistas']} estilos={status['estilos']['cantidad']} objetos={sum(status['conteos'].values())}")
    result = {"verificado_en_utc": datetime.now(timezone.utc).isoformat(), "correcto": not problems, "problemas": problems, "nodos": report}
    if save:
        path = Path(save)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if problems:
        raise RuntimeError("Integración incompleta:\n- " + "\n- ".join(problems))
    print("Integración correcta: seis nodos, autenticación, vistas y estilos conectados.")
    return result


def backup(node):
    # Ejecuta el respaldo lógico y físico de Andrés y añade los roles compartidos.
    directory = ROOT / "respaldos" / node
    before = set(directory.iterdir()) if directory.exists() else set()
    run([modern_bash(), ROOT / "scripts/respaldo.sh", node], cwd=ROOT)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    roles_path = directory / f"roles_{timestamp}.sql"
    with os.fdopen(os.open(roles_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as output:
        subprocess.run(["docker", "exec", f"sigtec-{node}", "pg_dumpall", "-U", "postgres", "--globals-only"], stdout=output, check=True)
    added = sorted(path.name for path in directory.iterdir() if path not in before)
    manifest = {"nodo": node, "fecha_utc": datetime.now(timezone.utc).isoformat(), "archivos": added,
                "incluye": ["base completa, vistas, funciones, permisos, estilos y datos", "roles PostgreSQL y verificadores de contraseña", "respaldo físico de Andrés"],
                "restauracion": "Restaurar roles antes del dump lógico en un clúster vacío. Revisar publicaciones/suscripciones después de una restauración; ver docs/INTEGRACION_ANDRES.md."}
    (directory / f"integrado_{timestamp}.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Respaldo integrado de {node}: {directory}")
    print("Incluye roles y objetos del complemento. Los respaldos no se incluyen en el ZIP de fuentes.")


def main():
    parser = argparse.ArgumentParser(description="SIG-TEC integrado: infraestructura de Andrés + complemento de Kay")
    parser.add_argument("accion", choices=("preparar", "iniciar", "estado", "contrato", "verificar", "detener", "respaldar"))
    parser.add_argument("nodo", nargs="?", choices=tuple(NODES))
    parser.add_argument("--qgis-python")
    parser.add_argument("--sin-datos", action="store_true", help="No importa los datos de referencia de San Carlos")
    parser.add_argument("--sin-instalar", action="store_true", help="No copia el complemento al perfil local")
    args = parser.parse_args()
    if args.accion == "preparar":
        python = qgis_python(args.qgis_python)
        print("1/5 · Iniciando la infraestructura de Andrés", flush=True)
        run(["bash", ROOT / "scripts/infra.sh", "up"])
        print("2/5 · Configurando autenticación, vistas y permisos", flush=True)
        run([sys.executable, ROOT / "scripts/integrar_qgis.py"])
        print("3/5 · Asegurando la distribución de estilos", flush=True)
        qgis_run(python, "publicar_estilos.py", "--conservar")
        if not args.sin_datos:
            print("4/5 · Importando datos de referencia sin duplicarlos", flush=True)
            qgis_run(python, "importar_osm.py")
        if not args.sin_instalar:
            print("5/5 · Instalando el complemento local", flush=True)
            run([sys.executable, ROOT / "scripts/instalar_complemento.py"])
        check_cluster(wait=45, save=ROOT / "docs/integracion_andres_estado.json")
        print("Abrí QGIS, activá SIG-TEC e ingresá con los accesos de .local/acceso_qgis.txt.")
    elif args.accion == "iniciar":
        run(["bash", ROOT / "scripts/infra.sh", "up"])
        check_cluster(wait=30)
    elif args.accion == "estado":
        check_cluster()
    elif args.accion == "verificar":
        check_cluster(wait=30, save=ROOT / "docs/integracion_andres_estado.json")
        run([sys.executable, ROOT / "scripts/validar_contrato.py", "--guardar"])
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONUNBUFFERED="1")
        run([qgis_python(args.qgis_python), ROOT / "pruebas/test_integracion.py"], env=env)
    elif args.accion == "contrato":
        run([sys.executable, ROOT / "scripts/validar_contrato.py", "--guardar"])
    elif args.accion == "detener":
        run(["bash", ROOT / "scripts/infra.sh", "stop"])
    elif args.accion == "respaldar":
        if not args.nodo:
            parser.error("respaldar requiere el nombre del nodo")
        backup(args.nodo)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error)) from None
