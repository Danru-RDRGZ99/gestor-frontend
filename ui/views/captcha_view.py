import flet as ft
from api_client import ApiClient
from ui.components.buttons import Primary, Ghost
from ui.components.cards import Card

def CaptchaView(page: ft.Page, api: ApiClient, on_success):
    # --- Estado y Mensajes ---
    info = ft.Text("", color=ft.Colors.RED_400, size=12)

    # --- Widgets de CAPTCHA ---
    
    # Usamos src_base64
    captcha_image = ft.Image(
        # La fuente se cargará con la función refresh_captcha
        src_base64=None, 
        height=70,
        fit=ft.ImageFit.CONTAIN,
        col=8, # Ocupa 8 de 12 columnas
    )
    
    def refresh_captcha(e):
        # Usamos el nuevo método del API Client
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
        col=4, # Ocupa 4 de 12 columnas
    )
    
    captcha_field = ft.TextField(
        label="Verifica que no eres un robot",
        autofocus=True,
        prefix_icon=ft.Icons.ABC,
        text_size=14,
        on_submit=lambda e: do_verify(), # Permite enviar con Enter
        text_align=ft.TextAlign.CENTER,
        capitalization=ft.TextCapitalization.CHARACTERS,
    )

    def do_verify():
        # 1. Obtenemos las credenciales guardadas
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
        
        # 2. Ahora sí, llamamos a la API con todo
        response_data = api.login(username, password, captcha)
        
        # 3. Manejamos la respuesta
        if not response_data:
            info.value = "Error de conexión o API no disponible."
            info.color = ft.Colors.RED_400

        # --- INICIO DE LA CORRECCIÓN ---
        # Comprobamos si la llave 'error' existe en la respuesta
        elif "error" in response_data: 
            info.value = response_data.get("error", "Error desconocido") # Muestra el error
            info.color = ft.Colors.RED_400
        # --- FIN DE LA CORRECCIÓN ---

        else: # ¡Éxito!
            page.session.remove("login_attempt")
            
            # --- CORRECCIÓN EXTRA ---
            # Guardamos solo el objeto 'user' que viene dentro de la respuesta
            user_data = response_data.get("user")
            page.session.set("user_session", user_data)
            print(f"LOGIN Y CAPTCHA EXITOSO, SESIÓN GUARDADA: {user_data}")
            # --- FIN CORRECCIÓN EXTRA ---
            
            on_success()
            return 

        # Si falló (ej. captcha incorrecto), refrescamos la imagen
        refresh_captcha(None)
        captcha_field.value = ""
        page.update()

    # --- Acciones y Validación ---
    btn_verify = Primary("Verificar", on_click=lambda e: do_verify(), width=260, height=46)
    btn_cancel = Ghost("Cancelar", on_click=lambda e: page.go("/"), width=260, height=40)

    def validate(_):
        btn_verify.disabled = not captcha_field.value.strip()
        page.update()

    captcha_field.on_change = validate
    validate(None) # Llamada inicial

    # Carga inicial del CAPTCHA al mostrar la vista
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
    
    card_container = ft.Container(
        content=Card(form, padding=22),
        width=440,
        border_radius=16,
        shadow=ft.BoxShadow(
            blur_radius=16, spread_radius=1,
            color=ft.Colors.with_opacity(0.18, ft.Colors.BLACK)
        ),
    )

    return ft.Container(
        expand=True,
        content=ft.Row([card_container], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=20,
    )