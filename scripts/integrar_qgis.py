"""Instala el contrato SQL de referencia y cuentas locales en los seis nodos.

No cambia roles existentes ni reemplaza código del repositorio de Andrés.
Las contraseñas de demostración se conservan únicamente en .local/ con modo 600.
"""
import json
import os
from pathlib import Path
import secrets
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CAMPUS = ((1, "cartago", "cartago", "demo_cartago"), (2, "sanjose", "san_jose", "demo_san_jose"),
          (3, "sancarlos", "san_carlos", "kay"), (4, "alajuela", "alajuela", "demo_alajuela"),
          (5, "limon", "limon", "demo_limon"))


def sql(node, statement):
    return subprocess.run(["docker", "exec", "-i", f"sigtec-{node}", "psql", "-U", "postgres", "-d", "sigtec", "-v", "ON_ERROR_STOP=1", "-At"],
        input=statement, text=True, capture_output=True, check=True).stdout.strip()


def literal(value):
    return "'" + value.replace("'", "''") + "'"


def main():
    local = ROOT / ".local"
    local.mkdir(exist_ok=True)
    access_file = local / "cuentas_demo.json"
    if access_file.exists():
        accounts = json.loads(access_file.read_text())
    else:
        if sql("central", "SELECT count(*) FROM pg_roles WHERE rolname='kay';") != "0":
            raise SystemExit("Ya existe el rol kay, pero falta .local/cuentas_demo.json. Recuperá el archivo de accesos antes de crear otras credenciales.")
        accounts = {user: secrets.token_urlsafe(18) for _, _, _, user in CAMPUS}
        # os.open fija los permisos antes de escribir credenciales.
        with os.fdopen(os.open(access_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as stream:
            json.dump(accounts, stream, indent=2)

    sql("central", (ROOT / "integracion/01_central.sql").read_text())
    views = (ROOT / "integracion/02_vistas.sql").read_text()
    for node in ("central", *(item[1] for item in CAMPUS)):
        sql(node, views)
        print(f"{node}: ocho vistas globales configuradas")

    for campus_id, node, schema, user in CAMPUS:
        password = accounts[user]
        for target in ("central", node):
            # Son nombres fijos del contrato, no entradas de la interfaz.
            exists = sql(target, f"SELECT count(*) FROM pg_roles WHERE rolname={literal(user)};")
            if exists == "0":
                sql(target, f'CREATE ROLE "{user}" LOGIN PASSWORD {literal(password)};')
        sql("central", f'''INSERT INTO sigtec_auth.usuarios(usuario,campus_id) VALUES ({literal(user)},{campus_id})
            ON CONFLICT (usuario) DO NOTHING;
            GRANT USAGE ON SCHEMA sigtec_auth TO "{user}";
            GRANT EXECUTE ON FUNCTION sigtec_auth.perfil_actual() TO "{user}";''')
        sql(node, f'''GRANT USAGE ON SCHEMA public, sigtec_qgis, cartago, san_jose, san_carlos, alajuela, limon TO "{user}";
            GRANT SELECT ON ALL TABLES IN SCHEMA cartago,san_jose,san_carlos,alajuela,limon TO "{user}";
            GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA sigtec_qgis TO "{user}";
            GRANT INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA "{schema}" TO "{user}";
            GRANT USAGE,SELECT ON SEQUENCE "{schema}".seq_id_global TO "{user}";
            GRANT SELECT ON public.campus,public.nodo_local TO "{user}";''')
        print(f"{node}: permisos de campus para {user}")
    instructions = local / "acceso_qgis.txt"
    text = "CUENTAS LOCALES DE DEMOSTRACIÓN — SIG-TEC\nNo son cuentas institucionales del TEC.\n\n"
    for campus_id, node, _, user in CAMPUS:
        text += f"Campus: {node} ({campus_id})\nUsuario: {user}\nContraseña: {accounts[user]}\n\n"
    with os.fdopen(os.open(instructions, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as stream:
        stream.write(text)
    print(f"Accesos guardados en {instructions}; no se imprimen contraseñas.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit("Falló una operación SQL: " + error.stderr) from None
