import os
import flet as ft
from ui.theme import apply_theme
from api_client import ApiClient

# Importa todas tus vistas
from views import (
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

# Definición de rutas, etiquetas e íconos
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

    # Configuración específica para despliegue web
    page.theme_mode = ft.ThemeMode.LIGHT
    page.fonts = {
        "Roboto": "https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap"
    }

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
            return ft.View() # Return an empty view if session is lost

        user_data = user_session.get("user", {})
        allowed = get_allowed_routes(user_data.get("rol", ""))

        # Redirect if current route is not allowed (e.g., after role change)
        if active_key not in allowed:
            print(f"Redirect: Route '{active_key}' not allowed for role '{user_data.get('rol', '')}'. Going to default.")
            active_key = allowed[0] # Default to first allowed route
            page.go(f"/{active_key}")
            # Still return an empty view here as page.go triggers a new route change
            return ft.View(f"/{active_key}", [])

        try:
            active_index = allowed.index(active_key)
        except ValueError:
            print(f"Warning: Active key '{active_key}' not found in allowed routes {allowed}. Defaulting index.")
            active_index = 0 # Default index if key somehow isn't found

        # --- Theme Toggle Logic ---
        top_app_bar = ft.AppBar() # Initialize AppBar

        def toggle_theme(_):
            new_mode = ft.ThemeMode.LIGHT if page.theme_mode == ft.ThemeMode.DARK else ft.ThemeMode.DARK
            apply_theme(page, new_mode)
            page.pubsub.send_all({"type": "theme_changed"})
            # Safely update the icon
            if top_app_bar and len(top_app_bar.actions) > 0 and isinstance(top_app_bar.actions[0], ft.IconButton):
                top_app_bar.actions[0].icon = ft.Icons.DARK_MODE if new_mode == ft.ThemeMode.LIGHT else ft.Icons.LIGHT_MODE
            page.update()

        theme_icon = ft.Icons.DARK_MODE if page.theme_mode == ft.ThemeMode.LIGHT else ft.Icons.LIGHT_MODE

        # --- Configure top_app_bar ---
        top_app_bar.title = ft.Text(ROUTE_META.get(active_key, ("Desconocido",))[0], size=20)
        top_app_bar.bgcolor = ft.Colors.SURFACE_CONTAINER_HIGHEST
        top_app_bar.actions = [
            ft.IconButton(theme_icon, tooltip="Cambiar tema", on_click=toggle_theme),
            ft.PopupMenuButton(
                items=[
                    ft.PopupMenuItem(text=user_data.get("user", "Usuario")),
                    ft.PopupMenuItem(), # Divider
                    ft.PopupMenuItem(text="Ajustes", icon=ft.Icons.SETTINGS, on_click=lambda _: page.go("/ajustes")),
                    ft.PopupMenuItem(text="Cerrar sesión", icon=ft.Icons.LOGOUT, on_click=logout),
                ]
            )
        ]
        # --- End Theme Toggle Logic ---

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
        current_route_key = page.route.strip("/") # Normalize route key

        # --- Lógica de enrutamiento ---

        if not user_session:
            # Vistas públicas: Login, Registro, Verificación de Captcha
            if current_route_key == "register":
                register_view_instance = register_view.RegisterView(page, api, on_success=lambda: page.go("/"))
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
            else: # Ruta raíz "" o cualquier otra no autenticada va al login
                 if current_route_key != "": # Avoid adding login view if already at root
                     page.go("/") # Redirect other unknown public routes to login
                 page.views.append(
                    ft.View(
                        "/",
                        [login_view.LoginView(page, api, on_success=lambda: page.go("/captcha-verify"))],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        vertical_alignment=ft.MainAxisAlignment.CENTER,
                    )
                 )
        else:
            # Vistas protegidas (requieren sesión activa)
            user_rol = user_session.get("user", {}).get("rol", "")
            allowed_routes_for_user = get_allowed_routes(user_rol)

            # Default route if empty or just '/'
            if not current_route_key:
                current_route_key = "dashboard" # Default protected route

            if current_route_key not in allowed_routes_for_user:
                print(f"WARN: Ruta '{current_route_key}' no permitida para rol '{user_rol}'. Redirigiendo a dashboard.")
                page.go("/dashboard")
                page.update()
                return

            # Mapa de vistas protegidas
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
                        ft.Text(f"Error al cargar la vista: {current_route_key}", color=ft.colors.ERROR),
                        ft.Text(str(e))
                        ])
                    page.views.append(build_shell(current_route_key, body))
            else:
                print(f"ERROR: Ruta '{current_route_key}' permitida pero no mapeada a una función de vista.")
                body = ft.Text(f"Error: Vista '{current_route_key}' no encontrada.", color=ft.colors.ERROR)
                page.views.append(build_shell(current_route_key, body))

        page.update()

    page.on_route_change = router
    page.go(page.route)

# Configuración para Railway
if __name__ == "__main__":
    # Obtener el puerto de Railway o usar 8501 por defecto
    port = int(os.environ.get("PORT", 8501))
    
    # Configuración para producción
    ft.app(
        target=main,
        view=ft.AppView.FLET_APP,  # Usar FLET_APP para mejor compatibilidad
        port=port,
        host="0.0.0.0"  # Importante: escuchar en todas las interfaces
    )