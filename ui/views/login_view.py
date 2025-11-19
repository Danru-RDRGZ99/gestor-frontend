import flet as ft
import os
import base64

from api_client import ApiClient
from ui.components.buttons import Primary, Ghost
from ui.components.cards import Card

def LoginView(page: ft.Page, api: ApiClient, on_success, is_mobile: bool):
    """
    Vista de inicio de sesión para la aplicación Flet.
    Usa una imagen de fondo desde URL para asegurar visualización inmediata,
    con fallback a archivo local o color sólido.
    """
    # Manejo de mensajes flash
    info = ft.Text("", color=ft.Colors.RED_400, size=12)
    flash = page.session.get("flash")
    if flash:
        info.value = flash
        page.session.remove("flash")

    # Campos del formulario
    user_field = ft.TextField(
        label="Usuario o Correo",
        prefix_icon=ft.Icons.PERSON,
        autofocus=True,
        text_size=14,
    )
    pwd_field = ft.TextField(
        label="Contraseña",
        password=True,
        can_reveal_password=True,
        prefix_icon=ft.Icons.LOCK,
        text_size=14,
        on_submit=lambda e: do_login(),
    )

    # Lógica de login
    def do_login():
        username = user_field.value.strip()
        password = pwd_field.value or ""
        if not username or not password:
            info.value = "Por favor, completa ambos campos."
            info.color = ft.Colors.RED_400
            page.update()
            return
        
        page.session.set("login_attempt", {"username": username, "password": password})
        page.go("/captcha-verify")

    # Botones
    btn_login = Primary("Entrar", on_click=lambda e: do_login(), width=260, height=46)
    btn_register = Ghost("Registrarse", on_click=lambda e: page.go("/register"), width=260, height=40)

    # Validación
    def validate(_):
        btn_login.disabled = not (user_field.value.strip() and pwd_field.value)
        page.update()

    user_field.on_change = validate
    pwd_field.on_change = validate
    validate(None)

    # --- Lógica del Logo ---
    LOGO_PATH = "ui/assets/a.png"
    logo_b64 = None
    try:
        if os.path.exists(LOGO_PATH):
            with open(LOGO_PATH, "rb") as image_file:
                logo_b64 = base64.b64encode(image_file.read()).decode("utf-8")
    except Exception as e:
        print(f"Error logo: {e}")

    if logo_b64:
        logo_content = ft.Image(src_base64=logo_b64, fit=ft.ImageFit.COVER)
    else:
        logo_content = ft.Icon(ft.Icons.SCIENCE, size=34)

    logo = ft.Container(content=logo_content, width=56, height=56, alignment=ft.alignment.center)

    # Encabezado y Formulario
    header = ft.Column(
        [
            logo,
            ft.Text("BLACKLAB", size=24, weight=ft.FontWeight.BOLD),
            ft.Text("Inicia sesión para gestionar reservas y recursos", size=12, opacity=0.8),
        ],
        spacing=8,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    form = ft.Column(
        controls=[
            header,
            ft.Divider(opacity=0.2),
            user_field,
            pwd_field,
            info,
            ft.Container(height=4),
            btn_login,
            ft.Container(height=20),
            btn_register,
        ],
        spacing=10,
        tight=True,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # --- FONDO DE PANTALLA (Estrategia URL + Local) ---
    
    # 1. URL de una imagen abstracta oscura (Funciona siempre que haya internet)
    bg_src = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=2564&auto=format&fit=crop"
    
    # 2. Si existe la imagen local que intentamos usar antes, la priorizamos
    local_bg_path = "ui/assets/dark_abstract_background.jpg"
    if os.path.exists(local_bg_path):
        bg_src = local_bg_path

    background_image_control = ft.Image(
        src=bg_src,
        fit=ft.ImageFit.COVER,
        expand=True,
        opacity=0.8, # Un poco de transparencia base
        # Fallback de seguridad en HEXADECIMAL para evitar errores de ft.Colors
        error_content=ft.Container(bgcolor="#0f172a") 
    )

    # Contenedor de la tarjeta
    card_container = ft.Container(
        content=Card(form, padding=22),
        width=440,
        border_radius=16,
        shadow=ft.BoxShadow(blur_radius=30, spread_radius=3, color=ft.Colors.with_opacity(0.5, ft.Colors.BLACK)), 
    )

    content_layer = ft.Container(
        content=ft.Row(
            [card_container],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.MainAxisAlignment.CENTER,
        ),
        expand=True,
        padding=20,
    )
    
    # Overlay para oscurecer la imagen y que el texto resalte
    overlay = ft.Container(bgcolor=ft.Colors.with_opacity(0.4, ft.Colors.BLACK), expand=True)

    main_container = ft.Container(
        expand=True,
        content=ft.Stack([
            background_image_control,
            overlay,
            content_layer
        ]),
        bgcolor="#000000" # Color de fondo base del contenedor principal
    )

    # Ajustes Móvil
    if is_mobile:
        card_container.width = None
        card_container.shadow = None
        card_container.border_radius = 0
        content_layer.padding = 0
        content_layer.content.vertical_alignment = ft.MainAxisAlignment.START
        # En móvil quitamos el overlay para que se vea más limpio
        if overlay in main_container.content.controls:
            main_container.content.controls.remove(overlay)

    return main_container
