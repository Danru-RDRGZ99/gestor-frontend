import os
import flet as ft
import sys
import base64

port = int(os.environ.get("PORT", 8501))

print("=== INICIANDO APLICACIÓN ===")
print("Estructura detectada:")
for item in os.listdir('.'):
    if os.path.isdir(item):
        print(f"📁 {item}/")

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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
MOBILE_BREAKPOINT = 768

ICON_PATH = "ui/assets/icon.png"
SPLASH_PATH = "ui/assets/splash.png"

favicons_dict = {}
splash_b64_data_uri = None

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


def main(page: ft.Page):

    if favicons_dict:
        page.favicons = favicons_dict
        
    if splash_b64_data_uri:
        page.splash = ft.Image(src_base64=splash_b64_data_uri)

    port = int(os.environ.get("PORT", 8501))
    
    page.title = "BLACKLAB"
    page.padding = 0

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
        print("DEBUG: on_login_success llamado, redirigiendo a /dashboard")
        page.go("/dashboard")

    def build_shell(active_key: str, body: ft.Control, is_mobile: bool):
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

        mobile_nav_keys = [key for key in allowed if key != "ajustes"]

        def nav_change(e):
            selected_index = e.control.selected_index
            selected_route_key = mobile_nav_keys[selected_index]
            page.go(f"/{selected_route_key}")
        
        def rail_nav_change(e):
            selected_route_key = e.control.destinations[e.control.selected_index].data
            page.go(f"/{selected_route_key}")
        
        main_content = ft.Container(
            content=body,
            expand=True,
            padding=ft.padding.all(10 if is_mobile else 15), 
        )

        if is_mobile:
            
            top_app_bar.leading = None
            
            mobile_active_index = 0
            if active_key in mobile_nav_keys:
                mobile_active_index = mobile_nav_keys.index(active_key)
            
            bottom_tabs = ft.Tabs(
                selected_index=mobile_active_index,
                on_change=nav_change,
                scrollable=True,
                expand=True,
                tabs=[
                    ft.Tab(
                        icon=ROUTE_META.get(key, ("", ft.Icons.ERROR))[1],
                        text=ROUTE_META.get(key, ("Error",))[0]
                    ) for key in mobile_nav_keys
                ]
            )
            
            bottom_bar_container = ft.Container(
                content=bottom_tabs,
                height=65,
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                padding=ft.padding.only(top=5),
            )

            page_layout = ft.Column(
                controls=[
                    # top_app_bar SE MOVIÓ AL appbar DE ft.View
                    main_content,
                    bottom_bar_container
                ],
                expand=True,
                spacing=0
            )

            return ft.View(
                f"/{active_key}",
                [
                    page_layout
                ],
                appbar=top_app_bar,  # <--- CORRECCIÓN AQUÍ
                padding=0,
                spacing=0
            )
            
        else:
            navigation_rail = ft.NavigationRail(
                selected_index=active_index,
                label_type=ft.NavigationRailLabelType.ALL,
                min_width=100,
                min_extended_width=NAV_WIDTH,
                extended=True,
                destinations=[
                    ft.NavigationRailDestination(
                        data=key,
                        icon=ROUTE_META.get(key, ("", ft.Icons.ERROR))[1],
                        label=ROUTE_META.get(key, ("Error",))[0]
                    ) for key in allowed
                ],
                on_change=rail_nav_change,
                expand=True
            )

            nav_panel_content = ft.Column(
                [navigation_rail, ft.VerticalDivider(width=1)],
                spacing=0,
                width=NAV_WIDTH 
            )
            
            nav_container = ft.Container(
                content=nav_panel_content,
                width=NAV_WIDTH, 
                animate=ft.Animation(duration=300, curve=ft.AnimationCurve.EASE_OUT_CUBIC), 
            )

            def toggle_nav_slide(e):
                if nav_container.width == NAV_WIDTH:
                    nav_container.width = 0
                else:
                    nav_container.width = NAV_WIDTH
                page.update()

            top_app_bar.leading = ft.IconButton(
                icon=ft.Icons.MENU,
                tooltip="Menú",
                on_click=toggle_nav_slide 
            )

            return ft.View(
                f"/{active_key}",
                [
                    # top_app_bar SE MOVIÓ AL appbar DE ft.View
                    ft.Row(
                        [
                            nav_container,
                            main_content,
                        ],
                        expand=True,
                        spacing=0 
                    ),
                ],
                appbar=top_app_bar, # <--- CORRECCIÓN AQUÍ
                padding=0,
            )

    def router(route):
        page.views.clear()
        user_session = page.session.get("user_session") or {}
        current_route_key = page.route.strip("/")
        
        current_width = page.width if page.width is not None else 1024
        is_mobile = current_width < MOBILE_BREAKPOINT
        
        try:
            page.client_storage.set("is_mobile", is_mobile)
        except Exception as e:
            if "Timeout" in str(e):
                print(f"WARN: Timeout en client_storage.set. {e}")
            else:
                # No relanzar la excepción, solo registrarla
                print(f"Error en client_storage.set: {e}")

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
                        [login_view.LoginView(page, api, on_success=on_login_success, is_mobile=is_mobile)],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        vertical_alignment=ft.MainAxisAlignment.CENTER,
                    )
                )
        else:
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
                    page.views.append(build_shell(current_route_key, body, is_mobile))
                except Exception as e:
                    print(f"Error building view for '{current_route_key}': {e}")
                    import traceback
                    traceback.print_exc()
                    body = ft.Column([
                        ft.Text(f"Error al cargar la vista: {current_route_key}", color=ft.Colors.ERROR),
                        ft.Text(str(e))
                    ], expand=True)
                    page.views.append(build_shell(current_route_key, body, is_mobile))
            else:
                body = ft.Text(f"Error: Vista '{current_route_key}' no encontrada.", color=ft.Colors.ERROR)
                page.views.append(build_shell(current_route_key, body, is_mobile))

        page.update()

    def handle_resize(e):
        try:
            current_width = page.width if page.width is not None else 1024
            is_now_mobile = current_width < MOBILE_BREAKPOINT
            
            was_mobile = page.client_storage.get("is_mobile")
            
            if is_now_mobile != was_mobile:
                print(f"RESIZE: Cambiando a modo {'MÓVIL' if is_now_mobile else 'ESCRITORIO'} (Ancho: {current_width})")
                router(page.route)
        except Exception as ex:
            if "Timeout" in str(ex):
                print(f"WARN: Timeout en client_storage.get. ({ex})")
            else:
                print(f"Error en handle_resize: {ex}")
    
    page.on_resize = handle_resize

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