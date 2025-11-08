import os
import flet as ft
import sys
import base64  # <--- Importación clave

# Configuración para Railway
port = int(os.environ.get("PORT", 8501))

print("=== INICIANDO APLICACIÓN ===")
print("Estructura detectada:")
for item in os.listdir('.'):
    if os.path.isdir(item):
        print(f"📁 {item}/")

# Agregar directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importar módulos desde ui.views
try:
    from ui.views import (
        login_view,
        register_view,
        dashboard_view,
        planteles_view,
        laboratorios_view,
        reservas_view,
        prestamos_view,
        settings_view,
        captcha_view,
        horarios_admin_view,
    )
    print("✅ Todas las vistas importadas correctamente")
    VIEWS_AVAILABLE = True
except ImportError as e:
    print(f"❌ Error importando vistas: {e}")
    VIEWS_AVAILABLE = False
    # Crear placeholders de emergencia
    class EmergencyView(ft.Column):
        def __init__(self, *args, **kwargs):
            super().__init__()
            self.controls = [ft.Text("Sistema de Gestión de Laboratorios", size=20)]
            self.expand = True
            self.alignment = ft.MainAxisAlignment.CENTER
            self.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    login_view = type('login_view', (), {'LoginView': EmergencyView})()
    register_view = type('register_view', (), {'RegisterView': EmergencyView})()
    dashboard_view = type('dashboard_view', (), {'DashboardView': EmergencyView})()
    planteles_view = type('planteles_view', (), {'PlantelesView': EmergencyView})()
    laboratorios_view = type('laboratorios_view', (), {'LaboratoriosView': EmergencyView})()
    reservas_view = type('reservas_view', (), {'ReservasView': EmergencyView})()
    prestamos_view = type('prestamos_view', (), {'PrestamosView': EmergencyView})()
    settings_view = type('settings_view', (), {'SettingsView': EmergencyView})()
    captcha_view = type('captcha_view', (), {'CaptchaView': EmergencyView})()
    horarios_admin_view = type('horarios_admin_view', (), {'HorariosAdminView': EmergencyView})()

# Importar otros módulos
try:
    from ui.theme import apply_theme
    print("✅ Tema importado correctamente")
except ImportError as e:
    print(f"❌ Error importando tema: {e}")
    def apply_theme(page, theme_mode=None):
        page.theme_mode = theme_mode or ft.ThemeMode.LIGHT
        page.update()

try:
    from api_client import ApiClient
    print("✅ ApiClient importado correctamente")
except ImportError as e:
    print(f"❌ Error importando ApiClient: {e}")
    class ApiClient:
        def __init__(self, page):
            self.page = page

# Metadatos de las rutas
ROUTE_META = {
    "dashboard": ("Dashboard", ft.Icons.DASHBOARD),
    "planteles": ("Planteles", ft.Icons.DOMAIN),
    "laboratorios": ("Laboratorios", ft.Icons.COMPUTER),
    "recursos": ("Préstamos", ft.Icons.INVENTORY),
    "reservas": ("Reservas", ft.Icons.BOOKMARK_ADD),
    "ajustes": ("Ajustes", ft.Icons.SETTINGS),
    "horarios": ("Horarios Admin", ft.Icons.SCHEDULE),
}
NAV_WIDTH = 250
# --- INICIO CAMBIO RESPONSIVO ---
MOBILE_BREAKPOINT = 768 # Píxeles para cambiar a vista móvil
# --- FIN CAMBIO RESPONSIVO ---

# <--- INICIO: LÓGICA DE CARGA DE ASSETS (Base64) ---
# (Se ejecuta ANTES de iniciar la app para evitar la caché)

# 1. Definir rutas
ICON_PATH = "ui/assets/icon.png"
SPLASH_PATH = "ui/assets/splash.png"

# 2. Preparar variables
favicons_dict = {}
splash_b64_data_uri = None # <--- CORRECCIÓN: CAMBIADO A SOLO EL 'data URI'

