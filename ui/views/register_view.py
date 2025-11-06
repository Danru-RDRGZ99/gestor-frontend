import flet as ft
import re
from api_client import ApiClient
from ui.components.buttons import Primary, Ghost
from ui.components.cards import Card

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

def RegisterView(page: ft.Page, api: ApiClient, on_success):
    """
    Vista de registro de nuevos usuarios.
    """
    info = ft.Text("", color=ft.Colors.RED_400, size=12)

    # --- Campos del Formulario ---
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

    def show_snack(msg: str, is_error: bool = False):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(msg),
            bgcolor=ft.Colors.ERROR_CONTAINER if is_error else ft.Colors.INVERSE_SURFACE
        )
        page.snack_bar.open = True
        page.update()

    def do_register(e):
        # --- Validaciones ---
        nombre = nombre_field.value.strip()
        correo = correo_field.value.strip().lower()
        usuario = user_field.value.strip()
        rol = rol_dd.value
        password = pwd_field.value
        confirm_password = confirm_pwd_field.value

        if not all([nombre, correo, usuario, password, confirm_password, rol]):
            show_snack("Por favor, completa todos los campos.", is_error=True)
            return
        if not EMAIL_REGEX.match(correo):
            show_snack("El formato del correo electrónico no es válido.", is_error=True)
            return
        if len(password) < 6:
            show_snack("La contraseña debe tener al menos 6 caracteres.", is_error=True)
            return
        if password != confirm_password:
            show_snack("Las contraseñas no coinciden.", is_error=True)
            return

        # --- Llamada a la API ---
        result = api.register(nombre, correo, usuario, password, rol)
        
        if result:
            show_snack("¡Registro exitoso! Ahora puedes iniciar sesión.")
            # Llama a la función on_success para redirigir (ej. al login)
            on_success()
        else:
            # api_client se encarga de imprimir el detalle del error en la consola.
            show_snack("Error en el registro. El usuario o correo ya podría existir.", is_error=True)

    # --- Layout ---
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
        spacing=14, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )
    
    card_container = ft.Container(
        content=Card(form, padding=22),
        width=440,
        border_radius=16,
        shadow=ft.BoxShadow(
            blur_radius=16, spread_radius=1,
            color=ft.Colors.with_opacity(0.18, ft.Colors.BLACK)
        ),
    )

    return ft.View(
        "/register",
        [
            ft.Container(
                expand=True,
                content=ft.Row([card_container], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=20,
            )
        ]
    )
