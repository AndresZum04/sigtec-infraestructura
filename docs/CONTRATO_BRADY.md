# Contrato de integración SIG-TEC · v1.0.0

**Estado:** definido e implementado para la entrega de Kay.  
**Fuente verificable:** [`integracion/contrato_v1.json`](../integracion/contrato_v1.json).  
**Comprobación:** `bash sigtec.sh contrato`.

Este contrato permite a Brady continuar sobre una interfaz estable. La
implementación de vistas y disparadores entregada ya funciona; puede conservarla
o sustituir su interior sin cambiar las operaciones que consume el complemento.
No requiere redefinir el inicio de sesión ni rehacer las capas de QGIS.

## 1. Topología y pertenencia

Base: `sigtec`. Central de autenticación/coordinación: `localhost:5440`.
El central es distinto del nodo del Campus Central Cartago.

| campus_id | Campus | Servicio Docker | Esquema propietario | Puerto host | Rango de ids |
|---|---|---|---|---:|---|
| 1 | Cartago | `cartago` | `cartago` | 5441 | 1000001–1999999 |
| 2 | San José | `sanjose` | `san_jose` | 5442 | 2000001–2999999 |
| 3 | San Carlos | `sancarlos` | `san_carlos` | 5443 | 3000001–3999999 |
| 4 | Alajuela | `alajuela` | `alajuela` | 5444 | 4000001–4999999 |
| 5 | Limón | `limon` | `limon` | 5445 | 5000001–5999999 |

Dentro de Docker se usan los nombres de servicio y el puerto 5432; QGIS usa el
host/puerto configurado. Los puertos y hosts pueden cambiarse desde la ventana
Configurar conexiones. El campus se obtiene del central, no de una elección libre
hecha por el usuario.

## 2. Autenticación

1. El complemento abre una conexión real al central con usuario y contraseña.
2. PostgreSQL autentica ese rol.
3. Ejecuta la función sin parámetros:

```sql
SELECT campus_id, nombre, esquema FROM sigtec_auth.perfil_actual();
```

| Resultado | Significado y comportamiento |
|---|---|
| Una fila `(smallint, text, text)` | Campus autorizado; continuar al nodo configurado |
| Cero filas | Cuenta sin asignación activa; rechazar el acceso |
| Error de autenticación | Credenciales inválidas; permitir reintentar |
| Más de una fila | Contrato incompatible; rechazar el acceso |

La función de referencia es `STABLE SECURITY DEFINER`, tiene `search_path` fijo
 y usa `session_user`, el rol realmente autenticado. El usuario no tiene lectura
sobre el catálogo completo `sigtec_auth.usuarios`. El mismo rol y contraseña deben
existir en el central y en su nodo propietario. Las cuentas de demostración se
generan por instalación y se conservan en `.local/`; no se publican.

El complemento valida `public.campus_local()` en el nodo y comprueba que devuelve
el mismo `campus_id`. Una cuenta no puede escoger otro campus alterando un filtro.
Los errores de conexión se presentan sin registrar contraseñas o cadenas completas.

## 3. Vistas geográficas

Se requieren ocho vistas ordinarias en `sigtec_qgis`, con una fila por objeto y
un identificador único. Las columnas que siguen son la interfaz v1; la
implementación interna puede usar las tablas de Andrés u otra estrategia que
conserve el resultado. Las geometrías son de una sola parte y usan EPSG:5367.

### `sigtec_qgis.edificios`

| Columna | Tipo PostgreSQL |
|---|---|
| `id` | `bigint` |
| `campus_id` | `smallint` |
| `creado_en` | `timestamp with time zone` |
| `modificado_en` | `timestamp with time zone` |
| `codigo` | `character varying(20)` |
| `nombre` | `character varying(120)` |
| `area_m2` | `numeric(12,2)` |
| `pisos` | `smallint` |
| `geom` | `geometry(Polygon,5367)` |

### `sigtec_qgis.carreteras`

