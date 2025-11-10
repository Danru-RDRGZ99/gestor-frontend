import flet as ft
from api_client import ApiClient
from ui.components.cards import Card
from ui.components.inputs import TextField, Dropdown, generate_time_options
from ui.components.buttons import Primary, Danger, Icon, Ghost
from datetime import time, date, datetime, timedelta
import traceback
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

# --- Constantes ---
DIAS_SEMANA: Dict[int, str] = {
    0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"
}
DIAS_SEMANA_SHORT: Dict[int, str] = {k: v[:3] for k, v in DIAS_SEMANA.items()}

HORA_INICIO_DIA = time(0, 0)
HORA_FIN_DIA = time(23, 59)
INTERVALO_MINUTOS = 30
HORA_OPTIONS = generate_time_options(HORA_INICIO_DIA, HORA_FIN_DIA, INTERVALO_MINUTOS)

TIPO_OPTIONS = [
    ("disponible", "Disponible"),
    ("descanso", "Descanso"),
    ("mantenimiento", "Mantenimiento"),
]

def format_time_str(time_str: Optional[str]) -> str:
    if not time_str: return "N/A"
    try:
        return time_str[:5]
    except:
        return str(time_str)

def HorariosAdminView(page: ft.Page, api: ApiClient):
    user_session = page.session.get("user_session") or {}
    if user_session.get("rol") != "admin":
        return ft.Text("Acceso denegado. Solo para administradores.")

    MOBILE_BREAKPOINT = 768

    def get_is_mobile():
        return page.width is not None and page.width <= MOBILE_BREAKPOINT

    state = {
        "editing_group_rules": None,
        "editing_single_rule_id": None,
        "is_mobile": get_is_mobile(),
        "show_filters": False,  # Nuevo estado para mostrar/ocultar formulario en móvil
    }

    def update_mobile_state():
        new_is_mobile = get_is_mobile()
        if new_is_mobile != state["is_mobile"]:
            state["is_mobile"] = new_is_mobile
            state["show_filters"] = False
            print(f"INFO: Cambiando a layout {'MÓVIL' if new_is_mobile else 'WEB'}")
        else:
            state["is_mobile"] = new_is_mobile

    # --- Catálogos y Datos ---
    planteles_data = api.get_planteles()
    labs_data = api.get_laboratorios()
    if not isinstance(planteles_data, list): planteles_data = []
    if not isinstance(labs_data, list): labs_data = []
    labs_cache = labs_data
    lab_options = [("general", "General (Todos los Laboratorios)")] + \
                  [(str(l["id"]), l["nombre"]) for l in labs_cache if l.get("id")]
    lab_map = {str(l["id"]): l["nombre"] for l in labs_cache}
    lab_map["general"] = "General (Todos)"

    # --- CONTROLES PRINCIPALES ---
    dd_lab = Dropdown(
        label="Laboratorio", 
        options=lab_options, 
        value="general", 
        expand=True,
        filled=True
    )

    dias_checkboxes: Dict[int, ft.Checkbox] = {}
    checkbox_controls = []
    for dia_num, dia_nombre_short in DIAS_SEMANA_SHORT.items():
        cb = ft.Checkbox(label=dia_nombre_short, data=dia_num, tooltip=DIAS_SEMANA[dia_num])
        dias_checkboxes[dia_num] = cb
        checkbox_controls.append(cb)
    
    dias_checkboxes_row_control = ft.Row(
        checkbox_controls, 
        spacing=5, 
        wrap=True, 
        run_spacing=0, 
        alignment=ft.MainAxisAlignment.START
    )
    
    dias_checkboxes_container = ft.Column(
        [ft.Text("Días:", weight=ft.FontWeight.BOLD, size=12), dias_checkboxes_row_control],
        spacing=2
    )

    dd_inicio = Dropdown(
        label="Hora Inicio", 
        options=HORA_OPTIONS, 
        expand=True,
        filled=True
    )
    dd_fin = Dropdown(
        label="Hora Fin", 
        options=HORA_OPTIONS, 
        expand=True,
        filled=True
    )
    dd_tipo = Dropdown(
        label="Tipo", 
        options=TIPO_OPTIONS, 
        value="disponible",
        expand=True,
        filled=True
    )

    info_txt = ft.Text("")
    reglas_list_panel = ft.Column(spacing=10, scroll=ft.ScrollMode.ADAPTIVE, expand=True)

    # --- BOTÓN PARA TOGGLE DE FORMULARIO EN MÓVIL ---
    def toggle_form(e):
        state["show_filters"] = not state["show_filters"]
        render()

    toggle_form_button = ft.FilledButton(
        icon=ft.Icons.KEYBOARD_ARROW_RIGHT,
        text="Agregar reglas",
        on_click=toggle_form,
        visible=False,
        expand=True,
    )

    # --- GRUPOS DE CONTROLES DEL FORMULARIO ---
    # Formulario para móvil (expandible)
    form_group_mobile = ft.Column([
        ft.Text("Agregar/Editar Reglas:", size=16, weight=ft.FontWeight.BOLD),
        dd_lab,
        dias_checkboxes_container,
        dd_inicio,
        dd_fin,
        dd_tipo,
    ], spacing=12, visible=False)
    
    # Formulario para escritorio (siempre visible)
    form_group_desktop = ft.ResponsiveRow(
        [
            ft.Container(dd_lab, col={"sm": 12, "md": 4}),
            ft.Container(dias_checkboxes_container, col={"sm": 12, "md": 8}),
            ft.Container(dd_inicio, col={"sm": 12, "md": 3}),
            ft.Container(dd_fin, col={"sm": 12, "md": 3}),
            ft.Container(dd_tipo, col={"sm": 12, "md": 3}),
        ],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.END,
        visible=not state["is_mobile"],
    )

    # --- BOTONES DEL FORMULARIO ---
    btn_save = Primary("Agregar Regla(s)", on_click=lambda e: save_regla(e))
    btn_cancel = Ghost("Cancelar", on_click=lambda e: clear_form(e), visible=False)

    buttons_container_mobile = ft.Row([
        btn_save,
        btn_cancel,
    ], spacing=10) if state["is_mobile"] else ft.Column([
        btn_save,
        btn_cancel,
    ], spacing=5, horizontal_alignment=ft.CrossAxisAlignment.END)

    # --- FUNCIONES PRINCIPALES (sin cambios en la lógica) ---
    def load_reglas_for_render():
        return api.get_reglas_horario()

    def edit_group_click(group_rules: List[dict]):
        if not group_rules: return

        first_rule = group_rules[0]
        state["editing_group_rules"] = group_rules
        state["editing_single_rule_id"] = None

        dd_lab.value = str(first_rule.get("laboratorio_id")) if first_rule.get("laboratorio_id") is not None else "general"

        group_dias = {rule.get("dia_semana") for rule in group_rules}
        for dia_num, cb in dias_checkboxes.items():
            cb.value = (dia_num in group_dias)
            cb.update()

        dd_inicio.value = str(first_rule.get("hora_inicio"))
        dd_fin.value = str(first_rule.get("hora_fin"))
        dd_tipo.value = first_rule.get("tipo_intervalo", "disponible")

        btn_save.text = "Actualizar Grupo"
        btn_cancel.visible = True
        dias_str = ", ".join(DIAS_SEMANA_SHORT.get(d, '?') for d in sorted(group_dias) if d is not None)
        info_txt.value = f"Editando Grupo ({dias_str})"

        update_controls()

    def edit_regla_click(regla: dict):
        dia_a_editar = regla.get("dia_semana")
        state["editing_single_rule_id"] = regla.get("id")
        state["editing_group_rules"] = None

        dd_lab.value = str(regla.get("laboratorio_id")) if regla.get("laboratorio_id") is not None else "general"

        for dia_num, cb in dias_checkboxes.items():
            cb.value = (dia_num == dia_a_editar)
            cb.update()

        dd_inicio.value = str(regla.get("hora_inicio"))
        dd_fin.value = str(regla.get("hora_fin"))
        dd_tipo.value = regla.get("tipo_intervalo", "disponible")

        btn_save.text = f"Actualizar {DIAS_SEMANA_SHORT.get(dia_a_editar, '')}"
        btn_cancel.visible = True
        info_txt.value = f"Editando Regla ID: {regla.get('id')} ({DIAS_SEMANA_SHORT.get(dia_a_editar, '')})"

        update_controls()

    def delete_group_click(group_rules: List[dict]):
        if not group_rules: return

        rule_ids_to_delete = [rule.get("id") for rule in group_rules if rule.get("id")]
        if not rule_ids_to_delete:
            info_txt.value = "Error: No se encontraron IDs válidos en el grupo para eliminar."
            info_txt.update()
            return

        success_count = 0
        error_count = 0
        last_error = ""

        for rule_id in rule_ids_to_delete:
            result = api.delete_regla_horario(rule_id)
            if result and result.get("success"):
                success_count += 1
            else:
                error_count += 1
                last_error = result.get("error", "Error desconocido") if isinstance(result, dict) else "Error desconocido"

        if error_count == 0:
            info_txt.value = f"Grupo ({success_count} reglas) eliminado con éxito."
            render_reglas()
        else:
            info_txt.value = f"Error al eliminar grupo. {success_count} éxito(s), {error_count} error(es). Último error: {last_error}"
            render_reglas()
        info_txt.update()

    def delete_regla_click(regla_id: int):
        result = api.delete_regla_horario(regla_id)
        if result and result.get("success"):
            info_txt.value = "Regla eliminada."
            render_reglas()
        else:
            info_txt.value = result.get("error", "Error al eliminar.") if isinstance(result, dict) else "Error desconocido al eliminar."
        info_txt.update()

    def group_card(group_rules: List[dict]) -> ft.Control:
        if not group_rules: return ft.Container()

        first_rule = group_rules[0]
        lab_id = first_rule.get('laboratorio_id')
        lab_name = lab_map.get(str(lab_id)) if lab_id is not None else lab_map["general"]

        group_dias = sorted([r.get("dia_semana") for r in group_rules if r.get("dia_semana") is not None])
        dias_str = ", ".join(DIAS_SEMANA_SHORT.get(d, '?') for d in group_dias)

        title = ft.Text(
            f"{lab_name} - {dias_str}",
            size=15, weight=ft.FontWeight.W_600
        )

        hora_inicio_str = format_time_str(first_rule.get('hora_inicio'))
        hora_fin_str = format_time_str(first_rule.get('hora_fin'))
        hora_str = f"{hora_inicio_str} a {hora_fin_str}"

        tipo_str = str(first_rule.get('tipo_intervalo', 'N/A')).capitalize()
        es_hab = first_rule.get('es_habilitado', False)
        status_color = ft.Colors.GREEN_700 if es_hab else ft.Colors.AMBER_700

        subtitle = ft.Text(f"Horario: {hora_str}", size=12, opacity=0.8)

        status_chip = ft.Chip(label=ft.Text(tipo_str, size=11, color=status_color),
                                  bgcolor=ft.Colors.with_opacity(0.1, status_color),
                                  height=28)

        btns = ft.Row([
            Icon(ft.Icons.EDIT_NOTE_OUTLINED, "Editar Grupo", on_click=lambda e, grp=group_rules: edit_group_click(grp)),
            Icon(ft.Icons.DELETE_SWEEP_OUTLINED, "Eliminar Grupo", icon_color=ft.Colors.ERROR, on_click=lambda e, grp=group_rules: delete_group_click(grp)),
        ], spacing=6)

        header = ft.Row([
            ft.Column([title, subtitle], spacing=2, expand=True),
            status_chip,
            btns
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER)

        return Card(header, padding=14)

    def regla_card(regla: dict) -> ft.Control:
        lab_id = regla.get('laboratorio_id')
        lab_name = lab_map.get(str(lab_id)) if lab_id is not None else lab_map["general"]
        dia_num = regla.get('dia_semana')

        title = ft.Text(
            f"{lab_name} - {DIAS_SEMANA.get(dia_num, 'N/A')}",
            size=15, weight=ft.FontWeight.W_600
        )

        hora_inicio_str = format_time_str(regla.get('hora_inicio'))
        hora_fin_str = format_time_str(regla.get('hora_fin'))
        hora_str = f"{hora_inicio_str} a {hora_fin_str}"

        tipo_str = str(regla.get('tipo_intervalo', 'N/A')).capitalize()
        es_hab = regla.get('es_habilitado', False)
        status_color = ft.Colors.GREEN_700 if es_hab else ft.Colors.AMBER_700

        subtitle = ft.Text(f"Horario: {hora_str}", size=12, opacity=0.8)

        status_chip = ft.Chip(label=ft.Text(tipo_str, size=11, color=status_color),
                                  bgcolor=ft.Colors.with_opacity(0.1, status_color),
                                  height=28)

        btns = ft.Row([
            Icon(ft.Icons.EDIT_OUTLINED, "Editar", on_click=lambda e, r=regla: edit_regla_click(r)),
            Icon(ft.Icons.DELETE_OUTLINED, "Eliminar", icon_color=ft.Colors.ERROR, on_click=lambda e, rid=regla.get('id'): delete_regla_click(rid) if rid else None),
        ], spacing=6)

        header = ft.Row([
            ft.Column([title, subtitle], spacing=2, expand=True),
            status_chip,
            btns
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER)

        return Card(header, padding=14)

    def render_reglas():
        reglas_list_panel.controls.clear()
        all_reglas = load_reglas_for_render()

        if not isinstance(all_reglas, list):
            detail = all_reglas.get("error", "Error") if isinstance(all_reglas, dict) else "Error desconocido"
            reglas_list_panel.controls.append(ft.Text(f"Error al cargar reglas: {detail}", color=ft.Colors.ERROR))
        elif not all_reglas:
            reglas_list_panel.controls.append(ft.Text("No hay reglas de horario definidas."))
        else:
            grouped_rules = defaultdict(list)
            for regla in all_reglas:
                lab_id_key = regla.get('laboratorio_id') if regla.get('laboratorio_id') is not None else "general"
                group_key = (
                    lab_id_key,
                    regla.get('hora_inicio'),
                    regla.get('hora_fin'),
                    regla.get('tipo_intervalo'),
                    regla.get('es_habilitado')
                )
                grouped_rules[group_key].append(regla)

            rendered_items = []
            for group_key, rules_in_group in grouped_rules.items():
                if len(rules_in_group) > 1:
                    rules_in_group.sort(key=lambda r: r.get('dia_semana', -1))
                    rendered_items.append(group_card(rules_in_group))
                else:
                    rendered_items.append(regla_card(rules_in_group[0]))

            def get_sort_key(card):
                try:
                    title_text = card.content.controls[0].controls[0].value
                    sort_key = (
                        not title_text.startswith("General (Todos)"),
                        title_text
                    )
                    return sort_key
                except Exception:
                    return (1, "")

            rendered_items.sort(key=get_sort_key)
            reglas_list_panel.controls.extend(rendered_items)

        if reglas_list_panel.page: reglas_list_panel.update()

    def clear_form(e=None):
        state["editing_group_rules"] = None
        state["editing_single_rule_id"] = None

        dd_lab.value = "general"
        for cb in dias_checkboxes.values():
            cb.value = False
            cb.update()
        dd_inicio.value = None
        dd_fin.value = None
        dd_tipo.value = "disponible"

        btn_save.text = "Agregar Regla(s)"
        btn_cancel.visible = False
        info_txt.value = ""

        update_controls()

    def save_regla(e):
        lab_id = int(dd_lab.value) if dd_lab.value and dd_lab.value != "general" else None
        inicio_str = dd_inicio.value
        fin_str = dd_fin.value
        tipo_seleccionado = dd_tipo.value.strip() if dd_tipo.value else None
        selected_dias_nums = {num for num, cb in dias_checkboxes.items() if cb.value}

        if not all([selected_dias_nums, inicio_str, fin_str, tipo_seleccionado]):
            info_txt.value = "Completa Laboratorio, al menos un Día, Hora Inicio, Hora Fin y Tipo."
            info_txt.color=ft.Colors.ERROR
            info_txt.update(); return
        try:
            inicio = datetime.strptime(inicio_str, "%H:%M:%S").time()
            fin = datetime.strptime(fin_str, "%H:%M:%S").time()
        except (ValueError, TypeError):
            info_txt.value = "Error: Formato de hora inválido."
            info_txt.color=ft.Colors.ERROR
            info_txt.update(); return
        if inicio >= fin:
            info_txt.value = "Error: Hora inicio debe ser anterior a Hora fin."
            info_txt.color=ft.Colors.ERROR
            info_txt.update(); return

        success_count = 0
        error_count = 0
        delete_count = 0
        last_error = ""
        action_summary = ""

        es_habilitado_auto = (tipo_seleccionado == "disponible")

        if state["editing_group_rules"]:
            action_summary = "Actualizando Grupo: "
            original_rules = state["editing_group_rules"]
            original_rule_map = {r.get("dia_semana"): r for r in original_rules}
            original_dias_nums = set(original_rule_map.keys())

            dias_to_update = original_dias_nums.intersection(selected_dias_nums)
            dias_to_delete = original_dias_nums.difference(selected_dias_nums)
            dias_to_create = selected_dias_nums.difference(original_dias_nums)

            for dia_num in dias_to_update:
                rule_to_update = original_rule_map.get(dia_num)
                if rule_to_update and rule_to_update.get("id"):
                    payload = {
                        "laboratorio_id": lab_id, "dia_semana": dia_num,
                        "hora_inicio": inicio.isoformat(), "hora_fin": fin.isoformat(),
                        "es_habilitado": es_habilitado_auto, "tipo_intervalo": tipo_seleccionado,
                    }
                    try:
                        result = api.update_regla_horario(rule_to_update["id"], payload)
                        if result and result.get("id"): success_count += 1
                        else: error_count += 1; last_error = result.get("error", "Update failed") if isinstance(result, dict) else "Update failed"
                    except Exception as ex: error_count += 1; last_error = f"Update Ex: {ex}"

            for dia_num in dias_to_delete:
                rule_to_delete = original_rule_map.get(dia_num)
                if rule_to_delete and rule_to_delete.get("id"):
                    try:
                        result = api.delete_regla_horario(rule_to_delete["id"])
                        if result and result.get("success"): delete_count += 1
                        else: error_count += 1; last_error = result.get("error", "Delete failed") if isinstance(result, dict) else "Delete failed"
                    except Exception as ex: error_count += 1; last_error = f"Delete Ex: {ex}"

            for dia_num in dias_to_create:
                payload = {
                    "laboratorio_id": lab_id, "dia_semana": dia_num,
                    "hora_inicio": inicio.isoformat(), "hora_fin": fin.isoformat(),
                    "es_habilitado": es_habilitado_auto, "tipo_intervalo": tipo_seleccionado,
                }
                try:
                    result = api.create_regla_horario(payload)
                    if result and result.get("id"): success_count += 1
                    else: error_count += 1; last_error = result.get("error", "Create failed") if isinstance(result, dict) else "Create failed"
                except Exception as ex: error_count += 1; last_error = f"Create Ex: {ex}"

        elif state["editing_single_rule_id"]:
            action_summary = "Actualizando Regla Individual: "
            if len(selected_dias_nums) != 1:
                info_txt.value = "Error: Al editar una regla individual, solo debe seleccionar un día."
                info_txt.color=ft.Colors.ERROR
                info_txt.update(); return
            dia_num = list(selected_dias_nums)[0]
            payload = {
                "laboratorio_id": lab_id, "dia_semana": dia_num,
                "hora_inicio": inicio.isoformat(), "hora_fin": fin.isoformat(),
                "es_habilitado": es_habilitado_auto, "tipo_intervalo": tipo_seleccionado,
            }
            try:
                result = api.update_regla_horario(state["editing_single_rule_id"], payload)
                if result and result.get("id"): success_count += 1
                else: error_count += 1; last_error = result.get("error", "Update failed") if isinstance(result, dict) else "Update failed"
            except Exception as ex: error_count += 1; last_error = f"Update Ex: {ex}"

        else:
            action_summary = "Creando Nueva(s) Regla(s): "
            for dia_num in selected_dias_nums:
                payload = {
                    "laboratorio_id": lab_id, "dia_semana": dia_num,
                    "hora_inicio": inicio.isoformat(), "hora_fin": fin.isoformat(),
                    "es_habilitado": es_habilitado_auto, "tipo_intervalo": tipo_seleccionado,
                }
                try:
                    result = api.create_regla_horario(payload)
                    if result and result.get("id"): success_count += 1
                    else: error_count += 1; last_error = result.get("error", "Create failed") if isinstance(result, dict) else "Create failed"
                except Exception as ex: error_count += 1; last_error = f"Create Ex: {ex}"

        final_message = action_summary
        if success_count > 0: final_message += f"{success_count} éxito(s). "
        if delete_count > 0: final_message += f"{delete_count} eliminada(s). "
        if error_count > 0:
            final_message += f"{error_count} error(es). Último: {last_error}"
            info_txt.color = ft.Colors.WARNING if success_count > 0 or delete_count > 0 else ft.Colors.ERROR
        else:
            info_txt.color = ft.Colors.GREEN
            clear_form()

        info_txt.value = final_message
        render_reglas()
        info_txt.update()

    def update_controls():
        dd_lab.update()
        dd_inicio.update()
        dd_fin.update()
        dd_tipo.update()
        btn_save.update()
        btn_cancel.update()
        info_txt.update()

    def render():
        update_mobile_state()

        # Configurar controles según el modo
        if state["is_mobile"]:
            form_group_mobile.visible = state["show_filters"]
            toggle_form_button.visible = True
            form_group_desktop.visible = False
            
            # Configurar el botón de toggle
            toggle_form_button.icon = ft.Icons.KEYBOARD_ARROW_DOWN if state["show_filters"] else ft.Icons.KEYBOARD_ARROW_RIGHT
            toggle_form_button.text = "Ocultar formulario" if state["show_filters"] else "Agregar reglas"
            
        else:
            form_group_mobile.visible = False
            toggle_form_button.visible = False
            form_group_desktop.visible = True

        # Actualizar controles
        if form_group_mobile.page:
            form_group_mobile.update()
        if toggle_form_button.page:
            toggle_form_button.update()
        if form_group_desktop.page:
            form_group_desktop.update()

        # Renderizar reglas
        render_reglas()

    # --- HEADER CON FORMULARIO ---
    header_controls_container = ft.Column(
        [toggle_form_button, form_group_mobile, form_group_desktop], 
        spacing=8
    )

    # Agregar botones al formulario móvil
    if state["is_mobile"]:
        form_group_mobile.controls.append(buttons_container_mobile)

    # Agregar botones al formulario desktop
    form_group_desktop.controls.append(
        ft.Container(
            buttons_container_mobile,
            col={"sm": 12, "md": 3},
            alignment=ft.alignment.center_right
        )
    )

    # --- LAYOUT MÓVIL ---
    def mobile_layout():
        return ft.Column(
            controls=[
                ft.Text("Gestión de Horarios", 
                       size=20, 
                       weight=ft.FontWeight.BOLD,
                       text_align=ft.TextAlign.CENTER),
                Card(header_controls_container, padding=12),
                info_txt,
                ft.Divider(height=1, color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK)),
                ft.Container(
                    content=reglas_list_panel, 
                    expand=True, 
                    padding=ft.padding.symmetric(horizontal=8, vertical=8)
                ),
            ],
            expand=True,
            scroll=ft.ScrollMode.ADAPTIVE,
            spacing=12,
        )

    # --- LAYOUT ESCRITORIO ---
    def desktop_layout():
        return ft.Column(
            [
                ft.Text("Gestión de Reglas de Horario", size=22, weight=ft.FontWeight.BOLD),
                Card(header_controls_container, padding=14),
                info_txt,
                ft.Divider(height=10),
                reglas_list_panel,
            ],
            expand=True, 
            alignment=ft.MainAxisAlignment.START, 
            spacing=15
        )

    def handle_page_resize(e):
        current_is_mobile = state["is_mobile"]
        new_is_mobile = get_is_mobile()
        if current_is_mobile != new_is_mobile:
            state["show_filters"] = False
            render()

    page.on_resize = handle_page_resize

    # Carga inicial
    render()

    if state["is_mobile"]:
        return mobile_layout()
    else:
        return desktop_layout()