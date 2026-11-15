"""Configuración de conexiones; nunca almacena contraseñas."""
import copy
import json
import re
from pathlib import Path

THEMES = ("edificios", "carreteras", "aceras", "parqueos", "zonas_verdes", "puntos_interes", "iluminacion", "accesibilidad")
IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def validate(config):
    value = copy.deepcopy(config)
    if value.get("version") != 1:
        raise ValueError("Versión de configuración no compatible.")
    for key in ("auth_schema", "auth_function", "view_schema", "geometry_column", "key_column"):
        if not IDENTIFIER.fullmatch(value.get(key, "")):
            raise ValueError(f"Identificador inválido: {key}.")
    if set(value.get("views", {})) != set(THEMES):
        raise ValueError("Se requieren las ocho vistas temáticas.")
    if any(not IDENTIFIER.fullmatch(v) for v in value["views"].values()):
        raise ValueError("Nombre de vista inválido.")
    if len(set(value["views"].values())) != len(THEMES):
        raise ValueError("Cada tema debe usar una vista distinta.")
    if set(value.get("campuses", {})) != {str(i) for i in range(1, 6)}:
        raise ValueError("Se requieren los cinco nodos de campus.")
    for endpoint in [value["central"], *value["campuses"].values()]:
        if not isinstance(endpoint.get("host"), str) or not endpoint["host"].strip():
            raise ValueError("El host es obligatorio.")
        endpoint["port"] = int(endpoint["port"])
        if not 1 <= endpoint["port"] <= 65535:
            raise ValueError("Puerto inválido.")
        if not endpoint.get("database"):
            raise ValueError("La base de datos es obligatoria.")
        if endpoint.get("sslmode", "prefer") not in ("disable", "allow", "prefer", "require", "verify-ca", "verify-full"):
            raise ValueError("Modo SSL inválido.")
        if any(k in endpoint for k in ("password", "user")):
            raise ValueError("Las credenciales se ingresan en la ventana de acceso.")
    value["timeout"] = max(2, min(15, int(value.get("timeout", 5))))
    return value


def defaults():
    return validate(json.loads(Path(__file__).with_name("config.json").read_text()))


def load(path=None):
    if path and Path(path).exists():
        return validate(json.loads(Path(path).read_text()))
    return defaults()


def save(path, config):
    value = validate(config)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(destination)
