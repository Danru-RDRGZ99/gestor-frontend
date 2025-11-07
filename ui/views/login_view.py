import flet as ft
from api_client import ApiClient
from ui.components.buttons import Primary, Secondary, TextButton
from ui.components.inputs import TextField

def LoginView(page: ft.Page, api: ApiClient):
    # --- Estado para mostrar/ocultar contraseña y CAPTCHA ---
    password_visible = ft.Ref[ft.IconButton]()
    captcha_row_visible = ft.Ref[ft.Row]()
    captcha_img = ft.Ref[ft.Image]()
    
    # --- Referencias a los campos de entrada ---
    username_field = TextField("Usuario o Correo")
    password_field = TextField("Contraseña", password=True, can_reveal_password=True)
    captcha_field = TextField("CAPTCHA", width=150)

    # --- Mensaje de error/información ---
    info_text = ft.Text("", color=ft.colors.RED_500, size=12)

    # --- Handlers de eventos ---
    def reload_captcha():
        # Llama a la API para obtener una nueva imagen de CAPTCHA
        captcha_b64 = api.get_captcha_image()
        if captcha_b64:
            captcha_img.current.src_base64 = captcha_b64
            captcha_img.current.update()
            captcha_field.current.value = ""
            captcha_field.current.update()
        else:
            info_text.value = "Error al cargar CAPTCHA."
            page.update()

    def do_login(e):
        info_text.value = "" # Limpiar mensaje previo

        if not username_field.value or not password_field.value:
            info_text.value = "Por favor, ingresa usuario y contraseña."
            page.update()
            return

        # Si el CAPTCHA no es visible, lo mostramos primero
        if not captcha_row_visible.current.visible:
            captcha_row_visible.current.visible = True
            reload_captcha() # Cargar el primer CAPTCHA
            page.update()
            return
        
        # Si ya está visible, intentamos el login con CAPTCHA
        if not captcha_field.value:
            info_text.value = "Por favor, ingresa el texto del CAPTCHA."
            page.update()
            return

        response = api.login(
            username_field.value,
            password_field.value,
            captcha_field.value
        )

        if response and "access_token" in response:
            page.session.set("user_session", response.get("user"))
            page.go("/dashboard")
        else:
            error_message = response.get("error", "Error de inicio de sesión. Verifica tus credenciales y el CAPTCHA.")
            info_text.value = error_message
            reload_captcha() # Recargar CAPTCHA en caso de error
            page.update()
    
    def do_login_with_google(e):
        # Esta es una simulación. En una app real, necesitarías:
        # 1. Un cliente OAuth de Google configurado en tu frontend.
        # 2. Abrir una ventana/pestaña para la autenticación de Google.
        # 3. Recibir el ID Token de Google después de que el usuario se autentique.
        # 4. Enviar ese ID Token a tu backend para verificación.
        # 5. Si el backend valida el token y retorna un token de sesión/JWT propio,
        #    entonces proceder con el login en tu aplicación.

        # Por ahora, simplemente muestra un mensaje.
        print("Intentando iniciar sesión con Google (simulado)...")
        info_text.value = "Funcionalidad de Google Login en desarrollo."
        page.update()
        # Aquí iría la lógica real de inicio de sesión con Google

    def go_to_register(e):
        page.go("/register")

    # --- Layout de la vista ---
    return ft.View(
        "/login",
        [
            ft.AppBar(title=ft.Text("Login"), bgcolor=page.theme.primary_color),
            ft.Container(
                content=ft.Column(
                    [
                        # --- INICIO DE LA MODIFICACIÓN ---
                        ft.Image(
                            src="/assets/a.png",  # Ruta de tu imagen (asume que está en la carpeta 'assets')
                            width=100,
                            height=100,
                            fit=ft.ImageFit.CONTAIN,
                        ),
                        ft.Text(
                            "Black Lab", # Título cambiado
                            size=24,
                            weight=ft.FontWeight.BOLD,
                        ),
                        # --- FIN DE LA MODIFICACIÓN ---
                        ft.Text("Inicia sesión para gestionar reservas y recursos"),
                        
                        ft.Container(height=20), # Espaciador
                        
                        username_field,
                        password_field,
                        
                        # CAPTCHA (inicialmente oculto)
                        ft.Row(
                            [
                                ft.Column([
                                    ft.Container(height=5), # Espaciador
                                    ft.Text("Ingresa el texto de la imagen:", size=12),
                                    ft.Image(ref=captcha_img, width=150, height=50, fit=ft.ImageFit.CONTAIN),
                                    TextButton("Recargar CAPTCHA", on_click=lambda e: reload_captcha())
                                ]),
                                captcha_field,
                            ],
                            visible=False,
                            ref=captcha_row_visible,
                            spacing=10,
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        
                        info_text, # Para mensajes de error o información
                        
                        ft.Container(height=20), # Espaciador
                        
                        Primary("Entrar", on_click=do_login, expand=True),
                        ft.Text("O", text_align=ft.TextAlign.CENTER, width=page.width),
                        Secondary("➡️ Entrar con Google", on_click=do_login_with_google, expand=True),
                        TextButton("Registrarse", on_click=go_to_register, expand=True)
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=15,
                    width=350, # Ancho fijo para el formulario
                ),
                alignment=ft.alignment.center,
                expand=True,
            )
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
    )
