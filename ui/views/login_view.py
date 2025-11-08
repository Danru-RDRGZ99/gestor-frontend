import flet as ft
import os
import base64 

from api_client import ApiClient
from ui.components.buttons import Primary, Ghost
from ui.components.cards import Card
from flet.auth.providers import GoogleOAuthProvider 

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "322045933748-h6d7muuo3thc9o53lktsu92uba3glin3.apps.googleusercontent.com")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "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")
REDIRECT_URL = os.getenv("GOOGLE_REDIRECT_URL", "http://localhost:8551/oauth_callback")

# --- INICIO DE LA CORRECCIÓN 1: Aceptar 'is_mobile' ---
def LoginView(page: ft.Page, api: ApiClient, on_success, is_mobile: bool):
# --- FIN DE LA CORRECCIÓN 1 ---

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
         return ft.View(
             "/login",
             [ft.Text("Error: Faltan GOOGLE_CLIENT_ID o GOOGLE_CLIENT_SECRET en las variables de entorno.")]
         )

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
        username = user_field.value.strip()
        password = pwd_field.value or ""

        if not username or not password:
            info.value = "Por favor, completa ambos campos."
            info.color = ft.Colors.RED_400
            page.update()
            return

        page.session.set("login_attempt", {
            "username": username,
            "password": password
        })
        page.go("/captcha-verify")


    def on_page_login(e: ft.LoginEvent):
        if e.error:
            error_desc = e.error_description or e.error
            info.value = f"Error de Google: {error_desc}"
            info.color = ft.Colors.RED_400
            page.update()
            return

        try:
            google_id_token = page.auth.user.token.id_token 
            print(f"DEBUG: ID Token recibido de Flet: {google_id_token[:30]}...")
        except AttributeError:
            info.value = "Error: No se pudo encontrar el ID Token en la respuesta de Flet."
            info.color = ft.Colors.RED_400
            print("ERROR: page.auth.user.token.id_token no encontrado en LoginEvent.")
            page.update()
            return
            
        resultado = api.login_with_google(google_id_token)

        # --- CORRECCIÓN: Guardar 'resultado.get("user")' en la sesión ---
        if resultado and "access_token" in resultado:
            page.session.set("user_session", resultado.get("user")) 
            on_success() 
        else:
            error_detalle = resultado.get("error", "Error desconocido") if isinstance(resultado, dict) else "Error"
            info.value = f"Error de API: {error_detalle}"
            info.color = ft.Colors.RED_400
            page.update()

    page.on_login = on_page_login

    google_provider = GoogleOAuthProvider(
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET, 
        redirect_url=REDIRECT_URL
    )
    
    def login_button_click(e):
        page.login(google_provider, scope=["openid", "email", "profile"])


    btn_login = Primary("Entrar", on_click=lambda e: do_login(), width=260, height=46)

    btn_google_login = ft.ElevatedButton(
        text="Entrar con Google",
        icon=ft.Icons.LOGIN,
        on_click=login_button_click,
        width=260,
    )

    btn_register = Ghost("Registrarse", on_click=lambda e: page.go("/register"), width=260, height=40)

    def validate(_):
        btn_login.disabled = not (user_field.value.strip() and pwd_field.value)
        page.update()

    user_field.on_change = validate
    pwd_field.on_change = validate
    validate(None)

    LOGO_PATH = "ui/assets/a.png" 
    
    logo_b64 = None
    try:
        if os.path.exists(LOGO_PATH):
            with open(LOGO_PATH, "rb") as image_file:
                logo_b64 = base64.b64encode(image_file.read()).decode('utf-8')
        else:
            print(f"ADVERTENCIA: No se encontró el logo en la ruta: {LOGO_PATH}")
    except Exception as e:
        print(f"Error al cargar el logo: {e}")

    if logo_b64:
        logo_content = ft.Image(
            src_base64=logo_b64, 
            fit=ft.ImageFit.COVER 
        )
    else:
        logo_content = ft.Icon(ft.Icons.SCIENCE, size=34) 

    logo = ft.Container(
        content=logo_content, 
        width=56, height=56,
        alignment=ft.alignment.center,
    )
    
    header = ft.Column(
        [
            logo, 
            ft.Text("BLACKLAB", size=24, weight=ft.FontWeight.BOLD),
            ft.Text("Inicia sesión para gestionar reservas y recursos", size=12, opacity=0.8),
        ],
        spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER
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
            ft.Row(
                [ft.Divider(), ft.Text("O", opacity=0.6), ft.Divider()],
                alignment=ft.MainAxisAlignment.CENTER, width=260
            ),
            btn_google_login,
            ft.Container(height=10),
            btn_register
        ],
        spacing=10,
        tight=True,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )

    # --- INICIO DE LA CORRECCIÓN 2: Lógica Responsiva ---

    # 1. Definir la tarjeta (versión escritorio por defecto)
    card_container = ft.Container(
        content=Card(form, padding=22),
        width=440,
        border_radius=16,
        shadow=ft.BoxShadow(
            blur_radius=16, spread_radius=1,
            color=ft.Colors.with_opacity(0.18, ft.Colors.BLACK)
        ),
    )

    # 2. Definir el contenedor principal (versión escritorio por defecto)
    main_container = ft.Container(
        expand=True,
        content=ft.Row([card_container], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.MainAxisAlignment.CENTER),
        padding=20,
    )

    # 3. Modificar si es móvil
    if is_mobile:
        card_container.width = None # Ocupa todo el ancho
        card_container.shadow = None # Sin sombra
        card_container.border_radius = 0
        main_container.padding = 0 # Sin padding exterior
        main_container.vertical_alignment = ft.MainAxisAlignment.START # Alinear arriba
        main_container.alignment = ft.alignment.top_center

    # 4. Devolver el contenedor principal configurado
    return main_container
    # --- FIN DE LA CORRECCIÓN 2 ---