# 3. Cargar Favicon (Ícono de la App)
try:
    if os.path.exists(ICON_PATH):
        with open(ICON_PATH, "rb") as image_file:
            icon_b64 = base64.b64encode(image_file.read()).decode('utf-8')
            favicons_dict = {
                "": f"data:image/png;base64,{icon_b64}"
            }
            print("✅ Favicon (icon.png) cargado en Base64.")
    else:
        print(f"❌ ADVERTENCIA: No se encontró icon.png en {ICON_PATH}")
except Exception as e:
    print(f"❌ Error al cargar el favicon: {e}")

# 4. Cargar Splash (Pantalla de Carga)
try:
    if os.path.exists(SPLASH_PATH):
        with open(SPLASH_PATH, "rb") as image_file:
            splash_b64 = base64.b64encode(image_file.read()).decode('utf-8')
            # Guardamos solo el string del 'data URIa'
            splash_b64_data_uri = f"data:image/png;base64,{splash_b64}" 
            print("✅ Pantalla de carga (splash.png) cargada en Base64.")
    else:
        print(f"❌ ADVERTENCIA: No se encontró splash.png en {SPLASH_PATH}")
except Exception as e:
    print(f"❌ Error al cargar la pantalla de carga: {e}")
# --- FIN: LÓGICA DE CARGA DE ASSETS ---


