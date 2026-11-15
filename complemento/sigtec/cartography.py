"""Simbología, etiquetas y formularios comunes a todos los campus."""
from qgis.PyQt.QtGui import QColor
from qgis.core import (
    QgsDefaultValue, QgsEditorWidgetSetup, QgsExpressionContextUtils,
    QgsFieldConstraints, QgsFillSymbol, QgsLineSymbol, QgsMarkerSymbol,
    QgsPalLayerSettings, QgsTextBufferSettings, QgsTextFormat, QgsVectorLayerSimpleLabeling,
)

LABELS = {"edificios": "Edificios", "carreteras": "Carreteras", "aceras": "Aceras", "parqueos": "Parqueos", "zonas_verdes": "Zonas verdes", "puntos_interes": "Puntos de interés", "iluminacion": "Iluminación", "accesibilidad": "Accesibilidad"}
ORDER = ("iluminacion", "puntos_interes", "accesibilidad", "aceras", "carreteras", "edificios", "parqueos", "zonas_verdes")
COLORS = {"edificios": "#c98367", "carreteras": "#58697d", "aceras": "#c4a67a", "parqueos": "#aebac5", "zonas_verdes": "#9dbf83", "puntos_interes": "#1c648e", "iluminacion": "#efbd49", "accesibilidad": "#00847e"}
ALIASES = {"id": "Identificador global", "campus_id": "Campus", "nombre": "Nombre", "codigo": "Código", "area_m2": "Área (m²)", "pisos": "Cantidad de pisos", "tipo": "Tipo", "superficie": "Superficie", "material": "Material", "ancho_m": "Ancho (m)", "condicion": "Condición", "capacidad": "Capacidad", "espacios_disponibles": "Espacios disponibles", "tipo_vegetacion": "Tipo de vegetación", "descripcion": "Descripción", "potencia_w": "Potencia (W)", "estado": "Estado", "creado_en": "Fecha de creación", "modificado_en": "Última modificación"}


def institutional_style(layer, theme):
    color = COLORS[theme]
    if theme in ("edificios", "parqueos", "zonas_verdes"):
        symbol = QgsFillSymbol.createSimple({"color": color, "outline_color": "#4c5c60", "outline_width": "0.22"})
    elif theme in ("puntos_interes", "iluminacion"):
        symbol = QgsMarkerSymbol.createSimple({"name": "diamond" if theme == "iluminacion" else "circle", "color": color, "size": "2.4", "outline_color": "#ffffff", "outline_width": "0.3"})
    else:
        symbol = QgsLineSymbol.createSimple({"line_color": color, "line_width": "0.8" if theme == "carreteras" else "0.5", "line_style": "dash" if theme == "accesibilidad" else "solid"})
    layer.renderer().setSymbol(symbol)
    label_field = "nombre" if layer.fields().indexFromName("nombre") >= 0 else "codigo"
    if layer.fields().indexFromName(label_field) >= 0:
        settings = QgsPalLayerSettings()
        settings.fieldName = f'CASE WHEN regexp_match("{label_field}", \' OSM [0-9]+$\') THEN NULL ELSE "{label_field}" END'
        settings.isExpression = True
        text = QgsTextFormat()
        text.setSize(9)
        text.setColor(QColor("#223745"))
        buffer = QgsTextBufferSettings()
        buffer.setEnabled(True)
        buffer.setSize(0.7)
        buffer.setColor(QColor("#ffffff"))
        text.setBuffer(buffer)
        settings.setFormat(text)
        layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
        layer.setLabelsEnabled(True)
        layer.setDisplayExpression(f'coalesce("{label_field}", \'Sin nombre\')')


def configure_forms(layer, campus_id):
    QgsExpressionContextUtils.setLayerVariable(layer, "sigtec_campus_id", campus_id)
    form = layer.editFormConfig()
    for index, field in enumerate(layer.fields()):
        name = field.name()
        if name in ALIASES:
            layer.setFieldAlias(index, ALIASES[name])
        if name in ("id", "campus_id", "creado_en", "modificado_en", "area_m2"):
            form.setReadOnly(index, True)
        if name == "campus_id":
            layer.setEditorWidgetSetup(index, QgsEditorWidgetSetup("ValueMap", {"map": {"Cartago": 1, "San José": 2, "San Carlos": 3, "Alajuela": 4, "Limón": 5}}))
            layer.setDefaultValueDefinition(index, QgsDefaultValue("@sigtec_campus_id"))
        elif name == "area_m2":
            layer.setDefaultValueDefinition(index, QgsDefaultValue("round($area, 2)", True))
        elif name == "descripcion":
            layer.setEditorWidgetSetup(index, QgsEditorWidgetSetup("TextEdit", {"IsMultiline": True}))
        elif name in ("pisos", "capacidad", "espacios_disponibles", "potencia_w", "ancho_m"):
            layer.setEditorWidgetSetup(index, QgsEditorWidgetSetup("Range", {"Min": 1 if name == "pisos" else 0, "Max": 999999, "Step": 0.1 if name == "ancho_m" else 1, "AllowNull": True, "Style": "SpinBox"}))
        if name == "nombre":
            layer.setConstraintExpression(index, '"nombre" IS NULL OR length(trim("nombre")) > 0', "Escribí un nombre o dejá el campo vacío si no se conoce.")
            layer.setFieldConstraint(index, QgsFieldConstraints.ConstraintExpression)
        if name in ("pisos", "ancho_m"):
            layer.setConstraintExpression(index, f'"{name}" IS NULL OR "{name}" > 0', "El valor debe ser mayor que cero.")
            layer.setFieldConstraint(index, QgsFieldConstraints.ConstraintExpression)
        if name == "espacios_disponibles":
            layer.setConstraintExpression(index, '"espacios_disponibles" IS NULL OR ("espacios_disponibles" >= 0 AND ("capacidad" IS NULL OR "espacios_disponibles" <= "capacidad"))', "La disponibilidad no puede superar la capacidad.")
            layer.setFieldConstraint(index, QgsFieldConstraints.ConstraintExpression)
    layer.setEditFormConfig(form)


def validate_required_fields(layer, theme):
    if theme in ("edificios", "puntos_interes"):
        index = layer.fields().indexFromName("nombre")
        layer.setFieldConstraint(index, QgsFieldConstraints.ConstraintNotNull)
