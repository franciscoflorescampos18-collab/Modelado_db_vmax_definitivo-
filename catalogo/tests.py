
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from cuentas.models import Usuario
from gestion.models import Categoria, Unidad, Producto


@override_settings(
    SECURE_SSL_REDIRECT=False,
    STORAGES={
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        }
    },
)
class CatalogoTests(TestCase):

    def setUp(self):
        self.admin = Usuario.objects.create_superuser(
            "admin", "admin@example.test", "Temporal-segura-298!"
        )

        self.operador = Usuario.objects.create_user(
            "operador",
            "operador@example.test",
            "Temporal-segura-298!",
            estado="aprobado",
            is_active=True,
        )

        self.categoria = Categoria.objects.create(
            nombre_categoria="Librería"
        )

        self.unidad = Unidad.objects.create(
            nombre_unidad="Unidad",
            abreviatura_unidad="un",
        )

        self.producto = Producto.objects.create(
            codigo_barra="P-01",
            nombre_producto="Cuaderno",
            id_categoria=self.categoria,
            id_unidad=self.unidad,
            precio_producto="100.00",
            stock_minimo=2,
            creado_por=self.admin,
            actualizado_por=self.admin,
        )

        self.data = {
            "codigo_barra": "P-02",
            "nombre_producto": "Otro",
            "descripcion_producto": "Texto",
            "id_categoria": self.categoria.pk,
            "id_unidad": self.unidad.pk,
            "precio_producto": "20.50",
            "stock_minimo": 5,
        }

    def test_anonimo_no_lee_ni_escribe(self):
        for name, args in [
            ("lista", []),
            ("detalle", [self.producto.pk]),
            ("crear", []),
            ("editar", [self.producto.pk]),
            ("eliminar", [self.producto.pk]),
            ("categorias", []),
        ]:
            response = self.client.get(
                reverse("catalogo:" + name, args=args)
            )
            self.assertEqual(response.status_code, 302)

        response = self.client.post(
            reverse("catalogo:crear"), self.data
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Producto.objects.count(), 1)

    def test_ciclo_completo_y_autoria(self):
        self.client.force_login(self.operador)

        response = self.client.post(
            reverse("catalogo:crear"), self.data
        )
        self.assertEqual(response.status_code, 302)

        producto = Producto.objects.get(codigo_barra="P-02")
        self.assertEqual(producto.creado_por, self.operador)
        self.assertEqual(producto.stock_actual, 0)

        self.assertContains(
            self.client.get(
                reverse("catalogo:detalle", args=[producto.pk])
            ),
            "Otro",
        )

        datos_edicion = {
            **self.data,
            "nombre_producto": "Actualizado",
        }

        self.client.post(
            reverse("catalogo:editar", args=[producto.pk]),
            datos_edicion,
        )

        producto.refresh_from_db()
        self.assertEqual(producto.nombre_producto, "Actualizado")

        self.assertEqual(
            self.client.post(
                reverse("catalogo:eliminar", args=[producto.pk])
            ).status_code,
            403,
        )

        self.assertTrue(
            Producto.objects.filter(pk=producto.pk).exists()
        )

        self.client.force_login(self.admin)

        self.assertEqual(
            self.client.get(
                reverse("catalogo:eliminar", args=[producto.pk])
            ).status_code,
            200,
        )

        self.client.post(
            reverse("catalogo:eliminar", args=[producto.pk])
        )

        self.assertFalse(
            Producto.objects.filter(pk=producto.pk).exists()
        )

    def test_precio_y_categoria_invalidos(self):
        self.client.force_login(self.operador)

        casos = [
            ("precio_producto", "-1"),
            ("id_categoria", 999999),
        ]

        for field, value in casos:
            data = {**self.data, field: value}

            response = self.client.post(
                reverse("catalogo:crear"), data
            )

            self.assertEqual(response.status_code, 200)
            self.assertIn(
                field, response.context["form"].errors
            )

        self.assertEqual(Producto.objects.count(), 1)

    def test_codigo_duplicado_y_espacios(self):
        self.client.force_login(self.operador)

        data = {
            **self.data,
            "codigo_barra": " P-01 ",
        }

        response = self.client.post(
            reverse("catalogo:crear"), data
        )

        self.assertIn(
            "codigo_barra", response.context["form"].errors
        )

    def test_restriccion_precio_en_base(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Producto.objects.filter(
                pk=self.producto.pk
            ).update(precio_producto=-1)

    def test_eliminar_categoria_deja_producto_sin_categoria(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse(
                "catalogo:categoria_eliminar",
                args=[self.categoria.pk],
            )
        )

        self.assertEqual(response.status_code, 302)

        self.producto.refresh_from_db()
        self.assertIsNone(self.producto.id_categoria)

        self.assertTrue(
            Producto.objects.filter(pk=self.producto.pk).exists()
        )

        self.assertFalse(
            Categoria.objects.filter(pk=self.categoria.pk).exists()
        )

    def test_crud_categorias_y_permisos(self):
        self.client.force_login(self.operador)

        self.assertEqual(
            self.client.post(
                reverse("catalogo:categoria_crear"),
                {"nombre_categoria": "Nueva"},
            ).status_code,
            403,
        )

        self.client.force_login(self.admin)

        self.client.post(
            reverse("catalogo:categoria_crear"),
            {"nombre_categoria": "Nueva"},
        )

        categoria = Categoria.objects.get(
            nombre_categoria="Nueva"
        )

        self.client.post(
            reverse(
                "catalogo:categoria_editar",
                args=[categoria.pk],
            ),
            {"nombre_categoria": "Actualizada"},
        )

        categoria.refresh_from_db()

        self.assertEqual(
            categoria.nombre_categoria, "Actualizada"
        )

        self.client.post(
            reverse(
                "catalogo:categoria_eliminar",
                args=[categoria.pk],
            )
        )

        self.assertFalse(
            Categoria.objects.filter(pk=categoria.pk).exists()
        )

    def test_busqueda_paginacion_y_escape_html(self):
        self.client.force_login(self.operador)

        self.producto.nombre_producto = (
            '<script>alert("x")</script>'
        )
        self.producto.save()

        response = self.client.get(
            reverse("catalogo:detalle", args=[self.producto.pk])
        )

        self.assertNotContains(
            response, '<script>alert("x")</script>'
        )
        self.assertContains(response, "&lt;script&gt;")

        self.assertEqual(
            self.client.get(
                reverse("catalogo:lista"), {"q": "P-01"}
            ).context["paginator"].count,
            1,
        )

        self.assertContains(
            self.client.get(
                reverse("catalogo:lista"),
                {"q": "inexistente"},
            ),
            "No encontramos coincidencias",
        )

        for n in range(13):
            Producto.objects.create(
                codigo_barra=f"OTRO-{n}",
                nombre_producto=f"Producto {n}",
                id_categoria=self.categoria,
                id_unidad=self.unidad,
                precio_producto=1,
                stock_minimo=0,
                creado_por=self.admin,
                actualizado_por=self.admin,
            )

        self.assertEqual(
            len(
                self.client.get(
                    reverse("catalogo:lista")
                ).context["object_list"]
            ),
            12,
        )

        self.assertEqual(
            len(
                self.client.get(
                    reverse("catalogo:lista"),
                    {"page": 2},
                ).context["object_list"]
            ),
            2,
        )

    def test_csrf_impide_modificacion(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.operador)

        self.assertEqual(
            client.post(
                reverse("catalogo:crear"), self.data
            ).status_code,
            403,
        )

    def test_demo_repetible_sin_sobrescribir(self):
        call_command("cargar_demo", usuario="admin", verbosity=0)

        producto = Producto.objects.get(
            codigo_barra="DEMO-001"
        )

        cantidad = Producto.objects.count()
        nombre_original = producto.nombre_producto

        call_command("cargar_demo", usuario="admin", verbosity=0)

        producto.refresh_from_db()

        self.assertEqual(
            producto.nombre_producto, nombre_original
        )
        self.assertEqual(
            Producto.objects.count(), cantidad
        )
        self.assertEqual(producto.stock_actual, 0)

    def test_salud_y_pagina_inexistente(self):
        self.assertEqual(
            self.client.get(
                reverse("inicio:salud")
            ).json(),
            {"estado": "ok"},
        )

        self.client.force_login(self.operador)

        self.assertEqual(
            self.client.get(
                reverse("catalogo:detalle", args=[999999])
            ).status_code,
            404,
        )
