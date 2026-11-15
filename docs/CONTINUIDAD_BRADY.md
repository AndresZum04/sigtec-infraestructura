# Continuidad para Brady

**Punto de partida:** entrega de Kay v1.0.0, integrada con los seis nodos de Andrés.
El complemento y el contrato ya funcionan. Esta guía identifica el trabajo que
continúa y la forma de comprobar que QGIS sigue siendo compatible.

## 1. Preparar tu instalación

```sh
git clone --branch kay/qgis-v1 https://github.com/AndresZum04/sigtec-infraestructura.git
cd sigtec-infraestructura
bash sigtec.sh preparar
bash sigtec.sh contrato
bash sigtec.sh verificar
```

Se requieren Docker Desktop, QGIS LTR 3.44 con su Python y Bash actualizado.
El preparador genera tus propias cuentas locales. No se necesita el archivo de
contraseñas de Kay. Ver el README para rutas de Windows u otro perfil de QGIS.

## 2. Lo que ya recibís

| Recurso | Ubicación |
|---|---|
| Infraestructura de Andrés | `docker-compose.yml`, `init/` y los scripts originales |
| Implementación de autenticación | `integracion/01_central.sql` |
| Implementación de vistas/disparadores | `integracion/02_vistas.sql` |
| Contrato completo v1 | `docs/CONTRATO_BRADY.md` |
| Tipos y columnas verificables | `integracion/contrato_v1.json` |
| Cuentas y permisos por campus | `scripts/integrar_qgis.py` |
| Distribución de estilos | `scripts/publicar_estilos.py` |
| Complemento de Kay | `complemento/sigtec/` |
| Pruebas funcionales | `pruebas/test_integracion.py` |

Podés mantener el SQL entregado o sustituir su implementación interna. Conservá
las ocho vistas y la firma de perfil v1 para no cambiar el complemento.

## 3. Trabajo que continúa

- Implementar y demostrar las transacciones distribuidas / 2PC según el diseño
  del equipo; `max_prepared_transactions` ya está habilitado en los nodos.
- Documentar coordinador, participantes, decisión de commit/rollback, fallos y
  tratamiento de transacciones preparadas pendientes.
- Añadir pruebas propias de esa implementación; las pruebas actuales no la cubren.
- Coordinar con Andrés una recuperación integral que incluya roles, vistas,
  permisos y suscripciones de estilos.
- Incorporar tu sección al informe y preparar con el equipo la demostración final.

El complemento realiza edición local sobre vistas y no actúa como coordinador
2PC. No hay que convertir una edición local normal en escritura sobre las copias
ajenas. El diseño de la transacción distribuida debe mantener la propiedad de
los datos por campus.

## 4. Criterio de compatibilidad

Después de aplicar una migración, ejecutar:

```sh
bash sigtec.sh contrato
bash sigtec.sh verificar
```

Debe conservarse: autenticación real, pertenencia al campus, ocho capas EPSG:5367,
ids globales, edición local permitida, escritura ajena rechazada, replicación y
estilos comunes. No se deben descartar ediciones pendientes ni publicar contraseñas.

La replicación lógica no replica DDL. Aplicá las vistas, funciones y permisos en
los nodos correspondientes, y versioná cada migración. Si necesitás cambiar la
interfaz pública, conservá un alias compatible o acordá un contrato mayor nuevo.

## 5. Estado al recibir

La entrega de Kay incluye software, datos de referencia, documentación, contrato
y paquetes generables. El video se pospone expresamente. Los datos OSM no son un
inventario oficial; las capas vacías permanecen editables y documentadas.
La aceptación global del proyecto pertenece al equipo y requiere completar las
pruebas y la demostración de los componentes posteriores.
