from rest_framework import serializers
from gestion.models import Producto, Categoria, Unidad


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = [
            "id_categoria",
            "nombre_categoria",
            "descripcion_categoria",
        ]


class UnidadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unidad
        fields = [
            "id_unidad",
            "nombre_unidad",
            "abreviatura_unidad",
        ]


class ProductoSerializer(serializers.ModelSerializer):
    categoria = CategoriaSerializer(
        source="id_categoria",
        read_only=True
    )

    unidad = UnidadSerializer(
        source="id_unidad",
        read_only=True
    )

    id_categoria = serializers.PrimaryKeyRelatedField(
        queryset=Categoria.objects.all(),
        required=False,
        allow_null=True
    )

    id_unidad = serializers.PrimaryKeyRelatedField(
        queryset=Unidad.objects.all()
    )

    class Meta:
        model = Producto
        fields = [
            "id_producto",
            "id_categoria",
            "categoria",
            "id_unidad",
            "unidad",
            "codigo_barra",
            "nombre_producto",
            "descripcion_producto",
            "precio_producto",
            "stock_actual",
            "stock_minimo",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id_producto",
            "stock_actual",
            "fecha_creacion",
            "fecha_actualizacion",
        ]