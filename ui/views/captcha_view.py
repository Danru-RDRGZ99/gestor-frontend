import flet as ft
from api_client import ApiClient
from ui.components.buttons import Primary, Ghost
from ui.components.cards import Card


def CaptchaView(page: ft.Page, api: ApiClient, on_success):
    # -----------------------------
    # Estado y mensajes
    # -----------------------------
    info = ft.Text(
        "",
        color=ft.Colors.RED_400,
        size=12,
        text_align=ft.TextAlign.CENTER,
    )

    # -----------------------------
    # CAPTCHA WIDGETS
    # -----------------------------
    captcha_image = ft.Image(
        src_base64=None,
        height=70,
        fit=ft.ImageFit.CONTAIN,
        col=8,
    )

    def refresh_captcha(e):
        """Solicita una nueva imagen CAPTCHA desde la API"""
        img_base64 = api.get_captcha_image()

        if img_base64:
            captcha_image.src_base64 = img_base64
        else:
            info.value = "Error al cargar CAPTCHA desde la API."
            info.color = ft.Colors.RED_400

        page.update()

    refresh_btn = ft.IconButton(
        icon=ft.Icons.REFRESH,
        on_click=refresh_captcha,
        tooltip="Refrescar imagen",
        col=4,
    )

    captcha_field = ft.TextField(
        label="Verifica que no eres un robot",
        autofocus=True,
        prefix_icon=ft.Icons.ABC,
        text_size=14,
        on_submit=lambda e: do_verify(),
        text_align=ft.TextAlign.CENTER,
        capitalization=ft.TextCapitalization.CHARACTERS,
    )

    # -----------------------------
    # Lógica principal
    # -----------------------------
    def do_verify():
        login_attempt = page.session.get("login_attempt")

        if not login_attempt:
            info.value = "Error de sesión. Regresa al login."
            info.color = ft.Colors.RED_400
            page.update()
            return

        username = login_attempt.get("username")
        password = login_attempt.get("password")
        captcha = captcha_field.value.strip()

        if not captcha:
            info.value = "Introduce el texto mostrado en la imagen."
            info.color = ft.Colors.RED_400
            page.update()
            return

        # Petición a la API
        response_data = api.login(username, password, captcha)

        if not response_data:
            info.value = "Error de conexión o API no disponible."
            info.color = ft.Colors.RED_400

        elif "error" in response_data:
            info.value = response_data.get("error", "Error desconocido")
            info.color = ft.Colors.RED_400

        else:
            # -----------------------------
            # ✅ FIX: evitar KeyError
            # -----------------------------
            if page.session.contains_key("login_attempt"):
                page.session.remove("login_attempt")

            # Guardar el usuario en sesión
            user_data = response_data.get("user")
            page.session.set("user_session", user_data)

            print(f"[CAPTCHA] Sesión validada. Usuario: {user_data}")

            on_success()
            return

        # Si falló, refrescar captcha
        refresh_captcha(None)
        captcha_field.value = ""
        page.update()

    # -----------------------------
    # Botones
    # -----------------------------
    btn_verify = Primary(
        "Verificar",
        on_click=lambda e: do_verify(),
        height=46,
    )

    btn_cancel = Ghost(
        "Cancelar",
        on_click=lambda e: page.go("/"),
        height=40,
    )

    def validate(_):
        btn_verify.disabled = not captcha_field.value.strip()
        page.update()

    captcha_field.on_change = validate
    validate(None)

    # Cargar captcha inicial
    refresh_captcha(None)

    # -----------------------------
    # Layout general
    # -----------------------------
    header = ft.Column(
        [
            ft.Icon(ft.Icons.SHIELD, size=34),
            ft.Text("Verificación Requerida", size=24, weight=ft.FontWeight.BOLD),
        ],
        spacing=8,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    form = ft.Column(
        controls=[
            header,
            ft.Divider(opacity=0.2),
            ft.ResponsiveRow(
                [captcha_image, refresh_btn],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=5,
            ),
            captcha_field,
            info,
            ft.Container(height=4),
            btn_verify,
            btn_cancel,
        ],
        spacing=14,
        tight=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    card_container = ft.Container(
        content=Card(form, padding=22),
        border_radius=16,
        shadow=ft.BoxShadow(
            blur_radius=16,
            spread_radius=1,
            color=ft.Colors.with_opacity(0.18, ft.Colors.BLACK),
        ),
        col={"xs": 12, "sm": 10, "md": 8, "lg": 6, "xl": 4},
    )

    return ft.Container(
        expand=True,
        content=ft.ResponsiveRow(
            [card_container],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=20,
    )
