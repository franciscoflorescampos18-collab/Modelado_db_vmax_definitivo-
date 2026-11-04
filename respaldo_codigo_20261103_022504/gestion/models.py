from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Q
from django.db.models.functions import Lower

# ==========================================================
# PERSONAL Y USUARIOS
# ==========================================================

class Rol(models.Model):
    id_rol = models.AutoField(primary_key=True)
    nombre_rol = models.CharField(max_length=150, unique=True)
    descripcion_rol = models.TextField(blank=True)

    class Meta:
        db_table = "roles"
        verbose_name = "Rol"
        verbose_name_plural = "Roles"
        ordering = ["nombre_rol"]

    def __str__(self):
        return self.nombre_rol


class Empleado(models.Model):
    id_empleado = models.AutoField(primary_key=True)
    nombre_empleado = models.CharField(max_length=150)
    apellido_empleado = models.CharField(max_length=150)
    dni_empleado = models.CharField(max_length=15, unique=True)
    telefono_empleado = models.CharField(max_length=20)
    email_empleado = models.EmailField(max_length=150)
    fecha_alta_empleado = models.DateField(null=True, blank=True)
    fecha_baja_empleado = models.DateField(null=True, blank=True)
    estado_empleado = models.BooleanField(default=True)

    class Meta:
        db_table = "empleados"
        verbose_name = "Empleado"
        verbose_name_plural = "Empleados"
        ordering = ["apellido_empleado", "nombre_empleado"]

    def __str__(self):
        return f"{self.apellido_empleado}, {self.nombre_empleado}"


class UsuarioManager(UserManager):
    def _create_user(self, username, email, password, **extra_fields):
        return super()._create_user(
            username.strip().lower(),
            (email or "").strip().lower(),
            password,
            **extra_fields,
        )

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        # Todo usuario necesita un Empleado. El primer administrador recibe uno provisorio.
        with transaction.atomic():
            if "id_empleado" not in extra_fields:
                extra_fields["id_empleado"] = Empleado.objects.create(
                    nombre_empleado=username,
                    apellido_empleado="Administrador",
                    dni_empleado=f"ADM-{username}"[:15],
                    telefono_empleado="-",
                    email_empleado=email or "",
                )
            extra_fields.update(is_active=True, estado="aprobado")
            return super().create_superuser(username, email, password, **extra_fields)


class Usuario(AbstractUser):
    """Cuenta de acceso (AUTH_USER_MODEL). Cada usuario pertenece a un Empleado.

    Campos que ya trae AbstractUser: username, password, email, date_joined,
    is_active, is_staff, is_superuser.
    """

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        APROBADO = "aprobado", "Aprobado"
        RECHAZADO = "rechazado", "Rechazado"

    id_usuario = models.AutoField(primary_key=True)

    id_empleado = models.ForeignKey(
        Empleado,
        on_delete=models.RESTRICT,
        db_column="id_empleado",
        related_name="usuarios",
    )

    email = models.EmailField("correo electrónico", unique=True)
    is_active = models.BooleanField("puede ingresar", default=False)
    estado = models.CharField(
        max_length=12, choices=Estado.choices, default=Estado.PENDIENTE
    )

    objects = UsuarioManager()

    class Meta:
        db_table = "usuarios"
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        ordering = ["username"]
        constraints = [
            models.UniqueConstraint(
                Lower("email"), name="usuario_email_sin_mayusculas"
            ),
            models.UniqueConstraint(
                Lower("username"), name="usuario_nombre_sin_mayusculas"
            ),
            models.CheckConstraint(
                condition=models.Q(is_active=False) | models.Q(estado="aprobado"),
                name="activo_solo_aprobado",
            ),
        ]

    def __str__(self):
        return self.username

    @property
    def es_administrador(self):
        """True si es superusuario o tiene el rol Administrador vigente."""
        if self.is_superuser:
            return True
        return self.asignaciones_rol.filter(
            id_rol__nombre_rol="Administrador", fecha_baja_rol__isnull=True
        ).exists()


