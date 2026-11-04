from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction

from gestion.models import Categoria, Unidad, Producto


class Command(BaseCommand):
    help = "Agrega productos ficticios sin modificar registros existentes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--usuario",
            required=True,
            help="Nombre del administrador existente",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        Usuario = get_user_model()

        try:
            usuario = Usuario.objects.get(
                username=options["usuario"],
                is_superuser=True,
                is_active=True,
            )
        except Usuario.DoesNotExist:
            raise CommandError(
                "Primero creá un administrador con createsuperuser."
            )

        unidad, _ = Unidad.objects.get_or_create(
            abreviatura_unidad="un",
            defaults={"nombre_unidad": "Unidad"},
        )

        ejemplos = [
            ("DEMO-001", "Cuaderno de tapa dura", "Librería", "8500.00", 5),
            ("DEMO-002", "Lápiz de grafito", "Librería", "650.00", 10),
            ("DEMO-003", "Botella reutilizable", "Accesorios", "12000.00", 3),
        ]

        for codigo, nombre, categoria_nombre, precio, stock_minimo in ejemplos:
            categoria = Categoria.objects.filter(
                nombre_categoria__iexact=categoria_nombre
            ).first()

            if not categoria:
                categoria = Categoria.objects.create(
                    nombre_categoria=categoria_nombre
                )

            producto = Producto.objects.filter(
                codigo_barra__iexact=codigo
            ).first()

            if not producto:
                Producto.objects.create(
                    codigo_barra=codigo,
                    nombre_producto=nombre,
                    id_categoria=categoria,
                    id_unidad=unidad,
                    precio_producto=precio,
                    stock_minimo=stock_minimo,
                    creado_por=usuario,
                    actualizado_por=usuario,
                )

        self.stdout.write(
            self.style.SUCCESS("Ejemplos ficticios cargados correctamente.")
        )