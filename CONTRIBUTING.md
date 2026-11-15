# Desarrollo e integración del equipo

La interfaz de integración está definida por `integracion/contrato_v1.json` y
`docs/CONTRATO_BRADY.md`. La versión de esta entrega individual es `1.0.0`.

## Preparación

```sh
bash sigtec.sh preparar
bash sigtec.sh contrato
bash sigtec.sh verificar
```

La preparación genera cuentas locales propias de cada instalación. No copiar
`.local/`, WAL, respaldos ni credenciales de otro integrante al repositorio.

## Cambios de base de datos

- Conservar la firma de autenticación, columnas y SRID del contrato v1.
- Para cambiar implementación interna, mantener vistas de compatibilidad.
- Aplicar cambios de esquema en cada nodo: la replicación lógica no replica DDL.
- Escribir únicamente en el esquema original del nodo propietario.
- Versionar las migraciones SQL y ejecutar contrato y pruebas antes de fusionar.
- Documentar los cambios de 2PC y recuperación en los archivos del equipo.

## Cambios del complemento

- Los widgets y las capas QGIS se crean en el hilo principal.
- La consulta de autenticación se ejecuta en una tarea en segundo plano.
- Mantener contraseñas fuera de configuración, logs y proyectos guardados.
- Conservar las ediciones pendientes y las capas que no pertenecen al complemento.
- Los estilos compartidos usan variables del campus, no un campus fijo.

## Entrega

`python3 scripts/instalar_complemento.py --solo-zip` genera el instalable.
`python3 scripts/empaquetar_entrega.py` construye los paquetes de fuentes y sus
sumas SHA-256. El paquete integrado incluye el código original de infraestructura
y su procedencia, conservando la autoría de Andrés.

La publicación de esta versión corresponde a la entrega de Kay. El video y la
aceptación integral del equipo se registran por separado.
