from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.urls import reverse


class Categoria(models.Model):
    nombre = models.CharField(max_length=80, unique=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "categoría"
        constraints = [
            models.UniqueConstraint(
                Lower("nombre"),
                name="categoria_nombre_sin_mayusculas",
            )
        ]

    def __str__(self):
        return self.nombre


class Unidad(models.Model):
    id_unidad = models.AutoField(primary_key=True)
    nombre_unidad = models.CharField(max_length=150, unique=True)
    abreviatura_unidad = models.CharField(max_length=10, unique=True)

    class Meta:
        db_table = "unidades"
        verbose_name = "Unidad"
        verbose_name_plural = "Unidades"
        ordering = ["nombre_unidad"]

    def __str__(self):
        return self.nombre_unidad


class Producto(models.Model):
    codigo = models.CharField("código", max_length=30, unique=True)
    codigo_barras = models.CharField(
        "código de barras",
        max_length=50,
        unique=True,
        null=True,
        blank=True,
    )
    nombre = models.CharField(max_length=120)

    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        verbose_name="categoría",
        related_name="productos",
    )

    unidad = models.ForeignKey(
        Unidad,
        on_delete=models.PROTECT,
        verbose_name="unidad",
        related_name="productos",
        null=True,
        blank=True,
    )

    descripcion = models.TextField(
        "descripción",
        blank=True,
        max_length=2000,
    )

    precio = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    stock = models.DecimalField(
        max_digits=13,
        decimal_places=3,
        default=0,
        validators=[MinValueValidator(0)],
    )

    stock_minimo = models.DecimalField(
        max_digits=13,
        decimal_places=3,
        default=0,
        validators=[MinValueValidator(0)],
    )

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="productos_creados",
    )

    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="productos_actualizados",
    )

    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre", "pk"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(precio__gte=0),
                name="producto_precio_no_negativo",
            ),
            models.CheckConstraint(
                condition=models.Q(stock__gte=0),
                name="producto_stock_no_negativo",
            ),
            models.CheckConstraint(
                condition=models.Q(stock_minimo__gte=0),
                name="producto_stock_minimo_no_negativo",
            ),
            models.UniqueConstraint(
                Lower("codigo"),
                name="producto_codigo_sin_mayusculas",
            ),
        ]

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse("catalogo:detalle", args=[self.pk])