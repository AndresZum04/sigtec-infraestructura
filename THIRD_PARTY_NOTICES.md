# Procedencia y atribuciones

| Componente | Fuente | Tratamiento |
|---|---|---|
| Infraestructura PostgreSQL/PostGIS | https://github.com/AndresZum04/sigtec-infraestructura | Archivos originales de Andrés; commit y hashes en `docs/infraestructura_origen.json` |
| Datos del campus | © OpenStreetMap contributors | ODbL; fuente, identificadores y hash en `datos/procedencia_san_carlos.json` |
| QGIS/PyQGIS | https://qgis.org/ | Dependencia instalada; documentación de APIs citada en el informe |
| PostgreSQL/PostGIS/Docker | Distribuciones originales | Dependencias externas; no se redistribuyen imágenes o ejecutables en este repositorio |

Los datos derivados de OpenStreetMap se acompañan de atribución y de su licencia:
https://www.openstreetmap.org/copyright y https://opendatacommons.org/licenses/odbl/1-0/.
Las consultas OSM son acotadas al campus y se conservan para reproducibilidad.

Este repositorio no atribuye a Kay la infraestructura original de Andrés.
La implementación del complemento y los recursos de integración se elaboraron
con asistencia de Codex. La documentación identifica los límites de validación.

La publicación del material de trabajo del equipo no constituye una licencia
adicional sobre el código de terceros. Se conservan su procedencia y los avisos
incluidos por sus autores.