| Columna | Tipo PostgreSQL |
|---|---|
| `id` | `bigint` |
| `campus_id` | `smallint` |
| `creado_en` | `timestamp with time zone` |
| `modificado_en` | `timestamp with time zone` |
| `nombre` | `character varying(120)` |
| `tipo` | `character varying(40)` |
| `superficie` | `character varying(40)` |
| `geom` | `geometry(LineString,5367)` |

### `sigtec_qgis.aceras`

| Columna | Tipo PostgreSQL |
|---|---|
| `id` | `bigint` |
| `campus_id` | `smallint` |
| `creado_en` | `timestamp with time zone` |
| `modificado_en` | `timestamp with time zone` |
| `material` | `character varying(40)` |
| `ancho_m` | `numeric(5,2)` |
| `condicion` | `character varying(20)` |
| `geom` | `geometry(LineString,5367)` |

### `sigtec_qgis.parqueos`

| Columna | Tipo PostgreSQL |
|---|---|
| `id` | `bigint` |
| `campus_id` | `smallint` |
| `creado_en` | `timestamp with time zone` |
| `modificado_en` | `timestamp with time zone` |
| `nombre` | `character varying(120)` |
| `capacidad` | `integer` |
| `tipo` | `character varying(40)` |
| `espacios_disponibles` | `integer` |
| `geom` | `geometry(Polygon,5367)` |

### `sigtec_qgis.zonas_verdes`

| Columna | Tipo PostgreSQL |
|---|---|
| `id` | `bigint` |
| `campus_id` | `smallint` |
| `creado_en` | `timestamp with time zone` |
| `modificado_en` | `timestamp with time zone` |
| `nombre` | `character varying(120)` |
| `area_m2` | `numeric(12,2)` |
| `tipo_vegetacion` | `character varying(60)` |
| `geom` | `geometry(Polygon,5367)` |

### `sigtec_qgis.puntos_interes`

| Columna | Tipo PostgreSQL |
|---|---|
| `id` | `bigint` |
| `campus_id` | `smallint` |
| `creado_en` | `timestamp with time zone` |
| `modificado_en` | `timestamp with time zone` |
| `nombre` | `character varying(120)` |
| `tipo` | `character varying(40)` |
| `descripcion` | `text` |
| `geom` | `geometry(Point,5367)` |

### `sigtec_qgis.iluminacion`

| Columna | Tipo PostgreSQL |
|---|---|
| `id` | `bigint` |
| `campus_id` | `smallint` |
| `creado_en` | `timestamp with time zone` |
| `modificado_en` | `timestamp with time zone` |
| `codigo` | `character varying(20)` |
| `potencia_w` | `integer` |
| `estado` | `character varying(20)` |
| `geom` | `geometry(Point,5367)` |

### `sigtec_qgis.accesibilidad`

| Columna | Tipo PostgreSQL |
|---|---|
| `id` | `bigint` |
| `campus_id` | `smallint` |
| `creado_en` | `timestamp with time zone` |
| `modificado_en` | `timestamp with time zone` |
| `tipo` | `character varying(40)` |
| `descripcion` | `text` |
| `geom` | `geometry(LineString,5367)` |

## 4. Reglas de edición y valores automáticos

| Operación | Regla obligatoria |
|---|---|
| SELECT | Consultar los cinco campus desde el nodo asignado |
| INSERT | Guardar en el esquema del campus local; rechazar otro campus |
| UPDATE | Editar solo objetos locales; no permitir cambiar id o campus |
| DELETE | Eliminar solo objetos locales |
| Geometría | Tipo de la capa, SRID 5367, válida y no vacía |

- `id` se genera con la secuencia global del campus. No se reutilizan ids borrados.
- `campus_id` se asigna al nodo autorizado y se mantiene inmutable.
- `creado_en` se asigna al insertar y se conserva al actualizar.
- `modificado_en` se actualiza con el reloj del servidor al guardar.
- `area_m2` se calcula en PostgreSQL para edificios y zonas verdes.
- `nombre` es obligatorio en edificios y puntos de interés.
- Los controles originales de las tablas siguen aplicándose: pisos positivos,
  ids en rango, campus coherente y capacidades no negativas.
- Las ayudas adicionales del formulario, como disponibilidad menor o igual que
  capacidad, no sustituyen restricciones que el equipo decida añadir a la base.

