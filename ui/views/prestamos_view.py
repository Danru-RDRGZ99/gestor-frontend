from __future__ import annotations

import flet as ft
from api_client import ApiClient
from datetime import datetime, time, timedelta
import traceback

from ui.components.cards import Card
from ui.components.buttons import Primary, Ghost, Tonal, Danger
from ui.components.inputs import TextField

CLASS_START = time(7, 0)
CLASS_END = time(14, 30)
MAX_LOAN_HOURS = 7


def PrestamosView(page: ft.Page, api: ApiClient):
    user_session = page.session.get("user_session") or {}
    user_data = user_session
    is_admin = user_data.get("rol") == "admin"

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

    small_style = {
        "content_padding": ft.padding.symmetric(vertical=6, horizontal=10),
        "label_style": ft.TextStyle(size=13),
        "text_style": ft.TextStyle(size=14),
    }

    dd_plantel_filter = ft.Dropdown(label="Plantel", options=[ft.dropdown.Option("", "Todos")], width=220, **small_style)
    dd_lab_filter = ft.Dropdown(label="Laboratorio", options=[ft.dropdown.Option("", "Todos")], width=220, **small_style)
    dd_estado_filter = ft.Dropdown(
        label="Disponibilidad",
        options=[
            ft.dropdown.Option("", "Todos"),
            ft.dropdown.Option("disponible", "Disponible"),
            ft.dropdown.Option("prestado", "Prestado"),
            ft.dropdown.Option("mantenimiento", "Mantenimiento"),
        ],
        width=200,
        **small_style
    )
    dd_tipo_filter = ft.Dropdown(label="Tipo", options=[ft.dropdown.Option("", "Todos")], width=200, **small_style)

    recursos_list_display = ft.Column(spacing=10, scroll=ft.ScrollMode.ADAPTIVE, expand=True)
    solicitudes_list_display = ft.Column(spacing=10, scroll=ft.ScrollMode.ADAPTIVE, expand=True)
    
    error_display = ft.Text("", color=PAL["error_text"])

    planteles_cache = []
    labs_cache = []
    tipos_cache = []
    error_loading_data = None

    try:
        planteles_data = api.get_planteles()
        labs_data = api.get_laboratorios()
        tipos_data = api.get_recurso_tipos()

        if isinstance(planteles_data, list):
            planteles_cache = planteles_data
            dd_plantel_filter.options = [ft.dropdown.Option("", "Todos")] + [
                ft.dropdown.Option(str(p["id"]), p["nombre"]) for p in planteles_cache if p.get("id")
            ]
        else:
            detail = planteles_data.get("error", "Error") if isinstance(planteles_data, dict) else "Respuesta inválida"
            error_loading_data = f"Error al cargar planteles: {detail}"
            print(f"ERROR PrestamosView: {error_loading_data}")

        if isinstance(labs_data, list):
            labs_cache = labs_data
        elif error_loading_data is None:
            detail = labs_data.get("error", "Error") if isinstance(labs_data, dict) else "Respuesta inválida"
            error_loading_data = f"Error al cargar laboratorios: {detail}"
            print(f"ERROR PrestamosView: {error_loading_data}")
        else:
            detail = labs_data.get("error", "Error") if isinstance(labs_data, dict) else "Respuesta inválida"
            print(f"ERROR PrestamosView: (secondary) Error al cargar laboratorios: {detail}")

        if isinstance(tipos_data, list):
            tipos_cache = tipos_data
            dd_tipo_filter.options = [ft.dropdown.Option("", "Todos")] + [
                ft.dropdown.Option(t, t.capitalize()) for t in tipos_cache if t
            ]
        elif error_loading_data is None:
            detail = tipos_data.get("error", "Error") if isinstance(tipos_data, dict) else "Respuesta inválida"
            error_loading_data = f"Error al cargar tipos de recurso: {detail}"
            print(f"ERROR PrestamosView: {error_loading_data}")
        else:
            detail = tipos_data.get("error", "Error") if isinstance(tipos_data, dict) else "Respuesta inválida"
            print(f"ERROR PrestamosView: (secondary) Error al cargar tipos: {detail}")

    except Exception as e:
        error_loading_data = f"Excepción al cargar datos iniciales: {e}"
        print(f"CRITICAL PrestamosView: {error_loading_data}")
        traceback.print_exc()

    if error_loading_data:
        return ft.Column([
            ft.Text("Préstamos y Recursos", size=22, weight=ft.FontWeight.BOLD),
            ft.Text("Error al cargar datos necesarios:", color=PAL["error_text"], weight=ft.FontWeight.BOLD),
            ft.Text(error_loading_data, color=PAL["error_text"]),
        ])

    tf_recurso_tipo = TextField("Tipo de Recurso (ej: Cable HDMI, Proyector)")
    tf_recurso_tipo.col = {"sm": 12, "md": 4}
    tf_recurso_detalles = TextField("Detalles/Specs (opcional)")
    tf_recurso_detalles.col = {"sm": 12, "md": 4}

    dd_recurso_estado_admin = ft.Dropdown(
        label="Estado Inicial",
        options=[
            ft.dropdown.Option("disponible", "Disponible"),
            ft.dropdown.Option("mantenimiento", "Mantenimiento"),
        ],
        value="disponible",
    )
    dd_recurso_estado_admin.col = {"sm": 12, "md": 4}

    lab_options_admin = []
    plantel_map_for_admin = {p["id"]: p["nombre"] for p in planteles_cache if p.get("id")}
    labs_grouped = {}
    for lab in labs_cache:
        pid = lab.get("plantel_id")
        if pid in plantel_map_for_admin:
            if pid not in labs_grouped:
                labs_grouped[pid] = []
            labs_grouped[pid].append(lab)

    for pid, pname in plantel_map_for_admin.items():
        lab_options_admin.append(ft.dropdown.Option(key=None, text=pname, disabled=True))
        if pid in labs_grouped:
            for l in sorted(labs_grouped[pid], key=lambda x: x.get("nombre", "")):
                lab_options_admin.append(ft.dropdown.Option(key=str(l["id"]), text=f"  {l['nombre']}"))

    dd_recurso_lab_admin = ft.Dropdown(label="Laboratorio de Origen", options=lab_options_admin)
    dd_recurso_lab_admin.col = {"sm": 12, "md": 9}

    btn_recurso_save = Primary("Agregar Recurso", on_click=lambda e: save_recurso())
    btn_recurso_save.col = {"sm": 6, "md": "auto"}

    btn_recurso_cancel = Ghost("Cancelar", on_click=lambda e: clear_recurso_form())
    btn_recurso_cancel.visible = False
    btn_recurso_cancel.col = {"sm": 6, "md": "auto"}

    recursos_admin_list_display = ft.Column(spacing=10, scroll=ft.ScrollMode.ADAPTIVE, expand=True)
    admin_form_container = ft.ResponsiveRow(
        [
            tf_recurso_tipo,
            tf_recurso_detalles,
            dd_recurso_estado_admin,
            dd_recurso_lab_admin,
            ft.Column([ft.Row([btn_recurso_save, btn_recurso_cancel])], col={"sm": 12, "md": 3}),
        ],
        vertical_alignment=ft.CrossAxisAlignment.END,
        spacing=10,
    )

    def render_recursos():
        recursos_list_display.controls.clear()
        error_display.value = ""
        recursos_data = api.get_recursos(
            plantel_id=state["filter_plantel_id"],
            lab_id=state["filter_lab_id"],
            estado=state["filter_estado"],
            tipo=state["filter_tipo"],
        )
        if isinstance(recursos_data, dict) and "error" in recursos_data:
            detail = recursos_data.get("error", "Error")
            error_msg = f"Error al cargar recursos: {detail}"
            print(f"ERROR render_recursos: {error_msg}")
            error_display.value = error_msg
            if error_display.page:
                error_display.update()
            if recursos_list_display.page:
                recursos_list_display.update()
            return
        if not isinstance(recursos_data, list):
            detail = "Respuesta inválida del API"
            error_msg = f"Error al cargar recursos: {detail}"
            print(f"ERROR render_recursos: {error_msg}")
            error_display.value = error_msg
            if error_display.page:
                error_display.update()
            if recursos_list_display.page:
                recursos_list_display.update()
            return
        recursos = recursos_data
        if not recursos:
            recursos_list_display.controls.append(
                ft.Text(
                    "No se encontraron recursos con los filtros seleccionados.",
                    color=PAL["muted_text"],
                )
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

    def render_solicitudes():
        solicitudes_list_display.controls.clear()
        error_display.value = ""
        solicitudes_data = api.get_todos_los_prestamos() if is_admin else api.get_mis_prestamos()
        if isinstance(solicitudes_data, dict) and "error" in solicitudes_data:
            detail = solicitudes_data.get("error", "Error")
            error_msg = f"Error al cargar solicitudes: {detail}"
            print(f"ERROR render_solicitudes: {error_msg}")
            error_display.value = error_msg
            if error_display.page:
                error_display.update()
            if solicitudes_list_display.page:
                solicitudes_list_display.update()
            return
        if not isinstance(solicitudes_data, list):
            detail = "Respuesta inválida del API"
            error_msg = f"Error al cargar solicitudes: {detail}"
            print(f"ERROR render_solicitudes: {error_msg}")
            error_display.value = error_msg
            if error_display.page:
                error_display.update()
            if solicitudes_list_display.page:
                solicitudes_list_display.update()
            return
        solicitudes = solicitudes_data
        if not solicitudes:
            solicitudes_list_display.controls.append(
                ft.Text("No hay solicitudes para mostrar.", color=PAL["muted_text"]) 
            )
        else:
            for s in solicitudes:
                if isinstance(s, dict):
                    if state["is_mobile"]:
                        solicitudes_list_display.controls.append(solicitud_tile_mobile(s))
                    else:
                        solicitudes_list_display.controls.append(solicitud_tile(s))
                else:
                    print(f"WARN render_solicitudes: Expected dict for solicitud, got {type(s)}")
        if page:
            page.update()

    def render_admin_recursos():
        recursos_admin_list_display.controls.clear()
        error_display.value = ""
        recursos_data = api.get_recursos()
        if isinstance(recursos_data, dict) and "error" in recursos_data:
            detail = recursos_data.get("error", "Error")
            error_msg = f"Error al cargar lista de admin: {detail}"
            print(f"ERROR render_admin_recursos: {error_msg}")
            error_display.value = error_msg
            if error_display.page:
                error_display.update()
            if recursos_admin_list_display.page:
                recursos_admin_list_display.update()
            return
        if not isinstance(recursos_data, list):
            detail = "Respuesta inválida del API"
            error_msg = f"Error al cargar lista de admin: {detail}"
            print(f"ERROR render_admin_recursos: {error_msg}")
            error_display.value = error_msg
            if error_display.page:
                error_display.update()
            if recursos_admin_list_display.page:
                recursos_admin_list_display.update()
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
        if recursos_admin_list_display.page:
            recursos_admin_list_display.update()

    def on_filter_change(e):
        pid_val = dd_plantel_filter.value
        if pid_val and str(pid_val).isdigit():
            state["filter_plantel_id"] = int(pid_val)
        else:
            state["filter_plantel_id"] = None
        if state["filter_plantel_id"]:
            labs_filtrados = [
                l for l in labs_cache if l.get("plantel_id") == state["filter_plantel_id"]
            ]
            dd_lab_filter.options = [ft.dropdown.Option("", "Todos")] + [
                ft.dropdown.Option(str(l["id"]), l["nombre"]) for l in labs_filtrados if l.get("id")
            ]
        else:
            dd_lab_filter.options = [ft.dropdown.Option("", "Todos")]
        dd_lab_filter.value = ""
        if dd_lab_filter.page:
            dd_lab_filter.update()
        state["filter_lab_id"] = None
        state["filter_estado"] = dd_estado_filter.value or ""
        state["filter_tipo"] = dd_tipo_filter.value or ""
        render_recursos()

    def on_lab_filter_change(e):
        lid_val = dd_lab_filter.value
        if lid_val and str(lid_val).isdigit():
            state["filter_lab_id"] = int(lid_val)
        else:
            state["filter_lab_id"] = None
        state["filter_estado"] = dd_estado_filter.value or ""
        state["filter_tipo"] = dd_tipo_filter.value or ""
        render_recursos()

    dd_plantel_filter.on_change = on_filter_change
    dd_lab_filter.on_change = on_lab_filter_change
    dd_estado_filter.on_change = on_lab_filter_change
    dd_tipo_filter.on_change = on_lab_filter_change

    def update_loan_status(prestamo_id: int, new_status: str):
        result = api.update_prestamo_estado(prestamo_id, new_status)
        if result and "error" not in result:
            page.snack_bar = ft.SnackBar(ft.Text(f"Préstamo actualizado a '{new_status}'"), open=True)
            render_solicitudes()
            render_recursos()
        else:
            detail = result.get("error", "Error desconocido") if isinstance(result, dict) else "Error"
            page.snack_bar = ft.SnackBar(ft.Text(f"Error al actualizar estado: {detail}"), open=True)
        if page:
            page.update()

    def clear_recurso_form(e=None):
        state["editing_recurso_id"] = None
        tf_recurso_tipo.value = ""
        tf_recurso_detalles.value = ""
        dd_recurso_estado_admin.value = "disponible"
        dd_recurso_lab_admin.value = None
        btn_recurso_save.text = "Agregar Recurso"
        btn_recurso_cancel.visible = False
        if admin_form_container.page:
            admin_form_container.update()

    def save_recurso():
        if not all([tf_recurso_tipo.value, dd_recurso_estado_admin.value, dd_recurso_lab_admin.value]):
            page.snack_bar = ft.SnackBar(ft.Text("Tipo, Estado y Laboratorio son obligatorios."), open=True)
            if page:
                page.update()
            return
        try:
            lab_id = int(dd_recurso_lab_admin.value)
        except (ValueError, TypeError):
            page.snack_bar = ft.SnackBar(ft.Text("Selecciona un Laboratorio válido."), open=True)
            if page:
                page.update()
            return
        tipo = tf_recurso_tipo.value.strip()
        estado = dd_recurso_estado_admin.value
        specs = tf_recurso_detalles.value.strip() or ""
        recurso_id = state.get("editing_recurso_id")
        result = None
        is_update = bool(recurso_id)
        try:
            if is_update:
                result = api.update_recurso(recurso_id, tipo, estado, lab_id, specs)
                msg = "Recurso actualizado"
            else:
                result = api.create_recurso(tipo, estado, lab_id, specs)
                msg = "Recurso creado"
            if result and "error" not in result:
                page.snack_bar = ft.SnackBar(ft.Text(msg), open=True)
                clear_recurso_form()
                render_admin_recursos()
                render_recursos()
                if not is_update and tipo not in tipos_cache:
                    tipos_cache.append(tipo)
                    tipos_cache.sort()
                    dd_tipo_filter.options = [ft.dropdown.Option("", "Todos")] + [
                        ft.dropdown.Option(t, t.capitalize()) for t in tipos_cache
                    ]
                    if dd_tipo_filter.page:
                        dd_tipo_filter.update()
            else:
                detail = result.get("error", "Error desconocido") if isinstance(result, dict) else "Error"
                page.snack_bar = ft.SnackBar(ft.Text(f"Error al guardar el recurso: {detail}"), open=True)
        except Exception as e:
            page.snack_bar = ft.SnackBar(ft.Text(f"Error inesperado al guardar: {e}"), open=True)
            print(f"ERROR save_recurso: {e}")
            traceback.print_exc()
        if page:
            page.update()

    def edit_recurso_click(r: dict):
        state["editing_recurso_id"] = r.get("id")
        tf_recurso_tipo.value = r.get("tipo")
        tf_recurso_detalles.value = r.get("specs")
        dd_recurso_estado_admin.value = r.get("estado")
        lab_id_val = r.get("laboratorio_id")
        dd_recurso_lab_admin.value = str(lab_id_val) if lab_id_val is not None else None
        btn_recurso_save.text = "Actualizar Recurso"
        btn_recurso_cancel.visible = True
        if admin_form_container.page:
            admin_form_container.update()
        page.snack_bar = ft.SnackBar(ft.Text(f"Editando recurso #{r.get('id')}..."), open=True)
        if page:
            page.update()

    def delete_recurso_click(r: dict):
        page.dialog = delete_dialog
        page.dialog.data = r.get("id")
        page.dialog.open = True
        if page:
            page.update()

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
        if page:
            page.update()

    delete_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirmar eliminación"),
        content=ft.Text(
            "¿Estás seguro de que quieres eliminar este recurso? Esta acción no se puede deshacer y fallará si tiene préstamos asociados."
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: (setattr(page.dialog, "open", False), page.update())),
            Danger("Eliminar", on_click=confirm_delete_recurso),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    if delete_dialog not in page.overlay:
        page.overlay.append(delete_dialog)

    def recurso_tile_mobile(r: dict):
        lab_id = r.get("laboratorio_id")
        lab = next((l for l in labs_cache if l.get("id") == lab_id), {})
        plantel_id = lab.get("plantel_id")
        plantel = next((p for p in planteles_cache if p.get("id") == plantel_id), {})
        title = ft.Text(f"{r.get('tipo', 'Recurso').capitalize()} #{r.get('id', 'N/A')}", size=15, weight=ft.FontWeight.W_600)
        subtitle = ft.Text(
            f"Plantel: {plantel.get('nombre', '-')}\nLab: {lab.get('nombre', '-')}",
            size=11,
            opacity=0.85,
        )
        estado_chip = chip_estado(r.get("estado"))
        if r.get("estado") == "disponible":
            btn = Primary("Solicitar", height=34, expand=True, on_click=lambda e, _r=r: open_solicitud_sheet(_r))
        else:
            btn = ft.OutlinedButton(
                f"{r.get('estado', 'No disponible').capitalize()}", height=34, expand=True, disabled=True
            )
        return Card(
            ft.Container(
                ft.Column([
                    ft.Row([title, estado_chip], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    subtitle,
                    btn,
                ], spacing=8),
            ),
            padding=12,
        )

    def solicitud_tile_mobile(s: dict):
        recurso = s.get("recurso", {})
        usuario = s.get("usuario", {})
        solicitud_id = s.get("id", "N/A")
        recurso_tipo = recurso.get("tipo", "Recurso").capitalize()
        recurso_id_val = recurso.get("id", "N/A")
        title = ft.Text(f"Solicitud #{solicitud_id}", size=15, weight=ft.FontWeight.W_600)
        recurso_info = ft.Text(f"{recurso_tipo} #{recurso_id_val}", size=12, opacity=0.85)
        timeline = ft.Text(
            f"Pedido: {format_iso_date(s.get('created_at'))}\nDevolución: {format_iso_date(s.get('fin'))}",
            size=10,
            opacity=0.7,
        )
        estado_chip = chip_estado(s.get("estado"))
        admin_info = None
        if is_admin:
            solicitante_nombre = usuario.get("nombre", "-")
            admin_info = ft.Text(f"Solicitante: {solicitante_nombre}", size=11, italic=True, opacity=0.8)
        content = [ft.Row([title, estado_chip], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)]
        if admin_info:
            content.append(admin_info)
        content.extend([recurso_info, timeline])
        admin_actions = None
        current_status = s.get("estado", "pendiente")
        if is_admin:
            if current_status == "pendiente":
                admin_actions = ft.Row([
                    Primary("Aprobar", height=32, expand=True, on_click=lambda _, _id=s["id"]: update_loan_status(_id, "aprobado")),
                    Danger("Rechazar", height=32, expand=True, on_click=lambda _, _id=s["id"]: update_loan_status(_id, "rechazado")),
                ], spacing=6)
            elif current_status == "aprobado":
                admin_actions = Primary(
                    "Marcar Entregado", height=32, expand=True, on_click=lambda _, _id=s["id"]: update_loan_status(_id, "entregado")
                )
            elif current_status == "entregado":
                admin_actions = Primary(
                    "Marcar Devuelto", height=32, expand=True, on_click=lambda _, _id=s["id"]: update_loan_status(_id, "devuelto")
                )
        if admin_actions:
            content.append(admin_actions)
        return Card(ft.Container(ft.Column(content, spacing=6)), padding=12)

    def recurso_tile(r: dict):
        lab_id = r.get("laboratorio_id")
        lab = next((l for l in labs_cache if l.get("id") == lab_id), {})
        plantel_id = lab.get("plantel_id")
        plantel = next((p for p in planteles_cache if p.get("id") == plantel_id), {})
        title = ft.Text(f"{r.get('tipo', 'Recurso').capitalize()} #{r.get('id', 'N/A')}", size=15, weight=ft.FontWeight.W_600)
        subtitle = ft.Text(
            f"Plantel: {plantel.get('nombre', '-')}\nLab: {lab.get('nombre', '-')}",
            size=12,
            opacity=0.8,
        )
        if r.get("estado") == "disponible":
            btn = ft.ElevatedButton("Solicitar", on_click=lambda e, _r=r: open_solicitud_sheet(_r))
        else:
            btn = ft.OutlinedButton(f"{r.get('estado', 'No disponible').capitalize()}", disabled=True)
        return ItemCard(
            ft.Row([ft.Column([title, subtitle], spacing=2, expand=True), btn], vertical_alignment=ft.CrossAxisAlignment.CENTER)
        )

    def solicitud_tile(s: dict):
        recurso = s.get("recurso", {})
        usuario = s.get("usuario", {})
        solicitud_id = s.get("id", "N/A")
        recurso_tipo = recurso.get("tipo", "Recurso").capitalize()
        recurso_id_val = recurso.get("id", "N/A")
        title = ft.Text(
            f"Solicitud #{solicitud_id} · {recurso_tipo} #{recurso_id_val}", size=15, weight=ft.FontWeight.W_600
        )
        timeline = ft.Text(
            f"Pedido: {format_iso_date(s.get('created_at'))} · Devolución: {format_iso_date(s.get('fin'))}",
            size=11,
        )
        if is_admin:
            solicitante_nombre = usuario.get("nombre", "-")
            solicitante = ft.Text(f"Solicitante: {solicitante_nombre}", size=12, italic=True)
            info_col = ft.Column([title, solicitante, timeline], spacing=2, expand=True)
        else:
            info_col = ft.Column([title, timeline], spacing=2, expand=True)
        admin_menu = None
        current_status = s.get("estado", "pendiente")
        if is_admin:
            menu_items = []
            if current_status == "pendiente":
                menu_items.append(
                    ft.PopupMenuItem(text="Aprobar", on_click=lambda _, _id=s["id"]: update_loan_status(_id, "aprobado"))
                )
                menu_items.append(
                    ft.PopupMenuItem(text="Rechazar", on_click=lambda _, _id=s["id"]: update_loan_status(_id, "rechazado"))
                )
            elif current_status == "aprobado":
                menu_items.append(
                    ft.PopupMenuItem(
                        text="Marcar como Entregado", on_click=lambda _, _id=s["id"]: update_loan_status(_id, "entregado")
                    )
                )
            elif current_status == "entregado":
                menu_items.append(
                    ft.PopupMenuItem(
                        text="Markar como Devuelto", on_click=lambda _, _id=s["id"]: update_loan_status(_id, "devuelto")
                    )
                )
            if menu_items:
                admin_menu = ft.PopupMenuButton(items=menu_items, icon=ft.Icons.MORE_VERT)
            else:
                admin_menu = ft.Container(width=48)
        controls = [info_col, chip_estado(current_status)]
        if admin_menu:
            controls.append(admin_menu)
        return ItemCard(ft.Row(controls, vertical_alignment=ft.CrossAxisAlignment.CENTER))

    def admin_recurso_tile(r: dict):
        lab_id = r.get("laboratorio_id")
        lab = next((l for l in labs_cache if l.get("id") == lab_id), {})
        plantel_id = lab.get("plantel_id")
        plantel = next((p for p in planteles_cache if p.get("id") == plantel_id), {})
        title = ft.Text(f"{r.get('tipo', 'Recurso').capitalize()} #{r.get('id', 'N/A')}", size=15, weight=ft.FontWeight.W_600)
        subtitle = ft.Text(
            f"Plantel: {plantel.get('nombre', '-')}\nLab: {lab.get('nombre', '-')}",
            size=12,
            opacity=0.8,
        )
        actions = ft.Row(
            [
                Tonal("Editar", icon=ft.Icons.EDIT_OUTLINED, on_click=lambda e, _r=r: edit_recurso_click(_r), height=36),
                Danger("Eliminar", icon=ft.Icons.DELETE_OUTLINED, on_click=lambda e, _r=r: delete_recurso_click(_r), height=36),
            ],
            spacing=5,
        )
        return ItemCard(
            ft.Row([
                ft.Column([title, subtitle, chip_estado(r.get("estado"))], spacing=4, expand=True),
                actions,
            ], vertical_alignment=ft.CrossAxisAlignment.START)
        )

    def admin_recurso_tile_mobile(r: dict):
        lab_id = r.get("laboratorio_id")
        lab = next((l for l in labs_cache if l.get("id") == lab_id), {})
        plantel_id = lab.get("plantel_id")
        plantel = next((p for p in planteles_cache if p.get("id") == plantel_id), {})
        
        title = ft.Text(f"{r.get('tipo', 'Recurso').capitalize()} #{r.get('id', 'N/A')}", size=15, weight=ft.FontWeight.W_600)
        subtitle = ft.Text(
            f"Plantel: {plantel.get('nombre', '-')}\nLab: {lab.get('nombre', '-')}",
            size=11,
            opacity=0.85,
        )
        estado_chip = chip_estado(r.get("estado"))

        actions = ft.Row(
            [
                Tonal("Editar", icon=ft.Icons.EDIT_OUTLINED, on_click=lambda e, _r=r: edit_recurso_click(_r), height=34, expand=True),
                Danger("Eliminar", icon=ft.Icons.DELETE_OUTLINED, on_click=lambda e, _r=r: delete_recurso_click(_r), height=34, expand=True),
            ],
            spacing=6,
        )
        
        return Card(
            ft.Container(
                ft.Column([
                    ft.Row([title, estado_chip], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    subtitle,
                    ft.Divider(height=5, opacity=0),
                    actions,
                ], spacing=6),
            ),
            padding=12,
        )

    bs_title = ft.Text("Solicitar Recurso", size=18, weight=ft.FontWeight.BOLD)
    tf_motivo = ft.TextField(label="Motivo (opcional)", multiline=True, min_lines=2)
    slider_horas = ft.Slider(min=1, max=MAX_LOAN_HOURS, divisions=MAX_LOAN_HOURS - 1, value=2, label="{value} h")

    def open_solicitud_sheet(recurso: dict):
        bs_title.value = f"Solicitar: {recurso.get('tipo','Recurso').capitalize()} #{recurso.get('id')}"
        state["solicitar_recurso_id"] = recurso.get("id")
        tf_motivo.value = ""
        slider_horas.value = 2
        bs_solicitud.open = True
        if bs_solicitud.page:
            bs_solicitud.update()
        if page:
            page.update()

    def close_solicitud_sheet(e):
        bs_solicitud.open = False
        if page:
            page.update()

    def crear_solicitud(e):
        if not state.get("solicitar_recurso_id"):
            print("ERROR: No resource ID selected for loan request.")
            page.snack_bar = ft.SnackBar(ft.Text("Error interno: No hay recurso seleccionado."), open=True)
            if page:
                page.update()
            return
        inicio = datetime.now()
        horas_prestamo = int(slider_horas.value)
        fin = inicio + timedelta(hours=horas_prestamo)
        prestamo_data = {
            "recurso_id": state["solicitar_recurso_id"],
            "usuario_id": user_data.get("id"),
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
        if page:
            page.update()

    bs_solicitud = ft.BottomSheet(
        ft.Container(
            ft.Column(
                [
                    bs_title,
                    tf_motivo,
                    ft.Text("Duración (horas)"),
                    slider_horas,
                    ft.Row(
                        [ft.TextButton("Cancelar", on_click=close_solicitud_sheet), ft.FilledButton("Enviar Solicitud", on_click=crear_solicitud)],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                tight=True,
            ),
            padding=20,
        ),
        on_dismiss=close_solicitud_sheet,
    )
    if bs_solicitud not in page.overlay:
        page.overlay.append(bs_solicitud)

    def close_filter_sheet(e):
        bs_filtros.open = False
        if bs_filtros.page:
            bs_filtros.update()

    bs_filtros = ft.BottomSheet(
        ft.Container(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("Filtros", size=18, weight=ft.FontWeight.BOLD),
                            # --- ¡CORRECCIÓN 1 AQUÍ! ---
                            ft.IconButton(icon=ft.Icons.CLOSE, on_click=close_filter_sheet),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    dd_plantel_filter,
                    dd_lab_filter,
                    dd_estado_filter,
                    dd_tipo_filter,
                ],
                tight=True,
                spacing=8,
            ),
            padding=ft.padding.only(top=10, left=20, right=20, bottom=30),
        ),
        on_dismiss=close_filter_sheet,
    )
    if bs_filtros not in page.overlay:
        page.overlay.append(bs_filtros)

    def open_filter_sheet(e):
        bs_filtros.open = True
        if bs_filtros.page:
            bs_filtros.update()

    def format_iso_date(date_str: str | None) -> str:
        if not date_str:
            return ""
        try:
            if isinstance(date_str, str) and date_str.endswith("Z"):
                date_str = date_str[:-1] + "+00:00"
            dt = datetime.fromisoformat(str(date_str))
            return dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError) as e:
            print(f"WARN format_iso_date: Could not format '{date_str}': {e}")
            return str(date_str)

    def chip_estado(txt: str):
        color = PAL.get("chip_text", ft.Colors.BLACK87)
        border_color = PAL.get("border", ft.Colors.BLACK26)
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
        elif txt == "disponible":
            color = ft.Colors.GREEN_700
        elif txt == "prestado":
            color = ft.Colors.AMBER_800
        elif txt == "mantenimiento":
            color = ft.Colors.PURPLE_700
        return ft.Container(
            content=ft.Text((txt or "-").capitalize(), size=11, weight=ft.FontWeight.W_500, color=color),
            padding=ft.padding.symmetric(horizontal=8, vertical=3),
            border_radius=20,
            border=ft.border.all(1, border_color),
        )

    def ItemCard(child: ft.Control):
        return Card(child, padding=12, radius=10)

    def on_tabs_change(e):
        idx = e.control.selected_index
        state["active_tab"] = idx
        error_display.value = ""
        if error_display.page:
            error_display.update()
        if idx == 0:
            render_recursos()
        elif idx == 1:
            render_solicitudes()
        elif idx == 2 and is_admin:
            render_admin_recursos()

    render_recursos()

    def apply_filter_styles():
        if state["is_mobile"]:
            for dd in (dd_plantel_filter, dd_lab_filter, dd_estado_filter, dd_tipo_filter):
                dd.width = None
                dd.expand = True
        else:
            dd_plantel_filter.width, dd_lab_filter.width, dd_estado_filter.width, dd_tipo_filter.width = 220, 220, 200, 200
            for dd in (dd_plantel_filter, dd_lab_filter, dd_estado_filter, dd_tipo_filter):
                dd.expand = False
        for dd in (dd_plantel_filter, dd_lab_filter, dd_estado_filter, dd_tipo_filter):
            if dd.page:
                dd.update()

    def filtros_control():
        if state["is_mobile"]:
            return ft.Row(
                [
                    ft.FilledButton(
                        "Mostrar Filtros",
                        # --- ¡CORRECCIÓN 2 AQUÍ! ---
                        icon=ft.Icons.FILTER_LIST,
                        on_click=open_filter_sheet,
                        height=40
                    )
                ],
                alignment=ft.MainAxisAlignment.END,
            )
        else:
            content = ft.Row([dd_plantel_filter, dd_lab_filter, dd_estado_filter, dd_tipo_filter], wrap=True, spacing=12)
            return Card(ft.Container(content), padding=12)

    tab_disponibles = ft.Tab(
        text="Solicitar Recursos",
        icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
        content=recursos_list_display,
    )
    tab_solicitudes = ft.Tab(
        text="Mis Solicitudes" if not is_admin else "Todas las Solicitudes",
        icon=ft.Icons.PENDING_ACTIONS,
        content=solicitudes_list_display,
    )

    tab_admin_recursos_content = ft.Column(
        [
            ft.Text("Gestión de Inventario de Recursos", size=18, weight=ft.FontWeight.BOLD),
            Card(admin_form_container, padding=14),
            ft.Divider(height=10),
            ft.Text("Todos los Recursos", size=16, weight=ft.FontWeight.W_600),
            recursos_admin_list_display,
        ],
        expand=True,
        scroll=ft.ScrollMode.ADAPTIVE,
    )

    tab_admin_recursos = ft.Tab(
        text="Administrar Recursos",
        icon=ft.Icons.INVENTORY,
        content=ft.Container(tab_admin_recursos_content, padding=ft.padding.only(top=15)),
    )

    tabs_list = [tab_disponibles, tab_solicitudes]
    if is_admin:
        tabs_list.append(tab_admin_recursos)

    tabs = ft.Tabs(
        selected_index=state["active_tab"], 
        on_change=on_tabs_change, 
        tabs=tabs_list, 
        expand=1
    )
    
    desktop_tabs = ft.Tabs(
        selected_index=state["active_tab"], 
        on_change=on_tabs_change, 
        tabs=tabs_list, 
        expand=1
    )

    def mobile_layout():
        return ft.SafeArea(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("Préstamos y Recursos", size=20, weight=ft.FontWeight.BOLD),
                        error_display,
                        filtros_control(),
                        tabs,
                    ],
                    expand=True,
                    spacing=12,
                ),
                padding=10, 
                expand=True
            )
        )

    def desktop_layout():
        return ft.Column(
            [
                ft.Text("Préstamos y Recursos", size=22, weight=ft.FontWeight.BOLD),
                error_display,
                filtros_control(),
                desktop_tabs,
            ],
            expand=True,
            spacing=18,
        )

    def _on_resize(e):
        new_mobile = detect_mobile()
        
        if new_mobile != state["is_mobile"]:
            state["is_mobile"] = new_mobile
            apply_filter_styles()
            
            if page:
                page.update()

    page.on_resize = _on_resize
    apply_filter_styles()

    if state["is_mobile"]:
        return mobile_layout()
    else:
        return desktop_layout()