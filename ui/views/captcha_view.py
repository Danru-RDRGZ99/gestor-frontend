import flet as ft
from api_client import ApiClient
from ui.components.buttons import Primary, Ghost
from ui.components.cards import Card

# --- INICIO DE LA CORRECCIÓN 1: Aceptar 'is_mobile' ---
def CaptchaView(page: ft.Page, api: ApiClient, on_success, is_mobile: bool):
# --- FIN DE LA CORRECCIÓN 1 ---
    
    # --- Estado y Mensajes ---
    info = ft.Text("", color=ft.Colors.RED_400, size=12)

    # --- Widgets de CAPTCHA ---
    captcha_image = ft.Image(
        src_base64=None, 
        height=70,
        fit=ft.ImageFit.CONTAIN,
        col=8,
    )
    
    def refresh_captcha(e):
        img_base64 = api.get_captcha_image() 
        
        if img_base64:
            captcha_image.src_base64 = img_base64
        else:
            info.value = "Error al cargar CAPTCHA. Revise la API."
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

    def do_verify():
        login_attempt = page.session.get("login_attempt")
        
        if not login_attempt:
            info.value = "Error de sesión. Por favor, vuelve a la página de login."
            info.color = ft.Colors.RED_400
            page.update()
            return

        username = login_attempt.get("username")
        password = login_attempt.get("password")
        captcha = captcha_field.value.strip()

        if not captcha:
            info.value = "Por favor, introduce el texto de la imagen."
            info.color = ft.Colors.RED_400
            page.update()
            return
        
        response_data = api.login(username, password, captcha)
        
        if not response_data:
            info.value = "Error de conexión o API no disponible."
            info.color = ft.Colors.RED_400
        elif "error" in response_data: 
            info.value = response_data.get("error", "Error desconocido")
            info.color = ft.Colors.RED_400
        else: 
            page.session.remove("login_attempt")
            user_data = response_data.get("user")
            page.session.set("user_session", user_data)
            print(f"LOGIN Y CAPTCHA EXITOSO, SESIÓN GUARDADA: {user_data}")
            on_success()
            return 

        refresh_captcha(None)
        captcha_field.value = ""
        page.update()

    btn_verify = Primary("Verificar", on_click=lambda e: do_verify(), width=260, height=46)
    btn_cancel = Ghost("Cancelar", on_click=lambda e: page.go("/"), width=260, height=40)

    def validate(_):
        btn_verify.disabled = not captcha_field.value.strip()
        page.update()

    captcha_field.on_change = validate
    validate(None)
    refresh_captcha(None)

    # --- Construcción del Layout ---
    header = ft.Column(
        [
            ft.Icon(ft.Icons.SHIELD, size=34),
            ft.Text("Verificación Requerida", size=24, weight=ft.FontWeight.BOLD),
        ],
        spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )
    form = ft.Column(
        controls=[
            header, 
            ft.Divider(opacity=0.2),
            ft.ResponsiveRow(
                [captcha_image, refresh_btn], 
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=5
            ),
            captcha_field,
            info, 
            ft.Container(height=4), 
            btn_verify, 
            btn_cancel
        ],
        spacing=14, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )
    
    # --- INICIO DE LA CORRECCIÓN 2: Lógica Responsiva (copiada de LoginView) ---

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
    #    OJO: Usamos ft.MainAxisAlignment.CENTER para el vertical_alignment del Row
    main_container = ft.Container(
        expand=True,
        content=ft.Row(
            [card_container], 
            alignment=ft.MainAxisAlignment.CENTER, 
            vertical_alignment=ft.MainAxisAlignment.CENTER # Centrado en PC
        ),
        padding=20,
    )

    # 3. Modificar si es móvil
    if is_mobile:
        card_container.width = None # Ocupa todo el ancho
        card_container.shadow = None # Sin sombra
        card_container.border_radius = 0 # Sin bordes (para que llene la pantalla)
        
        main_container.padding = 0 # Sin padding exterior
        
        # Alinear el contenedor principal arriba (para que el Row se pegue arriba)
        main_container.alignment = ft.alignment.top_center 
        
        # Alinear el Row interno arriba (para que la tarjeta se pegue arriba)
        main_container.content.vertical_alignment = ft.MainAxisAlignment.START 

    # 4. Devolver el contenedor principal configurado
    return main_container
    # --- FIN DE LA CORRECCIÓN 2 ---