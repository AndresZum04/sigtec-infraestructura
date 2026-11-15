# Verificación de la entrega de Kay · v1.0.0

## Cierre individual v1.0.0 — 15 de noviembre de 2026

El contrato v1 se validó contra las seis bases. La entrega añade seis pruebas
de fuentes, además de las 11 funcionales y las cuatro de distribución.
Las geometrías vacías se rechazan y se comprueban los rangos de ids.
La configuración evita vistas duplicadas y el cambio de filtro revierte
el conjunto si alguna capa no puede aplicarlo. Los campus sin objetos propios
muestran los datos institucionales disponibles.

El flujo de GitHub Actions comprueba fuentes y construye paquetes; las pruebas
funcionales reales se acreditan con las ejecuciones locales adjuntas.

## Integración conjunta con Andrés — 15 de noviembre de 2026

Se añadió un procedimiento único `bash sigtec.sh preparar` y un paquete que
incluye los archivos originales de Andrés y el complemento. La preparación se
ejecutó sobre el entorno existente y conservó sus datos y estilos.

- Seis nodos con 40 tablas, ocho vistas y ocho estilos cada uno.
- Los seis nodos coinciden en los 358 objetos de referencia.
- Las 11 pruebas funcionales pasan desde `bash sigtec.sh verificar`:
  [`pruebas_sistema_integrado.txt`](pruebas_sistema_integrado.txt).
- Cuatro pruebas del ZIP pasan, incluida la resolución de rutas Compose al
  extraerlo en otra carpeta: [`pruebas_paquete_integrado.txt`](pruebas_paquete_integrado.txt).
- Se generaron respaldos integrados del central y San Carlos, usando el script
  original de Andrés y agregando roles. Sus dumps contienen los objetos del
  complemento y sus respaldos físicos pasan `pg_verifybackup`.
- Evidencia de configuración: [`integracion_andres_estado.json`](integracion_andres_estado.json).
- Procedencia del código: [`infraestructura_origen.json`](infraestructura_origen.json).

No se ejecutó una restauración destructiva ni una prueba nueva de PITR o caída
de nodo. Ver [procedimiento conjunto](INTEGRACION_ANDRES.md).

Entorno: Mac Apple Silicon, Docker Desktop, QGIS LTR 3.44.15, PostgreSQL 16 y
PostGIS 3.4. Pruebas realizadas durante esta sesión de trabajo en noviembre de 2026.

## Resultado automatizado

**11 pruebas de integración aprobadas**. Salida real en
[`pruebas_integracion.txt`](pruebas_integracion.txt).

| Prueba | Qué acredita |
|---|---|
| Autenticación y campus | Los cinco usuarios reciben su campus real y las ocho capas; contraseña inválida y campos vacíos se rechazan |
| Configuración y vistas | Se informa cuando faltan vistas, el nodo configurado es incorrecto o el servidor no responde; se validan identificadores |
| Capas y proyecto | Ocho vistas válidas en EPSG:5367, estilos desde la base, campos protegidos y proyecto sin contraseña |
| CRUD de ocho capas | Inserción, modificación y eliminación con PyQGIS, ids del campus y propagación a los otros campus a través del central |
| Escritura ajena | Se rechazan UPDATE/DELETE ajenos, INSERT en otro campus, cambio de id/campus y escritura directa en una copia de otro campus |
| Geometría | Se rechaza un polígono autointersectado |
| Ediciones y capas propias | Recarga/cierre no descartan ediciones pendientes y se conservan capas ajenas, incluso dentro de un grupo de SIG-TEC |
| Interfaz y tareas | Inicio asíncrono, recuperación de un error de contraseña, filtro, actualización sin duplicados y cierre de sesión |
| Estilos | El contenido predeterminado es idéntico en los cinco campus; la cuenta de campus no puede borrarlo |
| Catálogo central | La cuenta de usuario no puede consultar el catálogo completo de asignaciones |
| Usuario inactivo | Una cuenta real de PostgreSQL sin asignación activa no ingresa |

Los mensajes de Qt sobre `propagateSizeHints` o `raise` corresponden al entorno
sin pantalla de las pruebas. Se comprobó adicionalmente la interfaz nativa.

## Comprobaciones adicionales

- Los seis nodos presentan los mismos conteos por capa: ver
  [`conteos_verificados.json`](conteos_verificados.json).
- Hay 358 objetos de referencia de San Carlos, con ids y procedencia OSM.
- Los ocho estilos están almacenados en el central y copiados por replicación.
- Repetir la instalación SQL conserva roles y datos existentes.
- Repetir la importación agregó cero objetos; reconoció los 358 ya importados.
- El repositorio original de Andrés permanece sin modificaciones de archivos.
- El complemento se instaló y activó en el perfil real de QGIS; se observó el
  ingreso de `kay` y su sesión de San Carlos con ocho vistas.
- La ventana se revisó con el tema oscuro de Mac y se ajustó su contraste.
- El paquete se inspecciona, incluidos ZIP y QGZ anidados, para excluir las
  contraseñas locales generadas.

## Reproducir

Con la infraestructura, el contrato y los estilos instalados:

```sh
QT_QPA_PLATFORM=offscreen /Applications/QGIS-LTR.app/Contents/MacOS/python pruebas/test_integracion.py
```

El script utiliza cuentas locales y elimina sus objetos temporales. Consume
identificadores de secuencia. No trunca tablas ni reemplaza objetos geográficos
reales del campus. Para preparar este entorno desde cero, seguir el README.

## Límites

- La validación de escritorio se realizó en Mac; Windows/Linux requieren su
  propia comprobación de instalación y rutas de QGIS.
- Los datos son comunitarios, con atributos desconocidos y capas vacías de
  iluminación y accesibilidad. Requieren validación y captura del campus.
- Las pruebas no acreditan 2PC, PITR, recuperación de un nodo, resistencia a
  particiones de red, alta concurrencia ni un despliegue institucional.
- El contrato SQL de referencia debe coordinarse con Brady antes de fusionar
  implementaciones. La recuperación integral debe incluir roles, vistas,
  permisos, procedencia y la distribución de estilos.
- El guion del video está preparado; el video integral del equipo no se grabó.
