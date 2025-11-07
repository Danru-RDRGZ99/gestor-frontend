import flet as ft
import os # Necesario para leer variables de entorno
# --- Imports necesarios ---
from api_client import ApiClient
from ui.components.buttons import Primary, Ghost
from ui.components.cards import Card
# --- Import Proveedor ---
from flet.auth.providers import GoogleOAuthProvider 

# --- CONSTANTES DE GOOGLE ---
# ¡IMPORTANTE! Asegúrate de que estas variables estén definidas en tu entorno
# Puedes usar un archivo .env y python-dotenv si lo prefieres
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "322045933748-h6d7muuo3thc9o53lktsu92uba3glin3.apps.googleusercontent.com") # Valor por defecto por si acaso
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "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") # Valor por defecto por si acaso
REDIRECT_URL = os.getenv("GOOGLE_REDIRECT_URL", "http://localhost:8551/oauth_callback")

def LoginView(page: ft.Page, api: ApiClient, on_success):

    # --- Verificar configuración ---
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
         return ft.View(
             "/login",
             [ft.Text("Error: Faltan GOOGLE_CLIENT_ID o GOOGLE_CLIENT_SECRET en las variables de entorno.")]
         )

    # --- Estado y Mensajes ---
    info = ft.Text("", color=ft.Colors.RED_400, size=12)
    flash = page.session.get("flash")
    if flash:
        info.value = flash
        page.session.remove("flash")

    # --- Campos del Formulario (Sin cambios) ---
    user_field = ft.TextField(
        label="Usuario o Correo",
        prefix_icon=ft.Icons.PERSON, # <-- Correcto aquí
        autofocus=True,
        text_size=14,
    )
    pwd_field = ft.TextField(
        label="Contraseña",
        password=True,
        can_reveal_password=True,
        prefix_icon=ft.Icons.LOCK, # <-- Correcto aquí
        text_size=14,
        on_submit=lambda e: do_login(), # Llama a la función que va al captcha
    )

    def do_login():
        """Guarda credenciales y redirige a la vista de CAPTCHA."""
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


    # --- ¡NUEVA FUNCIÓN CALLBACK DE GOOGLE (para page.on_login)! ---
    def on_page_login(e: ft.LoginEvent): # Cambié el nombre para evitar confusión
        """
        Callback que Flet llama DESPUÉS de page.login().
        Contiene el resultado del login con Google.
        """
        if e.error:
            # Manejar error si Flet no pudo obtener el token
            error_desc = e.error_description or e.error # Usa descripción si existe
            info.value = f"Error de Google: {error_desc}"
            info.color = ft.Colors.RED_400
            page.update()
            return

        # ¡Éxito! Flet nos da el token de Google. 
        # El token está DENTRO del objeto 'user' en el evento.
        try:
            # Accede al token ID a través del objeto 'user' y 'token'
            google_id_token = page.auth.user.token.id_token 
            print(f"DEBUG: ID Token recibido de Flet: {google_id_token[:30]}...") # Imprime inicio del token
        except AttributeError:
            info.value = "Error: No se pudo encontrar el ID Token en la respuesta de Flet."
            info.color = ft.Colors.RED_400
            print("ERROR: page.auth.user.token.id_token no encontrado en LoginEvent.")
            page.update()
            return
            
        # Llamamos al método del ApiClient (¡igual que antes!)
        resultado = api.login_with_google(google_id_token)

        # Procesamos la respuesta de NUESTRO backend (¡igual que antes!)
        if resultado and "access_token" in resultado:
            page.session.set("user_session", resultado) 
            on_success() # Llama al on_success (que te redirige)
        else:
            # Error del backend (ej. token inválido, error de servidor)
            error_detalle = resultado.get("detail", "Error desconocido")
            info.value = f"Error de API: {error_detalle}"
            info.color = ft.Colors.RED_400
            page.update()

    # --- ASIGNAR EL CALLBACK A LA PÁGINA ---
    page.on_login = on_page_login

    # --- ¡PROVEEDOR DE GOOGLE (CON ARGUMENTOS REQUERIDOS)! ---
    google_provider = GoogleOAuthProvider(
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET, 
        redirect_url=REDIRECT_URL # Asegúrate que esta URL esté en Google Cloud Console       
    )
    
    # --- Función que llama page.login ---
    def login_button_click(e):
        # Inicia el flujo de login usando el proveedor
        page.login(google_provider, scope=["openid", "email", "profile"]) # Añadir scope es buena práctica


    # --- Acciones y Validación ---
    btn_login = Primary("Entrar", on_click=lambda e: do_login(), width=260, height=46)

    # Botón de Login con Google (Ahora es un botón normal que llama a page.login)
    btn_google_login = ft.ElevatedButton( # O ft.OutlinedButton, etc.
        text="Entrar con Google",
        icon=ft.Icons.LOGIN, # <-- ¡CORREGIDO!
        on_click=login_button_click, # Llama a la función que inicia page.login
        width=260,
    )

    btn_register = Ghost("Registrarse", on_click=lambda e: page.go("/register"), width=260, height=40)

    def validate(_):
        btn_login.disabled = not (user_field.value.strip() and pwd_field.value)
        page.update()

    user_field.on_change = validate
    pwd_field.on_change = validate
    validate(None)

    # --- Construcción del Layout (Sin cambios, excepto el botón de Google) ---
    logo = ft.Container(
        # --- CAMBIO AQUÍ ---
        content=ft.Image(
            src="a.png"  # Flet ya sabe que está en "assets"
        ),
        # --- FIN DEL CAMBIO ---
        width=56, height=56,
        bgcolor=ft.Colors.PRIMARY_CONTAINER,
        border_radius=999, 
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
            btn_google_login, # Ahora es el ElevatedButton
            ft.Container(height=10),
            btn_register
        ],
        spacing=10,
        tight=True,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
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