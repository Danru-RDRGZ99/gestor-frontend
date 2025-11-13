import flet as ft

# Color que elegiste (aproximado de la imagen)
SEED_COLOR = "#1f8c9a" 

# Definimos los temas claro y oscuro
light_theme = ft.Theme(
    color_scheme_seed=SEED_COLOR,
    font_family="Roboto"
)

dark_theme = ft.Theme(
    color_scheme_seed=SEED_COLOR,
    font_family="Roboto"
)

# SOLUCIÓN: La función ahora acepta un segundo argumento opcional 'mode'.
def apply_theme(page: ft.Page, mode: ft.ThemeMode | None = None):
    """
    Aplica el tema. Si se pasa 'mode', lo aplica y lo guarda en la sesión.
    Si no, lee de la sesión o usa oscuro por defecto.
    """
    # Caso 1: Se está cambiando el tema explícitamente (desde el botón)
    if mode is not None:
        page.theme_mode = mode
        page.session.set("theme_mode", "light" if mode == ft.ThemeMode.LIGHT else "dark")
    # Caso 2: Se está iniciando la aplicación
    else:
        saved_mode = page.session.get("theme_mode")
        if saved_mode == "light":
            page.theme_mode = ft.ThemeMode.LIGHT
        else:
            # Por defecto o si está guardado como "dark"
            page.theme_mode = ft.ThemeMode.DARK

    # Asigna los temas definidos a la página
    page.theme = light_theme
    page.dark_theme = dark_theme
    
    page.update()

