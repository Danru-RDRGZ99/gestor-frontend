# prestamos_view.py
from __future__ import annotations

import flet as ft
from api_client import ApiClient
from datetime import datetime, time, timedelta
# Removed math import as floor is not used
import traceback # For better error logging

from ui.components.cards import Card
from ui.components.buttons import Primary, Ghost, Tonal, Danger # Added Danger
from ui.components.inputs import TextField

# Reglas de préstamo (por horas) - Consider moving to config if needed elsewhere
CLASS_START = time(7, 0)
CLASS_END = time(14, 30)
MAX_LOAN_HOURS = 7

def PrestamosView(page: ft.Page, api: ApiClient):
    """
    Vista completa para la gestión y solicitud de préstamos y recursos.
    Incluye pestañas para usuarios y administradores, filtros y paneles de gestión.
    Esta versión contiene adaptaciones para móvil y escritorio en el mismo archivo.
    """
    # --- INICIO DE LA CORRECCIÓN ---
    user_session = page.session.get("user_session") or {}
    user_data = user_session # <-- ¡Esta es la corrección!
    is_admin = user_data.get("rol") == "admin"
    # --- FIN DE LA CORRECCIÓN ---

    # ---------------------------------
    # Paleta adaptativa (CORREGIDO)
    # ---------------------------------
    def get_palette():
        dark = page.theme_mode == ft.ThemeMode.DARK
        return {
            "border": ft.Colors.WHITE24 if dark else ft.Colors.BLACK26, # Corrected
            "text_primary": ft.Colors.WHITE if dark else ft.Colors.BLACK, # Corrected
            "text_secondary": ft.Colors.GREY_400 if dark else ft.Colors.GREY_700, # Corrected
            "muted_text": ft.Colors.GREY_600 if dark else ft.Colors.GREY_800, # Corrected
            "error_text": ft.Colors.RED_400, # Added for error display
        }
    PAL = get_palette() # Call it once

    # ---------------------------------
    # Device detection (desktop vs mobile)
    # ---------------------------------
    def detect_mobile() -> bool:
        width = getattr(page, "window_width", None)
        platform = getattr(page, "platform", None)
        is_mobile_platform = False
        try:
            # PagePlatform has a name attribute
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
        "editing_recurso_id": None, # Para el form de admin
        "is_mobile": detect_mobile(),
    }

    # Keep UI responsive to resize events
    def _on_resize(e):
        new_mobile = detect_mobile()
        if new_mobile != state["is_mobile"]:
            state["is_mobile"] = new_mobile
            # trigger rerender/refresh layout
            if page: page.update()
    page.on_resize = _on_resize

    # --- Controles de Filtros y Listas ---
    dd_plantel_filter = ft.Dropdown(label="Plantel", options=[ft.dropdown.Option("", "Todos")], width=220)
    dd_lab_filter = ft.Dropdown(label="Laboratorio", options=[ft.dropdown.Option("", "Todos")], width=220)
    dd_estado_filter = ft.Dropdown(
        label="Disponibilidad",
        options=[
            ft.dropdown.Option("", "Todos"),
            ft.dropdown.Option("disponible", "Disponible"),
            ft.dropdown.Option("prestado", "Prestado"),
            ft.dropdown.Option("mantenimiento", "Mantenimiento"),
        ],
        width=200,
    )
    dd_tipo_filter = ft.Dropdown(label="Tipo", options=[ft.dropdown.Option("", "Todos")], width=200)

    recursos_list_display = ft.Column(spacing=10, scroll=ft.ScrollMode.ADAPTIVE)
    solicitudes_list_display = ft.Column(spacing=10, scroll=ft.ScrollMode.ADAPTIVE)
    error_display = ft.Text("", color=PAL["error_text"]) # For displaying load errors

    # --- Cargar catálogos iniciales (CON VERIFICACIÓN) ---
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
            # We don't populate lab filter options here, depends on plantel filter
        elif error_loading_data is None: # Only record first error
            detail = labs_data.get("error", "Error") if isinstance(labs_data, dict) else "Respuesta inválida"
            error_loading_data = f"Error al cargar laboratorios: {detail}"
            print(f"ERROR PrestamosView: {error_loading_data}")
        else:
            detail = labs_data.get("error", "Error") if isinstance(labs_data, dict) else "Respuesta inválida"
            print(f"ERROR PrestamosView: (secondary) Error al cargar laboratorios: {detail}")


        # Verificar Tipos
        if isinstance(tipos_data, list):
            tipos_cache = tipos_data
            dd_tipo_filter.options = [ft.dropdown.Option("", "Todos")] + \
                                     [ft.dropdown.Option(t, t.capitalize()) for t in tipos_cache if t]
        elif error_loading_data is None: # Only record first error
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

    # Si hubo error cargando datos esenciales, mostrar error y salir
    if error_loading_data:
        return ft.Column([
            ft.Text("Préstamos y Recursos", size=22, weight=ft.FontWeight.BOLD),
            ft.Text("Error al cargar datos necesarios:", color=PAL["error_text"], weight=ft.FontWeight.BOLD),
            ft.Text(error_loading_data, color=PAL["error_text"])
        ])
    # --- FIN CARGA INICIAL ---


    # ---------------------------------
    # Controles de Gestión de Recursos (Admin)
    # ---------------------------------
    tf_recurso_tipo = TextField("Tipo de Recurso (ej: Cable HDMI, Proyector)")
    tf_recurso_tipo.col = {"sm": 12, "md": 4}
    tf_recurso_detalles = TextField("Detalles/Specs (opcional)") # Changed label
    tf_recurso_detalles.col = {"sm": 12, "md": 4}

    dd_recurso_estado_admin = ft.Dropdown(
        label="Estado Inicial",
        options=[
            ft.dropdown.Option("disponible", "Disponible"),
            ft.dropdown.Option("mantenimiento", "Mantenimiento"),
        ],
        value="disponible"
    )
    dd_recurso_estado_admin.col = {"sm": 12, "md": 4}

    # Agrupar laboratorios por plantel para el dropdown de admin
    lab_options_admin = []
    plantel_map_for_admin = {p['id']: p['nombre'] for p in planteles_cache if p.get('id')} # Map IDs to names
    labs_grouped = {}
    for lab in labs_cache:
        pid = lab.get("plantel_id")
        if pid in plantel_map_for_admin:
            if pid not in labs_grouped:
                labs_grouped[pid] = []
            labs_grouped[pid].append(lab)

    for pid, pname in plantel_map_for_admin.items():
        lab_options_admin.append(ft.dropdown.Option(key=None, text=pname, disabled=True)) # Group header
        if pid in labs_grouped:
            for l in sorted(labs_grouped[pid], key=lambda x: x.get('nombre', '')): # Sort labs alphabetically
                lab_options_admin.append(ft.dropdown.Option(key=str(l['id']), text=f"  {l['nombre']}"))


    dd_recurso_lab_admin = ft.Dropdown(label="Laboratorio de Origen", options=lab_options_admin)
    dd_recurso_lab_admin.col = {"sm": 12, "md": 9}

    btn_recurso_save = Primary("Agregar Recurso", on_click=lambda e: save_recurso())
    btn_recurso_save.col = {"sm": 6, "md": "auto"}

    btn_recurso_cancel = Ghost("Cancelar", on_click=lambda e: clear_recurso_form())
    btn_recurso_cancel.visible = False
    btn_recurso_cancel.col = {"sm": 6, "md": "auto"}

    # Lista para la pestaña de gestión de admin
    recursos_admin_list_display = ft.Column(spacing=10, scroll=ft.ScrollMode.ADAPTIVE, expand=True)
    admin_form_container = ft.ResponsiveRow( # Contenedor del formulario
        [
            tf_recurso_tipo,
            tf_recurso_detalles,
            dd_recurso_estado_admin,
            dd_recurso_lab_admin,
            # Use Column for buttons to stack on small screens if needed
            ft.Column([ft.Row([btn_recurso_save, btn_recurso_cancel])], col={"sm": 12, "md": 3})
        ],
        vertical_alignment=ft.CrossAxisAlignment.END, # Align based on bottom
        spacing=10
    )

    # ---------------------------------
    # Lógica de renderizado y filtros
    # ---------------------------------
    def render_recursos():
        recursos_list_display.controls.clear()
        error_display.value = "" # Clear error
        recursos_data = api.get_recursos(
            plantel_id=state["filter_plantel_id"],
            lab_id=state["filter_lab_id"],
            estado=state["filter_estado"],
            tipo=state["filter_tipo"]
        )

        # --- INICIO CORRECCIÓN DE ERRORES ---
        if isinstance(recursos_data, dict) and "error" in recursos_data:
            detail = recursos_data.get("error", "Error")
            error_msg = f"Error al cargar recursos: {detail}"
            print(f"ERROR render_recursos: {error_msg}")
            error_display.value = error_msg
            if error_display.page: error_display.update()
            if recursos_list_display.page: recursos_list_display.update() # Update to show empty state potentially
            return
        
        if not isinstance(recursos_data, list):
        # --- FIN CORRECCIÓN DE ERRORES ---
            detail = "Respuesta inválida del API"
            error_msg = f"Error al cargar recursos: {detail}"
            print(f"ERROR render_recursos: {error_msg}")
            error_display.value = error_msg
            if error_display.page: error_display.update()
            if recursos_list_display.page: recursos_list_display.update()
            return

        recursos = recursos_data
        if not recursos:
            recursos_list_display.controls.append(ft.Text("No se encontraron recursos con los filtros seleccionados.", color=PAL["muted_text"]))
        else:
            for r in recursos:
                if isinstance(r, dict): # Ensure 'r' is a dict
                    recursos_list_display.controls.append(recurso_tile(r))
                else:
                    print(f"WARN render_recursos: Expected dict for resource, got {type(r)}")

        if page: page.update()

    def render_solicitudes():
        solicitudes_list_display.controls.clear()
        error_display.value = ""
        solicitudes_data = (api.get_todos_los_prestamos() if is_admin else api.get_mis_prestamos())

        # --- INICIO CORRECCIÓN DE ERRORES ---
        if isinstance(solicitudes_data, dict) and "error" in solicitudes_data:
            detail = solicitudes_data.get("error", "Error")
            error_msg = f"Error al cargar solicitudes: {detail}"
            print(f"ERROR render_solicitudes: {error_msg}")
            error_display.value = error_msg
            if error_display.page: error_display.update()
            if solicitudes_list_display.page: solicitudes_list_display.update()
            return

        if not isinstance(solicitudes_data, list):
        # --- FIN CORRECCIÓN DE ERRORES ---
            detail = "Respuesta inválida del API"
            error_msg = f"Error al cargar solicitudes: {detail}"
            print(f"ERROR render_solicitudes: {error_msg}")
            error_display.value = error_msg
            if error_display.page: error_display.update()
            if solicitudes_list_display.page: solicitudes_list_display.update()
            return

        solicitudes = solicitudes_data
        if not solicitudes:
            solicitudes_list_display.controls.append(ft.Text("No hay solicitudes para mostrar.", color=PAL["muted_text"]))
        else:
            for s in solicitudes:
                if isinstance(s, dict): # Ensure 's' is a dict
                    solicitudes_list_display.controls.append(solicitud_tile(s))
                else:
                    print(f"WARN render_solicitudes: Expected dict for solicitud, got {type(s)}")

        if page: page.update()

    # Renderer para la lista de gestión de recursos
    def render_admin_recursos():
        recursos_admin_list_display.controls.clear()
        error_display.value = ""
        recursos_data = api.get_recursos() # Admin ve *todos* los recursos

        # --- INICIO CORRECCIÓN DE ERRORES ---
        if isinstance(recursos_data, dict) and "error" in recursos_data:
            detail = recursos_data.get("error", "Error")
            error_msg = f"Error al cargar lista de admin: {detail}"
            print(f"ERROR render_admin_recursos: {error_msg}")
            error_display.value = error_msg
            if error_display.page: error_display.update()
            if recursos_admin_list_display.page: recursos_admin_list_display.update()
            return
            
        if not isinstance(recursos_data, list):
        # --- FIN CORRECCIÓN DE ERRORES ---
            detail = "Respuesta inválida del API"
            error_msg = f"Error al cargar lista de admin: {detail}"
            print(f"ERROR render_admin_recursos: {error_msg}")
            error_display.value = error_msg
            if error_display.page: error_display.update()
            if recursos_admin_list_display.page: recursos_admin_list_display.update()
            return

        recursos = recursos_data
        if not recursos:
            recursos_admin_list_display.controls.append(ft.Text("No hay recursos creados."))
        else:
            for r in recursos:
                if isinstance(r, dict): # Ensure 'r' is a dict
                    recursos_admin_list_display.controls.append(admin_recurso_tile(r))
                else:
                    print(f"WARN render_admin_recursos: Expected dict for resource, got {type(r)}")

        if recursos_admin_list_display.page:
            recursos_admin_list_display.update()

    def on_filter_change(e):
        pid_val = dd_plantel_filter.value

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
        dd_lab_filter.value = "" # Reset lab selection when plantel changes
        if dd_lab_filter.page: dd_lab_filter.update() # Update the dropdown UI

        # Actualizar state lab_id (ahora está reseteado)
        state["filter_lab_id"] = None

        # Actualizar otros filtros
        state["filter_estado"] = dd_estado_filter.value or ""
        state["filter_tipo"] = dd_tipo_filter.value or ""

        # Volver a renderizar la lista de recursos con los nuevos filtros
        render_recursos()

    # --- INICIO CORRECCIÓN ---
    # Handler específico para el filtro de lab (no resetea nada)
    def on_lab_filter_change(e):
        lid_val = dd_lab_filter.value
        if lid_val and lid_val.isdigit():
            state["filter_lab_id"] = int(lid_val)
        else:
            state["filter_lab_id"] = None
        
        # No es necesario actualizar plantel_id, ya está seteado
        # state["filter_plantel_id"] = ... 

        state["filter_estado"] = dd_estado_filter.value or ""
        state["filter_tipo"] = dd_tipo_filter.value or ""
        render_recursos()
    # --- FIN CORRECCIÓN ---


    # Asignar handlers
    dd_plantel_filter.on_change = on_filter_change
    dd_lab_filter.on_change = on_lab_filter_change # <-- Handler separado
    dd_estado_filter.on_change = on_lab_filter_change # Puede usar el mismo que lab
    dd_tipo_filter.on_change = on_lab_filter_change # Puede usar el mismo que lab

    # ---------------------------------
    # Handlers de Gestión (Admin) - Sin cambios, excepto llamadas a render
    # ---------------------------------
    def update_loan_status(prestamo_id: int, new_status: str):
        result = api.update_prestamo_estado(prestamo_id, new_status)
        # --- INICIO CORRECCIÓN DE ERRORES ---
        if result and "error" not in result: 
        # --- FIN CORRECCIÓN DE ERRORES ---
            page.snack_bar = ft.SnackBar(ft.Text(f"Préstamo actualizado a '{new_status}'"), open=True)
            render_solicitudes()
            render_recursos() # El estado del recurso puede haber cambiado
        else:
            detail = result.get("error", "Error desconocido") if isinstance(result, dict) else "Error"
            page.snack_bar = ft.SnackBar(ft.Text(f"Error al actualizar estado: {detail}"), open=True)
        if page: page.update()

    def clear_recurso_form(e=None):
        state["editing_recurso_id"] = None
        tf_recurso_tipo.value = ""
        tf_recurso_detalles.value = ""
        dd_recurso_estado_admin.value = "disponible"
        dd_recurso_lab_admin.value = None
        btn_recurso_save.text = "Agregar Recurso"
        btn_recurso_cancel.visible = False
        if admin_form_container.page: admin_form_container.update()

    def save_recurso():
        if not all([tf_recurso_tipo.value, dd_recurso_estado_admin.value, dd_recurso_lab_admin.value]):
            page.snack_bar = ft.SnackBar(ft.Text("Tipo, Estado y Laboratorio son obligatorios."), open=True)
            if page: page.update(); return

        try:
            lab_id = int(dd_recurso_lab_admin.value)
        except (ValueError, TypeError):
            page.snack_bar = ft.SnackBar(ft.Text("Selecciona un Laboratorio válido."), open=True)
            if page: page.update(); return

        tipo = tf_recurso_tipo.value.strip()
        estado = dd_recurso_estado_admin.value
        # Use 'specs' to match Pydantic model
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

            # Check if API call was successful
            # --- INICIO CORRECCIÓN DE ERRORES ---
            if result and "error" not in result:
            # --- FIN CORRECCIÓN DE ERRORES ---
                page.snack_bar = ft.SnackBar(ft.Text(msg), open=True)
                clear_recurso_form()
                render_admin_recursos()
                render_recursos() # Re-render user view too

                # Actualizar cache de tipos si es nuevo y no es update
                if not is_update and tipo not in tipos_cache:
                    tipos_cache.append(tipo)
                    tipos_cache.sort() # Keep sorted
                    dd_tipo_filter.options = [ft.dropdown.Option("", "Todos")] + [ft.dropdown.Option(t, t.capitalize()) for t in tipos_cache]
                    if dd_tipo_filter.page: dd_tipo_filter.update()
            else:
                detail = result.get("error", "Error desconocido") if isinstance(result, dict) else "Error"
                page.snack_bar = ft.SnackBar(ft.Text(f"Error al guardar el recurso: {detail}"), open=True)

        except Exception as e:
            page.snack_bar = ft.SnackBar(ft.Text(f"Error inesperado al guardar: {e}"), open=True)
            print(f"ERROR save_recurso: {e}")
            traceback.print_exc()

        if page: page.update() # Ensure UI refresh after snackbar or renders


    def edit_recurso_click(r: dict):
        state["editing_recurso_id"] = r.get('id')
        tf_recurso_tipo.value = r.get('tipo')
        tf_recurso_detalles.value = r.get('specs') # Use 'specs' field
        dd_recurso_estado_admin.value = r.get('estado')
        # Ensure lab ID is string for dropdown value
        lab_id_val = r.get('laboratorio_id')
        dd_recurso_lab_admin.value = str(lab_id_val) if lab_id_val is not None else None

        btn_recurso_save.text = "Actualizar Recurso"
        btn_recurso_cancel.visible = True
        if admin_form_container.page: admin_form_container.update()
        page.snack_bar = ft.SnackBar(ft.Text(f"Editando recurso #{r.get('id')}..."), open=True)
        if page: page.update()

    def delete_recurso_click(r: dict):
        # Use the existing delete_dialog for consistency
        page.dialog = delete_dialog
        # Pass the resource dict or just the ID
        page.dialog.data = r.get('id') # Store ID to delete
        page.dialog.open = True
        if page: page.update()

    def confirm_delete_recurso(e):
        recurso_id = page.dialog.data
        page.dialog.open = False

        result = api.delete_recurso(recurso_id)

        # Check API response
        # --- INICIO CORRECCIÓN DE ERRORES ---
        if result and "success" in result:
        # --- FIN CORRECCIÓN DE ERRORES ---
            page.snack_bar = ft.SnackBar(ft.Text("Recurso eliminado."), open=True)
            render_admin_recursos()
            render_recursos()
        else:
            detail = result.get("error", "Error desconocido") if isinstance(result, dict) else "Error"
            page.snack_bar = ft.SnackBar(ft.Text(f"Error al eliminar: {detail}"), open=True)
        if page: page.update()

    # Diálogo de confirmación para eliminar recursos
    delete_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirmar eliminación"),
        content=ft.Text("¿Estás seguro de que quieres eliminar este recurso? Esta acción no se puede deshacer y fallará si tiene préstamos asociados."), # Added warning
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: (setattr(page.dialog, 'open', False), page.update())),
            Danger("Eliminar", on_click=confirm_delete_recurso), # Changed button type
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    # Add dialog only once
    if delete_dialog not in page.overlay:
        page.overlay.append(delete_dialog)


    # ---------------------------------
    # Creación de Tiles (elementos de lista) - CON ACCESO SEGURO
    # ---------------------------------
    def recurso_tile(r: dict):
        # Safely get lab and plantel info
        lab_id = r.get('laboratorio_id')
        lab = next((l for l in labs_cache if l.get('id') == lab_id), {}) # Find lab dict
        plantel_id = lab.get('plantel_id')
        plantel = next((p for p in planteles_cache if p.get('id') == plantel_id), {}) # Find plantel dict

        title = ft.Text(f"{r.get('tipo', 'Recurso').capitalize()} #{r.get('id', 'N/A')}", size=15, weight=ft.FontWeight.W_600)
        subtitle = ft.Text(f"Plantel: {plantel.get('nombre', '-')} · Lab: {lab.get('nombre', '-')}", size=12, opacity=0.8)

        if r.get("estado") == "disponible":
            # Pass the whole resource dict 'r' to the sheet opener
            btn = ft.ElevatedButton("Solicitar", on_click=lambda e, _r=r: open_solicitud_sheet(_r))
        else:
            btn = ft.OutlinedButton(f"{r.get('estado', 'No disponible').capitalize()}", disabled=True)

        return ItemCard(ft.Row([ft.Column([title, subtitle], spacing=2, expand=True), btn], vertical_alignment=ft.CrossAxisAlignment.CENTER))


    # Tile de Solicitud con menú de admin
    def solicitud_tile(s: dict):
        recurso = s.get('recurso', {}) # Nested object from API
        usuario = s.get('usuario', {}) # Nested object from API
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

        # Menú de acciones de Admin
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
            else:
                admin_menu = ft.Container(width=48) # Placeholder para alinear

        controls = [info_col, chip_estado(current_status)]
        if admin_menu:
            controls.append(admin_menu)

        return ItemCard(ft.Row(controls, vertical_alignment=ft.CrossAxisAlignment.CENTER))


    # Tile de Gestión de Recursos (Admin)
    def admin_recurso_tile(r: dict):
        lab_id = r.get('laboratorio_id')
        lab = next((l for l in labs_cache if l.get('id') == lab_id), {})
        plantel_id = lab.get('plantel_id')
        plantel = next((p for p in planteles_cache if p.get('id') == plantel_id), {})

        title = ft.Text(f"{r.get('tipo', 'Recurso').capitalize()} #{r.get('id', 'N/A')}", size=15, weight=ft.FontWeight.W_600)
        subtitle = ft.Text(f"Plantel: {plantel.get('nombre', '-')} · Lab: {lab.get('nombre', '-')}", size=12, opacity=0.8)

        # Usar componentes Icon (asumiendo que existen y funcionan como IconButton)
        actions = ft.Row([
            # Pass the full resource dict 'r'
            Tonal("Editar", icon=ft.Icons.EDIT_OUTLINED, on_click=lambda e, _r=r: edit_recurso_click(_r), height=36),
            Danger("Eliminar", icon=ft.Icons.DELETE_OUTLINED, on_click=lambda e, _r=r: delete_recurso_click(_r), height=36)
        ], spacing=5)


        return ItemCard(ft.Row([
            ft.Column([title, subtitle, chip_estado(r.get('estado'))], spacing=4, expand=True),
            actions
        ], vertical_alignment=ft.CrossAxisAlignment.START))

    # ---------------------------------
    # Panel de Solicitud (BottomSheet)
    # ---------------------------------
    bs_title = ft.Text("Solicitar Recurso", size=18, weight=ft.FontWeight.BOLD)
    tf_motivo = ft.TextField(label="Motivo (opcional)", multiline=True, min_lines=2)
    slider_horas = ft.Slider(min=1, max=MAX_LOAN_HOURS, divisions=MAX_LOAN_HOURS - 1, value=2, label="{value} h")

    def open_solicitud_sheet(recurso: dict):
        # Update title based on resource
        bs_title.value = f"Solicitar: {recurso.get('tipo','Recurso').capitalize()} #{recurso.get('id')}"
        state["solicitar_recurso_id"] = recurso.get('id')
        # Reset fields
        tf_motivo.value = ""
        slider_horas.value = 2
        bs_solicitud.open = True
        if bs_solicitud.page: bs_solicitud.update() # Update sheet content
        if page: page.update() # Update page to show sheet

    def close_solicitud_sheet(e):
        bs_solicitud.open = False
        if page: page.update()

    def crear_solicitud(e):
        if not state.get("solicitar_recurso_id"):
            print("ERROR: No resource ID selected for loan request.")
            page.snack_bar = ft.SnackBar(ft.Text("Error interno: No hay recurso seleccionado."), open=True)
            if page: page.update()
            return

        # Calculate start and end times (ensure they are timezone-aware if needed by backend)
        # Assuming backend expects naive or handles timezone
        inicio = datetime.now()
        horas_prestamo = int(slider_horas.value)
        fin = inicio + timedelta(hours=horas_prestamo)

        prestamo_data = {
            "recurso_id": state["solicitar_recurso_id"],
            "usuario_id": user_data.get('id'),
            # "solicitante" is set by backend based on usuario_id
            "cantidad": 1,
            "inicio": inicio.isoformat(), # Send as ISO string
            "fin": fin.isoformat(),     # Send as ISO string
            "comentario": tf_motivo.value.strip() or None, # Send None if empty
        }

        result = api.create_prestamo(prestamo_data)

        # --- INICIO CORRECCIÓN DE ERRORES ---
        if result and "error" not in result:
        # --- FIN CORRECCIÓN DE ERRORES ---
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
                bs_title, # Title that updates
                tf_motivo,
                ft.Text("Duración (horas)"),
                slider_horas,
                ft.Row([
                    ft.TextButton("Cancelar", on_click=close_solicitud_sheet),
                    ft.FilledButton("Enviar Solicitud", on_click=crear_solicitud) # Changed text
                ], alignment=ft.MainAxisAlignment.END)
            ], tight=True), # Use tight=True
            padding=20
        ),
        # Add dismissal handling
        on_dismiss=close_solicitud_sheet,
    )
    # Add bottom sheet only once
    if bs_solicitud not in page.overlay:
        page.overlay.append(bs_solicitud)

    # ---------------------------------
    # Helpers y Layout General (Mostly unchanged)
    # ---------------------------------
    def format_iso_date(date_str: str | None) -> str:
        # Duplicated function - keep consistent with dashboard
        if not date_str: return ""
        try:
            if isinstance(date_str, str) and date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'
            dt = datetime.fromisoformat(str(date_str))
            return dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError) as e:
            print(f"WARN format_iso_date: Could not format '{date_str}': {e}")
            return str(date_str)


    def chip_estado(txt: str):
        # Duplicated function - keep consistent
        color = PAL.get("chip_text", ft.Colors.BLACK87) # Default color
        border_color = PAL.get("border", ft.Colors.BLACK26)
        # Basic coloring example
        if txt == 'pendiente': color = ft.Colors.ORANGE_ACCENT_700
        elif txt == 'aprobado': color = ft.Colors.LIGHT_GREEN_700
        elif txt == 'entregado': color = ft.Colors.BLUE_700
        elif txt == 'devuelto': color = ft.Colors.BLACK54 if page.theme_mode != ft.ThemeMode.DARK else ft.Colors.WHITE60
        elif txt == 'rechazado': color = ft.Colors.RED_700
        elif txt == 'disponible': color = ft.Colors.GREEN_700
        elif txt == 'prestado': color = ft.Colors.AMBER_800
        elif txt == 'mantenimiento': color = ft.Colors.PURPLE_700


        return ft.Container(
            content=ft.Text((txt or "-").capitalize(), size=11, weight=ft.FontWeight.W_500, color=color),
            padding=ft.padding.symmetric(horizontal=8, vertical=3),
            border_radius=20, border=ft.border.all(1, border_color),
        )

    def ItemCard(child: ft.Control):
        # Duplicated function - remove bgcolor arg if Card component doesn't accept it
        # return Card(child, padding=12, radius=10, bgcolor=PAL["card_bg"])
        return Card(child, padding=12, radius=10) # Assuming Card doesn't take bgcolor

    # Handler de Tabs
    def on_tabs_change(e):
        idx = e.control.selected_index
        # Store index for state persistence if needed
        state["active_tab"] = idx
        # Clear specific errors when changing tabs
        error_display.value = ""
        if error_display.page: error_display.update()

        # Load data for the selected tab
        if idx == 0:
            render_recursos()
        elif idx == 1:
            render_solicitudes()
        elif idx == 2 and is_admin:
            render_admin_recursos()

    # Render inicial (tab 0)
    render_recursos()

    # ---------------------------------
    # Layouts: desktop and mobile (same logic, different composition)
    # ---------------------------------
    filtros_card = Card(
        ft.Row([dd_plantel_filter, dd_lab_filter, dd_estado_filter, dd_tipo_filter], wrap=True, spacing=12)
    )

    # Mobile-friendly compact filters card
    def filtros_card_mobile():
        # On mobile we use stacked dropdowns with full width for touch
        return Card(
            ft.Column(
                [
                    ft.Row([ft.Text("Filtros", weight=ft.FontWeight.W_600)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Row([dd_plantel_filter, dd_lab_filter], wrap=True, spacing=8),
                    ft.Row([dd_estado_filter, dd_tipo_filter], wrap=True, spacing=8),
                ],
                spacing=8
            ),
            padding=12
        )

    tab_disponibles = ft.Tab(
        text="Solicitar Recursos", # Changed label
        icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
        content=ft.Container(recursos_list_display, padding=ft.padding.only(top=15))
    )
    tab_solicitudes = ft.Tab(
        text="Mis Solicitudes" if not is_admin else "Todas las Solicitudes",
        icon=ft.Icons.PENDING_ACTIONS,
        content=ft.Container(solicitudes_list_display, padding=ft.padding.only(top=15))
    )

    # Contenido de la pestaña de admin
    tab_admin_recursos_content = ft.Column(
        [
            ft.Text("Gestión de Inventario de Recursos", size=18, weight=ft.FontWeight.BOLD),
            Card(admin_form_container, padding=14),
            ft.Divider(height=10),
            ft.Text("Todos los Recursos", size=16, weight=ft.FontWeight.W_600),
            recursos_admin_list_display # Esta columna tiene expand=True
        ],
        expand=True, # Allow this column to take space
        scroll=ft.ScrollMode.ADAPTIVE # Add scroll to the admin content column
    )

    tab_admin_recursos = ft.Tab(
        text="Administrar Recursos", # Changed label
        icon=ft.Icons.INVENTORY,
        # Wrap content in a Container to ensure padding is applied correctly
        content=ft.Container(tab_admin_recursos_content, padding=ft.padding.only(top=15))
    )

    # Lista de TABS
    tabs_list = [tab_disponibles, tab_solicitudes]
    if is_admin:
        tabs_list.append(tab_admin_recursos) # Añadir pestaña solo si es admin

    tabs = ft.Tabs(
        selected_index=state["active_tab"], # Restore selected index if needed
        on_change=on_tabs_change,
        tabs=tabs_list,
        expand=1
    )

    # --- Mobile specific: condensed header + floating action for "Agregar" (if admin) ---
    def mobile_layout():
        header = ft.Row(
            [
                ft.Text("Préstamos y Recursos", size=20, weight=ft.FontWeight.BOLD),
                ft.Container()  # spacer
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )

        content = ft.Column(
            [
                header,
                error_display,
                filtros_card_mobile(),
                tabs
            ],
            expand=True,
            spacing=12
        )

        if state["is_mobile"] and is_admin:
            fab = ft.Container(
                Primary("Agregar Recurso", on_click=lambda e: (setattr(state, "active_tab", 2), page.update())),
                width=160,
                height=48,
                alignment=ft.alignment.bottom_right,
                margin=ft.margin.only(right=16, bottom=16)
            )
            return ft.Stack([content, fab])

        return content

    def desktop_layout():
        return ft.Column(
            [
                ft.Text("Préstamos y Recursos", size=22, weight=ft.FontWeight.BOLD),
                error_display, # Show global errors here
                filtros_card,
                tabs, # Tabs take remaining space
            ],
            expand=True, spacing=18
        )

    # Finalmente, retornar layout basado en detección
    if state["is_mobile"]:
        return mobile_layout()
    else:
        return desktop_layout()
