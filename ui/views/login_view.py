import flet as ft
import os
import base64

from api_client import ApiClient
from ui.components.buttons import Primary, Ghost
from ui.components.cards import Card

def LoginView(page: ft.Page, api: ApiClient, on_success, is_mobile: bool):
    """
    Vista de inicio de sesión para BLACKLAB.
    Corrección: Fuerza los márgenes de la página a 0 y usa anclaje absoluto para el fondo.
    """
    # --- CORRECCIÓN CRÍTICA DE PANTALLA ---
    # Forzamos que la página no tenga márgenes para que el fondo llegue al borde
    page.padding = 0
    page.spacing = 0
    # Aseguramos que la alineación base no interfiera
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.START
    page.update() # Aplicamos los cambios inmediatamente

    # --- Variables de Estilo ---
    THEME_CYAN = "#00E5FF"
    THEME_BG = "#111111"
    
    info = ft.Text("", color="#EF5350", size=12)
    flash = page.session.get("flash")
    if flash:
        info.value = flash
        page.session.remove("flash")

    # Campos de texto
    user_field = ft.TextField(
        label="Usuario o Correo",
        prefix_icon=ft.Icons.PERSON,
        autofocus=True,
        text_size=14,
        border_color="#424242",
        focused_border_color=THEME_CYAN,
        cursor_color=THEME_CYAN,
    )
    pwd_field = ft.TextField(
        label="Contraseña",
        password=True,
        can_reveal_password=True,
        prefix_icon=ft.Icons.LOCK,
        text_size=14,
        border_color="#424242",
        focused_border_color=THEME_CYAN,
        cursor_color=THEME_CYAN,
        on_submit=lambda e: do_login(),
    )

    def do_login():
        username = user_field.value.strip()
        password = pwd_field.value or ""
        if not username or not password:
            info.value = "Por favor, completa ambos campos."
            info.color = "#EF5350"
            page.update()
            return
        
        page.session.set("login_attempt", {"username": username, "password": password})
        page.go("/captcha-verify")

    btn_login = Primary("Entrar", on_click=lambda e: do_login(), width=260, height=46)
    btn_register = Ghost("Registrarse", on_click=lambda e: page.go("/register"), width=260, height=40)

    def validate(_):
        btn_login.disabled = not (user_field.value.strip() and pwd_field.value)
        page.update()

    user_field.on_change = validate
    pwd_field.on_change = validate
    validate(None)

    # --- Logo (Base64) ---
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
        logo_content = ft.Icon(ft.Icons.SCIENCE, size=34, color=THEME_CYAN)

    logo = ft.Container(
        content=logo_content, 
        width=56, height=56, 
        alignment=ft.alignment.center,
        shadow=ft.BoxShadow(blur_radius=20, color=ft.Colors.with_opacity(0.2, THEME_CYAN))
    )

    # Estructura del Formulario
    header = ft.Column(
        [
            logo,
            ft.Text("BLACKLAB", size=24, weight=ft.FontWeight.BOLD, color="white"),
            ft.Text("Inicia sesión para gestionar reservas y recursos", size=12, color="#BDBDBD"),
        ],
        spacing=8,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    form = ft.Column(
        controls=[
            header,
            ft.Divider(color="#424242"),
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

    # --- FONDO ---
    default_bg_url = "https://images.unsplash.com/photo-1614850523459-c2f4c699c52e?q=80&w=2070&auto=format&fit=crop"
    local_bg_options = ["ui/assets/background.jpg", "ui/assets/dark_abstract_background.jpg"]
    bg_src_base64 = None

    for local_path in local_bg_options:
        if os.path.exists(local_path):
            try:
                with open(local_path, "rb") as f:
                    bg_src_base64 = base64.b64encode(f.read()).decode("utf-8")
                    break
            except Exception:
                pass

    if bg_src_base64:
        bg_image_control = ft.Image(
            src_base64=bg_src_base64,
            fit=ft.ImageFit.COVER,
            opacity=0.6
        )
    else:
        bg_image_control = ft.Image(
            src=default_bg_url,
            fit=ft.ImageFit.COVER,
            opacity=0.6,
            error_content=ft.Container(bgcolor=THEME_BG)
        )

    # Tarjeta de Login
    card_content = ft.Container(
        content=Card(form, padding=22),
        width=440,
        border_radius=16,
        shadow=ft.BoxShadow(
            blur_radius=40, 
            spread_radius=0, 
            color=ft.Colors.with_opacity(0.15, THEME_CYAN)
        ), 
    )

    # --- ESTRUCTURA FINAL (SOLUCIÓN A CORTE DE PANTALLA) ---
    # Usamos un Stack que ocupe todo.
    # Clave: Configuramos el fondo para anclarse a los 4 bordes (left=0, top=0, etc)
    
    main_stack = ft.Stack(
        controls=[
            # 1. Fondo Anclado: Esto fuerza a la imagen a estirarse a todo el contenedor padre
            ft.Container(
                content=bg_image_control,
                left=0,
                top=0,
                right=0,
                bottom=0,
            ),
            # 2. Overlay Anclado
            ft.Container(
                bgcolor=ft.Colors.with_opacity(0.4, "#000000"),
                left=0,
                top=0,
                right=0,
                bottom=0,
            ),
            # 3. Formulario Centrado (Sin anclaje, usando alignment del padre)
            ft.Container(
                content=card_content,
                alignment=ft.alignment.center, # Centra la tarjeta en el stack
            )
        ],
        expand=True # El Stack se expande para llenar el contenedor principal
    )

    main_container = ft.Container(
        content=main_stack,
        expand=True, # El contenedor principal se expande para llenar la página
        bgcolor=THEME_BG,
        padding=0,
        margin=0,
        alignment=ft.alignment.center
    )

    if is_mobile:
        card_content.width = None
        card_content.shadow = None
        card_content.border_radius = 0
        # En móvil simplificamos
        main_container.content = ft.Column([card_content], alignment=ft.MainAxisAlignment.START)

    return main_container
