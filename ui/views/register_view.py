import flet as ft
import re
from api_client import ApiClient
from ui.components.buttons import Primary, Ghost
from ui.components.cards import Card

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

def RegisterView(page: ft.Page, api: ApiClient, on_success):
    info = ft.Text("", size=12)

    nombre_field = ft.TextField(label="Nombre Completo", autofocus=True, text_size=14)
    correo_field = ft.TextField(label="Correo Electrónico", text_size=14)
    user_field = ft.TextField(label="Nombre de Usuario", text_size=14)
    rol_dd = ft.Dropdown(
        label="Rol",
        options=[
            ft.dropdown.Option("estudiante", "Estudiante"),
            ft.dropdown.Option("docente", "Docente"),
        ],
        value="estudiante"
    )
    pwd_field = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, text_size=14)
    confirm_pwd_field = ft.TextField(label="Confirmar Contraseña", password=True, can_reveal_password=True, text_size=14)

    is_mobile = page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]

    def clear_errors():
        info.value = ""
        info.color = ft.Colors.PRIMARY
        for f in (nombre_field, correo_field, user_field, pwd_field, confirm_pwd_field):
            f.error_text = None

    def show_alert(msg: str, is_error: bool = True):
        info.value = msg
        info.color = ft.Colors.RED_400 if is_error else ft.Colors.GREEN_600
        info.update()
        # En desktop además usamos SnackBar
        if not is_mobile:
            page.snack_bar = ft.SnackBar(
                content=ft.Text(msg),
                bgcolor=ft.Colors.ERROR_CONTAINER if is_error else ft.Colors.INVERSE_SURFACE
            )
            page.snack_bar.open = True
        page.update()

    def do_register(e):
        clear_errors()

        nombre = (nombre_field.value or "").strip()
        correo = (correo_field.value or "").strip().lower()
        usuario = (user_field.value or "").strip()
        rol = rol_dd.value
        password = pwd_field.value or ""
        confirm_password = confirm_pwd_field.value or ""

        missing = []
        if not nombre:
            nombre_field.error_text = "Requerido"
            missing.append("nombre")
        if not correo:
            correo_field.error_text = "Requerido"
            missing.append("correo")
        if not usuario:
            user_field.error_text = "Requerido"
            missing.append("usuario")
        if not rol:
            rol_dd.error_text = "Selecciona un rol"
            missing.append("rol")
        else:
            rol_dd.error_text = None
        if not password:
            pwd_field.error_text = "Requerido"
            missing.append("contraseña")
        if not confirm_password:
            confirm_pwd_field.error_text = "Requerido"
            missing.append("confirmación")

        if missing:
            show_alert("Completa los campos requeridos.", is_error=True)
            for f in (nombre_field, correo_field, user_field, pwd_field, confirm_pwd_field, rol_dd):
                if hasattr(f, "update"):
                    f.update()
            return

        if not EMAIL_REGEX.match(correo):
            correo_field.error_text = "Formato de correo inválido"
            correo_field.update()
            show_alert("El formato del correo electrónico no es válido.", is_error=True)
            return

        if len(password) < 6:
            pwd_field.error_text = "Mínimo 6 caracteres"
            pwd_field.update()
            show_alert("La contraseña debe tener al menos 6 caracteres.", is_error=True)
            return

        if password != confirm_password:
            confirm_pwd_field.error_text = "No coincide con la contraseña"
            confirm_pwd_field.update()
            show_alert("Las contraseñas no coinciden.", is_error=True)
            return

        user_data = {
            "nombre": nombre,
            "correo": correo,
            "user": usuario,
            "password": password,
            "rol": rol
        }

        result = api.register(user_data)

        if result and "error" not in result:
            show_alert("¡Registro exitoso! Ahora puedes iniciar sesión.", is_error=False)
            on_success()
        else:
            msg = "Error en el registro."
            if isinstance(result, dict):
                detail = result.get("error") or result.get("detail") or ""
                if isinstance(detail, str) and detail.strip():
                    msg = f"Error: {detail}"
                elif isinstance(detail, list) and detail:
                    msg = f"Error: {detail[0]}"
            show_alert(msg, is_error=True)

    header = ft.Column(
        [
            ft.Text("Crear una Cuenta", size=24, weight=ft.FontWeight.BOLD),
            ft.Text("Ingresa tus datos para registrarte en el sistema", size=12, opacity=0.8),
        ],
        spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )

    form = ft.Column(
        controls=[
            header, ft.Divider(opacity=0.2),
            nombre_field, correo_field, user_field, rol_dd,
            pwd_field, confirm_pwd_field,
            info, ft.Container(height=4),
            Primary("Registrarse", on_click=do_register, width=260, height=46),
            Ghost("Volver al Login", on_click=lambda e: page.go("/"), width=260, height=40)
        ],
        spacing=14,
        tight=True,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # --- Contenedor Card (igual que antes) ---
    if is_mobile:
        card_container = ft.Container(
            content=Card(form, padding=18),
            width=None,
            border_radius=16,
            shadow=None
        )
        outer_padding = ft.padding.symmetric(horizontal=12, vertical=12)
    else:
        card_container = ft.Container(
            content=Card(form, padding=22),
            width=440,
            border_radius=16,
            shadow=ft.BoxShadow(
                blur_radius=16, spread_radius=1,
                color=ft.Colors.with_opacity(0.18, ft.Colors.BLACK)
            ),
        )
        outer_padding = 20

    # --- NUEVO: Layout raíz scrollable + SafeArea ---
    # Hacemos scroll a nivel de la vista para que, al crecer por errores/teclado,
    # siempre puedas deslizar y alcanzar los botones.
    content_column = ft.Column(
        controls=[
            ft.Row(
                [card_container],
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            )
        ],
        expand=True,
        scroll=ft.ScrollMode.ADAPTIVE,   # <- scroll vertical
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    safe_root = ft.SafeArea(
        ft.Container(
            expand=True,
            content=content_column,
            padding=outer_padding
        )
    )

    return ft.View(
        "/register",
        [safe_root],
        scroll=ft.ScrollMode.ADAPTIVE,  # <- respaldo: la vista también permite scroll
    )
