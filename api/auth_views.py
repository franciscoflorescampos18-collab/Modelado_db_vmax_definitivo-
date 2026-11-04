from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.views.decorators.http import require_GET, require_POST


@require_GET
@ensure_csrf_cookie
def csrf_token(request):
    return JsonResponse({"mensaje": "Token CSRF disponible"})


@require_POST
@csrf_protect
def iniciar_sesion(request):
    import json

    try:
        datos = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Datos inválidos"}, status=400)

    username = datos.get("username", "").strip()
    password = datos.get("password", "")

    usuario = authenticate(
        request,
        username=username,
        password=password
    )

    if usuario is None:
        return JsonResponse(
            {"error": "Usuario o contraseña incorrectos"},
            status=401
        )

    if not usuario.is_active:
        return JsonResponse(
            {"error": "La cuenta no está habilitada"},
            status=403
        )

    login(request, usuario)

    return JsonResponse({
        "mensaje": "Inicio de sesión exitoso",
        "usuario": usuario.username
    })


@require_POST
def cerrar_sesion(request):
    logout(request)
    return JsonResponse({"mensaje": "Sesión cerrada"})


@require_GET
def usuario_actual(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {"autenticado": False},
            status=401
        )

    return JsonResponse({
        "autenticado": True,
        "usuario": request.user.username,
        "email": request.user.email,
    })