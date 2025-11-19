import flet as ft
import os
import base64

from api_client import ApiClient
from ui.components.buttons import Primary, Ghost
from ui.components.cards import Card

def LoginView(page: ft.Page, api: ApiClient, on_success, is_mobile: bool):
    """
    Vista de inicio de sesión para BLACKLAB.
    Tema: Negro, Gris y Cian.
    Usa carga Base64 para el fondo para garantizar que se muestre la imagen local.
    """
    # --- Variables de Estilo ---
    THEME_CYAN = "#00E5FF"  # Cian vibrante
    THEME_BG = "#111111"    # Negro casi puro
    
    # Mensajes de error/info
    info = ft.Text("", color="#EF5350", size=12) # Red 400 hex
    flash = page.session.get("flash")
    if flash:
        info.value = flash
        page.session.remove("flash")

    # Campos de texto con estilo
    user_field = ft.TextField(
        label="Usuario o Correo",
        prefix_icon=ft.Icons.PERSON,
        autofocus=True,
        text_size=14,
        border_color="#424242", # Grey 800
        focused_border_color=THEME_CYAN,
        cursor_color=THEME_CYAN,
    )
    pwd_field = ft.TextField(
        label="Contraseña",
        password=True,
        can_reveal_password=True,
        prefix_icon=ft.Icons.LOCK,
        text_size=14,
        border_color="#424242", # Grey 800
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
            ft.Text("Inicia sesión para gestionar reservas y recursos", size=12, color="#BDBDBD"), # Grey 400
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

    # --- CONFIGURACIÓN DEL FONDO (MÉTODO BASE64) ---
    # URL por defecto (Cyberpunk)
    default_bg_url = "https://images.unsplash.com/photo-1614850523459-c2f4c699c52e?q=80&w=2070&auto=format&fit=crop"
    
    # Rutas locales posibles
    local_bg_options = ["ui/assets/background.jpg", "ui/assets/dark_abstract_background.jpg"]
    bg_src_base64 = None

    # Intentamos leer el archivo local y convertirlo a Base64
    for local_path in local_bg_options:
        if os.path.exists(local_path):
            try:
                with open(local_path, "rb") as f:
                    bg_src_base64 = base64.b64encode(f.read()).decode("utf-8")
                    print(f"Éxito: Fondo local cargado desde {local_path}")
                    break
            except Exception as e:
                print(f"Error leyendo imagen de fondo: {e}")

    # Configuramos el control de imagen
    if bg_src_base64:
        # Si leímos el archivo local con éxito
        bg_image_control = ft.Image(
            src_base64=bg_src_base64,
            fit=ft.ImageFit.COVER,
            expand=True,
            opacity=0.6
        )
    else:
        # Si falló todo lo local, usamos la URL
        bg_image_control = ft.Image(
            src=default_bg_url,
            fit=ft.ImageFit.COVER,
            expand=True,
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

    # Capa de contenido centrada
    content_layer = ft.Container(
        content=ft.Row(
            [card_content],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.MainAxisAlignment.CENTER,
        ),
        expand=True,
        padding=20, 
    )
    
    # Overlay oscuro
    overlay = ft.Container(
        bgcolor=ft.Colors.with_opacity(0.4, "#000000"), 
        expand=True
    )

    # Contenedor Principal con Stack
    main_container = ft.Container(
        expand=True,
        bgcolor=THEME_BG,
        padding=0,
        content=ft.Stack(
            controls=[
                bg_image_control, # 1. Fondo (Base64 o URL)
                overlay,          # 2. Capa oscura encima
                content_layer     # 3. Formulario al frente
            ],
            expand=True
        ),
        alignment=ft.alignment.center
    )

    # Ajustes Móvil
    if is_mobile:
        card_content.width = None
        card_content.shadow = None
        card_content.border_radius = 0
        content_layer.padding = 0
        content_layer.content.vertical_alignment = ft.MainAxisAlignment.START
        if overlay in main_container.content.controls:
            main_container.content.controls.remove(overlay)

    return main_container
