from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ProductoViewSet,
    CategoriaViewSet,
    UnidadViewSet,
)

from .auth_views import (
    csrf_token,
    iniciar_sesion,
    cerrar_sesion,
    usuario_actual,
)

router = DefaultRouter()

router.register("productos", ProductoViewSet)
router.register("categorias", CategoriaViewSet)
router.register("unidades", UnidadViewSet)

urlpatterns = [
    path("auth/csrf/", csrf_token),
    path("auth/login/", iniciar_sesion),
    path("auth/logout/", cerrar_sesion),
    path("auth/me/", usuario_actual),
] + router.urls