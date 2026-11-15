# Datos de referencia de San Carlos

Fuente: **© OpenStreetMap contributors**, licencia [ODbL](https://www.openstreetmap.org/copyright).
El campus se identifica por [way/351554216](https://www.openstreetmap.org/way/351554216).
La ubicación en Santa Clara coincide con la [descripción del TEC](https://tec.ac.cr/campus-tecnologico-local-san-carlos).

El JSON original está en `fuentes/`; `procedencia_san_carlos.json` conserva el hash
del archivo, la fecha del snapshot y la correspondencia entre cada objeto
importado y el identificador original de OSM. Las etiquetas del JSON pueden
incluir nombres públicos de colaboradores de OSM, como parte de sus metadatos.

## Contenido importado

| Capa | Objetos |
|---|---:|
| Edificios | 61 |
| Carreteras | 29 |
| Aceras y recorridos peatonales | 231 |
| Parqueos | 22 |
| Zonas verdes | 1 |
| Puntos de interés | 14 |
| Iluminación | 0 |
| Accesibilidad | 0 |
| Total | 358 |

Es una base comunitaria para trabajar, no un inventario oficial del TEC.
Los nombres genéricos `Edificio OSM <id>` indican que la fuente no proporciona
un nombre. No se asignan nombres institucionales inventados.

Las vías OSM `footway`, `pedestrian`, `path`, `steps` y `corridor` se clasificaron
en la capa lineal de aceras/recorridos. Esto no certifica que cada tramo sea una
acera exterior ni que tenga condiciones de accesibilidad. Algunos corredores
están dentro de edificios y pueden superponerse en una representación 2D.

Los puntos de interés procedentes de polígonos usan un punto representativo
calculado; la descripción del objeto lo indica. Las geometrías se transforman
de EPSG:4326 a EPSG:5367. Las áreas son calculadas, no medidas en campo.

No se deducen luminarias ni rampas a partir de imágenes. Tampoco se inventan
pisos, materiales, potencia, estado, capacidad o espacios disponibles.
Los campos desconocidos quedan nulos.

## Completar la digitalización

1. Validar nombres y uso de los edificios con información del campus.
2. Revisar las vías y diferenciar aceras, escaleras y corredores.
3. Levantar luminarias con su código, potencia y estado cuando se conozcan.
4. Identificar rampas y rutas accesibles usando una fuente verificable.
5. Completar capacidad y disponibilidad de parqueos solo con datos reales.

Las ocho capas admiten edición desde QGIS. Las dos capas vacías se probaron
con objetos sintéticos temporales que se eliminaron al terminar las pruebas.

`scripts/importar_osm.py` no duplica objetos ni sobrescribe ediciones al repetirse.
El registro auxiliar `sigtec_importacion.origen` está en el nodo de San Carlos;
no pertenece a la replicación geográfica de Andrés y debe incluirse en un
respaldo completo del nodo. Si se borra un objeto importado, ejecutar de nuevo
el importador no lo resucita automáticamente.
