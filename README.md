# SIG-TEC: infraestructura

Seis nodos PostgreSQL 16 + PostGIS 3.4 en Docker (un central y cinco campus), con replicación lógica en dos niveles, WAL archivado y scripts de respaldo y recuperación.

## Arrancar

Requisitos: Docker Desktop y Git Bash (en Windows).

```bash
docker compose up -d          # levanta los 6 nodos y crea las capas
bash scripts/replicacion.sh   # una sola vez, con todo arriba
bash scripts/conteos.sh       # cuántos edificios ve cada nodo de cada campus
```

Para empezar de cero: `docker compose down -v`, borrar `wal/` y `respaldos/`, y volver a arrancar.

## Nodos

| Nodo | Contenedor | campus_id | Esquema propio | Puerto |
|---|---|---|---|---|
| Central | sigtec-central | (ninguno) | (ninguno) | 5440 |
| Cartago | sigtec-cartago | 1 | cartago | 5441 |
| San José | sigtec-sanjose | 2 | san_jose | 5442 |
| San Carlos | sigtec-sancarlos | 3 | san_carlos | 5443 |
| Alajuela | sigtec-alajuela | 4 | alajuela | 5444 |
| Limón | sigtec-limon | 5 | limon | 5445 |

Base `sigtec`, usuario `postgres`, contraseña `sigtec2026`, host `localhost`. Es una contraseña de desarrollo local para el curso; no usarla en nada expuesto.

## Modelo

- Los 5 esquemas existen en **todos** los nodos con las mismas 8 capas: `edificios`, `carreteras`, `aceras`, `parqueos`, `zonas_verdes`, `puntos_interes`, `iluminacion`, `accesibilidad`.
- En cada campus solo se edita el esquema propio. Los otros cuatro son copias de consulta que llegan desde el central. **Escribir directo en una copia rompe la suscripción** con un conflicto de llave.
- Ids globales por rango: Cartago 1000001–1999999, San José 2000001–…, hasta Limón 5000001–5999999. Salen solos de `<esquema>.seq_id_global`. Un `CHECK` rechaza ids fuera de rango y otro rechaza un `campus_id` que no sea el del esquema.
- SRID 5367 (CRTM05). Las coordenadas en WGS84 se convierten con `ST_Transform(geom, 5367)`.
- `public.campus_local()` devuelve el campus del nodo (NULL en el central).

## Replicación

- Nivel 1: cada campus publica su esquema (`pub_<esquema>`) y el central se suscribe (`sub_desde_<esquema>`).
- Nivel 2: el central publica a cada campus los otros cuatro esquemas (`pub_global_para_<esquema>`) y el campus se suscribe (`sub_global_<esquema>`). Ningún campus recibe de vuelta su propio esquema, así que no hay ciclos.

## Scripts

| Script | Para qué |
|---|---|
| `scripts/replicacion.sh` | Crea las publicaciones y suscripciones de los dos niveles |
| `scripts/conteos.sh [tabla]` | Conteo por esquema en cada nodo (por defecto `edificios`) |
| `scripts/respaldo.sh <nodo>` | Respaldo lógico (`pg_dump`) y físico (`pg_basebackup`) en `respaldos/<nodo>/` |
| `scripts/restaurar_pitr.sh <nodo> <base_XXXX> "<instante+00>"` | Recuperación a un instante (PITR) con el WAL archivado |
| `scripts/resincronizar.sh <nodo>` | Rehace la replicación de un nodo después de un PITR |
| `scripts/recuperar_nodo.sh <nodo>` | Reconstruye un nodo perdido a partir de la copia del central |

## Para la Persona 2 (vistas, disparadores, 2PC)

- Las tablas reales están en `cartago`, `san_jose`, `san_carlos`, `alajuela` y `limon`, y existen en todos los nodos.
- `public.campus_local()` dice qué campus es el nodo.
- `max_prepared_transactions = 20` ya está activado para `PREPARE TRANSACTION`.
- `layer_styles`: QGIS crea la tabla la primera vez que se guarda un estilo en la base. Después se copia la estructura a los campus con `pg_dump -s -t public.layer_styles`, se crea `CREATE PUBLICATION pub_estilos FOR TABLE public.layer_styles;` en el central y se agrega una suscripción en cada campus.

## Para la Persona 3 (QGIS)

- Conexión: host `localhost`, puerto del campus, base `sigtec`, usuario `postgres`.
- Mientras no existan las vistas se puede digitalizar directo en `<esquema>.<capa>` del campus propio (por ejemplo `san_carlos.edificios` en el puerto 5443).
- El proyecto de QGIS va en EPSG:5367.

## Notas de Windows

- Los `.sh` tienen que quedar con fin de línea LF. El `.gitattributes` lo fuerza al clonar.
- Los scripts se corren desde Git Bash, en la raíz del repo.
- Si sale `the input device is not a TTY`, quitar la `-t` del `docker exec` o usar `winpty`.
