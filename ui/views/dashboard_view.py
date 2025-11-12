from __future__ import annotations
import flet as ft
from api_client import ApiClient
from datetime import datetime
import traceback

from ui.components.cards import Card


def DashboardView(page: ft.Page, api: ApiClient):
    user_session = page.session.get("user_session") or {}
    user_data = user_session
    role = (user_data.get("rol") or "").lower()

    # -------------------- Paleta --------------------
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

    # -------------------- UI helpers --------------------
    def SectionHeader(icon, title, extra_right: ft.Control | None = None):
        row_children = [
            ft.Row(
                [ft.Icon(icon, size=20, color=PAL["text_primary"]),
                 ft.Text(title, size=16, weight=ft.FontWeight.W_600, color=PAL["text_primary"])],
                spacing=8
            )
        ]
        if extra_right:
            row_children.append(extra_right)
        return ft.Row(row_children, alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    def ItemCard(child: ft.Control):
        return Card(child, padding=12, radius=10)

    def chip_estado(txt: str):
        color = PAL["chip_text"]
        if txt == "pendiente":
            color = ft.Colors.ORANGE_ACCENT_700
        elif txt == "aprobado":
            color = ft.Colors.LIGHT_GREEN_700
        elif txt == "entregado":
            color = ft.Colors.BLUE_700
        elif txt == "devuelto":
            color = ft.Colors.BLACK54 if page.theme_mode != ft.ThemeMode.DARK else ft.Colors.WHITE60
        elif txt == "rechazado":
            color = ft.Colors.RED_700
        elif txt == "activa":
            color = ft.Colors.GREEN_700
        elif txt == "cancelada":
            color = ft.Colors.RED_600
        elif txt == "finalizada":
            color = ft.Colors.BLUE_GREY_700

        return ft.Container(
            content=ft.Text((txt or "-").capitalize(), size=11, weight=ft.FontWeight.W_500, color=color),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=20,
            border=ft.border.all(1, PAL["border"]),
        )

    def format_iso_date(date_str: str | None) -> str:
        if not date_str:
            return ""
        try:
            if isinstance(date_str, str) and date_str.endswith("Z"):
                date_str = date_str[:-1] + "+00:00"
            dt = datetime.fromisoformat(str(date_str))
            return dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError) as e:
            print(f"WARN: Could not format date '{date_str}': {e}")
            return str(date_str)

    def elide(txt: str, max_len: int = 60) -> str:
        if not txt:
            return ""
        return txt if len(txt) <= max_len else (txt[: max_len - 1] + "…")

    # -------------------- Caches & lookups --------------------
    error_display = ft.Text("", color=PAL["error_text"])
    mis_prestamos_list = ft.Column(spacing=10)
    mis_reservas_list = ft.Column(spacing=10)

    planteles_cache: list[dict] = []
    labs_cache: list[dict] = []
    plantel_by_id: dict[int, dict] = {}
    lab_by_id: dict[int, dict] = {}

    def cargar_catálogos():
        nonlocal planteles_cache, labs_cache, plantel_by_id, lab_by_id
        try:
            planteles = api.get_planteles()
            labs = api.get_laboratorios()
            if isinstance(planteles, list):
                planteles_cache = planteles
                plantel_by_id = {p["id"]: p for p in planteles if isinstance(p, dict) and p.get("id") is not None}
            else:
                print("WARN: planteles response not list:", type(planteles))
            if isinstance(labs, list):
                labs_cache = labs
                lab_by_id = {l["id"]: l for l in labs if isinstance(l, dict) and l.get("id") is not None}
            else:
                print("WARN: labs response not list:", type(labs))
        except Exception as e:
            print(f"ERROR: cargar_catálogos(): {e}")
            traceback.print_exc()

    def ubicacion_from_recurso_or_lab(lab_id: int | None) -> tuple[str, str]:
        """Devuelve (plantel_nombre, lab_nombre) a partir de laboratorio_id."""
        if lab_id is None:
            return ("-", "-")
        lab = lab_by_id.get(lab_id) or {}
        lab_nombre = lab.get("nombre", f"Lab #{lab_id}")
        plantel_id = lab.get("plantel_id")
        plantel_nombre = plantel_by_id.get(plantel_id, {}).get("nombre", f"Plantel #{plantel_id}" if plantel_id else "-")
        return (plantel_nombre, lab_nombre)

    # -------------------- Render: Préstamos --------------------
    def render_mis_prestamos():
        mis_prestamos_list.controls.clear()
        error_display.value = ""

        prestamos_data = api.get_mis_prestamos()

        if isinstance(prestamos_data, dict) and "error" in prestamos_data:
            err = prestamos_data.get("error", "Error desconocido")
            error_display.value = f"Error al cargar préstamos: {err}"
            mis_prestamos_list.controls.append(SectionHeader(ft.Icons.SWIPE_RIGHT, "Mis Préstamos (Error)"))
            if error_display.page: error_display.update()
            if mis_prestamos_list.page: mis_prestamos_list.update()
            return

        if not isinstance(prestamos_data, list):
            error_display.value = f"Error al cargar préstamos: Respuesta inesperada ({type(prestamos_data)})"
            mis_prestamos_list.controls.append(SectionHeader(ft.Icons.SWIPE_RIGHT, "Mis Préstamos (Error)"))
            if error_display.page: error_display.update()
            if mis_prestamos_list.page: mis_prestamos_list.update()
            return

        prestamos = prestamos_data

        # Resumen (conteo/activos)
        activos = sum(1 for p in prestamos if (p.get("estado") in {"pendiente", "aprobado", "entregado"}))
        resumen = ft.Text(f"Total: {len(prestamos)} · Activos: {activos}", size=12, color=PAL["text_secondary"])
        mis_prestamos_list.controls.append(SectionHeader(ft.Icons.SWIPE_RIGHT, "Mis Préstamos", resumen))

        if not prestamos:
            mis_prestamos_list.controls.append(ft.Text("Aún no tienes préstamos.", color=PAL["text_secondary"]))
        else:
            for p in prestamos:
                if not isinstance(p, dict):
                    print("WARN: préstamo no es dict:", type(p))
                    continue

                # Campos de préstamo
                prestamo_id = p.get("id", "N/A")
                estado = p.get("estado", "-")
                created_at = p.get("created_at")
                fin = p.get("fin")

                # Recurso asociado (puede venir anidado)
                recurso = p.get("recurso") or {}
                recurso_id = recurso.get("id", "N/A")
                recurso_tipo = (recurso.get("tipo") or "Recurso").capitalize()
                specs = elide(recurso.get("specs") or "")

                # Ubicación: laboratorio y plantel desde el recurso
                lab_id = recurso.get("laboratorio_id")
                plantel_nombre, lab_nombre = ubicacion_from_recurso_or_lab(lab_id)

                title = ft.Text(
                    f"Préstamo #{prestamo_id} · {recurso_tipo} #{recurso_id}",
                    size=15, weight=ft.FontWeight.W_600
                )
                sub1 = ft.Text(f"Pedido: {format_iso_date(created_at)} · Devolución plan: {format_iso_date(fin)}",
                               size=11, color=PAL["text_secondary"])
                sub2 = ft.Text(f"Ubicación: {plantel_nombre} / {lab_nombre}",
                               size=11, color=PAL["text_secondary"])
                sub3 = ft.Text(f"Especificaciones: {specs or '-'}", size=11, color=PAL["muted_text"])

                izq = ft.Column([title, sub1, sub2, sub3], spacing=2, expand=True)
                der = chip_estado(estado)
                mis_prestamos_list.controls.append(
                    ItemCard(ft.Row([izq, der], vertical_alignment=ft.CrossAxisAlignment.CENTER))
                )

        if mis_prestamos_list.page:
            mis_prestamos_list.update()

    # -------------------- Render: Reservas --------------------
    def render_mis_reservas():
        mis_reservas_list.controls.clear()

        if role != "docente":
            if mis_reservas_list.page:
                mis_reservas_list.update()
            return

        if not hasattr(api, "get_mis_reservas"):
            mis_reservas_list.controls.append(SectionHeader(ft.Icons.BOOKMARK_ADD, "Mis Reservas"))
            mis_reservas_list.controls.append(ft.Text("Función no implementada en API client.", color=PAL["error_text"]))
            if mis_reservas_list.page:
                mis_reservas_list.update()
            return

        reservas_data = api.get_mis_reservas()

        if isinstance(reservas_data, dict) and "error" in reservas_data:
            err = reservas_data.get("error", "Error desconocido")
            mis_reservas_list.controls.append(SectionHeader(ft.Icons.BOOKMARK_ADD, "Mis Reservas (Error)"))
            mis_reservas_list.controls.append(ft.Text(f"Error al cargar reservas: {err}", color=PAL["error_text"]))
            if mis_reservas_list.page:
                mis_reservas_list.update()
            return

        if not isinstance(reservas_data, list):
            mis_reservas_list.controls.append(SectionHeader(ft.Icons.BOOKMARK_ADD, "Mis Reservas (Error)"))
            mis_reservas_list.controls.append(ft.Text(f"Respuesta inesperada del API ({type(reservas_data)})", color=PAL["error_text"]))
            if mis_reservas_list.page:
                mis_reservas_list.update()
            return

        reservas = reservas_data

        # Resumen reservas: activas por estado
        activas = sum(1 for r in reservas if (r.get("estado") in {"activa", "pendiente", "confirmada"}))
        resumen = ft.Text(f"Total: {len(reservas)} · Activas: {activas}", size=12, color=PAL["text_secondary"])
        mis_reservas_list.controls.append(SectionHeader(ft.Icons.BOOKMARK_ADD, "Mis Reservas", resumen))

        if not reservas:
            mis_reservas_list.controls.append(ft.Text("Aún no tienes reservas.", color=PAL["text_secondary"]))
        else:
            for r in reservas:
                if not isinstance(r, dict):
                    print("WARN: reserva no es dict:", type(r))
                    continue

                reserva_id = r.get("id", "N/A")
                lab_id = r.get("laboratorio_id")
                inicio = r.get("inicio")
                fin = r.get("fin")
                estado = r.get("estado", "-")

                plantel_nombre, lab_nombre = ubicacion_from_recurso_or_lab(lab_id)

                title = ft.Text(
                    f"Reserva #{reserva_id} · {plantel_nombre} / {lab_nombre}",
                    size=15, weight=ft.FontWeight.W_600
                )
                sub1 = ft.Text(f"Desde: {format_iso_date(inicio)} · Hasta: {format_iso_date(fin)}",
                               size=12, color=PAL["text_secondary"])

                izq = ft.Column([title, sub1], spacing=2, expand=True)
                der = chip_estado(estado)
                mis_reservas_list.controls.append(
                    ItemCard(ft.Row([izq, der], vertical_alignment=ft.CrossAxisAlignment.CENTER))
                )

        if mis_reservas_list.page:
            mis_reservas_list.update()

    # -------------------- Layout raíz --------------------
    saludo = ft.Text(
        f"Hola, {user_data.get('nombre', user_data.get('user', ''))}.",
        size=14, color=PAL["text_secondary"]
    )

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

    # -------------------- Inicialización --------------------
    try:
        cargar_catálogos()
        render_mis_prestamos()
        render_mis_reservas()
    except Exception as e:
        print(f"CRITICAL: Error during initial render in DashboardView: {e}")
        traceback.print_exc()
        error_display.value = f"Error inesperado al renderizar dashboard: {e}"

    # -------------------- Reactividad a tema --------------------
    def on_theme_change(_):
        nonlocal PAL
        PAL = get_palette()
        try:
            render_mis_prestamos()
            render_mis_reservas()
        except Exception as e:
            print(f"ERROR: Failed to re-render dashboard on theme change: {e}")
            error_display.value = f"Error al actualizar tema: {e}"
            if error_display.page:
                error_display.update()
        page.update()

    if page:
        page.pubsub.subscribe(on_theme_change)

    # -------------------- Responsivo --------------------
    responsive_content = ft.ResponsiveRow(
        [main_column],
        alignment=ft.MainAxisAlignment.CENTER
    )

    main_view_column = ft.Column(
        [responsive_content],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    root_container = ft.Container(
        content=main_view_column,
        expand=True,
    )

    def on_page_resize(e):
        MOBILE_BREAKPOINT = 768
        page_width = page.width or 1000
        if page_width < MOBILE_BREAKPOINT:
            main_view_column.alignment = ft.MainAxisAlignment.START
            main_view_column.horizontal_alignment = ft.CrossAxisAlignment.CENTER
            root_container.padding = ft.padding.only(top=15, left=12, right=12, bottom=15)
        else:
            main_view_column.alignment = ft.MainAxisAlignment.CENTER
            main_view_column.horizontal_alignment = ft.CrossAxisAlignment.CENTER
            root_container.padding = ft.padding.symmetric(horizontal=24, vertical=20)

        try:
            if root_container.page:
                root_container.update()
        except Exception as update_error:
            print(f"Error actualizando layout: {update_error}")

    page.on_resize = on_page_resize
    on_page_resize(None)

    return root_container
