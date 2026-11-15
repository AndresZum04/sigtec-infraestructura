# Integración de Andrés + Kay

La infraestructura y el complemento utilizan **las mismas seis instancias** de
PostgreSQL/PostGIS. No hay una segunda base independiente para QGIS.

## Código incluido

`infraestructura/` contiene los archivos originales del repositorio de Andrés.
`docs/infraestructura_origen.json` identifica el commit y el hash de cada archivo.
Los ajustes locales y la integración están fuera de esa carpeta.

El paquete conjunto es `dist/SIGTEC_Andres_Kay_integrado.zip`. Ya incluye el código
de infraestructura: no requiere clonarlo por separado al descomprimirlo.
Se excluyen `.git`, credenciales locales, volúmenes, WAL y respaldos.

## Un solo procedimiento

Con Docker Desktop abierto y QGIS instalado, desde la carpeta del paquete:

```sh
bash sigtec.sh preparar
```

El comando realiza, en orden:

1. Inicia el Compose de Andrés, espera las bases e identifica cada nodo.
2. Crea la replicación geográfica original si no está configurada.
3. Aplica el contrato de acceso, vistas y permisos del complemento.
4. Asegura `layer_styles` y su replicación, conservando estilos existentes.
5. Importa la referencia OSM sin duplicar ni sobrescribir objetos ya importados.
6. Copia el complemento al perfil local y comprueba los seis nodos.

`preparar` admite `--sin-datos`, `--sin-instalar` y
`--qgis-python /ruta/al/python-de-QGIS`. En Mac detecta QGIS LTR automáticamente.
En Windows se ejecuta desde Git Bash, con Python 3 disponible; cuando haga falta,
indicar el Python de QGIS desde su entorno configurado.

Después se puede usar:

```sh
bash sigtec.sh iniciar
bash sigtec.sh estado
bash sigtec.sh verificar
bash sigtec.sh detener
```

`iniciar` y `detener` conservan los volúmenes. `estado` comprueba identidad,
tablas, vistas, suscripciones, estilos y conteos. `verificar` ejecuta además las
11 pruebas reales de QGIS. No se ejecutan `down -v`, truncados o restauraciones
durante estos comandos.

## Relación de componentes

| Infraestructura de Andrés | Integración de Kay |
|---|---|
| `central:5440`, base `sigtec` | Autenticación y origen de los estilos |
| `sancarlos:5443`, base `sigtec` | Conexión del usuario `kay` a sus ocho vistas |
| Cinco esquemas y ocho tablas por esquema | Vistas globales `sigtec_qgis.<tema>` |
| `public.campus_local()` | Comprobación del nodo y restricción de edición |
| Secuencias globales por campus | Generación de ids al digitalizar |
| Replicación campus → central → otros campus | Difusión de los cambios hechos desde QGIS |
| Scripts de respaldo lógico y físico | Respaldo de roles y catálogo de objetos de QGIS |

Las vistas y funciones no se replican con la replicación lógica de tablas:
el preparador las instala en cada nodo. Las geometrías siguen almacenadas en
las tablas originales; se escriben desde las vistas con los disparadores de
integración. `public.layer_styles` usa una publicación dedicada para evitar
cambiar las publicaciones geográficas originales.

## Respaldar el sistema integrado

```sh
bash sigtec.sh respaldar central
bash sigtec.sh respaldar sancarlos
```

Admite los seis nombres de nodo. Cada ejecución invoca `respaldo.sh` de Andrés
(lógico completo, esquema propio cuando corresponda y físico), y añade:

- `roles_<fecha>.sql`, generado mediante `pg_dumpall --globals-only`.
- `integrado_<fecha>.json`, con el listado y alcance de ese respaldo.

El dump lógico completo contiene los esquemas de autenticación, vistas,
funciones, permisos, estilos y, en San Carlos, la procedencia de importación.
Los roles son objetos del clúster, por eso se respaldan separadamente.
El archivo de roles tiene permisos 600 y contiene verificadores de contraseña;
permanece en `infraestructura/respaldos/<nodo>/` y se excluye de los ZIP.

En una restauración lógica a un clúster vacío, restaurar primero los roles y
después la base. Para PITR o reconstrucción de un nodo, seguir el procedimiento
de Andrés, revisar suscripciones/slots y reaplicar el contrato QGIS mediante
`preparar`. Los scripts de resincronización originales pueden truncar copias;
se ejecutan como una operación de recuperación explícita, nunca al iniciar QGIS.

Este trabajo verifica la creación y contenido de los respaldos añadidos. No
equivale a una nueva prueba integral de PITR ni de caída de un nodo. El equipo
debe realizar esa demostración con la versión final del proyecto.

## Límite de esta integración

El adaptador SQL de vistas y autenticación sigue separado para coordinarlo con
Brady. La integración con Andrés está operativa; esto no implementa 2PC ni
convierte los datos OSM en un inventario oficial del campus.
