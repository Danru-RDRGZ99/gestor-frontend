from __future__ import annotations
import flet as ft
from api_client import ApiClient
from datetime import datetime
import traceback # For better error logging

# Make sure Card is imported correctly
from ui.components.cards import Card

def DashboardView(page: ft.Page, api: ApiClient):

    # --- INICIO DE LA CORRECCIÓN ---
    # 'user_session' (el diccionario guardado) ES 'user_data'.
    user_session = page.session.get("user_session") or {}
    user_data = user_session  # <-- ¡Esta es la corrección!
    role = user_data.get("rol", "").lower() # <-- Esta línea (14) ahora funcionará.
    # --- FIN DE LA CORRECCIÓN ---

    # --- Paleta de Colores Dinámica ---
    def get_palette():
        dark = page.theme_mode == ft.ThemeMode.DARK
        return {
            "section_bg": ft.Colors.BLACK if dark else ft.Colors.BLUE_GREY_50,
            # card_bg is no longer used directly on Card, but keep for other elements
            "card_bg": ft.Colors.WHITE10 if dark else ft.Colors.WHITE,
            "border": ft.Colors.WHITE24 if dark else ft.Colors.BLACK26,
            "text_primary": ft.Colors.WHITE if dark else ft.Colors.BLACK,
            "text_secondary": ft.Colors.GREY_400 if dark else ft.Colors.GREY_700,
            "chip_text": ft.Colors.WHITE70 if dark else ft.Colors.BLACK87,
            "error_text": ft.Colors.RED_400,
            "muted_text": ft.Colors.GREY_600 if dark else ft.Colors.GREY_800,
        }

    PAL = get_palette()
    
    # --- INICIO DE LA MODIFICACIÓN MÓVIL (Plataforma) ---
    
    # Detectamos si la plataforma es móvil (Android o iOS)
    is_mobile = page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]

    # Padding para la vista principal: más ajustado en móvil, más aire en desktop
    # El ResponsiveRow ya centra el contenido, esto es solo el espacio exterior.
    view_padding = ft.padding.symmetric(horizontal=12, vertical=15) if is_mobile else ft.padding.symmetric(horizontal=24, vertical=20)

    # --- FIN DE LA MODIFICACIÓN MÓVIL ---


    # --- Helpers de UI ---
    def SectionHeader(icon, title):
        return ft.Row([
            ft.Icon(icon, size=20, color=PAL["text_primary"]),
            ft.Text(title, size=16, weight=ft.FontWeight.W_600, color=PAL["text_primary"]),
        ])

    def ItemCard(child: ft.Control):
        # The custom Card component handles its own styling (padding, radius)
        # We removed bgcolor from here
        # NOTA: Si quisieras quitar sombras en móvil, tendrías que pasar 'shadow=None' aquí
        # asumiendo que tu 'Card' customizada acepta ese parámetro.
        # Por ejemplo: shadow = None if is_mobile else "default_shadow"
        return Card(child, padding=12, radius=10)

    def chip_estado(txt: str):
        return ft.Container(
            content=ft.Text((txt or "-").capitalize(), size=12, color=PAL["chip_text"]),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=20, border=ft.border.all(1, PAL["border"]),
        )

    # --- Formateo de Datos ---
    def format_iso_date(date_str: str | None) -> str:
        if not date_str: return ""
        try:
            if isinstance(date_str, str) and date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'
            dt = datetime.fromisoformat(str(date_str))
            return dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError) as e:
            print(f"WARN: Could not format date '{date_str}': {e}")
            return str(date_str)

    # --- Contenedores para las listas ---
    mis_prestamos_list = ft.Column(spacing=10)
    mis_reservas_list = ft.Column(spacing=10)
    error_display = ft.Text("", color=PAL["error_text"])

    # --- Renderizado de Secciones (CON VERIFICACIÓN) ---
    def render_mis_prestamos():
        mis_prestamos_list.controls.clear()
        error_display.value = ""
        prestamos_data = api.get_mis_prestamos()

        # Comprueba si la respuesta es un error
        if isinstance(prestamos_data, dict) and "error" in prestamos_data:
            error_detail = prestamos_data.get("error", "Error desconocido")
            error_msg = f"Error al cargar préstamos: {error_detail}"
            print(f"ERROR DashboardView: {error_msg}")
            error_display.value = error_msg
            mis_prestamos_list.controls.append(SectionHeader(ft.Icons.SWIPE_RIGHT, "Mis Préstamos Recientes (Error)"))
            if mis_prestamos_list.page: mis_prestamos_list.update()
            if error_display.page: error_display.update()
            return

        # Comprueba si la respuesta no es una lista (otro error)
        if not isinstance(prestamos_data, list):
            error_msg = f"Error al cargar préstamos: Respuesta inesperada del API ({type(prestamos_data)})"
            print(f"ERROR DashboardView: {error_msg}")
            error_display.value = error_msg
            mis_prestamos_list.controls.append(SectionHeader(ft.Icons.SWIPE_RIGHT, "Mis Préstamos Recientes (Error)"))
            if mis_prestamos_list.page: mis_prestamos_list.update()
            if error_display.page: error_display.update()
            return

        prestamos = prestamos_data
        mis_prestamos_list.controls.append(SectionHeader(ft.Icons.SWIPE_RIGHT, f"Mis Préstamos Recientes ({len(prestamos)})"))

        if not prestamos:
            mis_prestamos_list.controls.append(ft.Text("Aún no tienes préstamos.", color=PAL["text_secondary"]))
        else:
            for p in prestamos:
                if not isinstance(p, dict):
                        print(f"WARN: Expected dict for préstamo, got {type(p)}: {p}")
                        continue

                prestamo_id = p.get('id', 'N/A')
                recurso_id = p.get('recurso', {}).get('id', 'N/A')
                created_at = p.get('created_at')
                fin = p.get('fin')
                estado = p.get('estado', '-')

                title = ft.Text(f"Préstamo #{prestamo_id} · Recurso #{recurso_id}", size=15, weight=ft.FontWeight.W_600)
                timeline = ft.Text(f"Pedido: {format_iso_date(created_at)} · Devolución plan: {format_iso_date(fin)}", size=11, color=PAL["text_secondary"])

                left = ft.Column([title, timeline], spacing=2, expand=True)
                right = chip_estado(estado)
                mis_prestamos_list.controls.append(ItemCard(ft.Row([left, right], vertical_alignment=ft.CrossAxisAlignment.CENTER)))

        if mis_prestamos_list.page: mis_prestamos_list.update()


    def render_mis_reservas():
        mis_reservas_list.controls.clear()

        if role != "docente":
            if mis_reservas_list.page: mis_reservas_list.update()
            return
        
        # --- NOTA: 'get_mis_reservas' no existe en api_client.py ---
        # --- Deberás añadirlo para que esta sección funcione ---
        if not hasattr(api, "get_mis_reservas"):
            print("WARN: api.get_mis_reservas() no existe. Omitiendo sección.")
            mis_reservas_list.controls.append(SectionHeader(ft.Icons.BOOKMARK_ADD, "Mis Reservas Recientes"))
            mis_reservas_list.controls.append(ft.Text("Función no implementada en API client.", color=PAL["error_text"]))
            if mis_reservas_list.page: mis_reservas_list.update()
            return
        # --- FIN NOTA ---

        reservas_data = api.get_mis_reservas()

        if isinstance(reservas_data, dict) and "error" in reservas_data:
            error_detail = reservas_data.get("error", "Error desconocido")
            error_msg = f"Error al cargar reservas: {error_detail}"
            print(f"ERROR DashboardView: {error_msg}")
            mis_reservas_list.controls.append(SectionHeader(ft.Icons.BOOKMARK_ADD, "Mis Reservas Recientes (Error)"))
            mis_reservas_list.controls.append(ft.Text(error_msg, color=PAL["error_text"]))
            if mis_reservas_list.page: mis_reservas_list.update()
            return

        if not isinstance(reservas_data, list):
            error_msg = f"Error al cargar reservas: Respuesta inesperada del API ({type(reservas_data)})"
            print(f"ERROR DashboardView: {error_msg}")
            mis_reservas_list.controls.append(SectionHeader(ft.Icons.BOOKMARK_ADD, "Mis Reservas Recientes (Error)"))
            mis_reservas_list.controls.append(ft.Text(error_msg, color=PAL["error_text"]))
            if mis_reservas_list.page: mis_reservas_list.update()
            return
            
        reservas = reservas_data
        mis_reservas_list.controls.append(SectionHeader(ft.Icons.BOOKMARK_ADD, f"Mis Reservas Recientes ({len(reservas)})"))

        if not reservas:
            mis_reservas_list.controls.append(ft.Text("Aún no tienes reservas.", color=PAL["text_secondary"]))
        else:
            for r in reservas:
                if not isinstance(r, dict):
                    print(f"WARN: Expected dict for reserva, got {type(r)}: {r}")
                    continue

                reserva_id = r.get('id', 'N/A')
                lab_id = r.get('laboratorio_id', 'N/A')
                inicio = r.get('inicio')
                fin = r.get('fin')
                estado = r.get('estado', '-')

                title = ft.Text(f"Reserva #{reserva_id} · Laboratorio #{lab_id}", size=15, weight=ft.FontWeight.W_600)
                timeline = ft.Text(f"Desde: {format_iso_date(inicio)} · Hasta: {format_iso_date(fin)}", size=12, color=PAL["text_secondary"])

                left = ft.Column([title, timeline], spacing=2, expand=True)
                right = chip_estado(estado)
                mis_reservas_list.controls.append(ItemCard(ft.Row([left, right], vertical_alignment=ft.CrossAxisAlignment.CENTER)))

        if mis_reservas_list.page: mis_reservas_list.update()

    # --- Construcción del Layout Principal ---
    saludo = ft.Text(f"Hola, {user_data.get('nombre', user_data.get('user', ''))}.", size=14, color=PAL["text_secondary"])

    # --- Contenido dinámico según el rol ---
    main_column = ft.Column(spacing=20)
    
    # --- INICIO DE LA MODIFICACIÓN 1 ---
    # Asignamos las propiedades 'col' a la columna principal
    # Móvil (xs): 12/12 (ancho completo)
    # Tablet (md): 10/12
    # Escritorio (lg): 8/12
    # Escritorio Ancho (xl): 6/12
    main_column.col = {"xs": 12, "md": 10, "lg": 8, "xl": 6}
    # --- FIN DE LA MODIFICACIÓN 1 ---

    # Añadir el display de errores global
    main_column.controls.append(error_display)

    # Tarjeta de Bienvenida / Resumen
    welcome_content = [saludo]
    if role in ["admin", "docente", "estudiante"]:
        welcome_content.append(ft.Text(f"Rol actual: {role.capitalize()}", color=PAL["text_secondary"]))
    else:
        welcome_content.append(ft.Text("Bienvenido. Usa el menú de la izquierda.", color=PAL["text_secondary"]))
    
    # NOTA: Aquí también podrías aplicar la sombra condicional
    # main_column.controls.append(Card(ft.Column(welcome_content), shadow=card_shadow))
    main_column.controls.append(Card(ft.Column(welcome_content)))


    # Añadir sección de préstamos (siempre visible para roles definidos)
    if role in ["admin", "docente", "estudiante"]:
        main_column.controls.append(Card(mis_prestamos_list))

    # Añadir sección de reservas (solo para docente)
    if role == "docente":
        main_column.controls.append(Card(mis_reservas_list))


    # --- Render inicial ---
    try:
        render_mis_prestamos()
        render_mis_reservas()
    except Exception as e:
        print(f"CRITICAL: Error during initial render in DashboardView: {e}")
        traceback.print_exc()
        error_display.value = f"Error inesperado al renderizar dashboard: {e}"

    # --- Manejo de cambio de tema ---
    def on_theme_change(msg):
        nonlocal PAL
        PAL = get_palette()
        try:
            render_mis_prestamos()
            render_mis_reservas()
        except Exception as e:
            print(f"ERROR: Failed to re-render dashboard on theme change: {e}")
            error_display.value = f"Error al actualizar tema: {e}"
            if error_display.page: error_display.update()
        page.update()

    if page:
        page.pubsub.subscribe(on_theme_change)

    # --- INICIO DE LA MODIFICACIÓN 2 ---
    # Envolvemos el contenido en una Columna con scroll,
    # que contiene una ResponsiveRow para centrar el contenido.
    # AÑADIMOS EL 'view_padding' ADAPTATIVO
    return ft.Column(
        [
            ft.ResponsiveRow(
                [main_column],
                alignment=ft.MainAxisAlignment.CENTER
            )
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        padding=view_padding # <-- ÚNICO CAMBIO REAL
    )
    # --- FIN DE LA MODIFICACIÓN 2 ---