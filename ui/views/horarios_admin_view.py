import flet as ft
from api_client import ApiClient
from ui.components.cards import Card
from ui.components.inputs import TextField, Dropdown, generate_time_options
from ui.components.buttons import Primary, Danger, Icon, Ghost
from datetime import time, date, datetime, timedelta
import traceback
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import json

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

# Helper to format time strings nicely
def format_time_str(time_str: Optional[str]) -> str:
    if not time_str: return "N/A"
    try:
        return time_str[:5]
    except:
        return str(time_str)

def HorariosAdminView(page: ft.Page, api: ApiClient):
    # DEBUG: Verificar qué hay en la sesión
    print("🔍 DEBUG - Contenido completo de page.session:")
    for key in page.session.keys():
        print(f"   {key}: {page.session.get(key)}")
    
    # CORRECCIÓN: Buscar la sesión del usuario en diferentes lugares posibles
    user_session = None
    
    # Intentar diferentes posibles ubicaciones de la sesión
    possible_keys = ["user_session", "user", "usuario", "current_user", "user_data"]
    
    for key in possible_keys:
        if key in page.session.keys():
            user_session = page.session.get(key)
            print(f"✅ Encontrada sesión en clave: {key}")
            break
    
    # Si no se encontró en ninguna clave específica, buscar cualquier dato de usuario
    if user_session is None:
        print("🔍 Buscando datos de usuario en toda la sesión...")
        for key in page.session.keys():
            value = page.session.get(key)
            if isinstance(value, (dict, str)) and any(user_field in str(value).lower() for user_field in ['user', 'usuario', 'nombre', 'correo', 'rol', 'admin']):
                user_session = value
                print(f"✅ Encontrados datos de usuario en clave: {key}")
                break
    
    # Si user_session es un string, intentar parsearlo como JSON
    if isinstance(user_session, str):
        try:
            user_session = json.loads(user_session)
            print("✅ Sesión parseada de JSON string")
        except:
            user_session = {}
            print("❌ No se pudo parsear la sesión como JSON")
    # Si no es un diccionario, inicializar como vacío
    elif not isinstance(user_session, dict):
        user_session = {}
        print("❌ La sesión no es un diccionario")
    
    print(f"🔍 user_session final: {user_session}")
    
    # Verificar permisos de administrador - MÚLTIPLES FORMAS
    user_data = user_session.get("user", {})
    if not isinstance(user_data, dict):
        # Intentar acceder directamente a los campos
        user_data = user_session
    
    print(f"🔍 user_data final: {user_data}")
    
    # Verificar rol de múltiples formas
    user_role = None
    
    # Intentar diferentes nombres de campo para el rol
    role_fields = ["rol", "role", "tipo", "type", "user_rol"]
    for field in role_fields:
        if user_data.get(field):
            user_role = user_data.get(field)
            print(f"✅ Rol encontrado en campo '{field}': {user_role}")
            break
    
    # Si no se encontró en campos específicos, buscar en toda la estructura
    if user_role is None:
        # Buscar recursivamente en la estructura
        def find_role(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key.lower() in ["rol", "role", "tipo", "type"] and value:
                        return value
                    if isinstance(value, (dict, list)):
                        result = find_role(value, f"{path}.{key}")
                        if result:
                            return result
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    result = find_role(item, f"{path}[{i}]")
                    if result:
                        return result
            return None
        
        user_role = find_role(user_data)
        if user_role:
            print(f"✅ Rol encontrado recursivamente: {user_role}")
    
    print(f"🔍 Rol final determinado: {user_role}")
    
    # Si no es administrador, mostrar mensaje de acceso denegado
    if user_role != "admin":
        print(f"❌ Acceso denegado. Rol del usuario: {user_role}, se esperaba: admin")
        
        # Mostrar información de debug para ayudar
        debug_info = ft.Column([
            ft.Text("Acceso denegado. Solo para administradores.", color=ft.Colors.ERROR, size=16),
            ft.Text("Información de debug:", weight=ft.FontWeight.BOLD),
            ft.Text(f"Rol detectado: {user_role}"),
            ft.Text(f"Session keys: {list(page.session.keys())}"),
            ft.Text(f"User session type: {type(user_session)}"),
            ft.Text(f"User data: {user_data}"),
        ])
        return debug_info

    # Si llegamos aquí, el usuario es administrador
    print("✅ Acceso concedido - usuario es administrador")

    # Modified state to track group editing
    state = {
        "editing_group_rules": None,
        "editing_single_rule_id": None,
    }

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

    # --- 1. Definir Controles ---
    dd_lab = Dropdown(label="Laboratorio", options=lab_options, value="general", col={"md": 4})

    dias_checkboxes: Dict[int, ft.Checkbox] = {}
    checkbox_controls = []
    for dia_num, dia_nombre_short in DIAS_SEMANA_SHORT.items():
        cb = ft.Checkbox(label=dia_nombre_short, data=dia_num, tooltip=DIAS_SEMANA[dia_num])
        dias_checkboxes[dia_num] = cb
        checkbox_controls.append(cb)
    dias_checkboxes_row_control = ft.Row(checkbox_controls, spacing=5, wrap=True, run_spacing=0, alignment=ft.MainAxisAlignment.START)
    dias_checkboxes_container = ft.Column(
         [ft.Text("Días:", weight=ft.FontWeight.BOLD, size=12), dias_checkboxes_row_control],
         col={"md": 8}, spacing=2
    )

    dd_inicio = Dropdown(label="Hora Inicio", options=HORA_OPTIONS, col={"sm": 6, "md": 3})
    dd_fin = Dropdown(label="Hora Fin", options=HORA_OPTIONS, col={"sm": 6, "md": 3})
    dd_tipo = Dropdown(label="Tipo", options=TIPO_OPTIONS, value="disponible", col={"sm": 12, "md": 3})

    info_txt = ft.Text("")
    reglas_list_panel = ft.Column(spacing=10, scroll=ft.ScrollMode.ADAPTIVE, expand=True)

    # --- 2. Declarar variables ---
    btn_save = None
    btn_cancel = None
    form_row = None

    # --- 3. Definir Funciones ---

    def load_reglas_for_render():
        return api.get_reglas_horario()

    # --- NEW: Edit Group Function ---
    def edit_group_click(group_rules: List[dict]):
        nonlocal state, dd_lab, dias_checkboxes, dd_inicio, dd_fin, dd_tipo, btn_save, btn_cancel, info_txt
        if not group_rules: return

        # Use the first rule for common data
        first_rule = group_rules[0]
        state["editing_group_rules"] = group_rules
        state["editing_single_rule_id"] = None

        dd_lab.value = str(first_rule.get("laboratorio_id")) if first_rule.get("laboratorio_id") is not None else "general"

        # Check all days present in the group
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

        # Update controls
        dd_lab.update()
        dd_inicio.update()
        dd_fin.update()
        dd_tipo.update()
        btn_save.update()
        btn_cancel.update()
        info_txt.update()

    # --- MODIFIED: Edit Single Rule Function ---
    def edit_regla_click(regla: dict):
        nonlocal state, dd_lab, dias_checkboxes, dd_inicio, dd_fin, dd_tipo, btn_save, btn_cancel, info_txt

        dia_a_editar = regla.get("dia_semana")
        state["editing_single_rule_id"] = regla.get("id")
        state["editing_group_rules"] = None

        dd_lab.value = str(regla.get("laboratorio_id")) if regla.get("laboratorio_id") is not None else "general"

        # Check only this specific day
        for dia_num, cb in dias_checkboxes.items():
            cb.value = (dia_num == dia_a_editar)
            cb.update()

        dd_inicio.value = str(regla.get("hora_inicio"))
        dd_fin.value = str(regla.get("hora_fin"))
        dd_tipo.value = regla.get("tipo_intervalo", "disponible")

        btn_save.text = f"Actualizar {DIAS_SEMANA_SHORT.get(dia_a_editar, '')}"
        btn_cancel.visible = True
        info_txt.value = f"Editando Regla ID: {regla.get('id')} ({DIAS_SEMANA_SHORT.get(dia_a_editar, '')})"

        # Update controls
        dd_lab.update()
        dd_inicio.update()
        dd_fin.update()
        dd_tipo.update()
        btn_save.update()
        btn_cancel.update()
        info_txt.update()

    # --- NEW: Delete Group Function ---
    def delete_group_click(group_rules: List[dict]):
        nonlocal info_txt
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
            if result is True:
                success_count += 1
            else:
                error_count += 1
                last_error = result.get("detail", "Error desconocido") if isinstance(result, dict) else "Error desconocido"

        if error_count == 0:
            info_txt.value = f"Grupo ({success_count} reglas) eliminado con éxito."
            render_reglas()
        else:
            info_txt.value = f"Error al eliminar grupo. {success_count} éxito(s), {error_count} error(es). Último error: {last_error}"
            render_reglas()
        info_txt.update()

    # --- MODIFIED: Delete Single Rule Function ---
    def delete_regla_click(regla_id: int):
        nonlocal info_txt
        result = api.delete_regla_horario(regla_id)
        if result is True:
            info_txt.value = "Regla eliminada."
            render_reglas()
        else:
            info_txt.value = result.get("detail", "Error al eliminar.") if isinstance(result, dict) else "Error desconocido al eliminar."
        info_txt.update()

    # --- NEW: Group Card ---
    def group_card(group_rules: List[dict]) -> ft.Control:
        nonlocal lab_map
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

    # --- MODIFIED: Single Rule Card ---
    def regla_card(regla: dict) -> ft.Control:
        nonlocal lab_map
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

    # --- MODIFIED: Render Function with Grouping ---
    def render_reglas():
        nonlocal reglas_list_panel
        reglas_list_panel.controls.clear()
        all_reglas = load_reglas_for_render()

        if not isinstance(all_reglas, list):
            detail = all_reglas.get("detail", "Error") if isinstance(all_reglas, dict) else "Error desconocido"
            reglas_list_panel.controls.append(ft.Text(f"Error al cargar reglas: {detail}", color=ft.Colors.ERROR))
        elif not all_reglas:
            reglas_list_panel.controls.append(ft.Text("No hay reglas de horario definidas."))
        else:
            # Group rules
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

            # Render groups and single rules
            rendered_items = []
            for group_key, rules_in_group in grouped_rules.items():
                if len(rules_in_group) > 1:
                    rules_in_group.sort(key=lambda r: r.get('dia_semana', -1))
                    rendered_items.append(group_card(rules_in_group))
                else:
                    rendered_items.append(regla_card(rules_in_group[0]))

            # Sort rendered cards
            rendered_items.sort(key=lambda card: (
                not card.content.controls[0].controls[0].value.startswith("General (Todos)"),
                card.content.controls[0].controls[0].value
            ))

            reglas_list_panel.controls.extend(rendered_items)

        if reglas_list_panel.page: reglas_list_panel.update()

    # --- MODIFIED: Clear Form ---
    def clear_form(e=None):
        nonlocal state, dd_lab, dias_checkboxes, dd_inicio, dd_fin, dd_tipo, btn_save, btn_cancel, info_txt

        # Reset state fully
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

        # Update controls
        dd_lab.update()
        dd_inicio.update()
        dd_fin.update()
        dd_tipo.update()
        btn_save.update()
        btn_cancel.update()
        info_txt.update()

    # --- HEAVILY MODIFIED: Save Function ---
    def save_regla(e):
        nonlocal state, dd_lab, dias_checkboxes, dd_inicio, dd_fin, dd_tipo, info_txt

        # --- Get common data from form ---
        lab_id = int(dd_lab.value) if dd_lab.value and dd_lab.value != "general" else None
        inicio_str = dd_inicio.value
        fin_str = dd_fin.value
        tipo_seleccionado = dd_tipo.value.strip() if dd_tipo.value else None
        selected_dias_nums = {num for num, cb in dias_checkboxes.items() if cb.value}

        # --- Basic Validation ---
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

        # --- Determine Mode and Execute ---
        success_count = 0
        error_count = 0
        delete_count = 0
        last_error = ""
        action_summary = ""

        es_habilitado_auto = (tipo_seleccionado == "disponible")

        # Mode 1: Editing a Group
        if state["editing_group_rules"]:
            action_summary = "Actualizando Grupo: "
            original_rules = state["editing_group_rules"]
            original_rule_map = {r.get("dia_semana"): r for r in original_rules}
            original_dias_nums = set(original_rule_map.keys())

            dias_to_update = original_dias_nums.intersection(selected_dias_nums)
            dias_to_delete = original_dias_nums.difference(selected_dias_nums)
            dias_to_create = selected_dias_nums.difference(original_dias_nums)

            # Update existing days
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
                        else: error_count += 1; last_error = result.get("detail", "Update failed") if isinstance(result, dict) else "Update failed"
                    except Exception as ex: error_count += 1; last_error = f"Update Ex: {ex}"

            # Delete removed days
            for dia_num in dias_to_delete:
                 rule_to_delete = original_rule_map.get(dia_num)
                 if rule_to_delete and rule_to_delete.get("id"):
                    try:
                        result = api.delete_regla_horario(rule_to_delete["id"])
                        if result is True: delete_count += 1
                        else: error_count += 1; last_error = result.get("detail", "Delete failed") if isinstance(result, dict) else "Delete failed"
                    except Exception as ex: error_count += 1; last_error = f"Delete Ex: {ex}"

            # Create added days
            for dia_num in dias_to_create:
                payload = {
                    "laboratorio_id": lab_id, "dia_semana": dia_num,
                    "hora_inicio": inicio.isoformat(), "hora_fin": fin.isoformat(),
                    "es_habilitado": es_habilitado_auto, "tipo_intervalo": tipo_seleccionado,
                }
                try:
                    result = api.create_regla_horario(payload)
                    if result and result.get("id"): success_count += 1
                    else: error_count += 1; last_error = result.get("detail", "Create failed") if isinstance(result, dict) else "Create failed"
                except Exception as ex: error_count += 1; last_error = f"Create Ex: {ex}"

        # Mode 2: Editing a Single Rule
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
                else: error_count += 1; last_error = result.get("detail", "Update failed") if isinstance(result, dict) else "Update failed"
            except Exception as ex: error_count += 1; last_error = f"Update Ex: {ex}"

        # Mode 3: Creating New Rule(s)
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
                    else: error_count += 1; last_error = result.get("detail", "Create failed") if isinstance(result, dict) else "Create failed"
                except Exception as ex: error_count += 1; last_error = f"Create Ex: {ex}"

        # --- Final Feedback ---
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
        print(f"Save results: {final_message}")

    # --- 4. Definir botones y formulario ---
    btn_save = Primary("Agregar Regla(s)", on_click=save_regla, col={"sm": 6, "md": 2})
    btn_cancel = Ghost("Cancelar", on_click=clear_form, visible=False, col={"sm": 6, "md": 1})
    buttons_container = ft.Column(
        [btn_save, btn_cancel],
        col={"sm": 12, "md": 3},
        alignment=ft.MainAxisAlignment.END,
        horizontal_alignment=ft.CrossAxisAlignment.END,
        spacing=5
    )
    form_row = ft.ResponsiveRow(
        [
            dd_lab, dias_checkboxes_container,
            dd_inicio, dd_fin, dd_tipo,
            buttons_container,
        ],
        vertical_alignment=ft.CrossAxisAlignment.END,
        spacing=10, run_spacing=15
    )
    form_card = Card(form_row, padding=14)

    # --- 5. Carga inicial ---
    render_reglas()

    # --- 6. Layout Final ---
    return ft.Column(
        [
            ft.Text("Gestión de Reglas de Horario", size=22, weight=ft.FontWeight.BOLD),
            form_card,
            info_txt,
            ft.Divider(height=10),
            reglas_list_panel,
        ],
        expand=True, alignment=ft.MainAxisAlignment.START, spacing=15
    )