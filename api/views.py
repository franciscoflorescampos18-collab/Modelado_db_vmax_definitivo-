from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from gestion.models import Producto, Categoria, Unidad
from .serializers import (
    ProductoSerializer,
    CategoriaSerializer,
    UnidadSerializer,
)


class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.select_related(
        "id_categoria",
        "id_unidad"
    ).all()

    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated]


class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [IsAuthenticated]


class UnidadViewSet(viewsets.ModelViewSet):
    queryset = Unidad.objects.all()
    serializer_class = UnidadSerializer
    permission_classes = [IsAuthenticated]
# Create your views here.
