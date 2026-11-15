# Interfaz geográfica y complemento PyQGIS

## Objetivo y alcance

La interfaz SIG-TEC permite autenticarse contra el nodo central, obtener el campus
asignado, conectarse a su nodo operativo y cargar ocho capas institucionales en
el proyecto QGIS actual. El usuario consulta todos los campus y modifica solamente
los objetos del campus autorizado. El campus inicial de trabajo y carga de datos
de referencia es San Carlos.

La infraestructura base de Docker, PostgreSQL/PostGIS y replicación proviene del
repositorio de Andrés. El complemento, estilos, formularios y pruebas se encuentran
en la carpeta de trabajo de Kay. Como no había un contrato de vistas y acceso
disponible, se implementó un adaptador SQL separado en `integracion/` que debe
coordinarse con la implementación de Brady.

## Flujo de acceso

La ventana presenta usuario, contraseña y botón de ingreso. Una tarea de QGIS
realiza las consultas de autenticación fuera del hilo de interfaz; la creación
de capas y widgets ocurre en el hilo principal, siguiendo las recomendaciones
de la documentación de PyQGIS [1].

Las credenciales se validan abriendo una conexión real con PostgreSQL central.
La función `sigtec_auth.perfil_actual()` devuelve el campus del usuario autenticado
sin exponer el catálogo completo de cuentas. El complemento conecta a su nodo y
comprueba su identidad mediante `public.campus_local()`.

Las credenciales se mantienen en memoria para la sesión y el mecanismo de
conexiones de QGIS. No se escriben en la configuración del complemento ni en las
fuentes del proyecto. Los accesos generados para la demostración se guardan en un
archivo local separado que se excluye de los paquetes de entrega.

## Capas, edición y formularios

Las vistas integran edificios, carreteras, aceras, parqueos, zonas verdes,
puntos de interés, iluminación y accesibilidad. Todas declaran geometrías en
EPSG:5367. Se utiliza `id` como clave única y `campus_id` como pertenencia.

Los formularios presentan alias legibles y controles numéricos, protegen campos
automáticos y calculan áreas. Los campos desconocidos se pueden dejar nulos cuando
lo admite el modelo; edificios y puntos de interés requieren nombre.

La restricción de escritura se verifica en PostgreSQL, mediante permisos por
esquema y disparadores `INSTEAD OF` sobre las vistas. Los intentos de modificar
objetos ajenos, mover su campus o cambiar su identificador son rechazados. Esta
protección continúa aplicándose aunque se quite el filtro de visualización de
QGIS. El complemento conserva las ediciones pendientes al intentar cerrar sesión
o recargar las capas.

## Estilos institucionales

Se definió una simbología común por tema y etiquetas para los nombres conocidos.
Los estilos incluyen configuración de formularios y se guardan como QML para su
respaldo. QGIS proporciona el mecanismo nativo de almacenamiento en la tabla
`layer_styles` [2].

Los ocho estilos predeterminados se almacenan en el central y se distribuyen
mediante una publicación lógica dedicada y una suscripción por campus. El
complemento aplica el QML recibido desde su nodo. Si el estilo no está disponible,
utiliza el archivo incluido en el complemento. La cuenta de campus consulta
estilos; su publicación corresponde al administrador.

## Datos de referencia

Se descargó un conjunto acotado de datos vectoriales de OpenStreetMap para el
campus identificado por `way/351554216`. Se importaron 358 objetos: 61 edificios,
29 carreteras, 231 recorridos peatonales, 22 parqueos, una zona verde y 14 puntos
de interés. Las geometrías fueron transformadas de EPSG:4326 a EPSG:5367.

La procedencia registra los identificadores OSM, versiones, fecha de la fuente y
hash del archivo original. La fuente comunitaria se distribuye con atribución y
referencia a su licencia ODbL [3]. La ubicación en Santa Clara corresponde a la
descripción pública del campus del TEC [4].

Esta carga no constituye un inventario oficial. No se inventaron luminarias,
rampas, pisos, condiciones o capacidades ausentes en la fuente. Iluminación y
accesibilidad están disponibles para digitalizar, pero no tienen objetos reales
cargados. Sus operaciones se comprobaron con geometrías temporales de prueba.

## Validación

Las pruebas comprueban el acceso de los cinco campus, las ocho vistas y estilos,
las operaciones de edición con PyQGIS, la replicación de cambios, el rechazo de
escrituras ajenas y geometrías inválidas, y el tratamiento de sesiones y errores.
Los resultados reproducibles y sus límites se presentan en `docs/VERIFICACION.md`.
También se verificó la ventana del complemento y el ingreso de Kay en la
aplicación QGIS LTR instalada en Mac.

La recuperación de fallos y las transacciones distribuidas requieren una
demostración integral del equipo. Esta validación de la interfaz no acredita por
sí sola el funcionamiento de 2PC ni de los mecanismos de recuperación.

## Referencias

1. QGIS Project. *PyQGIS Developer Cookbook: Tasks*. https://github.com/qgis/QGIS-Documentation/blob/master/docs/pyqgis_developer_cookbook/tasks.rst
2. QGIS Project. *QGIS User Guide: Storing Styles in a File or a Database*. https://github.com/qgis/QGIS-Documentation/blob/master/docs/user_manual/introduction/general_tools.rst
3. OpenStreetMap Foundation. *Copyright and License*. https://www.openstreetmap.org/copyright
4. Tecnológico de Costa Rica. *Campus Tecnológico Local San Carlos*. https://tec.ac.cr/campus-tecnologico-local-san-carlos
5. Andrés. *SIG-TEC: infraestructura*. https://github.com/AndresZum04/sigtec-infraestructura

La implementación de esta carpeta se elaboró con asistencia de Codex. Las
fuentes externas utilizadas se identifican en las referencias y en la procedencia
de datos; la infraestructura original se conserva como dependencia separada.
