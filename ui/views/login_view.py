import flet as ft
import os
import base64

from api_client import ApiClient
from ui.components.buttons import Primary, Ghost
from ui.components.cards import Card

def LoginView(page: ft.Page, api: ApiClient, on_success, is_mobile: bool):
    """
    Vista de inicio de sesión para la aplicación Flet.
    Incluye una imagen de fondo local 'dark_abstract_background.jpg' con un overlay 
    para mejorar la legibilidad del contenido.
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
        """Maneja el intento de inicio de sesión de credenciales."""
        username = user_field.value.strip()
        password = pwd_field.value or ""
        if not username or not password:
            info.value = "Por favor, completa ambos campos."
            info.color = ft.Colors.RED_400
            page.update()
            return
        
        # Guarda las credenciales en la sesión y redirige para verificación (e.g., Captcha)
        page.session.set("login_attempt", {"username": username, "password": password})
        page.go("/captcha-verify")

    btn_login = Primary("Entrar", on_click=lambda e: do_login(), width=260, height=46)
    btn_register = Ghost("Registrarse", on_click=lambda e: page.go("/register"), width=260, height=40)

    def validate(_):
        """Habilita/deshabilita el botón de login basado en si los campos están llenos."""
        btn_login.disabled = not (user_field.value.strip() and pwd_field.value)
        page.update()

    user_field.on_change = validate
    pwd_field.on_change = validate
    validate(None)

    # --- Lógica de carga de Logo (si tienes un logo específico) ---
    LOGO_PATH = "ui/assets/a.png" # Asegúrate de que esta ruta sea correcta para tu logo
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
        logo_content = ft.Icon(ft.Icons.SCIENCE, size=34) # Ícono de fallback si no hay logo

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
            ft.Container(height=20),
            btn_register,
        ],
        spacing=10,
        tight=True,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # --- Contenedor principal con fondo de imagen y ajustes de responsividad ---
    
    # 1. Ruta local de la imagen de fondo generada
    BACKGROUND_IMAGE_PATH = "ui/assets/dark_abstract_background.png"

    # Verificar si la imagen existe localmente. Si no, usa un color de fondo.
    if os.path.exists(BACKGROUND_IMAGE_PATH):
        background_image_control = ft.Image(
            src=BACKGROUND_IMAGE_PATH,
            fit=ft.ImageFit.COVER,
            expand=True
        )
    else:
        print(f"ADVERTENCIA: No se encontró la imagen de fondo en la ruta: {BACKGROUND_IMAGE_PATH}. Usando color de fondo oscuro.")
        background_image_control = ft.Container(bgcolor=ft.colors.BLACK, expand=True) # Fallback a un color sólido oscuro
        
    # 2. El card de login, ligeramente ajustado para mejor sombra sobre el fondo.
    card_container = ft.Container(
        content=Card(form, padding=22),
        width=440,
        border_radius=16,
        # Sombra más pronunciada para que el card blanco resalte sobre el fondo.
        shadow=ft.BoxShadow(blur_radius=30, spread_radius=3, color=ft.colors.with_opacity(0.5, ft.colors.BLACK)), 
    )

    # 3. Capa de contenido: Centra el card y le aplica el padding.
    content_layer = ft.Container(
        content=ft.Row(
            [card_container],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.MainAxisAlignment.CENTER,
        ),
        expand=True,
        padding=20,
    )
    
    # 4. Overlay oscuro para asegurar la legibilidad de la tarjeta.
    # Ajustado a un 40% de opacidad para que la imagen de fondo se vea un poco más.
    overlay = ft.Container(bgcolor=ft.colors.with_opacity(0.4, ft.colors.BLACK), expand=True)

    # El contenedor principal es ahora un Stack para apilar los elementos
    main_container = ft.Container(
        expand=True,
        content=ft.Stack([
            background_image_control, # Usamos el control que puede ser imagen o color
            overlay,
            content_layer
        ]),
    )

    if is_mobile:
        # Ajustes específicos para móvil: el card ocupa todo el ancho y pierde sombra/bordes.
        card_container.width = None
        card_container.shadow = None
        card_container.border_radius = 0
        
        # Ajustar la capa de contenido
        content_layer.padding = 0
        
        # El Row interno se alinea arriba para que el contenido no quede centrado verticalmente
        content_layer.content.vertical_alignment = ft.MainAxisAlignment.START
        
        # Quitar o reducir la opacidad del overlay en móvil para que el fondo se vea más claro
        # Aquí lo quitamos, pero podrías ajustar su opacidad si prefieres mantenerlo.
        main_container.content.controls.remove(overlay) 

    return main_container
