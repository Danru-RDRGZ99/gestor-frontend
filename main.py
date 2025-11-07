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

# --- Importar Vistas (sin cambios) ---
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
    # ... (Placeholders de emergencia sin cambios) ...
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
# --- Fin de Imports ---

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

# <--- INICIO: LÓGICA DE CARGA DE ASSETS (Base64) ---
# (Se ejecuta ANTES de iniciar la app para evitar la caché)
ICON_PATH = "ui/assets/icon.png"
SPLASH_PATH = "ui/assets/splash.png"
favicons_dict = {}
splash_b64_data_uri = None 

try:
    if os.path.exists(ICON_PATH):
        with open(ICON_PATH, "rb") as image_file:
            icon_b64 = base64.b64encode(image_file.read()).decode('utf-8')
            favicons_dict = {"": f"data:image/png;base64,{icon_b64}"}
            print("✅ Favicon (icon.png) cargado en Base64.")
    else:
        print(f"❌ ADVERTENCIA: No se encontró icon.png en {ICON_PATH}")
except Exception as e:
    print(f"❌ Error al cargar el favicon: {e}")

try:
    if os.path.exists(SPLASH_PATH):
        with open(SPLASH_PATH, "rb") as image_file:
            splash_b64 = base64.b64encode(image_file.read()).decode('utf-8')
            splash_b64_data_uri = f"data:image/png;base64,{splash_b64}" 
            print("✅ Pantalla de carga (splash.png) cargada en Base64.")
    else:
        print(f"❌ ADVERTENCIA: No se encontró splash.png en {SPLASH_PATH}")
except Exception as e:
    print(f"❌ Error al cargar la pantalla de carga: {e}")
# <--- FIN: LÓGICA DE CARGA DE ASSETS ---


