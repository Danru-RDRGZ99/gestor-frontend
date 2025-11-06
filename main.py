import os
import flet as ft
import sys

# Agregar el directorio actual al path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Función para crear mocks compatibles con Flet
def create_compatible_mock():
    class CompatibleMock(ft.Column):
        def __init__(self, message="Vista en desarrollo"):
            super().__init__()
            self.controls = [
                ft.Text(message, size=20, weight=ft.FontWeight.BOLD),
                ft.Text("Esta funcionalidad estará disponible pronto", size=16),
            ]
            self.alignment = ft.MainAxisAlignment.CENTER
            self.horizontal_alignment = ft.CrossAxisAlignment.CENTER
            self.expand = True
    return CompatibleMock

# Importar módulos con mejor manejo de errores
def safe_import(module_name, class_name, fallback_message=None):
    try:
        module = __import__(module_name, fromlist=[class_name])
        return getattr(module, class_name)
    except ImportError as e:
        print(f"Error importando {class_name} from {module_name}: {e}")
        return create_compatible_mock()

# Importar todas las vistas
try:
    # Verificar si la carpeta views existe
    if not os.path.exists('views'):
        print("ERROR: No existe la carpeta 'views'")
        raise ImportError("No views directory")
    
    print("Archivos en views:", os.listdir('views'))
    
    # Importar cada vista individualmente
    LoginView = safe_import('views.login_view', 'LoginView', "Login no disponible")
    RegisterView = safe_import('views.register_view', 'RegisterView', "Registro no disponible")
    DashboardView = safe_import('views.dashboard_view', 'DashboardView', "Dashboard no disponible")
    PlantelesView = safe_import('views.planteles_view', 'PlantelesView', "Planteles no disponible")
    LaboratoriosView = safe_import('views.laboratorios_view', 'LaboratoriosView', "Laboratorios no disponible")
    ReservasView = safe_import('views.reservas_view', 'ReservasView', "Reservas no disponible")
    PrestamosView = safe_import('views.prestamos_view', 'PrestamosView', "Préstamos no disponible")
    SettingsView = safe_import('views.settings_view', 'SettingsView', "Ajustes no disponible")
    CaptchaView = safe_import('views.captcha_view', 'CaptchaView', "Captcha no disponible")
    HorariosAdminView = safe_import('views.horarios_admin_view', 'HorariosAdminView', "Horarios no disponible")
    
except Exception as e:
    print(f"Error crítico en imports: {e}")
    # Crear mocks de emergencia
    LoginView = create_compatible_mock()
    RegisterView = create_compatible_mock()
    DashboardView = create_compatible_mock()
    PlantelesView = create_compatible_mock()
    LaboratoriosView = create_compatible_mock()
    ReservasView = create_compatible_mock()
    PrestamosView = create_compatible_mock()
    SettingsView = create_compatible_mock()
    CaptchaView = create_compatible_mock()
    HorariosAdminView = create_compatible_mock()

# Importar otros módulos
try:
    from ui.theme import apply_theme
    print("Tema importado correctamente")
except ImportError:
    print("Usando tema por defecto")
    def apply_theme(page, theme_mode=None):
        page.theme_mode = theme_mode or ft.ThemeMode.LIGHT
        page.update()

try:
    from api_client import ApiClient
    print("ApiClient importado correctamente")
except ImportError:
    print("Usando ApiClient mock")
    class ApiClient:
        def __init__(self, page):
            self.page = page

# El resto de tu código permanece igual...
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

def main(page: ft.Page):
    # Configuración para Railway
    port = int(os.environ.get("PORT", 8501))
    
    page.title = "Gestor de Laboratorios"
    page.padding = 0
    page.window_min_width = 1100
    page.window_min_height = 680

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
        page.go("/dashboard")

    def build_shell(active_key: str, body: ft.Control):
        user_session = page.session.get("user_session") or {}
        if not user_session:
            page.go("/")
            return ft.View()

        user_data = user_session.get("user", {})
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
        )

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
                        navigation_rail,
                        ft.VerticalDivider(width=1),
                        main_content,
                    ],
                    expand=True,
                ),
            ],
            padding=0,
        )

    def router(route):
        page.views.clear()
        user_session = page.session.get("user_session") or {}
        current_route_key = page.route.strip("/")

        if not user_session:
            if current_route_key == "register":
                # Usar RegisterView directamente como función
                register_content = RegisterView(page, api, lambda: page.go("/"))
                page.views.append(register_content)
            elif current_route_key == "captcha-verify":
                captcha_content = CaptchaView(page, api, on_login_success)
                page.views.append(
                    ft.View(
                        "/captcha-verify",
                        [captcha_content],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        vertical_alignment=ft.MainAxisAlignment.CENTER,
                    )
                )
            else:
                if current_route_key != "":
                    page.go("/")
                login_content = LoginView(page, api, lambda: page.go("/captcha-verify"))
                page.views.append(
                    ft.View(
                        "/",
                        [login_content],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        vertical_alignment=ft.MainAxisAlignment.CENTER,
                    )
                )
        else:
            user_rol = user_session.get("user", {}).get("rol", "")
            allowed_routes_for_user = get_allowed_routes(user_rol)

            if not current_route_key:
                current_route_key = "dashboard"

            if current_route_key not in allowed_routes_for_user:
                page.go("/dashboard")
                page.update()
                return

            view_map = {
                "dashboard": lambda p, a: DashboardView(p, a),
                "planteles": lambda p, a: PlantelesView(p, a),
                "laboratorios": lambda p, a: LaboratoriosView(p, a),
                "recursos": lambda p, a: PrestamosView(p, a),
                "reservas": lambda p, a: ReservasView(p, a),
                "ajustes": lambda p, a: SettingsView(p, a),
                "horarios": lambda p, a: HorariosAdminView(p, a),
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
                        ft.Text(f"Error al cargar la vista: {current_route_key}", color=ft.colors.ERROR),
                        ft.Text(str(e))
                    ], expand=True)
                    page.views.append(build_shell(current_route_key, body))
            else:
                body = ft.Text(f"Error: Vista '{current_route_key}' no encontrada.", color=ft.colors.ERROR)
                page.views.append(build_shell(current_route_key, body))

        page.update()

    page.on_route_change = router
    page.go(page.route)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8501))
    print(f"Iniciando aplicación en puerto {port}")
    ft.app(
        target=main,
        view=ft.AppView.FLET_APP,
        port=port,
        host="0.0.0.0"
    )