def main(page: ft.Page):

    # <--- ¡CORRECCIÓN 1: ASIGNAR FAVICONS A 'page' AQUÍ! ---
    if favicons_dict:
        page.favicons = favicons_dict
        
    # <--- ¡CORRECCIÓN 2: ASIGNAR SPLASH A 'page' AQUÍ! ---
    # 'splash' también es una propiedad de 'page', no un argumento de 'ft.app()'
    if splash_b64_data_uri:
        page.splash = ft.Image(src_base64=splash_b64_data_uri)
    # <--- FIN DE LAS CORRECCIONES ---

    # Configuración para Railway
    port = int(os.environ.get("PORT", 8501))
    
    page.title = "BLACKLAB"
    page.padding = 0
    # --- INICIO CAMBIO RESPONSIVO ---
    # page.window_min_width = 1100 # <--- ELIMINADO para permitir resizing
    # page.window_min_height = 680 # <--- ELIMINADO
    # --- FIN CAMBIO RESPONSIVO ---

    apply_theme(page)

    api = ApiClient(page)

    def logout(e):
        page.session.remove("user_session")
        if page.session.contains_key("login_attempt"):
            page.session.remove("login_attempt")
        page.go("/")

    def get_allowed_routes(rol: str):
        allowed_map = {
            "admin": ["dashboard", "planteles", "laboratorios", "recursos", "reservas", "horarios", "ajustes"],
            "docente": ["dashboard", "recursos", "reservas", "ajustes"],
            "estudiante": ["dashboard", "recursos", "ajustes"],
        }
        return allowed_map.get(rol, ["dashboard"])

    def on_login_success():
        """Función central de éxito de login: redirige al dashboard."""
        print("DEBUG: on_login_success llamado, redirigiendo a /dashboard")
        page.go("/dashboard")

    # --- INICIO CAMBIO RESPONSIVO ---
    # El 'Shell' ahora decide si mostrar layout de PC o Móvil
    def build_shell(active_key: str, body: ft.Control, is_mobile: bool):
    # --- FIN CAMBIO RESPONSIVO ---
        user_session = page.session.get("user_session") or {}
        if not user_session:
            page.go("/")
            return ft.View()

        user_data = user_session 
        allowed = get_allowed_routes(user_data.get("rol", ""))
        
        if active_key not in allowed:
            active_key = allowed[0]
            page.go(f"/{active_key}")
            return ft.View(f"/{active_key}", [])

        try:
            active_index = allowed.index(active_key)
        except ValueError:
            active_index = 0

        top_app_bar = ft.AppBar()

        def toggle_theme(_):
            new_mode = ft.ThemeMode.LIGHT if page.theme_mode == ft.ThemeMode.DARK else ft.ThemeMode.DARK
            apply_theme(page, new_mode)
            page.pubsub.send_all({"type": "theme_changed"})
            if top_app_bar and len(top_app_bar.actions) > 0 and isinstance(top_app_bar.actions[0], ft.IconButton):
                top_app_bar.actions[0].icon = ft.Icons.DARK_MODE if new_mode == ft.ThemeMode.LIGHT else ft.Icons.LIGHT_MODE
            page.update()

        theme_icon = ft.Icons.DARK_MODE if page.theme_mode == ft.ThemeMode.LIGHT else ft.Icons.LIGHT_MODE

        top_app_bar.title = ft.Text(ROUTE_META.get(active_key, ("Desconocido",))[0], size=20)
        top_app_bar.bgcolor = ft.Colors.SURFACE_CONTAINER_HIGHEST
        top_app_bar.actions = [
            ft.IconButton(theme_icon, tooltip="Cambiar tema", on_click=toggle_theme),
            ft.PopupMenuButton(
                items=[
                    ft.PopupMenuItem(text=user_data.get("user", "Usuario")), 
                    ft.PopupMenuItem(),
                    ft.PopupMenuItem(text="Ajustes", icon=ft.Icons.SETTINGS, on_click=lambda _: page.go("/ajustes")),
                    ft.PopupMenuItem(text="Cerrar sesión", icon=ft.Icons.LOGOUT, on_click=logout),
                ]
            )
        ]

        def nav_change(e):
            selected_route = allowed[e.control.selected_index]
            page.go(f"/{selected_route}")
            
        # --- INICIO CAMBIO RESPONSIVO ---
        # Definir los destinos una sola vez
        nav_destinations = [
            ft.NavigationRailDestination(
                icon=ROUTE_META.get(key, ("", ft.Icons.ERROR))[1],
                label=ROUTE_META.get(key, ("Error",))[0]
            ) for key in allowed
        ]
        
        main_content = ft.Container(
            content=body,
            expand=True,
            # Reducir padding en móvil
            padding=ft.padding.all(10 if is_mobile else 15), 
        )

        if is_mobile:
            # --- VISTA MÓVIL ---
            # No usamos el botón de hamburguesa, el menú está abajo
            top_app_bar.leading = None 
            
            bottom_nav = ft.BottomNavigationBar(
                selected_index=active_index,
                on_change=nav_change,
                destinations=[
                    ft.NavigationDestination(
                        icon=dest.icon, 
                        label=dest.label
                    ) for dest in nav_destinations
                ]
            )
            
            return ft.View(
                f"/{active_key}",
                [
                    top_app_bar,
                    main_content, # El contenido principal ocupa todo
                ],
                navigation_bar=bottom_nav, # Menú en la parte inferior
                padding=0,
            )
            
        else:
            # --- VISTA ESCRITORIO ---
            # (Usamos el código de slide-out que ya teníamos)
            navigation_rail = ft.NavigationRail(
                selected_index=active_index,
                label_type=ft.NavigationRailLabelType.ALL,
                min_width=100,
                min_extended_width=NAV_WIDTH,
                extended=True, # El menú siempre está extendido por dentro
                destinations=nav_destinations, # Usar los destinos
                on_change=nav_change,
            )

            nav_panel_content = ft.Column(
                [navigation_rail, ft.VerticalDivider(width=1)],
                spacing=0,
                width=NAV_WIDTH 
            )
            
            nav_container = ft.Container(
                content=nav_panel_content,
                width=NAV_WIDTH, 
                bgcolor=ft.colors.BACKGROUND, # <--- CORRECCIÓN: 'Colors' a 'colors'
                animate=ft.animation.Animation(300, "easeOutCubic"), 
            )

            def toggle_nav_slide(e):
                if nav_container.width == NAV_WIDTH:
                    nav_container.width = 0
                else:
                    nav_container.width = NAV_WIDTH
                page.update()

            top_app_bar.leading = ft.IconButton(
                icon=ft.icons.MENU,
                tooltip="Menú",
                on_click=toggle_nav_slide 
            )

            return ft.View(
                f"/{active_key}",
                [
                    top_app_bar,
                    ft.Row(
                        [
                            nav_container,
                            main_content,
                        ],
                        expand=True,
                        spacing=0 
                    ),
                ],
                padding=0,
            )
        # --- FIN CAMBIO RESPONSIVO ---

    def router(route):
        page.views.clear()
        user_session = page.session.get("user_session") or {}
        current_route_key = page.route.strip("/")
        
        # --- INICIO CAMBIO RESPONSIVO ---
        # Determinar si estamos en móvil ANTES de construir la vista
        is_mobile = page.width < MOBILE_BREAKPOINT
        page.client_storage.set("is_mobile", is_mobile)
        # --- FIN CAMBIO RESPONSIVO ---

        if not user_session:
            if current_route_key == "register":
                # Flujo de Registro: va a on_login_success (-> /dashboard)
                register_view_instance = register_view.RegisterView(page, api, on_success=on_login_success)
                page.views.append(register_view_instance)
            
            elif current_route_key == "captcha-verify":
                # Flujo de Captcha: va a on_login_success (-> /dashboard)
                page.views.append(
                    ft.View(
                        "/captcha-verify",
                        [captcha_view.CaptchaView(page, api, on_login_success)],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        vertical_alignment=ft.MainAxisAlignment.CENTER,
                    )
                )
            else:
                if current_route_key != "":
                    page.go("/")
                
                # Flujo de Login:
                page.views.append(
                    ft.View(
                        "/",
                        [login_view.LoginView(page, api, on_success=on_login_success)],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        vertical_alignment=ft.MainAxisAlignment.CENTER,
                    )
                )
        else:
            # Flujo de Usuario Autenticado
            user_rol = user_session.get("rol", "")
            
            allowed_routes_for_user = get_allowed_routes(user_rol)

            if not current_route_key:
                current_route_key = "dashboard"

            if current_route_key not in allowed_routes_for_user:
                page.go("/dashboard")
                page.update()
                return

            view_map = {
                "dashboard": dashboard_view.DashboardView,
                "planteles": planteles_view.PlantelesView,
                "laboratorios": laboratorios_view.LaboratoriosView,
                "recursos": prestamos_view.PrestamosView,
                "reservas": reservas_view.ReservasView,
                "ajustes": settings_view.SettingsView,
                "horarios": horarios_admin_view.HorariosAdminView,
            }

            view_function = view_map.get(current_route_key)

            if view_function:
                try:
                    body = view_function(page, api)
                    # --- INICIO CAMBIO RESPONSIVO ---
                    # Pasar 'is_mobile' al construir el shell
                    page.views.append(build_shell(current_route_key, body, is_mobile))
                    # --- FIN CAMBIO RESPONSIVO ---
                except Exception as e:
                    print(f"Error building view for '{current_route_key}': {e}")
                    import traceback
                    traceback.print_exc()
                    body = ft.Column([
                        ft.Text(f"Error al cargar la vista: {current_route_key}", color=ft.Colors.ERROR),
                        ft.Text(str(e))
                    ], expand=True)
                    # --- INICIO CAMBIO RESPONSIVO ---
                    page.views.append(build_shell(current_route_key, body, is_mobile))
                    # --- FIN CAMBIO RESPONSIVO ---
            else:
                body = ft.Text(f"Error: Vista '{current_route_key}' no encontrada.", color=ft.Colors.ERROR)
                # --- INICIO CAMBIO RESPONSIVO ---
                page.views.append(build_shell(current_route_key, body, is_mobile))
                # --- FIN CAMBIO RESPONSIVO ---

        page.update()

    # --- INICIO CAMBIO RESPONSIVO ---
    # Nueva función para manejar el cambio de tamaño
    def handle_resize(e):
        # Comprobar si el *modo* (móvil/escritorio) ha cambiado
        is_now_mobile = page.width < MOBILE_BREAKPOINT
        was_mobile = page.client_storage.get("is_mobile")
        
        if is_now_mobile != was_mobile:
            # Si el modo cambió, volver a ejecutar el router
            # Esto reconstruirá la vista con el layout correcto (menú lateral o inferior)
            print(f"RESIZE: Cambiando a modo {'MÓVIL' if is_now_mobile else 'ESCRITORIO'}")
            router(page.route)
    
    page.on_resize = handle_resize
    # --- FIN CAMBIO RESPONSIVO ---

    page.on_route_change = router
    page.go(page.route)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8501))
    print(f"🚀 Iniciando aplicación en puerto {port}")
    ft.app(
        target=main,
        view=ft.AppView.FLET_APP,
        port=port,
        host="0.0.0.0",
        assets_dir="ui/assets" 
    )