def main(page: ft.Page):

    # Asignar Favicon y Splash (cargados en Base64)
    if favicons_dict:
        page.favicons = favicons_dict
        
    if splash_b64_data_uri:
        page.splash = ft.Image(src_base64=splash_b64_data_uri)
    
    # <--- INICIO: CAMBIOS RESPONSIVOS ---
    # Punto de quiebre para cambiar a vista móvil
    MOBILE_BREAKPOINT = 768 
    # <--- FIN: CAMBIOS RESPONSIVOS ---

    # Configuración para Railway
    port = int(os.environ.get("PORT", 8501))
    
    page.title = "BLACKLAB"
    page.padding = 0
    # <--- CAMBIO RESPONSIVO: Se eliminan los anchos mínimos ---
    # page.window_min_width = 1100  <-- Eliminado
    # page.window_min_height = 680 <-- Eliminado

    apply_theme(page)
    api = ApiClient(page)

    # --- Funciones de Utilidad (sin cambios) ---
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
    # --- Fin de Funciones de Utilidad ---


    def build_shell(active_key: str, body: ft.Control):
        user_session = page.session.get("user_session") or {}
        if not user_session:
            page.go("/")
            return ft.View()

        user_data = user_session 
        allowed = get_allowed_routes(user_data.get("rol", ""))
        
        # <--- INICIO: LÓGICA DE DETECCIÓN MÓVIL (CORREGIDA) ---
        # Usamos page.width en lugar de page.window_width
        is_mobile = False # Default to desktop
        if page.width: # Check if page.width has a value
            is_mobile = page.width < MOBILE_BREAKPOINT
        
        print(f"Construyendo shell. Ancho: {page.width}. Es móvil: {is_mobile}")
        # <--- FIN: LÓGICA DE DETECCIÓN MÓVIL (CORREGIDA) ---
        
        if active_key not in allowed:
            active_key = allowed[0]
            page.go(f"/{active_key}")
            return ft.View(f"/{active_key}", [])

        try:
            active_index = allowed.index(active_key)
        except ValueError:
            active_index = 0

        # --- AppBar (sin cambios) ---
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
        # --- Fin de AppBar ---

        def nav_change(e):
            selected_route = allowed[e.control.selected_index]
            page.go(f"/{selected_route}")

        # <--- INICIO: LÓGICA DE NAVEGACIÓN ADAPTATIVA ---
        
        # 1. NAVEGACIÓN DE ESCRITORIO (Lateral)
        navigation_rail = ft.NavigationRail(
            selected_index=active_index,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=NAV_WIDTH,
            extended=True,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ROUTE_META.get(key, ("", ft.Icons.ERROR))[1],
                    label=ROUTE_META.get(key, ("Error",))[0]
                ) for key in allowed
            ],
            on_change=nav_change,
            visible=not is_mobile # <--- Oculto en móvil
        )
        
        # 2. NAVEGACIÓN MÓVIL (Inferior)
        navigation_bar = ft.NavigationBar(
            selected_index=active_index,
            destinations=[
                ft.NavigationDestination(
                    icon=ROUTE_META.get(key, ("", ft.Icons.ERROR))[1],
                    label=ROUTE_META.get(key, ("Error",))[0]
                ) for key in allowed
            ],
            on_change=nav_change,
            visible=is_mobile # <--- Oculto en escritorio
        )
        # <--- FIN: LÓGICA DE NAVEGACIÓN ADAPTATIVA ---

        main_content = ft.Container(
            content=body,
            expand=True,
            padding=ft.padding.all(15),
        )

        return ft.View(
            f"/{active_key}",
            [
                top_app_bar,
                ft.Row(
                    [
                        navigation_rail, # <--- Se oculta/muestra solo
                        ft.VerticalDivider(width=1, visible=not is_mobile), # <--- Se oculta en móvil
                        main_content,
                    ],
                    expand=True,
                ),
            ],
            navigation_bar=navigation_bar, # <--- Se añade la barra inferior
            padding=0,
        )

    # --- Router (sin cambios en la lógica interna) ---
    def router(route):
        page.views.clear()
        user_session = page.session.get("user_session") or {}
        current_route_key = page.route.strip("/")

        if not user_session:
            if current_route_key == "register":
                register_view_instance = register_view.RegisterView(page, api, on_success=on_login_success)
                page.views.append(register_view_instance)
            
            elif current_route_key == "captcha-verify":
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
                    page.views.append(build_shell(current_route_key, body))
                except Exception as e:
                    print(f"Error building view for '{current_route_key}': {e}")
                    import traceback
                    traceback.print_exc()
                    body = ft.Column([
                        ft.Text(f"Error al cargar la vista: {current_route_key}", color=ft.Colors.ERROR),
                        ft.Text(str(e))
                    ], expand=True)
                    page.views.append(build_shell(current_route_key, body))
            else:
                body = ft.Text(f"Error: Vista '{current_route_key}' no encontrada.", color=ft.Colors.ERROR)
                page.views.append(build_shell(current_route_key, body))

        page.update()
    
    
    # <--- INICIO: MANEJADOR DE CAMBIO DE TAMAÑO ---
    def on_resize(e):
        """
        Se llama cuando el tamaño de la ventana cambia.
        Vuelve a cargar la ruta actual para que 'build_shell'
        pueda redibujar la navegación correcta (lateral o inferior).
        """
        print(f"Nuevo tamaño detectado: {page.width}") # <-- También cambiado a page.width
        page.go(page.route)
    # <--- FIN: MANEJADOR DE CAMBIO DE TAMAÑO ---
    
    # Asignar los manejadores a la página
    page.on_route_change = router
    page.on_resize = on_resize # <--- Se asigna el nuevo manejador
    
    # Carga inicial
    page.go(page.route)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8501))
    print(f"🚀 Iniciando aplicación en puerto {port}")
    ft.app(
        target=main,
        view=ft.AppView.FLET_APP,
        port=port,
        host="0.0.0.0",
        assets_dir="ui/assets" # Mantenemos esto por si acaso
    )