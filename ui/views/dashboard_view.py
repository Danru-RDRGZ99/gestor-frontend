from __future__ import annotations
import flet as ft
from api_client import ApiClient
from datetime import datetime
import traceback # For better error logging

# Make sure Card is imported correctly
from ui.components.cards import Card

def DashboardView(page: ft.Page, api: ApiClient):

    # --- 'user_session' (el diccionario guardado) ES 'user_data'. ---
    user_session = page.session.get("user_session") or {}
    user_data = user_session
    role = user_data.get("rol", "").lower()
    
    # --- Paleta de Colores Dinámica ---
    def get_palette():
        dark = page.theme_mode == ft.ThemeMode.DARK
        return {
            "border": ft.Colors.WHITE24 if dark else ft.Colors.BLACK26,
            "text_primary": ft.Colors.WHITE if dark else ft.Colors.BLACK,
            "text_secondary": ft.Colors.GREY_400 if dark else ft.Colors.GREY_700,
            "chip_text": ft.Colors.WHITE70 if dark else ft.Colors.BLACK87,
            "error_text": ft.Colors.RED_400,
        }

    PAL = get_palette()

    # --- Helpers de UI (Sin cambios) ---
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

    # --- Formateo de Datos (Sin cambios) ---
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

    # --- Contenedores para las listas (Sin cambios) ---
    mis_prestamos_list = ft.Column(spacing=10)
    mis_reservas_list = ft.Column(spacing=10)
    error_display = ft.Text("", color=PAL["error_text"])

    # --- Renderizado de Secciones (Sin cambios) ---
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

    # --- Construcción del Layout Principal (Modificado para Responsivo) ---
    
    # <--- INICIO: CAMBIO DE THEME-AWARE ---
    # Definimos los controles de texto aquí para poder actualizarlos
    saludo = ft.Text(
        f"Hola, {user_data.get('nombre', user_data.get('user', ''))}.",
        size=14,
        color=PAL["text_secondary"]
    )
    role_text = ft.Text(color=PAL["text_secondary"])
    # <--- FIN: CAMBIO DE THEME-AWARE ---


    # Tarjeta de Bienvenida / Resumen
    welcome_content = [saludo]
    if role in ["admin", "docente", "estudiante"]:
        role_text.value = f"Rol actual: {role.capitalize()}"
        welcome_content.append(role_text)
    else:
        role_text.value = "Bienvenido. Usa el menú de la izquierda."
        welcome_content.append(role_text)
    
    # Contenedor de la tarjeta de bienvenida
    welcome_card = Card(
        ft.Column(welcome_content),
        # Ocupa 12 columnas (ancho completo) en todas las pantallas
        col={"xs": 12} 
    )

    # Contenedor de la tarjeta de préstamos
    prestamos_card = Card(
        mis_prestamos_list,
        # Ocupa 12 en móvil, 6 (mitad) en escritorio
        col={"xs": 12, "lg": 6} 
    )
    
    # Contenedor de la tarjeta de reservas
    reservas_card = Card(
        mis_reservas_list,
        # Ocupa 12 en móvil, 6 (mitad) en escritorio
        col={"xs": 12, "lg": 6} 
    )


    # --- Contenido dinámico según el rol ---
    # <--- CAMBIO: Usamos ft.ResponsiveRow ---
    main_layout = ft.ResponsiveRow(
        spacing=20,
        controls=[
            # Añadir el display de errores global
            # Hacemos que ocupe todo el ancho
            ft.Container(content=error_display, col={"xs": 12}),
            
            # Tarjeta de Bienvenida
            welcome_card
        ]
    )

    # Añadir sección de préstamos (siempre visible para roles definidos)
    if role in ["admin", "docente", "estudiante"]:
        main_layout.controls.append(prestamos_card)

    # Añadir sección de reservas (solo para docente)
    if role == "docente":
        main_layout.controls.append(reservas_card)


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
        
        # <--- INICIO: CAMBIO DE THEME-AWARE ---
        # Actualiza también los colores de los textos estáticos
        try:
            if saludo.page:
                saludo.color = PAL["text_secondary"]
                saludo.update()
            if role_text.page:
                role_text.color = PAL["text_secondary"]
                role_text.update()
        except Exception as e:
            print(f"Error updating text colors on theme change: {e}")
        # <--- FIN: CAMBIO DE THEME-AWARE ---
            
        try:
            render_mis_prestamos()
            render_mis_reservas()
        except Exception as e:
            print(f"ERROR: Failed to re-render dashboard on theme change: {e}")
            error_display.value = f"Error al actualizar tema: {e}"
            if error_display.page: error_display.update()
        
        # No es necesario page.update() si actualizas controles individuales
        # page.update()

    if page:
        page.pubsub.subscribe(on_theme_change)

    # El return sigue siendo un Column, pero su contenido principal
    # es ahora el ResponsiveRow
    return ft.Column(
        [
            ft.Text("Dashboard", size=22, weight=ft.FontWeight.BOLD),
            main_layout, # <--- Se usa el ResponsiveRow
        ],
        expand=True,
        spacing=18,
        scroll=ft.ScrollMode.AUTO,
    )