class UsuarioRol(models.Model):
    id_usuario_rol = models.AutoField(primary_key=True)

    id_usuario = models.ForeignKey(
        Usuario,
        on_delete=models.RESTRICT,
        db_column="id_usuario",
        related_name="asignaciones_rol",
    )

    id_rol = models.ForeignKey(
        Rol,
        on_delete=models.RESTRICT,
        db_column="id_rol",
        related_name="asignaciones_usuario",
    )

    fecha_asignacion = models.DateField()
    fecha_baja_rol = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "usuarios_roles"
        verbose_name = "Asignación de Rol"
        verbose_name_plural = "Asignaciones de Roles"
        ordering = ["-fecha_asignacion"]
        constraints = [
            models.UniqueConstraint(
                fields=["id_usuario", "id_rol", "fecha_asignacion"],
                name="usuario_rol_fecha_unicos",
            )
        ]

    def __str__(self):
        return f"{self.id_usuario} - {self.id_rol}"


# ==========================================================
# CATÁLOGO
# ==========================================================

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

    # El servidor completa estos dos campos con request.user. React nunca los envía.
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


# ==========================================================
# PROVEEDORES Y COMPRAS
# ==========================================================

class Proveedor(models.Model):
    id_proveedor = models.AutoField(primary_key=True)
    razon_social_proveedor = models.CharField(max_length=150)
    cuit_proveedor = models.CharField(max_length=30, unique=True)
    telefono_proveedor = models.CharField(max_length=20)
    email_proveedor = models.EmailField(max_length=150)

    class Meta:
        db_table = "proveedores"
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ["razon_social_proveedor"]

    def __str__(self):
        return self.razon_social_proveedor


