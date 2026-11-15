"""Valida el contrato v1 contra los seis nodos sin modificar datos."""
import json
from pathlib import Path
import re
import sys

from sistema import NODES, sql

ROOT = Path(__file__).resolve().parents[1]


def validate_contract():
    contract = json.loads((ROOT / "integracion/contrato_v1.json").read_text())
    if contract["version"].split(".")[0] != "1":
        raise RuntimeError("Versión de contrato no soportada por este validador.")
    schema = contract["esquema_vistas"]
    identifiers = [schema, *contract["vistas"]]
    if not all(re.fullmatch(r"[a-z_][a-z0-9_]*", name) for name in identifiers):
        raise RuntimeError("El contrato contiene un identificador SQL inválido.")
    errors, report = [], {}
    for node in NODES:
        report[node] = {}
        for theme, definition in contract["vistas"].items():
            actual = json.loads(sql(node, f"""SELECT coalesce(json_agg(json_build_object(
                'nombre',a.attname,'tipo',format_type(a.atttypid,a.atttypmod)) ORDER BY a.attnum),'[]'::json)
                FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname='{schema}' AND c.relname='{theme}' AND c.relkind='v'
                AND a.attnum>0 AND NOT a.attisdropped;"""))
            if actual != definition["columnas"]:
                errors.append(f"{node}/{theme}: columnas o tipos incompatibles")
                continue
            quality = json.loads(sql(node, f"""SELECT json_build_object(
                'objetos',count(*),'ids_unicos',count(DISTINCT id),
                'geometrias_invalidas',count(*) FILTER(WHERE geom IS NULL OR ST_IsEmpty(geom) OR NOT ST_IsValid(geom) OR ST_SRID(geom)<>5367),
                'campus_invalidos',count(*) FILTER(WHERE campus_id IS NULL OR campus_id NOT BETWEEN 1 AND 5),
                'ids_fuera_de_rango',count(*) FILTER(WHERE id NOT BETWEEN campus_id::bigint*1000000+1 AND campus_id::bigint*1000000+999999))
                FROM {schema}.{theme};"""))
            if quality["objetos"] != quality["ids_unicos"] or quality["geometrias_invalidas"] or quality["campus_invalidos"] or quality["ids_fuera_de_rango"]:
                errors.append(f"{node}/{theme}: datos que incumplen el contrato")
            report[node][theme] = quality
        if node != "central":
            triggers = sql(node, f"""SELECT count(DISTINCT c.relname) FROM pg_trigger t
                JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname='{schema}' AND NOT t.tgisinternal
                AND (t.tgtype::integer & 64)=64 AND (t.tgtype::integer & 28)=28;""")
            if triggers != "8":
                errors.append(f"{node}: faltan disparadores INSTEAD OF de edición")
    function = sql("central", """SELECT coalesce((SELECT pg_get_function_result(p.oid)
        FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
        WHERE n.nspname='sigtec_auth' AND p.proname='perfil_actual' AND p.pronargs=0),'');""")
    if function != "TABLE(campus_id smallint, nombre text, esquema text)":
        errors.append("central: firma de perfil_actual() incompatible")
    result = {"contrato": contract["version"], "correcto": not errors, "problemas": errors, "nodos": report}
    if errors:
        raise RuntimeError("Contrato incumplido:\n- " + "\n- ".join(errors))
    print(f"Contrato {contract['version']}: 6/6 nodos, ocho vistas compatibles por nodo, geometrías e ids válidos.")
    return result


if __name__ == "__main__":
    try:
        result = validate_contract()
        if "--guardar" in sys.argv:
            (ROOT / "docs/contrato_verificado.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (RuntimeError, KeyError, ValueError) as error:
        raise SystemExit(str(error)) from None
