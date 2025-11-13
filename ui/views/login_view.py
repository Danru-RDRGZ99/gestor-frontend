import flet as ft
import os
import base64
import webbrowser

from api_client import ApiClient
from ui.components.buttons import Primary, Ghost
from ui.components.cards import Card
from ui.components.google_oauth import GoogleLoginDialog, GoogleLoginButton


def LoginView(page: ft.Page, api: ApiClient, on_success, is_mobile: bool):
    """
    Login view with support for:
    - Username/Email + Password + CAPTCHA
    - Google OAuth2 authentication
    """
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
    )
    pwd_field = ft.TextField(
        label="Contraseña",
        password=True,
        can_reveal_password=True,
        prefix_icon=ft.Icons.LOCK,
        text_size=14,
        on_submit=lambda e: do_login(),
    )

    def do_login():
        """Handle username/password login with CAPTCHA"""
        username = user_field.value.strip()
        password = pwd_field.value or ""
        if not username or not password:
            info.value = "Por favor, completa ambos campos."
            info.color = ft.Colors.RED_400
            page.update()
            return
        page.session.set("login_attempt", {"username": username, "password": password})
        page.go("/captcha-verify")

    def start_google_login(e):
        """
        Initiates Google OAuth2 login flow:
        1. Opens instructions dialog
        2. User follows steps to get Google ID Token
        3. Pastes token and authenticates
        """
        # Show Google login dialog
        google_dialog = GoogleLoginDialog(
            page=page,
            api_client=api,
            on_success=on_success,
            on_error=lambda err: _show_error(f"Google Login Error: {err}")
        )
        
        # Open browser to Google Sign-In
        try:
            # Create a simple HTML page that shows instructions
            instructions_url = "https://myaccount.google.com"  # Placeholder
            webbrowser.open(instructions_url)
        except Exception:
            pass  # If browser can't open, the dialog still works
        
        google_dialog.show()

    def _show_error(message: str):
        """Show error message"""
        info.value = message
        info.color = ft.Colors.RED_400
        page.update()

    btn_login = Primary("Entrar", on_click=lambda e: do_login(), width=260, height=46)
    btn_register = Ghost("Registrarse", on_click=lambda e: page.go("/register"), width=260, height=40)
    btn_google = GoogleLoginButton(on_click_handler=start_google_login, width=260, height=44)

    def validate(_):
        """Validate login form"""
        btn_login.disabled = not (user_field.value.strip() and pwd_field.value)
        page.update()

    user_field.on_change = validate
    pwd_field.on_change = validate
    validate(None)

    # Load logo
    LOGO_PATH = "ui/assets/a.png"
    logo_b64 = None
    try:
        if os.path.exists(LOGO_PATH):
            with open(LOGO_PATH, "rb") as image_file:
                logo_b64 = base64.b64encode(image_file.read()).decode("utf-8")
        else:
            print(f"ADVERTENCIA: No se encontró el logo en la ruta: {LOGO_PATH}")
    except Exception as e:
        print(f"Error al cargar el logo: {e}")

    if logo_b64:
        logo_content = ft.Image(src_base64=logo_b64, fit=ft.ImageFit.COVER)
    else:
        logo_content = ft.Icon(ft.Icons.SCIENCE, size=34)

    logo = ft.Container(content=logo_content, width=56, height=56, alignment=ft.alignment.center)

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
            ft.Container(height=10),
            ft.Text("O", size=12, opacity=0.6, text_align=ft.TextAlign.CENTER, width=260),
            ft.Container(height=6),
            btn_google,
            ft.Container(height=10),
            btn_register,
        ],
        spacing=10,
        tight=True,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    card_container = ft.Container(
        content=Card(form, padding=22),
        width=440,
        border_radius=16,
        shadow=ft.BoxShadow(blur_radius=16, spread_radius=1, color=ft.Colors.with_opacity(0.18, ft.Colors.BLACK)),
    )

    main_container = ft.Container(
        expand=True,
        content=ft.Row([card_container], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.MainAxisAlignment.CENTER),
        padding=20,
    )

    if is_mobile:
        card_container.width = None
        card_container.shadow = None
        card_container.border_radius = 0
        main_container.padding = 0
        main_container.vertical_alignment = ft.MainAxisAlignment.START
        main_container.alignment = ft.alignment.top_center

    return main_container
