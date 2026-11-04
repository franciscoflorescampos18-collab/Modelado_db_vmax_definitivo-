from django import forms
from gestion.models import Categoria, Producto


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = (
            "codigo_barra",
            "nombre_producto",
            "descripcion_producto",
            "id_categoria",
            "id_unidad",
            "precio_producto",
            "stock_minimo",
        )
        widgets = {
            "descripcion_producto": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_codigo_barra(self):
        codigo = self.cleaned_data.get("codigo_barra")

        if codigo:
            codigo = codigo.strip().upper()

            if (
                Producto.objects.filter(codigo_barra__iexact=codigo)
                .exclude(pk=self.instance.pk)
                .exists()
            ):
                raise forms.ValidationError(
                    "Ya existe un producto con ese código de barras."
                )

        return codigo


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ("nombre_categoria", "descripcion_categoria")

    def clean_nombre_categoria(self):
        nombre = self.cleaned_data["nombre_categoria"].strip()

        if (
            Categoria.objects.filter(nombre_categoria__iexact=nombre)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise forms.ValidationError("Ya existe esa categoría.")

        return nombre
