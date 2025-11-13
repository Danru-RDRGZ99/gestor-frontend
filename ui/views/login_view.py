import flet as ft
import os
import base64

from api_client import ApiClient
from ui.components.buttons import Primary, Ghost
from ui.components.cards import Card

def LoginView(page: ft.Page, api: ApiClient, on_success, is_mobile: bool):
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
        page.session.set("login_attempt", {"username": username, "password": password})
        page.go("/captcha-verify")

    btn_login = Primary("Entrar", on_click=lambda e: do_login(), width=260, height=46)
    btn_register = Ghost("Registrarse", on_click=lambda e: page.go("/register"), width=260, height=40)

    # --- Google Sign-In button and helper dialog ---
    def start_google_login(e):
        """
        Abre el navegador apuntando al endpoint de inicio de OAuth en el backend
        (por convención: /auth/google). Luego muestra un cuadro de diálogo donde
        el usuario puede pegar un idToken si el backend/flujo lo devuelve al usuario.

        Nota: Este flujo es una solución genérica. Idealmente el backend debería
        manejar la redirección y devolver una sesión; aquí ofrecemos una forma
        manual de completar el inicio si se obtiene un idToken.
        """
        auth_url = f"{api.base_url}/auth/google"
        try:
            # intentar abrir en el navegador del sistema
            import webbrowser
            webbrowser.open(auth_url)
        except Exception:
            try:
                ft.launch_url(auth_url)
            except Exception:
                print(f"No se pudo abrir el navegador para: {auth_url}")

        id_field = ft.TextField(label="ID Token (opcional)", hint_text="Pega aquí el idToken si tu backend lo muestra", width=420)
        status = ft.Text("", color=ft.Colors.RED_400, size=12)

        def submit_idtoken(ev):
            idt = (id_field.value or "").strip()
            if not idt:
                status.value = "Debes pegar un idToken o completar el flujo en el navegador."
                page.update()
                return
            status.value = "Verificando..."
            page.update()
            result = api.login_with_google(idt)
            if result and isinstance(result, dict) and result.get("access_token"):
                # almacenamiento mínimo de sesión; el backend debería retornar datos de usuario
                user_info = result.get("user") if isinstance(result.get("user"), dict) else {"user": result.get("user", "usuario")}
                page.session.set("user_session", {"user": user_info.get("user", "usuario"), "rol": result.get("rol", "")})
                dialog.open = False
                page.update()
                on_success()
            else:
                err = "Error autenticando con Google"
                if isinstance(result, dict) and result.get("error"):
                    err = result.get("error")
                status.value = err
                page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Iniciar sesión con Google"),
            content=ft.Column([
                ft.Text("Se abrirá el navegador para completar el flujo. Si obtienes un idToken, pégalo aquí y pulsa Continuar."),
                id_field,
                status
            ], tight=True),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda ev: (setattr(dialog, 'open', False), page.update())),
                ft.FilledButton("Continuar", on_click=submit_idtoken),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.dialog = dialog
        dialog.open = True
        page.update()

    # botón Google (estético simple). Puedes cambiar a Tonal/Outline o añadir imagen de logo.
    btn_google = ft.OutlinedButton("Iniciar sesión con Google", icon=ft.Icon(ft.Icons.LOGIN), on_click=start_google_login, width=260, height=44)

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
