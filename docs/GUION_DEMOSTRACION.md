# Guion de demostración de la parte QGIS

Este bloque puede ocupar unos 4 minutos del video integral de máximo 10 minutos.
Coordinar con el equipo el tiempo de arquitectura, 2PC y recuperación.

1. **Ingreso (30 s).** Abrir QGIS con un proyecto nuevo. Mostrar SIG-TEC, ingresar
   una contraseña inválida y luego las credenciales locales de `kay`. Explicar
   que PostgreSQL central autentica y devuelve el campus 3.
2. **Carga automática (30 s).** Mostrar las ocho vistas en el nodo de San Carlos,
   EPSG:5367, etiquetas y simbología común. Indicar la procedencia OSM y sus límites.
3. **Edición (60 s).** Crear un edificio claramente marcado como demostración,
   completar nombre y pisos, guardar la edición y mostrar que el id y campus se
   asignan solos. Modificarlo y mostrar su llegada al central y otro nodo.
4. **Autonomía (45 s).** Usar un objeto de otro campus que el equipo haya preparado
   en su propio nodo. Consultarlo desde San Carlos e intentar editarlo; mostrar
   el rechazo de la base. El filtro "solo mi campus" es de visualización.
5. **Estilos (30 s).** Mostrar `public.layer_styles` en el central y un campus,
   y explicar que los estilos predeterminados se distribuyen por replicación lógica.
6. **Cierre (15 s).** Eliminar el objeto de demostración, guardar y cerrar sesión.
   Mostrar que no se pierden capas independientes ni ediciones pendientes.

Para preparar objetos de demostración de otro campus se debe ingresar con su
cuenta y conectarse a su nodo; nunca escribir en sus copias desde San Carlos.
Las cuentas y contraseñas locales están en `.local/acceso_qgis.txt` y no deben
aparecer en el video ni en el ZIP de entrega.
