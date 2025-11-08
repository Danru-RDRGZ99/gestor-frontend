from __future__ import annotations
import flet as ft
from api_client import ApiClient
from datetime import datetime
import traceback

from ui.components.cards import Card

def DashboardView(page: ft.Page, api: ApiClient):

    user_session = page.session.get("user_session") or {}
    user_data = user_session
    role = user_data.get("rol", "").lower()

    def get_palette():
        dark = page.theme_mode == ft.ThemeMode.DARK
        return {
            "section_bg": ft.Colors.BLACK if dark else ft.Colors.BLUE_GREY_50,
            "card_bg": ft.Colors.WHITE10 if dark else ft.Colors.WHITE,
            "border": ft.Colors.WHITE24 if dark else ft.Colors.BLACK26,
            "text_primary": ft.Colors.WHITE if dark else ft.Colors.BLACK,
            "text_secondary": ft.Colors.GREY_400 if dark else ft.Colors.GREY_700,
            "chip_text": ft.Colors.WHITE70 if dark else ft.Colors.BLACK87,
            "error_text": ft.Colors.RED_400,
            "muted_text": ft.Colors.GREY_600 if dark else ft.Colors.GREY_800,
        }

    PAL = get_palette()

    def SectionHeader(icon, title):
        return ft.Row([
            ft.Icon(icon, size=20, color=PAL["text_primary"]),
            ft.Text(title, size=16, weight=ft.FontWeight.W_600, color=PAL["text_primary"]),
        ])

    def ItemCard(child: ft.Control):
        return Card(child, padding=12, radius=10)

    def chip_estado(txt: str):
        return ft.Container(
            content=ft.Text((txt or "-").capitalize(), size=12, color=PAL["chip_text"]),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=20, border=ft.border.all(1, PAL["border"]),
        )

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

    mis_prestamos_list = ft.Column(spacing=10)
    mis_reservas_list = ft.Column(spacing=10)
    error_display = ft.Text("", color=PAL["error_text"])

    def render_mis_prestamos():
        mis_prestamos_list.controls.clear()
        error_display.value = ""
        prestamos_data = api.get_mis_prestamos()

        if isinstance(prestamos_data, dict) and "error" in prestamos_data:
            error_detail = prestamos_data.get("error", "Error desconocido")
            error_msg = f"Error al cargar préstamos: {error_detail}"
            print(f"ERROR DashboardView: {error_msg}")
            error_display.value = error_msg
            mis_prestamos_list.controls.append(SectionHeader(ft.Icons.SWIPE_RIGHT, "Mis Préstamos Recientes (Error)"))
            if mis_prestamos_list.page: mis_prestamos_list.update()
            if error_display.page: error_display.update()
            return

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
        
        if not hasattr(api, "get_mis_reservas"):
            print("WARN: api.get_mis_reservas() no existe. Omitiendo sección.")
            mis_reservas_list.controls.append(SectionHeader(ft.Icons.BOOKMARK_ADD, "Mis Reservas Recientes"))
            mis_reservas_list.controls.append(ft.Text("Función no implementada en API client.", color=PAL["error_text"]))
            if mis_reservas_list.page: mis_reservas_list.update()
            return

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

    saludo = ft.Text(f"Hola, {user_data.get('nombre', user_data.get('user', ''))}.", size=14, color=PAL["text_secondary"])

    main_column = ft.Column(spacing=20)
    main_column.col = {"xs": 12, "md": 10, "lg": 8, "xl": 6}

    main_column.controls.append(error_display)

    welcome_content = [saludo]
    if role in ["admin", "docente", "estudiante"]:
        welcome_content.append(ft.Text(f"Rol actual: {role.capitalize()}", color=PAL["text_secondary"]))
    else:
        welcome_content.append(ft.Text("Bienvenido. Usa el menú de la izquierda.", color=PAL["text_secondary"]))
    
    main_column.controls.append(Card(ft.Column(welcome_content)))

    if role in ["admin", "docente", "estudiante"]:
        main_column.controls.append(Card(mis_prestamos_list))

    if role == "docente":
        main_column.controls.append(Card(mis_reservas_list))

    try:
        render_mis_prestamos()
        render_mis_reservas()
    except Exception as e:
        print(f"CRITICAL: Error during initial render in DashboardView: {e}")
        traceback.print_exc()
        error_display.value = f"Error inesperado al renderizar dashboard: {e}"

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

    # --- INICIO DE LA MODIFICACIÓN RESPONSIVA ---
    
    responsive_content = ft.ResponsiveRow(
        [main_column],
        alignment=ft.MainAxisAlignment.CENTER
    )

    main_view_column = ft.Column(
        [responsive_content],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        # La alineación vertical y horizontal se establecerá en on_page_resize
    )

    root_container = ft.Container(
        content=main_view_column,
        expand=True,
        # El padding se establecerá en on_page_resize
    )

    def on_page_resize(e):
        """Ajusta el layout basado en el ancho de la página."""
        MOBILE_BREAKPOINT = 768 # Breakpoint para layout móvil
        
        # Obtenemos el ancho de la página
        page_width = page.width or 1000 # Usamos 1000 como default si page.width es None
        
        if page_width < MOBILE_BREAKPOINT:
            # --- Layout Móvil ---
            main_view_column.alignment = ft.MainAxisAlignment.START
            main_view_column.horizontal_alignment = ft.CrossAxisAlignment.CENTER
            root_container.padding = ft.padding.only(top=15, left=12, right=12, bottom=15)
        else:
            # --- Layout PC (Centrado) ---
            main_view_column.alignment = ft.MainAxisAlignment.CENTER
            main_view_column.horizontal_alignment = ft.CrossAxisAlignment.CENTER
            root_container.padding = ft.padding.symmetric(horizontal=24, vertical=20)
        
        # Actualizamos los controles que cambiaron
        try:
            if root_container.page:
                root_container.update()
        except Exception as update_error:
            print(f"Error actualizando layout: {update_error}")

    # Registramos la función para que se llame CADA VEZ que la ventana cambie de tamaño
    page.on_resize = on_page_resize
    
    # Llamamos la función una vez al inicio para establecer el layout correcto
    on_page_resize(None)

    return root_container
    # --- FIN DE LA MODIFICACIÓN RESPONSIVA ---