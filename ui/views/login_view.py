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
    """
    # --- Variables de Estilo ---
    # Definimos los colores del tema aquí para usarlos consistentemente
    THEME_CYAN = "#00E5FF"  # Cian vibrante tipo neón
    THEME_BG = "#111111"    # Negro casi puro
    
    info = ft.Text("", color=ft.Colors.RED_400, size=12)
    flash = page.session.get("flash")
    if flash:
        info.value = flash
        page.session.remove("flash")

    user_field = ft.TextField(
        label="Usuario o Correo",
        prefix_icon=ft.Icons.PERSON,
        autofocus=True,
        text_size=14,
        border_color=ft.Colors.GREY_800,
        focused_border_color=THEME_CYAN, # Borde cian al enfocar
        cursor_color=THEME_CYAN,
    )
    pwd_field = ft.TextField(
        label="Contraseña",
        password=True,
        can_reveal_password=True,
        prefix_icon=ft.Icons.LOCK,
        text_size=14,
        border_color=ft.Colors.GREY_800,
        focused_border_color=THEME_CYAN,
        cursor_color=THEME_CYAN,
        on_submit=lambda e: do_login(),
    )

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

    # Botones personalizados (Si tus componentes Primary/Ghost aceptan color, genial. 
    # Si no, se verán con el estilo por defecto).
    btn_login = Primary("Entrar", on_click=lambda e: do_login(), width=260, height=46)
    btn_register = Ghost("Registrarse", on_click=lambda e: page.go("/register"), width=260, height=40)

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
        # Logo con un filtro de color sutil si es transparente, o natural
        logo_content = ft.Image(src_base64=logo_b64, fit=ft.ImageFit.COVER)
    else:
        # Fallback: Icono coloreado con el tema Cian
        logo_content = ft.Icon(ft.Icons.SCIENCE, size=34, color=THEME_CYAN)

    logo = ft.Container(
        content=logo_content, 
        width=56, height=56, 
        alignment=ft.alignment.center,
        # Sutil brillo cian detrás del logo
        shadow=ft.BoxShadow(blur_radius=20, color=ft.Colors.with_opacity(0.2, THEME_CYAN))
    )

    header = ft.Column(
        [
            logo,
            ft.Text("BLACKLAB", size=24, weight=ft.FontWeight.BOLD, color="white"),
            ft.Text("Inicia sesión para gestionar reservas y recursos", size=12, color=ft.Colors.GREY_400),
        ],
        spacing=8,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    form = ft.Column(
        controls=[
            header,
            ft.Divider(color=ft.Colors.GREY_800),
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

    # --- CONFIGURACIÓN DEL FONDO ---
    
    # 1. URL Web: Una imagen abstracta tecnológica oscura con toques cian/azules
    #    (Cyberpunk/Tech style)
    bg_src = "https://images.unsplash.com/photo-1535868463750-c78d9543614f?q=80&w=2000&auto=format&fit=crop"
    
    # 2. Archivo Local: Si guardas la imagen generada como 'background.jpg', se usará esa.
    local_bg_options = ["ui/assets/background.jpg", "ui/assets/dark_abstract_background.jpg"]
    
    for local_path in local_bg_options:
        if os.path.exists(local_path):
            bg_src = local_path
            print(f"Usando fondo local: {bg_src}")
            break

    background_image = ft.Image(
        src=bg_src,
        fit=ft.ImageFit.COVER,
        expand=True,
        opacity=0.7, # Transparencia para que no compita con el formulario
        error_content=ft.Container(bgcolor=THEME_BG) # Fallback seguro
    )

    card_content = ft.Container(
        content=Card(form, padding=22),
        width=440,
        border_radius=16,
        # Sombra con un toque muy sutil de cian para integrarlo
        shadow=ft.BoxShadow(
            blur_radius=40, 
            spread_radius=0, 
            color=ft.Colors.with_opacity(0.1, THEME_CYAN)
        ), 
    )

    content_layer = ft.Container(
        content=ft.Row(
            [card_content],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.MainAxisAlignment.CENTER,
        ),
        expand=True,
        padding=20,
    )
    
    # Overlay: Un degradado sutil o color plano para unificar
    # Usamos un gris muy oscuro con opacidad
    overlay = ft.Container(
        bgcolor=ft.Colors.with_opacity(0.5, "#000000"), 
        expand=True
    )

    main_container = ft.Container(
        expand=True,
        content=ft.Stack([
            ft.Container(bgcolor=THEME_BG, expand=True), # Fondo base sólido por si la imagen falla
            background_image,
            overlay,
            content_layer
        ]),
    )

    if is_mobile:
        card_content.width = None
        card_content.shadow = None
        card_content.border_radius = 0
        content_layer.padding = 0
        content_layer.content.vertical_alignment = ft.MainAxisAlignment.START
        if overlay in main_container.content.controls:
            main_container.content.controls.remove(overlay)

    return main_container
