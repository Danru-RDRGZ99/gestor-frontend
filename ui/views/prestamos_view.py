# prestamos_view.py
from __future__ import annotations

import flet as ft
from api_client import ApiClient
from datetime import datetime, time, timedelta
import traceback

from ui.components.cards import Card
from ui.components.buttons import Primary, Ghost, Tonal, Danger
from ui.components.inputs import TextField

# Reglas de préstamo (por horas)
CLASS_START = time(7, 0)
CLASS_END = time(14, 30)
MAX_LOAN_HOURS = 7

def PrestamosView(page: ft.Page, api: ApiClient):
    """
    Vista completa para la gestión y solicitud de préstamos y recursos.
    """
    # --- INICIO DE LA CORRECCIÓN ---
    user_session = page.session.get("user_session") or {}
    user_data = user_session
    is_admin = user_data.get("rol") == "admin"
    # --- FIN DE LA CORRECCIÓN ---

    # ---------------------------------
    # Paleta adaptativa
    # ---------------------------------
    def get_palette():
        dark = page.theme_mode == ft.ThemeMode.DARK
        return {
            "border": ft.Colors.WHITE24 if dark else ft.Colors.BLACK26,
            "text_primary": ft.Colors.WHITE if dark else ft.Colors.BLACK,
            "text_secondary": ft.Colors.GREY_400 if dark else ft.Colors.GREY_700,
            "muted_text": ft.Colors.GREY_600 if dark else ft.Colors.GREY_800,
            "error_text": ft.Colors.RED_400,
        }
    PAL = get_palette()

    # ---------------------------------
    # Device detection (desktop vs mobile)
    # ---------------------------------
    def detect_mobile() -> bool:
        width = getattr(page, "window_width", None)
        platform = getattr(page, "platform", None)
        is_mobile_platform = False
        try:
            is_mobile_platform = platform and getattr(platform, "name", "").lower() in ("android", "ios")
        except Exception:
            is_mobile_platform = False
        if width is None:
            return is_mobile_platform
        return (width < 700) or is_mobile_platform

    state = {
        "filter_plantel_id": None,
        "filter_lab_id": None,
        "filter_estado": "",
        "filter_tipo": "",
        "active_tab": 0,
        "solicitar_recurso_id": None,
        "editing_recurso_id": None,
        "is_mobile": detect_mobile(),
    }

    # Keep UI responsive to resize events
    def _on_resize(e):
        new_mobile = detect_mobile()
        if new_mobile != state["is_mobile"]:
            state["is_mobile"] = new_mobile
            if page: page.update()
    page.on_resize = _on_resize

    # --- Controles de Filtros y Listas ---
    dd_plantel_filter = ft.Dropdown(
        label="Plantel", 
        options=[ft.dropdown.Option("", "Todos")], 
        width=220 if not detect_mobile() else None,
        expand=detect_mobile()
    )
    dd_lab_filter = ft.Dropdown(
        label="Laboratorio", 
        options=[ft.dropdown.Option("", "Todos")], 
        width=220 if not detect_mobile() else None,
        expand=detect_mobile()
    )
    dd_estado_filter = ft.Dropdown(
        label="Disponibilidad",
        options=[
            ft.dropdown.Option("", "Todos"),
            ft.dropdown.Option("disponible", "Disponible"),
            ft.dropdown.Option("prestado", "Prestado"),
            ft.dropdown.Option("mantenimiento", "Mantenimiento"),
        ],
        width=200 if not detect_mobile() else None,
        expand=detect_mobile()
    )
    dd_tipo_filter = ft.Dropdown(
        label="Tipo", 
        options=[ft.dropdown.Option("", "Todos")], 
        width=200 if not detect_mobile() else None,
        expand=detect_mobile()
    )

    recursos_list_display = ft.Column(spacing=10, scroll=ft.ScrollMode.ADAPTIVE)
    solicitudes_list_display = ft.Column(spacing=10, scroll=ft.ScrollMode.ADAPTIVE)
    error_display = ft.Text("", color=PAL["error_text"])

    # --- Cargar catálogos iniciales ---
    planteles_cache = []
    labs_cache = []
    tipos_cache = []
    error_loading_data = None

    try:
        planteles_data = api.get_planteles()
        labs_data = api.get_laboratorios()
        tipos_data = api.get_recurso_tipos()

        # Verificar Planteles
        if isinstance(planteles_data, list):
            planteles_cache = planteles_data
            dd_plantel_filter.options = [ft.dropdown.Option("", "Todos")] + \
                                        [ft.dropdown.Option(str(p['id']), p['nombre']) for p in planteles_cache if p.get('id')]
        else:
            detail = planteles_data.get("error", "Error") if isinstance(planteles_data, dict) else "Respuesta inválida"
            error_loading_data = f"Error al cargar planteles: {detail}"
            print(f"ERROR PrestamosView: {error_loading_data}")

        # Verificar Laboratorios
        if isinstance(labs_data, list):
            labs_cache = labs_data
        elif error_loading_data is None:
            detail = labs_data.get("error", "Error") if isinstance(labs_data, dict) else "Respuesta inválida"
            error_loading_data = f"Error al cargar laboratorios: {detail}"
            print(f"ERROR PrestamosView: {error_loading_data}")

        # Verificar Tipos
        if isinstance(tipos_data, list):
            tipos_cache = tipos_data
            dd_tipo_filter.options = [ft.dropdown.Option("", "Todos")] + \
                                     [ft.dropdown.Option(t, t.capitalize()) for t in tipos_cache if t]
        elif error_loading_data is None:
            detail = tipos_data.get("error", "Error") if isinstance(tipos_data, dict) else "Respuesta inválida"
            error_loading_data = f"Error al cargar tipos de recurso: {detail}"
            print(f"ERROR PrestamosView: {error_loading_data}")

    except Exception as e:
        error_loading_data = f"Excepción al cargar datos iniciales: {e}"
        print(f"CRITICAL PrestamosView: {error_loading_data}")
        traceback.print_exc()

    # Si hubo error cargando datos esenciales, mostrar error y salir
    if error_loading_data:
        return ft.Column([
            ft.Text("Préstamos y Recursos", size=22, weight=ft.FontWeight.BOLD),
            ft.Text("Error al cargar datos necesarios:", color=PAL["error_text"], weight=ft.FontWeight.BOLD),
            ft.Text(error_loading_data, color=PAL["error_text"])
        ])

    # ---------------------------------
    # Lógica de renderizado y filtros
    # ---------------------------------
    def render_recursos():
        print("DEBUG: render_recursos llamado")  # Debug
        recursos_list_display.controls.clear()
        error_display.value = ""
        recursos_data = api.get_recursos(
            plantel_id=state["filter_plantel_id"],
            lab_id=state["filter_lab_id"],
            estado=state["filter_estado"],
            tipo=state["filter_tipo"]
        )

        print(f"DEBUG: recursos_data = {recursos_data}")  # Debug

        if isinstance(recursos_data, dict) and "error" in recursos_data:
            detail = recursos_data.get("error", "Error")
            error_msg = f"Error al cargar recursos: {detail}"
            print(f"ERROR render_recursos: {error_msg}")
            error_display.value = error_msg
            if page: page.update()
            return
        
        if not isinstance(recursos_data, list):
            detail = "Respuesta inválida del API"
            error_msg = f"Error al cargar recursos: {detail}"
            print(f"ERROR render_recursos: {error_msg}")
            error_display.value = error_msg
            if page: page.update()
            return

        recursos = recursos_data
        print(f"DEBUG: {len(recursos)} recursos encontrados")  # Debug
        
        if not recursos:
            recursos_list_display.controls.append(
                ft.Text("No se encontraron recursos con los filtros seleccionados.", color=PAL["muted_text"])
            )
        else:
            for r in recursos:
                if isinstance(r, dict):
                    if state["is_mobile"]:
                        recursos_list_display.controls.append(recurso_tile_mobile(r))
                    else:
                        recursos_list_display.controls.append(recurso_tile(r))
                else:
                    print(f"WARN render_recursos: Expected dict for resource, got {type(r)}")

        if page: 
            page.update()
            print("DEBUG: página actualizada después de render_recursos")  # Debug

    def render_solicitudes():
        solicitudes_list_display.controls.clear()
        error_display.value = ""
        solicitudes_data = (api.get_todos_los_prestamos() if is_admin else api.get_mis_prestamos())

        if isinstance(solicitudes_data, dict) and "error" in solicitudes_data:
            detail = solicitudes_data.get("error", "Error")
            error_msg = f"Error al cargar solicitudes: {detail}"
            print(f"ERROR render_solicitudes: {error_msg}")
            error_display.value = error_msg
            if page: page.update()
            return

        if not isinstance(solicitudes_data, list):
            detail = "Respuesta inválida del API"
            error_msg = f"Error al cargar solicitudes: {detail}"
            print(f"ERROR render_solicitudes: {error_msg}")
            error_display.value = error_msg
            if page: page.update()
            return

        solicitudes = solicitudes_data
        if not solicitudes:
            solicitudes_list_display.controls.append(ft.Text("No hay solicitudes para mostrar.", color=PAL["muted_text"]))
        else:
            for s in solicitudes:
                if isinstance(s, dict):
                    if state["is_mobile"]:
                        solicitudes_list_display.controls.append(solicitud_tile_mobile(s))
                    else:
                        solicitudes_list_display.controls.append(solicitud_tile(s))
                else:
                    print(f"WARN render_solicitudes: Expected dict for solicitud, got {type(s)}")

        if page: page.update()

    def render_admin_recursos():
        recursos_admin_list_display.controls.clear()
        error_display.value = ""
        recursos_data = api.get_recursos()

        if isinstance(recursos_data, dict) and "error" in recursos_data:
            detail = recursos_data.get("error", "Error")
            error_msg = f"Error al cargar lista de admin: {detail}"
            print(f"ERROR render_admin_recursos: {error_msg}")
            error_display.value = error_msg
            if page: page.update()
            return
            
        if not isinstance(recursos_data, list):
            detail = "Respuesta inválida del API"
            error_msg = f"Error al cargar lista de admin: {detail}"
            print(f"ERROR render_admin_recursos: {error_msg}")
            error_display.value = error_msg
            if page: page.update()
            return

        recursos = recursos_data
        if not recursos:
            recursos_admin_list_display.controls.append(ft.Text("No hay recursos creados."))
        else:
            for r in recursos:
                if isinstance(r, dict):
                    if state["is_mobile"]:
                        recursos_admin_list_display.controls.append(admin_recurso_tile_mobile(r))
                    else:
                        recursos_admin_list_display.controls.append(admin_recurso_tile(r))
                else:
                    print(f"WARN render_admin_recursos: Expected dict for resource, got {type(r)}")

        if page: page.update()

    def on_filter_change(e):
        pid_val = dd_plantel_filter.value
        print(f"DEBUG: on_filter_change - plantel value: {pid_val}")  # Debug

        # Actualizar state plantel_id
        if pid_val and pid_val.isdigit():
            state["filter_plantel_id"] = int(pid_val)
        else:
            state["filter_plantel_id"] = None

        # Actualizar opciones del dropdown de laboratorios
        if state["filter_plantel_id"]:
            labs_filtrados = [l for l in labs_cache if l.get("plantel_id") == state["filter_plantel_id"]]
            dd_lab_filter.options = [ft.dropdown.Option("", "Todos")] + [ft.dropdown.Option(str(l['id']), l['nombre']) for l in labs_filtrados if l.get('id')]
        else:
            dd_lab_filter.options = [ft.dropdown.Option("", "Todos")]
        dd_lab_filter.value = ""
        if page: dd_lab_filter.update()

        # Actualizar state lab_id
        state["filter_lab_id"] = None

        # Actualizar otros filtros
        state["filter_estado"] = dd_estado_filter.value or ""
        state["filter_tipo"] = dd_tipo_filter.value or ""

        print(f"DEBUG: Filtros actualizados - plantel: {state['filter_plantel_id']}, lab: {state['filter_lab_id']}, estado: {state['filter_estado']}, tipo: {state['filter_tipo']}")  # Debug

        # Volver a renderizar
        render_recursos()

    def on_lab_filter_change(e):
        lid_val = dd_lab_filter.value
        print(f"DEBUG: on_lab_filter_change - lab value: {lid_val}")  # Debug
        
        if lid_val and lid_val.isdigit():
            state["filter_lab_id"] = int(lid_val)
        else:
            state["filter_lab_id"] = None
        
        state["filter_estado"] = dd_estado_filter.value or ""
        state["filter_tipo"] = dd_tipo_filter.value or ""
        
        print(f"DEBUG: Filtros lab actualizados - lab: {state['filter_lab_id']}, estado: {state['filter_estado']}, tipo: {state['filter_tipo']}")  # Debug
        
        render_recursos()

    # Asignar handlers
    dd_plantel_filter.on_change = on_filter_change
    dd_lab_filter.on_change = on_lab_filter_change
    dd_estado_filter.on_change = on_lab_filter_change
    dd_tipo_filter.on_change = on_lab_filter_change

    # ========================================================================
    # TILES MÓVILES (MEJORADOS)
    # ========================================================================

    def recurso_tile_mobile(r: dict):
        """Tile móvil para recursos"""
        lab_id = r.get('laboratorio_id')
        lab = next((l for l in labs_cache if l.get('id') == lab_id), {})
        plantel_id = lab.get('plantel_id')
        plantel = next((p for p in planteles_cache if p.get('id') == plantel_id), {})

        title = ft.Text(
            f"{r.get('tipo', 'Recurso').capitalize()} #{r.get('id', 'N/A')}", 
            size=16, 
            weight=ft.FontWeight.W_600
        )
        
        subtitle = ft.Text(
            f"📍 {plantel.get('nombre', '-')} • 🏢 {lab.get('nombre', '-')}",
            size=12, 
            color=ft.Colors.GREY_600,
        )

        estado_chip = chip_estado(r.get("estado"))

        if r.get("estado") == "disponible":
            btn = Primary(
                "Solicitar", 
                on_click=lambda e, _r=r: open_solicitud_sheet(_r),
                expand=True
            )
        else:
            btn = ft.OutlinedButton(
                f"{r.get('estado', 'No disponible').capitalize()}", 
                disabled=True,
                expand=True
            )

        return Card(
            ft.Container(
                ft.Column([
                    ft.Row([
                        title,
                        estado_chip
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    subtitle,
                    ft.Container(btn, margin=ft.margin.only(top=10))
                ], spacing=8),
                padding=10
            ),
            padding=8
        )

    def solicitud_tile_mobile(s: dict):
        """Tile móvil para solicitudes"""
        recurso = s.get('recurso', {})
        usuario = s.get('usuario', {})
        solicitud_id = s.get('id', 'N/A')
        recurso_tipo = recurso.get('tipo', 'Recurso').capitalize()
        recurso_id_val = recurso.get('id', 'N/A')

        title = ft.Text(f"Solicitud #{solicitud_id}", size=16, weight=ft.FontWeight.W_600)
        
        recurso_info = ft.Text(f"📦 {recurso_tipo} #{recurso_id_val}", size=13, color=ft.Colors.GREY_700)
        
        timeline = ft.Text(
            f"📅 Pedido: {format_iso_date(s.get('created_at'))}\n"
            f"⏰ Devolución: {format_iso_date(s.get('fin'))}",
            size=11, 
            color=ft.Colors.GREY_600
        )

        estado_chip = chip_estado(s.get('estado'))

        # Información adicional para admin
        admin_info = None
        if is_admin:
            solicitante_nombre = usuario.get('nombre', '-')
            admin_info = ft.Text(f"👤 {solicitante_nombre}", size=12, color=ft.Colors.GREY_600)

        content = [
            ft.Row([title, estado_chip], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            recurso_info,
            timeline
        ]
        
        if admin_info:
            content.insert(1, admin_info)

        # Acciones para admin
        admin_actions = None
        current_status = s.get('estado', 'pendiente')
        if is_admin:
            if current_status == 'pendiente':
                admin_actions = ft.Row([
                    Primary("✅ Aprobar", expand=True,
                           on_click=lambda _, _id=s['id']: update_loan_status(_id, 'aprobado')),
                    Danger("❌ Rechazar", expand=True,
                          on_click=lambda _, _id=s['id']: update_loan_status(_id, 'rechazado')),
                ], spacing=6)
            elif current_status == 'aprobado':
                admin_actions = Primary("📦 Entregado", expand=True,
                                      on_click=lambda _, _id=s['id']: update_loan_status(_id, 'entregado'))
            elif current_status == 'entregado':
                admin_actions = Primary("🔄 Devuelto", expand=True,
                                      on_click=lambda _, _id=s['id']: update_loan_status(_id, 'devuelto'))

        if admin_actions:
            content.append(ft.Container(admin_actions, margin=ft.margin.only(top=10)))

        return Card(
            ft.Container(
                ft.Column(content, spacing=6),
                padding=10
            ),
            padding=8
        )

    def admin_recurso_tile_mobile(r: dict):
        """Tile móvil para gestión de recursos (admin)"""
        lab_id = r.get('laboratorio_id')
        lab = next((l for l in labs_cache if l.get('id') == lab_id), {})
        plantel_id = lab.get('plantel_id')
        plantel = next((p for p in planteles_cache if p.get('id') == plantel_id), {})

        title = ft.Text(
            f"{r.get('tipo', 'Recurso').capitalize()} #{r.get('id', 'N/A')}", 
            size=16, 
            weight=ft.FontWeight.W_600
        )
        
        subtitle = ft.Text(
            f"📍 {plantel.get('nombre', '-')} • 🏢 {lab.get('nombre', '-')}",
            size=12, 
            color=ft.Colors.GREY_600,
        )

        estado_chip = chip_estado(r.get('estado'))

        actions = ft.Row([
            Primary("✏️ Editar", expand=True,
                   on_click=lambda e, _r=r: edit_recurso_click(_r)),
            Danger("🗑️ Eliminar", expand=True,
                  on_click=lambda e, _r=r: delete_recurso_click(_r)),
        ], spacing=6)

        return Card(
            ft.Container(
                ft.Column([
                    ft.Row([title, estado_chip], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    subtitle,
                    ft.Container(actions, margin=ft.margin.only(top=10))
                ], spacing=6),
                padding=10
            ),
            padding=8
        )

    # ========================================================================
    # TILES ORIGINALES (WEB)
    # ========================================================================

    def recurso_tile(r: dict):
        lab_id = r.get('laboratorio_id')
        lab = next((l for l in labs_cache if l.get('id') == lab_id), {})
        plantel_id = lab.get('plantel_id')
        plantel = next((p for p in planteles_cache if p.get('id') == plantel_id), {})

        title = ft.Text(f"{r.get('tipo', 'Recurso').capitalize()} #{r.get('id', 'N/A')}", size=15, weight=ft.FontWeight.W_600)
        subtitle = ft.Text(f"Plantel: {plantel.get('nombre', '-')} · Lab: {lab.get('nombre', '-')}", size=12, opacity=0.8)

        if r.get("estado") == "disponible":
            btn = ft.ElevatedButton("Solicitar", on_click=lambda e, _r=r: open_solicitud_sheet(_r))
        else:
            btn = ft.OutlinedButton(f"{r.get('estado', 'No disponible').capitalize()}", disabled=True)

        return ItemCard(ft.Row([ft.Column([title, subtitle], spacing=2, expand=True), btn], vertical_alignment=ft.CrossAxisAlignment.CENTER))

    def solicitud_tile(s: dict):
        recurso = s.get('recurso', {})
        usuario = s.get('usuario', {})
        solicitud_id = s.get('id', 'N/A')
        recurso_tipo = recurso.get('tipo', 'Recurso').capitalize()
        recurso_id_val = recurso.get('id', 'N/A')

        title = ft.Text(f"Solicitud #{solicitud_id} · {recurso_tipo} #{recurso_id_val}", size=15, weight=ft.FontWeight.W_600)
        timeline = ft.Text(f"Pedido: {format_iso_date(s.get('created_at'))} · Devolución: {format_iso_date(s.get('fin'))}", size=11)

        if is_admin:
            solicitante_nombre = usuario.get('nombre', '-')
            solicitante = ft.Text(f"Solicitante: {solicitante_nombre}", size=12, italic=True)
            info_col = ft.Column([title, solicitante, timeline], spacing=2, expand=True)
        else:
            info_col = ft.Column([title, timeline], spacing=2, expand=True)

        admin_menu = None
        current_status = s.get('estado', 'pendiente')

        if is_admin:
            menu_items = []
            if current_status == 'pendiente':
                menu_items.append(ft.PopupMenuItem(text="Aprobar", on_click=lambda _, _id=s['id']: update_loan_status(_id, 'aprobado')))
                menu_items.append(ft.PopupMenuItem(text="Rechazar", on_click=lambda _, _id=s['id']: update_loan_status(_id, 'rechazado')))
            elif current_status == 'aprobado':
                menu_items.append(ft.PopupMenuItem(text="Marcar como Entregado", on_click=lambda _, _id=s['id']: update_loan_status(_id, 'entregado')))
            elif current_status == 'entregado':
                menu_items.append(ft.PopupMenuItem(text="Marcar como Devuelto", on_click=lambda _, _id=s['id']: update_loan_status(_id, 'devuelto')))

            if menu_items:
                admin_menu = ft.PopupMenuButton(items=menu_items, icon=ft.Icons.MORE_VERT)

        controls = [info_col, chip_estado(current_status)]
        if admin_menu:
            controls.append(admin_menu)

        return ItemCard(ft.Row(controls, vertical_alignment=ft.CrossAxisAlignment.CENTER))

    def admin_recurso_tile(r: dict):
        lab_id = r.get('laboratorio_id')
        lab = next((l for l in labs_cache if l.get('id') == lab_id), {})
        plantel_id = lab.get('plantel_id')
        plantel = next((p for p in planteles_cache if p.get('id') == plantel_id), {})

        title = ft.Text(f"{r.get('tipo', 'Recurso').capitalize()} #{r.get('id', 'N/A')}", size=15, weight=ft.FontWeight.W_600)
        subtitle = ft.Text(f"Plantel: {plantel.get('nombre', '-')} · Lab: {lab.get('nombre', '-')}", size=12, opacity=0.8)

        actions = ft.Row([
            Tonal("Editar", icon=ft.Icons.EDIT_OUTLINED, on_click=lambda e, _r=r: edit_recurso_click(_r), height=36),
            Danger("Eliminar", icon=ft.Icons.DELETE_OUTLINED, on_click=lambda e, _r=r: delete_recurso_click(_r), height=36)
        ], spacing=5)

        return ItemCard(ft.Row([
            ft.Column([title, subtitle, chip_estado(r.get('estado'))], spacing=4, expand=True),
            actions
        ], vertical_alignment=ft.CrossAxisAlignment.START))

    # ========================================================================
    # FUNCIONES DE GESTIÓN (SIMPLIFICADAS)
    # ========================================================================

    def update_loan_status(prestamo_id: int, new_status: str):
        result = api.update_prestamo_estado(prestamo_id, new_status)
        if result and "error" not in result: 
            page.snack_bar = ft.SnackBar(ft.Text(f"Préstamo actualizado a '{new_status}'"), open=True)
            render_solicitudes()
            render_recursos()
        else:
            detail = result.get("error", "Error desconocido") if isinstance(result, dict) else "Error"
            page.snack_bar = ft.SnackBar(ft.Text(f"Error al actualizar estado: {detail}"), open=True)
        if page: page.update()

    def edit_recurso_click(r: dict):
        state["editing_recurso_id"] = r.get('id')
        page.snack_bar = ft.SnackBar(ft.Text(f"Editando recurso #{r.get('id')}..."), open=True)
        if page: page.update()

    def delete_recurso_click(r: dict):
        page.dialog = delete_dialog
        page.dialog.data = r.get('id')
        page.dialog.open = True
        if page: page.update()

    def confirm_delete_recurso(e):
        recurso_id = page.dialog.data
        page.dialog.open = False
        result = api.delete_recurso(recurso_id)
        if result and "success" in result:
            page.snack_bar = ft.SnackBar(ft.Text("Recurso eliminado."), open=True)
            render_admin_recursos()
            render_recursos()
        else:
            detail = result.get("error", "Error desconocido") if isinstance(result, dict) else "Error"
            page.snack_bar = ft.SnackBar(ft.Text(f"Error al eliminar: {detail}"), open=True)
        if page: page.update()

    # Diálogo de confirmación
    delete_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirmar eliminación"),
        content=ft.Text("¿Estás seguro de que quieres eliminar este recurso?"),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: (setattr(page.dialog, 'open', False), page.update())),
            Danger("Eliminar", on_click=confirm_delete_recurso),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    if delete_dialog not in page.overlay:
        page.overlay.append(delete_dialog)

    # Panel de Solicitud
    bs_title = ft.Text("Solicitar Recurso", size=18, weight=ft.FontWeight.BOLD)
    tf_motivo = ft.TextField(label="Motivo (opcional)", multiline=True, min_lines=2)
    slider_horas = ft.Slider(min=1, max=MAX_LOAN_HOURS, divisions=MAX_LOAN_HOURS - 1, value=2, label="{value} h")

    def open_solicitud_sheet(recurso: dict):
        bs_title.value = f"Solicitar: {recurso.get('tipo','Recurso').capitalize()} #{recurso.get('id')}"
        state["solicitar_recurso_id"] = recurso.get('id')
        tf_motivo.value = ""
        slider_horas.value = 2
        bs_solicitud.open = True
        if page: page.update()

    def close_solicitud_sheet(e):
        bs_solicitud.open = False
        if page: page.update()

    def crear_solicitud(e):
        if not state.get("solicitar_recurso_id"):
            page.snack_bar = ft.SnackBar(ft.Text("Error interno: No hay recurso seleccionado."), open=True)
            if page: page.update()
            return

        inicio = datetime.now()
        horas_prestamo = int(slider_horas.value)
        fin = inicio + timedelta(hours=horas_prestamo)

        prestamo_data = {
            "recurso_id": state["solicitar_recurso_id"],
            "usuario_id": user_data.get('id'),
            "cantidad": 1,
            "inicio": inicio.isoformat(),
            "fin": fin.isoformat(),
            "comentario": tf_motivo.value.strip() or None,
        }

        result = api.create_prestamo(prestamo_data)
        if result and "error" not in result:
            page.snack_bar = ft.SnackBar(ft.Text("Solicitud creada con éxito."), open=True)
            close_solicitud_sheet(None)
            render_recursos()
            render_solicitudes()
        else:
            detail = result.get("error", "Error desconocido") if isinstance(result, dict) else "Error"
            page.snack_bar = ft.SnackBar(ft.Text(f"Error al crear la solicitud: {detail}"), open=True)
        if page: page.update()

    bs_solicitud = ft.BottomSheet(
        ft.Container(
            ft.Column([
                bs_title,
                tf_motivo,
                ft.Text("Duración (horas)"),
                slider_horas,
                ft.Row([
                    ft.TextButton("Cancelar", on_click=close_solicitud_sheet),
                    ft.FilledButton("Enviar Solicitud", on_click=crear_solicitud)
                ], alignment=ft.MainAxisAlignment.END)
            ], tight=True),
            padding=20
        ),
        on_dismiss=close_solicitud_sheet,
    )
    if bs_solicitud not in page.overlay:
        page.overlay.append(bs_solicitud)

    # ---------------------------------
    # Helpers
    # ---------------------------------
    def format_iso_date(date_str: str | None) -> str:
        if not date_str: return ""
        try:
            if isinstance(date_str, str) and date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'
            dt = datetime.fromisoformat(str(date_str))
            return dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError) as e:
            return str(date_str)

    def chip_estado(txt: str):
        color_map = {
            'pendiente': ft.Colors.ORANGE_ACCENT_700,
            'aprobado': ft.Colors.LIGHT_GREEN_700,
            'entregado': ft.Colors.BLUE_700,
            'devuelto': ft.Colors.BLACK54 if page.theme_mode != ft.ThemeMode.DARK else ft.Colors.WHITE60,
            'rechazado': ft.Colors.RED_700,
            'disponible': ft.Colors.GREEN_700,
            'prestado': ft.Colors.AMBER_800,
            'mantenimiento': ft.Colors.PURPLE_700,
        }
        color = color_map.get(txt, ft.Colors.BLACK87)
        border_color = PAL["border"]

        return ft.Container(
            content=ft.Text((txt or "-").capitalize(), size=11, weight=ft.FontWeight.W_500, color=color),
            padding=ft.padding.symmetric(horizontal=8, vertical=3),
            border_radius=20, 
            border=ft.border.all(1, border_color),
        )

    def ItemCard(child: ft.Control):
        return Card(child, padding=12, radius=10)

    # Handler de Tabs
    def on_tabs_change(e):
        idx = e.control.selected_index
        state["active_tab"] = idx
        error_display.value = ""
        if idx == 0:
            render_recursos()
        elif idx == 1:
            render_solicitudes()
        elif idx == 2 and is_admin:
            render_admin_recursos()
        if page: page.update()

    # ========================================================================
    # LAYOUTS
    # ========================================================================

    # Tabs
    tab_disponibles = ft.Tab(
        text="Solicitar Recursos",
        icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
        content=ft.Container(recursos_list_display, padding=ft.padding.only(top=15))
    )
    tab_solicitudes = ft.Tab(
        text="Mis Solicitudes" if not is_admin else "Todas las Solicitudes",
        icon=ft.Icons.PENDING_ACTIONS,
        content=ft.Container(solicitudes_list_display, padding=ft.padding.only(top=15))
    )

    tabs_list = [tab_disponibles, tab_solicitudes]

    tabs = ft.Tabs(
        selected_index=state["active_tab"],
        on_change=on_tabs_change,
        tabs=tabs_list,
        expand=1
    )

    def mobile_layout():
        # Filtros para móvil - diseño vertical
        filtros_content = ft.Column([
            ft.Row([ft.Text("Filtros", size=16, weight=ft.FontWeight.W_600)], 
                  alignment=ft.MainAxisAlignment.CENTER),
            dd_plantel_filter,
            dd_lab_filter,
            dd_estado_filter,
            dd_tipo_filter,
        ], spacing=10)

        filtros_card = Card(filtros_content, padding=12)

        return ft.ListView(
            controls=[
                ft.Text("Préstamos y Recursos", size=20, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                error_display,
                filtros_card,
                tabs
            ],
            expand=True,
            spacing=12,
            padding=10,
        )

    def desktop_layout():
        # Filtros para desktop - diseño horizontal
        filtros_content = ft.Row([
            dd_plantel_filter,
            dd_lab_filter,
            dd_estado_filter,
            dd_tipo_filter,
        ], wrap=True, spacing=12)

        filtros_card = Card(filtros_content, padding=12)

        return ft.Column(
            [
                ft.Text("Préstamos y Recursos", size=22, weight=ft.FontWeight.BOLD),
                error_display,
                filtros_card,
                tabs,
            ],
            expand=True, 
            spacing=18
        )

    # Render inicial
    print("DEBUG: Llamando render_recursos inicial...")  # Debug
    render_recursos()

    if state["is_mobile"]:
        return mobile_layout()
    else:
        return desktop_layout()