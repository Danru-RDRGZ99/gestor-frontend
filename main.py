import os
import flet as ft
import sys

# Diagnosticar la estructura de archivos
print("=== DIAGNÓSTICO DE ESTRUCTURA ===")
print("Directorio actual:", os.getcwd())
print("Contenido del directorio:", os.listdir('.'))

# Verificar estructura de carpetas
for item in os.listdir('.'):
    if os.path.isdir(item):
        print(f"Carpeta '{item}': {os.listdir(item)}")

# Agregar el directorio actual al path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Función para crear mocks compatibles que acepten cualquier argumento
def create_compatible_mock(message="Vista en desarrollo"):
    class CompatibleMock(ft.Column):
        def __init__(self, *args, **kwargs):
            super().__init__()
            self.controls = [
                ft.Text(message, size=20, weight=ft.FontWeight.BOLD),
                ft.Text("Esta funcionalidad estará disponible pronto", size=16),
                ft.Text(f"Args recibidos: {len(args)}", size=12),
                ft.Text(f"Ruta actual: {os.getcwd()}", size=10),
            ]
            self.alignment = ft.MainAxisAlignment.CENTER
            self.horizontal_alignment = ft.CrossAxisAlignment.CENTER
            self.expand = True
    return CompatibleMock()

# Crear mocks para todas las vistas (solución temporal)
LoginView = create_compatible_mock("Login")
RegisterView = create_compatible_mock("Registro")
DashboardView = create_compatible_mock("Dashboard")
PlantelesView = create_compatible_mock("Planteles")
LaboratoriosView = create_compatible_mock("Laboratorios")
ReservasView = create_compatible_mock("Reservas")
PrestamosView = create_compatible_mock("Préstamos")
SettingsView = create_compatible_mock("Ajustes")
CaptchaView = create_compatible_mock("Captcha")
HorariosAdminView = create_compatible_mock("Horarios Admin")

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
                    ft.PopupMenuItem(text="Usuario Demo"),
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
                page.views.append(
                    ft.View(
                        "/register",
                        [RegisterView],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        vertical_alignment=ft.MainAxisAlignment.CENTER,
                    )
                )
            elif current_route_key == "captcha-verify":
                page.views.append(
                    ft.View(
                        "/captcha-verify",
                        [CaptchaView],
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
                        [LoginView],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        vertical_alignment=ft.MainAxisAlignment.CENTER,
                    )
                )
        else:
            user_rol = user_session.get("user", {}).get("rol", "admin")
            allowed_routes_for_user = get_allowed_routes(user_rol)

            if not current_route_key:
                current_route_key = "dashboard"

            if current_route_key not in allowed_routes_for_user:
                page.go("/dashboard")
                page.update()
                return

            view_map = {
                "dashboard": DashboardView,
                "planteles": PlantelesView,
                "laboratorios": LaboratoriosView,
                "recursos": PrestamosView,
                "reservas": ReservasView,
                "ajustes": SettingsView,
                "horarios": HorariosAdminView,
            }

            body = view_map.get(current_route_key, DashboardView)
            page.views.append(build_shell(current_route_key, body))

        page.update()

    page.on_route_change = router
    
   
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8501))
    print(f"🚀 Iniciando aplicación en puerto {port}")
    ft.app(
        target=main,
        view=ft.AppView.FLET_APP,
        port=port,
        host="0.0.0.0"
    )