class ProveedorProducto(models.Model):
    id_prov_prod = models.AutoField(primary_key=True)

    id_proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.RESTRICT,
        db_column="id_proveedor",
        related_name="productos_ofrecidos",
    )

    id_producto = models.ForeignKey(
        Producto,
        on_delete=models.RESTRICT,
        db_column="id_producto",
        related_name="proveedores",
    )

    precio_costo = models.DecimalField(
        max_digits=13,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        db_table = "proveedores_productos"
        verbose_name = "Producto de Proveedor"
        verbose_name_plural = "Productos de Proveedores"
        ordering = ["id_prov_prod"]
        constraints = [
            models.UniqueConstraint(
                fields=["id_proveedor", "id_producto"],
                name="proveedor_producto_unico",
            )
        ]

    def __str__(self):
        return f"{self.id_proveedor} - {self.id_producto}"


class OrdCompra(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "Pendiente", "Pendiente"
        ENVIADA = "Enviada", "Enviada"
        RECIBIDA = "Recibida", "Recibida"
        CANCELADA = "Cancelada", "Cancelada"

    id_ord_compra = models.AutoField(primary_key=True)
    fecha_emision_orden = models.DateField()

    estado_orden = models.CharField(
        max_length=30,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )

    total_orden = models.DecimalField(
        max_digits=13,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        db_table = "ords_compra"
        verbose_name = "Orden de Compra"
        verbose_name_plural = "Órdenes de Compra"
        ordering = ["-fecha_emision_orden"]

    def __str__(self):
        return f"Orden {self.id_ord_compra}"


class DetOrdCompra(models.Model):
    id_det_ord_compra = models.AutoField(primary_key=True)

    id_ord_compra = models.ForeignKey(
        OrdCompra,
        on_delete=models.CASCADE,
        db_column="id_ord_compra",
        related_name="detalles",
    )

    id_proveedor_producto = models.ForeignKey(
        ProveedorProducto,
        on_delete=models.RESTRICT,
        db_column="id_proveedor_producto",
        related_name="detalles_orden",
    )

    cantidad_pedida = models.DecimalField(
        max_digits=13,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )

    class Meta:
        db_table = "detalles_ord_compra"
        verbose_name = "Detalle de Orden de Compra"
        verbose_name_plural = "Detalles de Órdenes de Compra"
        ordering = ["id_det_ord_compra"]

    def __str__(self):
        return f"Detalle Orden Compra {self.id_det_ord_compra}"


class Compra(models.Model):
    id_compra = models.AutoField(primary_key=True)

    id_caja = models.ForeignKey(
        "Caja",
        on_delete=models.RESTRICT,
        db_column="id_caja",
        related_name="compras",
    )

    id_proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.RESTRICT,
        db_column="id_proveedor",
        related_name="compras",
    )

    fecha_hora_compra = models.DateTimeField()

    total_compra = models.DecimalField(
        max_digits=13,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    num_factura_compra = models.CharField(max_length=30)

    class Meta:
        db_table = "compras"
        verbose_name = "Compra"
        verbose_name_plural = "Compras"
        ordering = ["-fecha_hora_compra"]

    def __str__(self):
        return f"Compra {self.id_compra}"


class DetCompra(models.Model):
    id_det_compra = models.AutoField(primary_key=True)

    id_compra = models.ForeignKey(
        Compra,
        on_delete=models.CASCADE,
        db_column="id_compra",
        related_name="detalles",
    )

    id_producto = models.ForeignKey(
        Producto,
        on_delete=models.RESTRICT,
        db_column="id_producto",
        related_name="detalles_compra",
    )

    cantidad = models.DecimalField(
        max_digits=13,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )

    costo_unit_compra = models.DecimalField(
        max_digits=13,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    subtotal_compra = models.DecimalField(
        max_digits=13,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        db_table = "detalles_compra"
        verbose_name = "Detalle de Compra"
        verbose_name_plural = "Detalles de Compra"
        ordering = ["id_det_compra"]

    def __str__(self):
        return f"Detalle Compra {self.id_det_compra}"


# ==========================================================
# CLIENTES Y VENTAS
# ==========================================================

class Cliente(models.Model):
    id_cliente = models.AutoField(primary_key=True)
    nombre_cliente = models.CharField(max_length=150)
    apellido_cliente = models.CharField(max_length=150)
    dni_cliente = models.CharField(max_length=15, unique=True)
    telefono_cliente = models.CharField(max_length=20)
    email_cliente = models.EmailField(max_length=150, null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "clientes"
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["apellido_cliente", "nombre_cliente"]

    def __str__(self):
        return f"{self.apellido_cliente}, {self.nombre_cliente}"


class Venta(models.Model):
    id_venta = models.AutoField(primary_key=True)

    id_caja = models.ForeignKey(
        "Caja",
        on_delete=models.RESTRICT,
        db_column="id_caja",
        related_name="ventas",
    )

    id_cliente = models.ForeignKey(
        Cliente,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column="id_cliente",
        related_name="ventas",
    )

    fecha_hora_venta = models.DateTimeField()

    monto_total_venta = models.DecimalField(
        max_digits=13,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        db_table = "ventas"
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ["-fecha_hora_venta"]

    def __str__(self):
        return f"Venta {self.id_venta}"


class DetVenta(models.Model):
    id_det_venta = models.AutoField(primary_key=True)

    id_venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        db_column="id_venta",
        related_name="detalles",
    )

    id_producto = models.ForeignKey(
        Producto,
        on_delete=models.RESTRICT,
        db_column="id_producto",
        related_name="detalles_venta",
    )

    cantidad = models.DecimalField(
        max_digits=13,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )

    precio_unit_venta = models.DecimalField(
        max_digits=13,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    subtotal_venta = models.DecimalField(
        max_digits=13,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        db_table = "detalles_venta"
        verbose_name = "Detalle de Venta"
        verbose_name_plural = "Detalles de Venta"
        ordering = ["id_det_venta"]

    def __str__(self):
        return f"Detalle Venta {self.id_det_venta}"


class Comprobante(models.Model):
    class EstadoComprobante(models.TextChoices):
        PENDIENTE = "Pendiente", "Pendiente"
        AUTORIZADO = "Autorizado", "Autorizado"
        RECHAZADO = "Rechazado", "Rechazado"

    id_comprobante = models.AutoField(primary_key=True)

    id_venta = models.ForeignKey(
        Venta,
        on_delete=models.RESTRICT,
        db_column="id_venta",
        related_name="comprobantes",
    )

    # Se conserva como texto libre, según lo definido.
    tipo_comprobante = models.CharField(max_length=50)

    estado_comprobante = models.CharField(
        max_length=30,
        choices=EstadoComprobante.choices,
        default=EstadoComprobante.PENDIENTE,
    )

    fecha_generacion_comprobante = models.DateTimeField()
    ruta_archivo = models.CharField(max_length=300)

    class Meta:
        db_table = "comprobantes"
        verbose_name = "Comprobante"
        verbose_name_plural = "Comprobantes"
        ordering = ["-fecha_generacion_comprobante"]

    def __str__(self):
        return f"Comprobante {self.id_comprobante}"


# ==========================================================
# MÉTODOS DE PAGO
# ==========================================================

class MetodoPago(models.Model):
    id_metodo_pago = models.AutoField(primary_key=True)
    nombre_metodo_pago = models.CharField(max_length=150, unique=True)
    descripcion_metodo_pago = models.TextField(blank=True)

    class Meta:
        db_table = "metodos_pago"
        verbose_name = "Método de Pago"
        verbose_name_plural = "Métodos de Pago"
        ordering = ["nombre_metodo_pago"]

    def __str__(self):
        return self.nombre_metodo_pago


class VentaMetodoPago(models.Model):
    id_venta_met_pago = models.AutoField(primary_key=True)

    id_venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        db_column="id_venta",
        related_name="pagos",
    )

    id_metodo_pago = models.ForeignKey(
        MetodoPago,
        on_delete=models.RESTRICT,
        db_column="id_metodo_pago",
        related_name="pagos_venta",
    )

    monto_abonado = models.DecimalField(
        max_digits=13,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    class Meta:
        db_table = "ventas_metodos_pago"
        verbose_name = "Venta - Método de Pago"
        verbose_name_plural = "Ventas - Métodos de Pago"
        ordering = ["id_venta_met_pago"]

    def __str__(self):
        return f"Pago Venta {self.id_venta_met_pago}"


class CompraMetodoPago(models.Model):
    id_compra_met_pago = models.AutoField(primary_key=True)

    id_compra = models.ForeignKey(
        Compra,
        on_delete=models.CASCADE,
        db_column="id_compra",
        related_name="pagos",
    )

    id_metodo_pago = models.ForeignKey(
        MetodoPago,
        on_delete=models.RESTRICT,
        db_column="id_metodo_pago",
        related_name="pagos_compra",
    )

    monto_pagado = models.DecimalField(
        max_digits=13,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    class Meta:
        db_table = "compras_metodos_pago"
        verbose_name = "Compra - Método de Pago"
        verbose_name_plural = "Compras - Métodos de Pago"
        ordering = ["id_compra_met_pago"]

    def __str__(self):
        return f"Pago Compra {self.id_compra_met_pago}"


# ==========================================================
# CAJA
# ==========================================================

class TipoMovCaja(models.Model):
    class Naturaleza(models.TextChoices):
        INGRESO = "Ingreso", "Ingreso"
        EGRESO = "Egreso", "Egreso"

    id_tipo_mov_caja = models.AutoField(primary_key=True)
    nombre_tipo_mov_caja = models.CharField(max_length=150)

    naturaleza_movimiento = models.CharField(
        max_length=20,
        choices=Naturaleza.choices,
    )

    class Meta:
        db_table = "tipos_mov_caja"
        verbose_name = "Tipo de Movimiento de Caja"
        verbose_name_plural = "Tipos de Movimiento de Caja"
        ordering = ["nombre_tipo_mov_caja"]

    def __str__(self):
        return self.nombre_tipo_mov_caja


class Caja(models.Model):
    class EstadoCaja(models.TextChoices):
        ABIERTA = "Abierta", "Abierta"
        CERRADA = "Cerrada", "Cerrada"

    id_caja = models.AutoField(primary_key=True)

    id_usuario = models.ForeignKey(
        Usuario,
        on_delete=models.RESTRICT,
        db_column="id_usuario",
        related_name="cajas",
    )

    fecha_apertura = models.DateTimeField()
    fecha_cierre = models.DateTimeField(null=True, blank=True)

    saldo_inicial = models.DecimalField(
        max_digits=13,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    saldo_final = models.DecimalField(
        max_digits=13,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )

    estado_caja = models.CharField(
        max_length=20,
        choices=EstadoCaja.choices,
        default=EstadoCaja.ABIERTA,
    )

    class Meta:
        db_table = "cajas"
        verbose_name = "Caja"
        verbose_name_plural = "Cajas"
        ordering = ["-fecha_apertura"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(fecha_cierre__isnull=True, saldo_final__isnull=True)
                    | Q(fecha_cierre__isnull=False, saldo_final__isnull=False)
                ),
                name="chk_caja_cierre_saldo",
            )
        ]

    def __str__(self):
        return f"Caja {self.id_caja} - {self.fecha_apertura}"


class MovCaja(models.Model):
    id_mov_caja = models.AutoField(primary_key=True)

    id_caja = models.ForeignKey(
        Caja,
        on_delete=models.RESTRICT,
        db_column="id_caja",
        related_name="movimientos",
    )

    id_tipo_mov_caja = models.ForeignKey(
        TipoMovCaja,
        on_delete=models.RESTRICT,
        db_column="id_tipo_mov_caja",
        related_name="movimientos",
    )

    id_venta = models.ForeignKey(
        Venta,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column="id_venta",
        related_name="movimientos_caja",
    )

    id_compra = models.ForeignKey(
        Compra,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column="id_compra",
        related_name="movimientos_caja",
    )

    monto_mov_caja = models.DecimalField(
        max_digits=13,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    hora_mov_caja = models.TimeField()
    observacion_mov_caja = models.TextField(blank=True)

    class Meta:
        db_table = "movs_caja"
        verbose_name = "Movimiento de Caja"
        verbose_name_plural = "Movimientos de Caja"
        ordering = ["-hora_mov_caja"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(id_venta__isnull=True)
                    | Q(id_compra__isnull=True)
                ),
                name="mov_caja_no_asociar_dos_operaciones",
            )
        ]

    def __str__(self):
        return f"Movimiento {self.id_mov_caja}"


# ==========================================================
# MOVIMIENTOS DE INVENTARIO
# ==========================================================

class TipoMovInventario(models.Model):
    class Efecto(models.TextChoices):
        SUMA = "Suma", "Suma"
        RESTA = "Resta", "Resta"
        NEUTRO = "Neutro", "Neutro"

    id_tipo_mov_inv = models.AutoField(primary_key=True)
    nombre_tipo_mov_inv = models.CharField(max_length=150)

    efecto_stock = models.CharField(
        max_length=20,
        choices=Efecto.choices,
    )

    class Meta:
        db_table = "tipos_mov_inventario"
        verbose_name = "Tipo de Movimiento de Inventario"
        verbose_name_plural = "Tipos de Movimiento de Inventario"
        ordering = ["nombre_tipo_mov_inv"]

    def __str__(self):
        return self.nombre_tipo_mov_inv


class MovInventario(models.Model):
    # Es el encabezado. Los productos y cantidades están en DetInventario.
    id_mov_inv = models.AutoField(primary_key=True)

    id_tipo_mov_inv = models.ForeignKey(
        TipoMovInventario,
        on_delete=models.RESTRICT,
        db_column="id_tipo_mov_inv",
        related_name="movimientos",
    )

    observacion_mov_inv = models.TextField(blank=True)
    fecha_mov_inv = models.DateField()

    class Meta:
        db_table = "movs_inventario"
        verbose_name = "Movimiento de Inventario"
        verbose_name_plural = "Movimientos de Inventario"
        ordering = ["-fecha_mov_inv"]

    def __str__(self):
        return f"Movimiento Inventario {self.id_mov_inv}"


class DetInventario(models.Model):
    class EstadoItem(models.TextChoices):
        BUENO = "Bueno", "Bueno"
        FALLADO = "Fallado", "Fallado"
        EN_GARANTIA = "En garantía", "En garantía"
        DANADO = "Dañado", "Dañado"

    id_det_inventario = models.AutoField(primary_key=True)

    id_mov_inv = models.ForeignKey(
        MovInventario,
        on_delete=models.CASCADE,
        db_column="id_mov_inv",
        related_name="detalles",
    )

    id_producto = models.ForeignKey(
        Producto,
        on_delete=models.RESTRICT,
        db_column="id_producto",
        related_name="detalles_inventario",
    )

    # Se relaciona con la línea de venta o compra cuando corresponda.
    # En un ajuste manual, ambas relaciones quedan vacías.
    id_det_venta = models.ForeignKey(
        DetVenta,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column="id_det_venta",
        related_name="movimientos_inventario",
    )

    id_det_compra = models.ForeignKey(
        DetCompra,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column="id_det_compra",
        related_name="movimientos_inventario",
    )

    cantidad_afectada = models.DecimalField(
        max_digits=13,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )

    estado_item = models.CharField(
        max_length=30,
        choices=EstadoItem.choices,
    )

    class Meta:
        db_table = "detalles_inventario"
        verbose_name = "Detalle de Inventario"
        verbose_name_plural = "Detalles de Inventario"
        ordering = ["id_det_inventario"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(id_det_venta__isnull=True)
                    | Q(id_det_compra__isnull=True)
                ),
                name="det_inv_no_asociar_venta_y_compra",
            )
        ]

    def __str__(self):
        return f"Detalle Inventario {self.id_det_inventario}"


# ==========================================================
# DEVOLUCIONES Y GARANTÍAS
# ==========================================================

class HistorialDevolucion(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "Pendiente", "Pendiente"
        EN_REVISION = "En revisión", "En revisión"
        FINALIZADO = "Finalizado", "Finalizado"
        RECHAZADO = "Rechazado", "Rechazado"

    id_devolucion = models.AutoField(primary_key=True)

    id_mov_inv = models.OneToOneField(
        MovInventario,
        on_delete=models.RESTRICT,
        db_column="id_mov_inv",
        related_name="devolucion",
    )

    id_det_venta = models.ForeignKey(
        DetVenta,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column="id_det_venta",
        related_name="devoluciones",
    )

    motivo_devolucion = models.TextField()
    fecha_devolucion = models.DateField()

    estado_devolucion = models.CharField(
        max_length=30,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )

    class Meta:
        db_table = "historiales_devoluciones"
        verbose_name = "Historial de Devolución"
        verbose_name_plural = "Historiales de Devoluciones"
        ordering = ["-fecha_devolucion"]

    def __str__(self):
        return f"Devolución {self.id_devolucion}"


class HistorialGarantia(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "Pendiente", "Pendiente"
        EN_PROCESO = "En proceso", "En proceso"
        FINALIZADO = "Finalizado", "Finalizado"
        RECHAZADO = "Rechazado", "Rechazado"

    id_garantia = models.AutoField(primary_key=True)

    id_det_venta = models.ForeignKey(
        DetVenta,
        on_delete=models.RESTRICT,
        db_column="id_det_venta",
        related_name="garantias",
    )

    fecha_reclamo = models.DateField()
    resolucion_garantia = models.TextField(blank=True)

    estado_garantia = models.CharField(
        max_length=30,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )

    class Meta:
        db_table = "historiales_garantias"
        verbose_name = "Historial de Garantía"
        verbose_name_plural = "Historiales de Garantías"
        ordering = ["-fecha_reclamo"]

    def __str__(self):
        return f"Garantía {self.id_garantia}"