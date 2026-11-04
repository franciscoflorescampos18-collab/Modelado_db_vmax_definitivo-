from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.db.models import ProtectedError
from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)

from gestion.models import Producto, Categoria
from .forms import ProductoForm, CategoriaForm


class GuardadoSeguroMixin:
    def form_valid(self, form):
        try:
            with transaction.atomic():
                response = super().form_valid(form)
        except IntegrityError:
            form.add_error(
                None,
                "No se pudo guardar. Revisá los datos e intentá nuevamente.",
            )
            return self.form_invalid(form)

        messages.success(self.request, "Cambios guardados.")
        return response


# ============================================================
# PRODUCTOS
# ============================================================

class ProductoListView(LoginRequiredMixin, ListView):
    model = Producto
    template_name = "catalogo/lista.html"
    paginate_by = 12

    def get_queryset(self):
        qs = super().get_queryset().select_related(
            "id_categoria",
            "id_unidad",
        )

        q = self.request.GET.get("q", "").strip()[:100]

        if q:
            qs = qs.filter(
                Q(nombre_producto__icontains=q)
                | Q(codigo_barra__icontains=q)
            )

        return qs


class ProductoDetailView(LoginRequiredMixin, DetailView):
    model = Producto
    template_name = "catalogo/detalle.html"


class ProductoCreateView(LoginRequiredMixin, GuardadoSeguroMixin, CreateView):
    model = Producto
    form_class = ProductoForm
    template_name = "catalogo/formulario.html"

    def form_valid(self, form):
        form.instance.creado_por = self.request.user
        form.instance.actualizado_por = self.request.user
        return super().form_valid(form)


class ProductoUpdateView(LoginRequiredMixin, GuardadoSeguroMixin, UpdateView):
    model = Producto
    form_class = ProductoForm
    template_name = "catalogo/formulario.html"

    def form_valid(self, form):
        form.instance.actualizado_por = self.request.user
        return super().form_valid(form)


class ProductoDeleteView(LoginRequiredMixin, DeleteView):
    model = Producto
    template_name = "catalogo/confirmar_baja.html"
    success_url = reverse_lazy("catalogo:lista")

    def form_valid(self, form):
        try:
            with transaction.atomic():
                response = super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                "No se puede eliminar un producto que tiene movimientos, "
                "compras o ventas relacionados.",
            )
            return self.get(self.request)

        messages.success(self.request, "Producto eliminado.")
        return response


# ============================================================
# CATEGORÍAS
# ============================================================

class CategoriaListView(LoginRequiredMixin, ListView):
    model = Categoria
    template_name = "catalogo/categorias.html"
    paginate_by = 20


class CategoriaCreateView(LoginRequiredMixin, GuardadoSeguroMixin, CreateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = "catalogo/categoria_form.html"
    success_url = reverse_lazy("catalogo:categorias")


class CategoriaUpdateView(LoginRequiredMixin, GuardadoSeguroMixin, UpdateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = "catalogo/categoria_form.html"
    success_url = reverse_lazy("catalogo:categorias")


class CategoriaDeleteView(LoginRequiredMixin, DeleteView):
    model = Categoria
    template_name = "catalogo/confirmar_baja.html"
    success_url = reverse_lazy("catalogo:categorias")

    def form_valid(self, form):
        try:
            with transaction.atomic():
                response = super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                "No se puede eliminar una categoría que tiene productos.",
            )
            return self.get(self.request)

        messages.success(self.request, "Categoría eliminada.")
        return response