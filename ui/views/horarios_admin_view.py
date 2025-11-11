import flet as ft
from api_client import ApiClient
from ui.components.cards import Card
from ui.components.inputs import TextField, Dropdown, generate_time_options
from ui.components.buttons import Primary, Danger, Icon, Ghost
from datetime import time, date, datetime, timedelta
import traceback
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict

# --- Constantes ---
DIAS_SEMANA: Dict[int, str] = {
    0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"
}
DIAS_SEMANA_SHORT: Dict[int, str] = {k: v[:3] for k, v in DIAS_SEMANA.items()}

HORA_INICIO_DIA = time(7, 0)
HORA_FIN_DIA = time(21, 0)
INTERVALO_MINUTOS = 30
HORA_OPTIONS = generate_time_options(HORA_INICIO_DIA, HORA_FIN_DIA, INTERVALO_MINUTOS)

TIPO_OPTIONS = [
    ("disponible", "🟢 Disponible"),
    ("descanso", "🟡 Descanso"),
    ("mantenimiento", "🔴 Mantenimiento"),
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

    state = {
        "editing_rule_id": None,
        "editing_rule_dia": None,
        "selected_lab": "general",
        "initialized": False,
        "grouped_horarios": {}
    }

    # --- Catálogos y Datos ---
    labs_data = api.get_laboratorios()
    if not isinstance(labs_data, list): labs_data = []
    labs_cache = labs_data
    lab_options = [("general", "🌐 General (Todos los Laboratorios)")] + \
                  [(str(l["id"]), f"🔬 {l['nombre']}") for l in labs_cache if l.get("id")]
    lab_map = {str(l["id"]): l["nombre"] for l in labs_cache}
    lab_map["general"] = "General (Todos)"

    # --- CONTROLES DEL FORMULARIO ---
    
    # Laboratorio
    dd_lab = Dropdown(
        label="Laboratorio", 
        options=lab_options, 
        value="general",
        on_change=lambda e: (state.update({"selected_lab": dd_lab.value}), safe_render_horarios()),
        col={"sm": 12, "md": 4} # Asignación de columna
    )

    # Checkboxes de Días
    day_checkboxes = []
    for dia_num, dia_nombre in DIAS_SEMANA.items():
        cb = ft.Checkbox(label=dia_nombre, data=dia_num)
        day_checkboxes.append(cb)
    
    days_container = ft.Column(
        controls=[ft.Text("Días:", weight=ft.FontWeight.BOLD)] + day_checkboxes,
        col={"sm": 12, "md": 2} # Asignación de columna
    )

    # Horas y Tipo
    dd_inicio = Dropdown(label="Hora Inicio", options=HORA_OPTIONS, filled=True)
    dd_fin = Dropdown(label="Hora Fin", options=HORA_OPTIONS, filled=True)
    dd_tipo = Dropdown(label="Tipo", options=TIPO_OPTIONS, value="disponible", filled=True)

    time_type_container = ft.Column(
        controls=[
            dd_inicio,
            dd_fin,
            dd_tipo,
        ],
        spacing=10,
        col={"sm": 12, "md": 4} # Asignación de columna
    )

    # Botones
    btn_save = Primary("➕ Agregar Regla(s)", on_click=lambda e: save_horario())
    btn_cancel = Ghost("❌ Cancelar", on_click=lambda e: clear_form(), visible=False)
    
    buttons_container = ft.Column(
        controls=[
            btn_save,
            btn_cancel
        ],
        col={"sm": 12, "md": 2}, # Asignación de columna
        alignment=ft.MainAxisAlignment.START,
    )
    
    info_txt = ft.Text("", size=14)
    horarios_list_panel = ft.Column(spacing=8, scroll=ft.ScrollMode.ADAPTIVE, expand=True)

    # --- FUNCIONES PARA AGRUPAR HORARIOS ---
    def group_horarios(horarios: List[Dict]) -> List[Dict]:
        grouped = defaultdict(list)
        for horario in horarios:
            key = (
                horario.get('hora_inicio'),
                horario.get('hora_fin'),
                horario.get('tipo_intervalo'),
                horario.get('laboratorio_id')
            )
            grouped[key].append(horario)
        
        result = []
        for key, horarios_group in grouped.items():
            if len(horarios_group) == 1:
                result.append(horarios_group[0])
            else:
                first_horario = horarios_group[0]
                grouped_horario = {
                    **first_horario,
                    'dias_semana': sorted(list(set(h.get('dia_semana') for h in horarios_group))),
                    'es_grupo': True,
                    'ids': [h.get('id') for h in horarios_group],
                    'count': len(horarios_group)
                }
                result.append(grouped_horario)
        return result

    def format_dias_semana(dias_list: List[int]) -> str:
        if not dias_list:
            return "Ningún día"
        
        dias_list = sorted(dias_list)
        
        if dias_list == [0, 1, 2, 3, 4]:
            return "Lunes a Viernes"
        if dias_list == [0, 1, 2, 3, 4, 5, 6]:
            return "Toda la semana"
        if dias_list == [5, 6]:
            return "Fin de semana"
        
        if len(dias_list) > 1 and all(dias_list[i] + 1 == dias_list[i+1] for i in range(len(dias_list)-1)):
            return f"{DIAS_SEMANA[dias_list[0]]} a {DIAS_SEMANA[dias_list[-1]]}"
        
        if len(dias_list) <= 3:
            return ", ".join(DIAS_SEMANA[dia] for dia in dias_list)
        else:
            return f"{len(dias_list)} días"

    def load_horarios():
        return api.get_reglas_horario()

    def safe_render_horarios():
        if state["initialized"]:
            render_horarios()

    def render_horarios():
        try:
            horarios_list_panel.controls.clear()
            
            all_horarios = load_horarios()

            if not isinstance(all_horarios, list):
                detail = all_horarios.get("error", "Error") if isinstance(all_horarios, dict) else "Error desconocido"
                horarios_list_panel.controls.append(ft.Text(f"Error al cargar horarios: {detail}", color=ft.Colors.ERROR))
                if horarios_list_panel.page:
                    horarios_list_panel.update()
                return

            # Filtrar por laboratorio seleccionado
            filtered_horarios = []
            for horario in all_horarios:
                lab_id = str(horario.get('laboratorio_id')) if horario.get('laboratorio_id') is not None else "general"
                if lab_id == state["selected_lab"]:
                    filtered_horarios.append(horario)

            # Agrupar horarios
            grouped_horarios = group_horarios(filtered_horarios)
            state["grouped_horarios"] = grouped_horarios

            # Ya no filtramos por día, solo mostramos los del lab
            display_horarios = grouped_horarios

            if not display_horarios:
                lab_nombre = lab_map.get(state["selected_lab"], "Laboratorio")
                horarios_list_panel.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.SCHEDULE_OUTLINED, size=48, color=ft.Colors.GREY_400),
                            ft.Text(f"No hay horarios para {lab_nombre}", size=16, color=ft.Colors.GREY_600),
                            ft.Text("Agrega el primer horario usando el formulario", size=12, color=ft.Colors.GREY_500),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                        padding=40,
                        alignment=ft.alignment.center
                    )
                )
            else:
                display_horarios.sort(key=lambda x: x.get('hora_inicio', ''))
                
                for horario in display_horarios:
                    horarios_list_panel.controls.append(horario_card(horario))

            if horarios_list_panel.page:
                horarios_list_panel.update()

        except Exception as e:
            print(f"Error en render_horarios: {e}")
            traceback.print_exc()

    def horario_card(horario: Dict) -> ft.Control:
        lab_id = horario.get('laboratorio_id')
        lab_name = lab_map.get(str(lab_id)) if lab_id is not None else lab_map["general"]
        
        hora_inicio_str = format_time_str(horario.get('hora_inicio'))
        hora_fin_str = format_time_str(horario.get('hora_fin'))
        
        tipo = horario.get('tipo_intervalo', 'disponible')
        es_grupo = horario.get('es_grupo', False)
        
        # Colores y texto de estado
        status_map = {
            "disponible": ("Disponible", ft.Colors.GREEN_600, ft.Icons.CHECK_CIRCLE_OUTLINED),
            "descanso": ("Descanso", ft.Colors.ORANGE_600, ft.Icons.FREE_BREAKFAST_OUTLINED),
            "mantenimiento": ("Mantenimiento", ft.Colors.RED_600, ft.Icons.BUILD_CIRCLE_OUTLINED),
        }
        status_text, color, icon = status_map.get(tipo, ("Desconocido", ft.Colors.GREY, ft.Icons.HELP_OUTLINE))
        
        badge_color = {
            "disponible": ft.colors.GREEN_200,
            "descanso": ft.colors.ORANGE_200,
            "mantenimiento": ft.colors.RED_200,
        }
        badge_text_color = {
            "disponible": ft.colors.GREEN_900,
            "descanso": ft.colors.ORANGE_900,
            "mantenimiento": ft.colors.RED_900,
        }
        
        badge = ft.Container(
            content=ft.Text(status_text.upper(), size=10, weight=ft.FontWeight.BOLD),
            bgcolor=badge_color.get(tipo, ft.colors.GREY_200),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=10
        )

        if es_grupo:
            dias_info = format_dias_semana(horario.get('dias_semana', []))
            dias_display = f"{dias_info} ({horario.get('count', 0)} reglas)"
        else:
            dia_num = horario.get('dia_semana')
            dias_display = DIAS_SEMANA.get(dia_num, 'N/A')

        # Contenido de la tarjeta
        content = ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(f"{lab_name} - {dias_display}", size=14, weight=ft.FontWeight.BOLD),
                        ft.Text(f"Horario: {hora_inicio_str} - {hora_fin_str}", size=12, color=ft.Colors.GREY_600),
                    ],
                    expand=True,
                    spacing=2
                ),
                badge,
                # Botones
                Icon(ft.Icons.EDIT_OUTLINED, "Editar", 
                     on_click=lambda e, h=horario: edit_horario_click(h),
                     icon_color=ft.Colors.BLUE),
                Icon(ft.Icons.DELETE_OUTLINED, "Eliminar", 
                     on_click=lambda e, h=horario: delete_horario_click(h), # Pasar el 'horario' completo
                     icon_color=ft.Colors.RED),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10
        )
        
        return Card(content, padding=16)


    def show_individual_horarios(horario_grupo: Dict):
        individual_ids = horario_grupo.get('ids', [])
        all_horarios = load_horarios()
        
        individual_horarios = [
            h for h in all_horarios 
            if h.get('id') in individual_ids
        ]
        
        individual_list = ft.Column(scroll=ft.ScrollMode.ADAPTIVE)
        
        for horario in individual_horarios:
            dia_num = horario.get('dia_semana')
            dia_nombre = DIAS_SEMANA.get(dia_num, 'N/A')
            hora_inicio_str = format_time_str(horario.get('hora_inicio'))
            hora_fin_str = format_time_str(horario.get('hora_fin'))
            
            def edit_and_close(h):
                page.dialog.open = False
                page.update()
                edit_horario_click(h)
            
            def delete_and_close(h):
                page.dialog.open = False
                page.update()
                if h:
                    delete_horario_click(h)
            
            individual_list.controls.append(
                ft.ListTile(
                    title=ft.Text(f"{dia_nombre}"),
                    subtitle=ft.Text(f"{hora_inicio_str} - {hora_fin_str}"),
                    trailing=ft.Row([
                        Icon(ft.Icons.EDIT_OUTLINED, "Editar", 
                             on_click=lambda e, h=horario: edit_and_close(h),
                             icon_color=ft.Colors.BLUE),
                        Icon(ft.Icons.DELETE_OUTLINED, "Eliminar", 
                             on_click=lambda e, h=horario: delete_and_close(h),
                             icon_color=ft.Colors.RED),
                    ], spacing=4)
                )
            )

        page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Horarios Individuales"),
            content=ft.Container(
                content=individual_list,
                width=400,
                height=300
            ),
            actions=[
                ft.TextButton("Cerrar", on_click=lambda e: setattr(page.dialog, 'open', False) or page.update()),
            ],
        )
        page.dialog.open = True
        page.update()

    def delete_horario_click(horario: Dict):
        es_grupo = horario.get('es_grupo', False)
        
        if es_grupo:
            confirm_title = "Confirmar eliminación de GRUPO"
            confirm_content = ft.Text(f"¿Estás seguro de que quieres eliminar {len(horario.get('ids', []))} horarios agrupados?")
            handler = lambda e: delete_horario_group_confirm(horario)
        else:
            confirm_title = "Confirmar eliminación"
            confirm_content = ft.Text("¿Estás seguro de que quieres eliminar este horario?")
            handler = lambda e: delete_horario_individual_confirm(horario.get('id'))

        page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(confirm_title),
            content=confirm_content,
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(page.dialog, 'open', False) or page.update()),
                Danger("Eliminar", on_click=handler),
            ],
        )
        page.dialog.open = True
        page.update()

    def delete_horario_group_confirm(horario_grupo: Dict):
        page.dialog.open = False
        page.update()
        
        individual_ids = horario_grupo.get('ids', [])
        success_count = 0
        
        for horario_id in individual_ids:
            result = api.delete_regla_horario(horario_id)
            if result and result.get("success"):
                success_count += 1
            else:
                print(f"Error eliminando ID {horario_id}: {result.get('error', 'Error')}")
        
        if success_count == len(individual_ids):
            info_txt.value = f"✅ {success_count} horarios eliminados correctamente"
            info_txt.color = ft.Colors.GREEN
        else:
            info_txt.value = f"⚠️ {success_count} de {len(individual_ids)} horarios eliminados"
            info_txt.color = ft.Colors.ORANGE
        
        info_txt.update()
        safe_render_horarios()

    def delete_horario_individual_confirm(horario_id: int):
        page.dialog.open = False
        page.update()
        
        if not horario_id:
            info_txt.value = "❌ Error: ID de horario no encontrado"
            info_txt.color = ft.Colors.RED
            info_txt.update()
            return

        result = api.delete_regla_horario(horario_id)
        
        if result and result.get("success"):
            info_txt.value = "✅ Horario eliminado correctamente"
            info_txt.color = ft.Colors.GREEN
            safe_render_horarios()
        else:
            error_msg = result.get("error", "Error desconocido")
            info_txt.value = f"❌ Error al eliminar: {error_msg}"
            info_txt.color = ft.Colors.RED
        
        info_txt.update()

    def edit_horario_click(horario: dict):
        if horario.get('es_grupo', False):
            # Si es un grupo, mostrar los individuales
            show_individual_horarios(horario)
            return

        # Si es individual, rellenar formulario
        state["editing_rule_id"] = horario.get("id")
        state["editing_rule_dia"] = horario.get("dia_semana")
        
        dd_lab.value = str(horario.get("laboratorio_id")) if horario.get("laboratorio_id") is not None else "general"
        dd_inicio.value = str(horario.get("hora_inicio"))
        dd_fin.value = str(horario.get("hora_fin"))
        dd_tipo.value = horario.get("tipo_intervalo", "disponible")

        # Desmarcar todos los checkboxes y marcar solo el de este horario
        for cb in day_checkboxes:
            cb.value = (cb.data == state["editing_rule_dia"])
            cb.disabled = True # Deshabilitar checkboxes en modo edición
            cb.update()
        
        btn_save.text = "💾 Actualizar Horario"
        btn_cancel.visible = True
        info_txt.value = f"Editando horario del {DIAS_SEMANA.get(horario.get('dia_semana'), 'día')}"
        info_txt.color = ft.Colors.BLUE
        info_txt.update()

        update_controls()

    def clear_form():
        state["editing_rule_id"] = None
        state["editing_rule_dia"] = None
        
        # No resetear laboratorio
        dd_inicio.value = None
        dd_fin.value = None
        dd_tipo.value = "disponible"

        # Limpiar y habilitar checkboxes
        for cb in day_checkboxes:
            cb.value = False
            cb.disabled = False
            cb.update()

        btn_save.text = "➕ Agregar Regla(s)"
        btn_cancel.visible = False
        info_txt.value = ""

        update_controls()

    def save_horario():
        # Validaciones básicas
        if not all([dd_inicio.value, dd_fin.value, dd_tipo.value]):
            info_txt.value = "❌ Completa todos los campos obligatorios"
            info_txt.color = ft.Colors.RED
            info_txt.update()
            return

        try:
            inicio = datetime.strptime(dd_inicio.value, "%H:%M:%S").time()
            fin = datetime.strptime(dd_fin.value, "%H:%M:%S").time()
        except (ValueError, TypeError):
            info_txt.value = "❌ Formato de hora inválido"
            info_txt.color = ft.Colors.RED
            info_txt.update()
            return

        if inicio >= fin:
            info_txt.value = "❌ La hora inicio debe ser anterior a la hora fin"
            info_txt.color = ft.Colors.RED
            info_txt.update()
            return

        lab_id = int(dd_lab.value) if dd_lab.value and dd_lab.value != "general" else None
        tipo = dd_tipo.value
        es_habilitado = (tipo == "disponible")

        if state["editing_rule_id"]:
            # --- MODO EDICIÓN ---
            if state["editing_rule_dia"] is None:
                info_txt.value = "❌ Error: No se encontró el día de la semana para editar."
                info_txt.color = ft.Colors.RED
                info_txt.update()
                return

            payload = {
                "laboratorio_id": lab_id,
                "hora_inicio": inicio.isoformat(),
                "hora_fin": fin.isoformat(),
                "es_habilitado": es_habilitado,
                "tipo_intervalo": tipo,
                "dia_semana": state["editing_rule_dia"]
            }
            
            result = api.update_regla_horario(state["editing_rule_id"], payload)
            
            if result and result.get("id"):
                info_txt.value = "✅ Horario actualizado correctamente"
                info_txt.color = ft.Colors.GREEN
                clear_form()
                safe_render_horarios()
            else:
                error_msg = result.get("error", "Error desconocido") if isinstance(result, dict) else "Error"
                info_txt.value = f"❌ Error al actualizar: {error_msg}"
                info_txt.color = ft.Colors.RED
        else:
            # --- MODO CREACIÓN ---
            dias_a_crear = [cb.data for cb in day_checkboxes if cb.value]
            
            if not dias_a_crear:
                info_txt.value = "❌ Debes seleccionar al menos un día de la semana"
                info_txt.color = ft.Colors.RED
                info_txt.update()
                return

            success_count = 0
            for dia_num in dias_a_crear:
                payload = {
                    "laboratorio_id": lab_id,
                    "dia_semana": dia_num,
                    "hora_inicio": inicio.isoformat(),
                    "hora_fin": fin.isoformat(),
                    "es_habilitado": es_habilitado,
                    "tipo_intervalo": tipo,
                }
                
                result = api.create_regla_horario(payload)
                if result and result.get("id"):
                    success_count += 1

            if success_count > 0:
                info_txt.value = f"✅ {success_count} horario(s) creado(s) correctamente"
                info_txt.color = ft.Colors.GREEN
                clear_form()
                safe_render_horarios()
            else:
                info_txt.value = "❌ Error al crear los horarios"
                info_txt.color = ft.Colors.RED

        info_txt.update()

    def update_controls():
        if state["initialized"]:
            try:
                dd_inicio.update()
                dd_fin.update()
                dd_tipo.update()
                btn_save.update()
                btn_cancel.update()
            except Exception as e:
                print(f"Error actualizando controles: {e}")

    # --- DISEÑO DE LA VISTA (LAYOUT) ---
    
    # Header
    header_section = ft.Text("Gestión de Reglas de Horario", size=24, weight=ft.FontWeight.BOLD)

    # Formulario
    form_section = Card(
        ft.Column([
            ft.ResponsiveRow(
                [
                    dd_lab,
                    days_container,
                    time_type_container,
                    buttons_container,
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
                spacing=20
            ),
            info_txt
        ])
    )

    # Lista
    list_section = ft.Column(
        [
            ft.Divider(),
            ft.Text("Horarios Configurados", size=18, weight=ft.FontWeight.BOLD),
            horarios_list_panel
        ],
        expand=True
    )

    # --- INICIO DE LA CORRECCIÓN ---

    # 1. Define tu Columna principal sin padding
    main_column = ft.Column(
        [
            header_section,
            form_section,
            list_section,
        ],
        expand=True,
        scroll=ft.ScrollMode.ADAPTIVE,
        spacing=20
        # 'padding' se elimina de aquí
    )

    # 2. Envuelve la columna en un Container y aplica el padding allí
    main_content = ft.Container(
        content=main_column,
        padding=20, # <--- El padding ahora está en el Container
        expand=True 
    )
    
    # --- FIN DE LA CORRECCIÓN ---
    
    # Inicialización
    state["initialized"] = True
    safe_render_horarios()

    return main_content