La restricción se implementa en la base con `INSTEAD OF`; un filtro de QGIS solo
cambia la visualización. La implementación de referencia usa vistas con
`security_invoker=true`, consulta en los cinco esquemas y DML exclusivamente en
el esquema propietario. El rol del usuario no tiene DML en las copias ajenas.

Cada sentencia se ejecuta bajo las garantías transaccionales locales de
PostgreSQL. El contrato no declara que un búfer completo de edición QGIS sea una
transacción distribuida ni ofrece detección de todos los conflictos de concurrencia.

## 5. Errores esperados

| SQLSTATE | Situación |
|---|---|
| `42501` | Escritura ajena, cambio de identidad o permiso insuficiente |
| `23514` | Geometría inválida/vacía o restricción de datos incumplida |
| `23502` | Atributo obligatorio ausente |
| `23505` | Identificador duplicado |
| `40001` | Objeto que deja de existir durante la operación del disparador |

Ante un rechazo al guardar, QGIS muestra el error y el usuario corrige o descarta
el búfer pendiente. No se descartan ediciones al cambiar filtros, recargar capas
o cerrar sesión. Las capas independientes del usuario se conservan.

## 6. Estilos institucionales

`public.layer_styles` conserva el formato nativo de QGIS. La asociación de un
estilo predeterminado es: base `sigtec`, esquema `sigtec_qgis`, nombre de vista y
columna `geom`. Se espera un predeterminado por tema.

El administrador guarda estilos en el central; una publicación dedicada los
replica a cada campus. Los usuarios de campus solo consultan esa tabla.
El complemento aplica el QML del nodo y usa los QML del paquete como respaldo.
Las expresiones usan `@sigtec_campus_id`, asignado después de cargar el estilo.

```sh
# Conservar lo existente durante la preparación ordinaria:
bash sigtec.sh preparar
# Publicar deliberadamente una nueva edición del estilo v1, con Python de QGIS:
python scripts/publicar_estilos.py
```

Para conservar varias versiones hay que asignar nombres distintos y elegir
explícitamente el predeterminado. Cambiar el nombre de una vista requiere
mantener un alias compatible o volver a asociar y probar sus estilos.

## 7. Integración con la replicación y recuperación

Las escrituras de QGIS alcanzan las tablas originales del campus. La replicación
existente de Andrés las lleva al central y después a las copias de consulta.
Los cambios de DDL no se replican: las vistas, funciones y permisos se instalan
explícitamente en cada nodo.

Los respaldos conjuntos llaman el script de Andrés y añaden un dump de roles.
La reconstrucción de un nodo debe recuperar también autenticación, vistas,
permisos, estilos y procedencia. Después de PITR o resincronización se revisan
slots/suscripciones y se reaplica la preparación. No se ejecutan recuperaciones
ni truncados desde el complemento.

## 8. Entrega y trabajo de Brady

| Kay entrega | Brady continúa |
|---|---|
| Complemento, formularios, estilos, contrato y pruebas | Integrar transacciones distribuidas/2PC |
| Vistas/disparadores funcionales de referencia | Conservarlos o adaptar su implementación manteniendo v1 |
| Integración con la infraestructura de Andrés | Coordinar con Andrés la recuperación de la versión final |
| Manual y sección del informe | Añadir su diseño, pruebas y documentación al informe grupal |

La grabación del video se pospone por solicitud de Kay. No bloquea la entrega de
estos fuentes y del contrato para que Brady avance.

## 9. Aceptación y evolución

```sh
bash sigtec.sh estado
bash sigtec.sh contrato
bash sigtec.sh verificar
```

La entrega se considera compatible cuando los seis nodos cumplen tipos y
columnas de v1, las ocho geometrías son válidas, el inicio de sesión identifica
el campus correcto, las operaciones locales se replican y las ajenas se rechazan.

Los cambios internos compatibles pueden publicarse sin cambiar esta interfaz.
Renombrar o eliminar columnas, cambiar tipos, SRID o la firma de autenticación
requiere un contrato mayor nuevo o vistas de compatibilidad. Los cambios se
registran en `CHANGELOG.md` y se prueban antes de fusionar.
