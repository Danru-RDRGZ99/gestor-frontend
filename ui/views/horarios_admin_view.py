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

    MOBILE_BREAKPOINT = 768

    def get_is_mobile():
        return page.width is not None and page.width <= MOBILE_BREAKPOINT

    state = {
        "editing_rule_id": None,
        "is_mobile": get_is_mobile(),
        "selected_lab": "general",
        "selected_day": None,
        "initialized": False,
        "grouped_horarios": {}
    }

    def update_mobile_state():
        new_is_mobile = get_is_mobile()
        if new_is_mobile != state["is_mobile"]:
            state["is_mobile"] = new_is_mobile
            print(f"INFO: Cambiando a layout {'MÓVIL' if new_is_mobile else 'WEB'}")
        else:
            state["is_mobile"] = new_is_mobile

    # --- Catálogos y Datos ---
    planteles_data = api.get_planteles()
    labs_data = api.get_laboratorios()
    if not isinstance(planteles_data, list): planteles_data = []
    if not isinstance(labs_data, list): labs_data = []
    labs_cache = labs_data
    lab_options = [("general", "🌐 General (Todos los Laboratorios)")] + \
                  [(str(l["id"]), f"🔬 {l['nombre']}") for l in labs_cache if l.get("id")]
    lab_map = {str(l["id"]): l["nombre"] for l in labs_cache}
    lab_map["general"] = "General (Todos)"

    # --- CONTROLES PRINCIPALES ---
    dd_lab = Dropdown(
        label="Laboratorio", 
        options=lab_options, 
        value="general",
        expand=True,
        filled=True,
        on_change=lambda e: on_filters_change()
    )

    # Selector de día simple
    day_buttons = []
    for dia_num in range(5):  # Solo Lunes a Viernes
        btn = ft.TextButton(
            DIAS_SEMANA_SHORT[dia_num],
            style=ft.ButtonStyle(
                color=ft.Colors.PRIMARY if state["selected_day"] == dia_num else ft.Colors.GREY_600,
                bgcolor=ft.Colors.PRIMARY_CONTAINER if state["selected_day"] == dia_num else None,
            ),
            data=dia_num,
            on_click=lambda e: (state.update({"selected_day": e.control.data}), on_filters_change())
        )
        day_buttons.append(btn)

    days_selector = ft.Row(day_buttons, spacing=5, alignment=ft.MainAxisAlignment.CENTER)

    info_txt = ft.Text("", size=14)
    horarios_list_panel = ft.Column(spacing=8, scroll=ft.ScrollMode.ADAPTIVE, expand=True)

    # --- FORMULARIO PARA AGREGAR/EDITAR ---
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
        label="Tipo de Horario", 
        options=TIPO_OPTIONS, 
        value="disponible",
        expand=True,
        filled=True
    )

    btn_save = Primary("➕ Agregar Horario", on_click=lambda e: save_horario())
    btn_cancel = Ghost("❌ Cancelar", on_click=lambda e: clear_form(), visible=False)

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
        
        if len(dias_list) > 1 and all(dias_list[i] + 1 == dias_list[i+1] for i in range(len(dias_list)-1)):
            return f"{DIAS_SEMANA[dias_list[0]]} a {DIAS_SEMANA[dias_list[-1]]}"
        
        if len(dias_list) <= 3:
            return ", ".join(DIAS_SEMANA[dia] for dia in dias_list)
        else:
            return f"{len(dias_list)} días"

    def load_horarios():
        return api.get_reglas_horario()

    def on_filters_change():
        """Se llama cuando cambian los filtros"""
        if state["initialized"]:
            page.update()
            # Usar un pequeño delay para asegurar que la UI se actualice primero
            import threading
            threading.Timer(0.1, render_horarios).start()

    def render_horarios():
        """Función principal para renderizar horarios"""
        try:
            # Limpiar controles existentes
            horarios_list_panel.controls.clear()
            
            all_horarios = load_horarios()

            if not isinstance(all_horarios, list):
                detail = all_horarios.get("error", "Error") if isinstance(all_horarios, dict) else "Error desconocido"
                horarios_list_panel.controls.append(ft.Text(f"Error al cargar horarios: {detail}", color=ft.Colors.ERROR))
                page.update()
                return

            # Filtrar por laboratorio
            filtered_horarios = []
            for horario in all_horarios:
                lab_id = str(horario.get('laboratorio_id')) if horario.get('laboratorio_id') is not None else "general"
                if lab_id == state["selected_lab"]:
                    filtered_horarios.append(horario)

            # Agrupar horarios
            grouped_horarios = group_horarios(filtered_horarios)
            state["grouped_horarios"] = grouped_horarios

            # Filtrar por día si está seleccionado
            if state["selected_day"] is not None:
                display_horarios = [
                    h for h in grouped_horarios 
                    if (h.get('es_grupo') and state["selected_day"] in h.get('dias_semana', [])) or
                       (not h.get('es_grupo') and h.get('dia_semana') == state["selected_day"])
                ]
            else:
                display_horarios = grouped_horarios

            if not display_horarios:
                if state["selected_day"] is not None:
                    dia_nombre = DIAS_SEMANA.get(state["selected_day"], "Día")
                    lab_nombre = lab_map.get(state["selected_lab"], "Laboratorio")
                    horarios_list_panel.controls.append(
                        ft.Container(
                            content=ft.Column([
                                ft.Icon(ft.Icons.SCHEDULE_OUTLINED, size=48, color=ft.Colors.GREY_400),
                                ft.Text(f"No hay horarios para {dia_nombre}", size=16, color=ft.Colors.GREY_600),
                                ft.Text(f"Laboratorio: {lab_nombre}", size=12, color=ft.Colors.GREY_500),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                            padding=40,
                            alignment=ft.alignment.center
                        )
                    )
                else:
                    lab_nombre = lab_map.get(state["selected_lab"], "Laboratorio")
                    horarios_list_panel.controls.append(
                        ft.Container(
                            content=ft.Column([
                                ft.Icon(ft.Icons.SCHEDULE_OUTLINED, size=48, color=ft.Colors.GREY_400),
                                ft.Text(f"No hay horarios para {lab_nombre}", size=16, color=ft.Colors.GREY_600),
                                ft.Text("Selecciona un día específico", size=12, color=ft.Colors.GREY_500),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                            padding=40,
                            alignment=ft.alignment.center
                        )
                    )
            else:
                # Ordenar por hora de inicio
                display_horarios.sort(key=lambda x: x.get('hora_inicio', ''))
                
                for horario in display_horarios:
                    horarios_list_panel.controls.append(create_horario_card(horario))

            page.update()

        except Exception as e:
            print(f"Error en render_horarios: {e}")
            traceback.print_exc()

    def create_horario_card(horario: Dict) -> ft.Control:
        """Crea una tarjeta para un horario individual o agrupado"""
        lab_id = horario.get('laboratorio_id')
        lab_name = lab_map.get(str(lab_id)) if lab_id is not None else lab_map["general"]
        
        hora_inicio_str = format_time_str(horario.get('hora_inicio'))
        hora_fin_str = format_time_str(horario.get('hora_fin'))
        
        tipo = horario.get('tipo_intervalo', 'disponible')
        es_grupo = horario.get('es_grupo', False)
        
        # Colores según tipo
        if tipo == "disponible":
            color = ft.Colors.GREEN_600
            icon = ft.Icons.CHECK_CIRCLE_OUTLINED
            status_text = "Disponible"
        elif tipo == "descanso":
            color = ft.Colors.ORANGE_600
            icon = ft.Icons.FREE_BREAKFAST_OUTLINED
            status_text = "Descanso"
        else:  # mantenimiento
            color = ft.Colors.RED_600
            icon = ft.Icons.BUILD_CIRCLE_OUTLINED
            status_text = "Mantenimiento"

        # Información de días
        if es_grupo:
            dias_info = format_dias_semana(horario.get('dias_semana', []))
            count_info = f"({horario.get('count', 0)} horarios)"
            dias_display = f"{dias_info} {count_info}"
        else:
            dia_num = horario.get('dia_semana')
            dias_display = DIAS_SEMANA.get(dia_num, 'N/A')

        # Botones de acción - SIMPLIFICADOS
        if es_grupo:
            actions = ft.Row([
                ft.IconButton(
                    icon=ft.Icons.VISIBILITY_OUTLINED,
                    icon_color=ft.Colors.BLUE,
                    tooltip="Ver individuales",
                    on_click=lambda e, h=horario: show_individual_horarios(h)
                ),
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINED,
                    icon_color=ft.Colors.RED,
                    tooltip="Eliminar grupo",
                    on_click=lambda e, h=horario: delete_horario_group_click(h)
                ),
            ], spacing=8)
        else:
            actions = ft.Row([
                ft.IconButton(
                    icon=ft.Icons.EDIT_OUTLINED,
                    icon_color=ft.Colors.BLUE,
                    tooltip="Editar",
                    on_click=lambda e, h=horario: edit_horario_click(h)
                ),
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINED,
                    icon_color=ft.Colors.RED,
                    tooltip="Eliminar",
                    on_click=lambda e, h=horario: delete_horario_click(h.get('id'))
                ),
            ], spacing=8)

        content = ft.Column([
            ft.Row([
                ft.Icon(icon, color=color, size=20),
                ft.Column([
                    ft.Text(f"{hora_inicio_str} - {hora_fin_str}", 
                           size=14, weight=ft.FontWeight.W_600),
                    ft.Text(f"{dias_display}", 
                           size=12, color=ft.Colors.GREY_600),
                    ft.Text(f"{lab_name} • {status_text}", 
                           size=12, color=ft.Colors.GREY_600),
                ], spacing=2, expand=True),
            ], vertical_alignment=ft.CrossAxisAlignment.START),
            ft.Container(height=8),
            actions
        ], spacing=0)

        return Card(content, padding=16)

    def show_individual_horarios(horario_grupo: Dict):
        """Muestra los horarios individuales de un grupo"""
        individual_ids = horario_grupo.get('ids', [])
        all_horarios = load_horarios()
        
        individual_horarios = [
            h for h in all_horarios 
            if h.get('id') in individual_ids
        ]
        
        # Crear diálogo con la lista individual
        individual_list = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=5)
        
        for horario in individual_horarios:
            dia_num = horario.get('dia_semana')
            dia_nombre = DIAS_SEMANA.get(dia_num, 'N/A')
            hora_inicio_str = format_time_str(horario.get('hora_inicio'))
            hora_fin_str = format_time_str(horario.get('hora_fin'))
            
            individual_list.controls.append(
                ft.Card(
                    ft.Container(
                        ft.Row([
                            ft.Column([
                                ft.Text(f"{dia_nombre}", weight=ft.FontWeight.W_600),
                                ft.Text(f"{hora_inicio_str} - {hora_fin_str}", size=12),
                            ], expand=True),
                            ft.Row([
                                ft.IconButton(
                                    icon=ft.Icons.EDIT,
                                    icon_color=ft.Colors.BLUE,
                                    icon_size=20,
                                    tooltip="Editar",
                                    on_click=lambda e, h=horario: (setattr(page.dialog, 'open', False), page.update(), edit_horario_click(h))
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE,
                                    icon_color=ft.Colors.RED,
                                    icon_size=20,
                                    tooltip="Eliminar",
                                    on_click=lambda e, h=horario: (setattr(page.dialog, 'open', False), page.update(), delete_horario_click(h.get('id')))
                                ),
                            ], spacing=5)
                        ]),
                        padding=10
                    ),
                    margin=2
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
                ft.TextButton("Cerrar", on_click=lambda e: (setattr(page.dialog, 'open', False), page.update())),
            ],
        )
        page.dialog.open = True
        page.update()

    def delete_horario_group_click(horario_grupo: Dict):
        """Elimina todos los horarios de un grupo"""
        def confirm_delete(e):
            page.dialog.open = False
            page.update()
            
            individual_ids = horario_grupo.get('ids', [])
            success_count = 0
            
            for horario_id in individual_ids:
                result = api.delete_regla_horario(horario_id)
                if result and result.get("success"):
                    success_count += 1
            
            if success_count == len(individual_ids):
                info_txt.value = f"✅ {success_count} horarios eliminados"
                info_txt.color = ft.Colors.GREEN
            else:
                info_txt.value = f"⚠️ {success_count} de {len(individual_ids)} horarios eliminados"
                info_txt.color = ft.Colors.ORANGE
            
            info_txt.update()
            render_horarios()

        page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar eliminación"),
            content=ft.Text(f"¿Eliminar {len(horario_grupo.get('ids', []))} horarios?"),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: (setattr(page.dialog, 'open', False), page.update())),
                Danger("Eliminar", on_click=confirm_delete),
            ],
        )
        page.dialog.open = True
        page.update()

    def edit_horario_click(horario: dict):
        state["editing_rule_id"] = horario.get("id")
        
        # Rellenar formulario con datos existentes
        dd_lab.value = str(horario.get("laboratorio_id")) if horario.get("laboratorio_id") is not None else "general"
        dd_inicio.value = str(horario.get("hora_inicio"))
        dd_fin.value = str(horario.get("hora_fin"))
        dd_tipo.value = horario.get("tipo_intervalo", "disponible")

        btn_save.text = "💾 Actualizar Horario"
        btn_cancel.visible = True
        info_txt.value = f"Editando horario del {DIAS_SEMANA.get(horario.get('dia_semana'), 'día')}"

        page.update()

    def delete_horario_click(horario_id: int):
        def confirm_delete(e):
            page.dialog.open = False
            page.update()
            
            result = api.delete_regla_horario(horario_id)
            if result and result.get("success"):
                info_txt.value = "✅ Horario eliminado"
                info_txt.color = ft.Colors.GREEN
                render_horarios()
            else:
                info_txt.value = "❌ Error al eliminar"
                info_txt.color = ft.Colors.RED
            
            info_txt.update()

        page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar eliminación"),
            content=ft.Text("¿Estás seguro de que quieres eliminar este horario?"),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: (setattr(page.dialog, 'open', False), page.update())),
                Danger("Eliminar", on_click=confirm_delete),
            ],
        )
        page.dialog.open = True
        page.update()

    def clear_form():
        state["editing_rule_id"] = None
        dd_inicio.value = None
        dd_fin.value = None
        dd_tipo.value = "disponible"
        btn_save.text = "➕ Agregar Horario"
        btn_cancel.visible = False
        info_txt.value = ""
        page.update()

    def save_horario():
        # Validaciones básicas
        if not all([dd_inicio.value, dd_fin.value, dd_tipo.value]):
            info_txt.value = "❌ Completa todos los campos"
            info_txt.color = ft.Colors.RED
            page.update()
            return

        try:
            inicio = datetime.strptime(dd_inicio.value, "%H:%M:%S").time()
            fin = datetime.strptime(dd_fin.value, "%H:%M:%S").time()
        except (ValueError, TypeError):
            info_txt.value = "❌ Formato de hora inválido"
            info_txt.color = ft.Colors.RED
            page.update()
            return

        if inicio >= fin:
            info_txt.value = "❌ La hora inicio debe ser anterior a la hora fin"
            info_txt.color = ft.Colors.RED
            page.update()
            return

        # Preparar datos
        lab_id = int(dd_lab.value) if dd_lab.value and dd_lab.value != "general" else None
        tipo = dd_tipo.value
        es_habilitado = (tipo == "disponible")

        # Si estamos editando, actualizar
        if state["editing_rule_id"]:
            payload = {
                "laboratorio_id": lab_id,
                "hora_inicio": inicio.isoformat(),
                "hora_fin": fin.isoformat(),
                "es_habilitado": es_habilitado,
                "tipo_intervalo": tipo,
                "dia_semana": next((h.get('dia_semana') for h in load_horarios() 
                                  if h.get('id') == state["editing_rule_id"]), 0)
            }
            
            result = api.update_regla_horario(state["editing_rule_id"], payload)
            if result and result.get("id"):
                info_txt.value = "✅ Horario actualizado"
                info_txt.color = ft.Colors.GREEN
                clear_form()
                render_horarios()
            else:
                error_msg = result.get("error", "Error desconocido") if isinstance(result, dict) else "Error"
                info_txt.value = f"❌ Error: {error_msg}"
                info_txt.color = ft.Colors.RED
        else:
            # Crear nuevos horarios
            dias_a_crear = [state["selected_day"]] if state["selected_day"] is not None else list(range(5))
            
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
                info_txt.value = f"✅ {success_count} horario(s) creado(s)"
                info_txt.color = ft.Colors.GREEN
                clear_form()
                render_horarios()
            else:
                info_txt.value = "❌ Error al crear horarios"
                info_txt.color = ft.Colors.RED

        page.update()

    # --- DISEÑO ---
    
    # Header con selección
    header_section = ft.Column([
        ft.Text("📅 Gestión de Horarios", 
               size=20, 
               weight=ft.FontWeight.BOLD,
               text_align=ft.TextAlign.CENTER),
        Card(ft.Column([
            ft.Text("Selecciona Laboratorio y Día:", size=14, weight=ft.FontWeight.W_600),
            dd_lab,
            ft.Container(height=10),
            days_selector,
        ], spacing=8), padding=16),
    ], spacing=12)

    # Formulario para agregar/editar
    form_section = Card(ft.Column([
        ft.Text("Agregar/Editar Horario:", size=16, weight=ft.FontWeight.W_600),
        ft.ResponsiveRow([
            ft.Container(dd_inicio, col={"sm": 12, "md": 4}),
            ft.Container(dd_fin, col={"sm": 12, "md": 4}),
            ft.Container(dd_tipo, col={"sm": 12, "md": 4}),
        ], spacing=10),
        ft.Container(height=10),
        ft.Row([btn_save, btn_cancel], spacing=10),
        info_txt,
    ], spacing=12), padding=16)

    # Layout principal
    def create_layout():
        update_mobile_state()
        
        if state["is_mobile"]:
            return ft.Column(
                controls=[
                    header_section,
                    form_section,
                    ft.Divider(height=20),
                    ft.Text("Horarios:", size=16, weight=ft.FontWeight.W_600),
                    ft.Container(content=horarios_list_panel, expand=True),
                ],
                expand=True,
                scroll=ft.ScrollMode.ADAPTIVE,
            )
        else:
            return ft.Column(
                [
                    header_section,
                    ft.ResponsiveRow([
                        ft.Container(form_section, col={"md": 4}),
                        ft.Container(
                            ft.Column([
                                ft.Text("Horarios Configurados", size=18, weight=ft.FontWeight.W_600),
                                horarios_list_panel,
                            ], spacing=12),
                            col={"md": 8},
                        ),
                    ]),
                ],
                expand=True,
            )

    # Inicialización
    main_content = create_layout()
    state["initialized"] = True
    
    # Cargar datos iniciales después de que la página esté lista
    def on_page_ready():
        render_horarios()
    
    # Usar el evento de resize para inicializar
    def handle_first_resize(e):
        page.on_resize = handle_page_resize
        on_page_ready()
    
    page.on_resize = handle_first_resize
    
    def handle_page_resize(e):
        current_is_mobile = state["is_mobile"]
        new_is_mobile = get_is_mobile()
        if current_is_mobile != new_is_mobile:
            state["is_mobile"] = new_is_mobile
            # Recrear el layout completo
            nonlocal main_content
            main_content = create_layout()
            page.controls.clear()
            page.add(main_content)
            render_horarios()

    return main_content