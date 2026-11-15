# Entrega individual de Kay · versión 1.0.0

Fecha: 15 de noviembre de 2026. Campus inicial: San Carlos.

## Alcance entregado

| Elemento | Estado | Evidencia |
|---|---|---|
| Complemento y acceso central | Implementado | Código y pruebas de interfaz y autenticación |
| Selección del campus | Implementado para cinco campus | Cuenta real y validación del nodo |
| Ocho capas globales | Implementado | Contrato v1 y geometrías EPSG:5367 |
| Edición local y consulta global | Implementado | Disparadores y pruebas de escrituras permitidas/ajenas |
| Estilos, etiquetas y formularios | Implementado | Ocho estilos distribuidos y QML de respaldo |
| Integración de infraestructura | Implementado | Arranque único y procedencia de los archivos de Andrés |
| Datos de referencia | Importación reproducible terminada | 358 objetos OSM con procedencia y auditoría geométrica |
| Manual y contrato para Brady | Entregados | README, contrato JSON, contrato técnico y guía de continuidad |
| Paquetes de distribución | Generables desde los fuentes | Scripts y SHA-256 |
| Video | Excluido de esta versión por solicitud de Kay | Guion preparado para la etapa grupal |

## Aceptación técnica

```sh
bash sigtec.sh estado
bash sigtec.sh contrato
bash sigtec.sh verificar
```

Los resultados y los límites se registran en `docs/VERIFICACION.md`. El contrato
es verificable por código; Brady puede sustituir la implementación conservando
la interfaz, sin tener que rehacer el complemento.

## Calidad y límites de los datos

La carga OSM constituye una referencia comunitaria, no un inventario oficial.
Se comprueban identificadores, campus, SRID, validez y geometrías no vacías.
No se inventan nombres, potencias, condiciones ni atributos desconocidos.
Iluminación y accesibilidad quedan vacías y editables; sus operaciones están
probadas. La captura de un inventario institucional requiere fuentes adicionales.

El enunciado no fija un número mínimo de objetos por capa. Esta entrega cubre
la interfaz y la administración de las ocho capas con datos de referencia
documentados; no certifica un levantamiento de campo.

## Continuidad del equipo

Brady recibe el contrato v1 y una implementación funcional de vistas/disparadores.
Su trabajo posterior es integrar las transacciones distribuidas / 2PC y mantener
la compatibilidad del contrato. El equipo debe cerrar la prueba integral de
recuperación, reunir sus secciones del documento y grabar el video final.

La entrega individual de software y documentación de Kay queda preparada para
esa integración. Este estado no declara terminado todo el proyecto grupal ni
anticipa la calificación del profesor.
