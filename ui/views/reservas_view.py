import flet as ft
from datetime import datetime, date, time, timedelta
from api_client import ApiClient
from ui.components.buttons import Primary, Tonal, Icon, Danger, Ghost
from ui.components.cards import Card
from dataclasses import dataclass
import traceback

# Lista de días en español
DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# Clase simple para simular la estructura del evento
@dataclass
class SimpleControlEvent:
    control: ft.Control

def ReservasView(page: ft.Page, api: ApiClient):
    user_session = page.session.get("user_session") or {}
    user_data = user_session
    
    def detect_mobile() -> bool:
        width = getattr(page, "window_width", None)
        return (width is not None and width < 700) or getattr(page.platform, "name", "").lower() in ("android", "ios")

    state = {
        "confirm_for": None,
        "is_mobile": detect_mobile()
    }

    # --- Controles de Filtros ---
    dd_plantel = ft.Dropdown(label="Plantel", options=[])
    dd_lab = ft.Dropdown(label="Laboratorio", options=[])

    # --- Estado y UI ---
    info = ft.Text("")
    # El grid es una Columna scrollable que contendrá los SLOTS
    grid = ft.Column(spacing=12, scroll=ft.ScrollMode.ADAPTIVE)

    # --- Catálogos cacheados (inicializados vacíos) ---
    planteles_cache = []
    labs_cache = []
    lab_map: dict[str, str] = {}
    
    # --- Lógica del Calendario (Un solo día) ---
    def is_weekend(d: date) -> bool: return d.weekday() >= 5
    def next_weekday(d: date, step: int = 1):
        n = d + timedelta(days=step)
        while n.weekday() >= 5: n = n + timedelta(days=1 if step >= 0 else -1)
        return n

    today = date.today()
    window = {"selected_date": today if not is_weekend(today) else next_weekday(today)}
    head_label = ft.Text("Cargando...", size=18, weight=ft.FontWeight.W_600)

    def goto_next(e=None):
        window["selected_date"] = next_weekday(window["selected_date"], step=1)
        state["confirm_for"] = None
        render()

    def goto_prev(e=None):
        window["selected_date"] = next_weekday(window["selected_date"], step=-1)
        state["confirm_for"] = None
        render()

    def slot_label(s: datetime, f: datetime): return f"{s.strftime('%H:%M')}–{f.strftime('%H:%M')}"
    # --- FIN Lógica Base ---

    # --- Acciones (Ahora asíncronas) ---
    def do_create_reservation(lab_id: int, s: datetime, f: datetime):
        if user_data.get("rol") not in ["admin", "docente"]:
            info.value = "Solo administradores y docentes pueden crear reservas."
            info.color = ft.Colors.ERROR
            info.update(); return

        info.value = "Creando reserva, por favor espera..."
        info.color = ft.Colors.BLUE_500
        grid.disabled = True
        page.update(info, grid)

        payload = {
            "laboratorio_id": lab_id,
            "usuario_id": user_data.get("id"), 
            "inicio": s.isoformat(), 
            "fin": f.isoformat()
        }
        # Corremos la creación en un hilo para no bloquear
        # --- ¡CORRECCIÓN! Usando page.run_thread ---
        page.run_thread(target=run_create_reservation, args=(payload,))

    def run_create_reservation(payload: dict):
        # Esta función se ejecuta en un hilo de fondo
        result = api.create_reserva(payload)
        
        # Volvemos al hilo principal para actualizar la UI
        grid.disabled = False
        info.color = None

        if result and "error" not in result:
            info.value = "Reserva creada con éxito."
            info.color = ft.Colors.GREEN_500
            state["confirm_for"] = None
            render() # Vuelve a cargar el calendario
        else:
            error_detail = result.get("error", "Error desconocido") if isinstance(result, dict) else "Error"
            info.value = f"Error al crear la reserva: {error_detail}"
            info.color = ft.Colors.ERROR
            page.update(info, grid) # Actualiza la UI desde el hilo principal

    def do_cancel_reservation(rid: int):
        info.value = "Cancelando reserva, por favor espera..."
        info.color = ft.Colors.AMBER_700
        grid.disabled = True
        page.update(info, grid)
        
        # Corremos la cancelación en un hilo
        # --- ¡CORRECCIÓN! Usando page.run_thread ---
        page.run_thread(target=run_cancel_reservation, args=(rid,))

    def run_cancel_reservation(rid: int):
        # Esta función se ejecuta en un hilo de fondo
        result = api.delete_reserva(rid)

        # Volvemos al hilo principal para actualizar la UI
        grid.disabled = False
        info.color = None
        state["confirm_for"] = None

        if result and "error" not in result:
            info.value = "Reserva cancelada exitosamente."
            info.color = ft.Colors.GREEN_500 
            render() # Vuelve a cargar el calendario
        else:
            error_detail = result.get("error", "Error desconocido") if isinstance(result, dict) else "Error desconocido"
            info.value = f"Error al cancelar la reserva: {error_detail}"
            info.color = ft.Colors.ERROR
            page.update(info, grid) # Actualiza la UI

    def ask_inline_cancel(rid: int, etiqueta: str):
        state["confirm_for"] = rid
        info.value = f"Confirmar cancelación para {etiqueta}"
        info.color = ft.Colors.AMBER_700
        render()

    # --- MODIFICACIÓN: Renderizado del Grid (asíncrono) ---
    
    # Esta función ahora hace TODO (obtener datos Y construir la UI)
    # Se ejecutará en un hilo de fondo.
    def render_grid_in_thread(d: date):
        
        new_controls = [] # Construimos los controles aquí
        try:
            # 1. Obtener datos
            if not dd_lab.value or not dd_lab.value.isdigit():
                raise Exception("Selecciona un laboratorio.")
            
            lid = int(dd_lab.value)
            end_dt = d + timedelta(days=1)
            
            horario_result = api.get_horario_laboratorio(lid, d, d)
            api_result = api.get_reservas(lid, d, end_dt)
            
            if isinstance(horario_result, dict) and "error" in horario_result:
                raise Exception(f"Error al cargar horario: {horario_result.get('error', 'Error')}")
            if not isinstance(horario_result, dict):
                 raise Exception(f"Respuesta inesperada del API de horario")
            if not isinstance(api_result, list):
                raise Exception(f"Error al cargar reservas: {api_result.get('error', 'Error')}")

            # 2. Mapear reservas por hora de inicio
            reservas_map = {}
            for r in all_reservas:
                start_str = r.get('inicio')
                if start_str:
                    dt_aware_utc = datetime.fromisoformat(str(start_str).replace('Z', '+00:00'))
                    dt_aware_local = dt_aware_utc.astimezone(None)
                    reservas_map[dt_aware_local.replace(tzinfo=None)] = r

            # 3. Obtener los slots de hoy
            slots_for_day = horario_result.get(d.isoformat(), [])
            
            if not slots_for_day:
                new_controls.append(ft.Row([ft.Text("No hay horarios habilitados para este día.")], alignment=ft.MainAxisAlignment.CENTER))

            # 4. Renderizar slots
            for slot in slots_for_day:
                s_dt = datetime.fromisoformat(str(slot.get('inicio'))).replace(tzinfo=None)
                f_dt = datetime.fromisoformat(str(slot.get('fin'))).replace(tzinfo=None)
                k_tipo = slot.get('tipo', 'no_habilitado')
                label = slot_label(s_dt, f_dt)
                found_res_data = reservas_map.get(s_dt) 

                if found_res_data:
                    rid = found_res_data.get('id')
                    user_info = found_res_data.get('usuario', {}) 
                    reserving_user_id = user_info.get('id')
                    nombre = user_info.get('nombre', 'N/A')
                    current_user_id = user_data.get("id")
                    current_user_rol = user_data.get("rol")
                    is_owner = (str(current_user_id) == str(reserving_user_id))
                    is_admin = (current_user_rol == "admin")
                    can_manage = is_owner or is_admin
                    label = f"Reservado por {nombre}"

                    if can_manage and state["confirm_for"] == rid:
                        new_controls.append(Card(ft.Row([
                            Danger("Confirmar", on_click=lambda _, _rid=rid: do_cancel_reservation(_rid) if _rid else None, expand=True),
                            Ghost("Volver", on_click=lambda e: (state.update({"confirm_for": None}), render())),
                        ])))
                    else:
                        new_controls.append(Card(Tonal(
                            label,
                            tooltip="Haz clic para cancelar" if can_manage else "No puedes cancelar esta reserva",
                            on_click=lambda _, _rid=rid, _lab=label: ask_inline_cancel(_rid, _lab) if can_manage and _rid else None,
                            disabled=not can_manage, 
                            height=50
                        )))
                elif k_tipo in ["disponible", "libre"]:
                    is_allowed_to_create = user_data.get("rol") in ["admin", "docente"]
                    reserve_button = Primary(label,
                                             on_click=lambda _, ss=s_dt, ff=f_dt, _lid=lid: do_create_reservation(_lid, ss, ff) if is_allowed_to_create else None,
                                             disabled=not is_allowed_to_create,
                                             height=50)
                    reserve_button.tooltip = "Solo admin/docente pueden reservar" if not is_allowed_to_create else None
                    new_controls.append(Card(reserve_button))
                else:
                    new_controls.append(Card(Tonal(f"{k_tipo.capitalize()} {label}", disabled=True, height=50)))

        except Exception as e:
            print(f"Error en render_grid_in_thread: {e}")
            traceback.print_exc()
            new_controls = [ft.Text(f"Error al cargar: {e}", color=ft.Colors.ERROR)]
        
        # 5. Actualizar la UI de golpe
        grid.controls = new_controls
        if grid.page: grid.update()


    def render():
        # Esta función AHORA es SÚPER RÁPIDA.
        # Solo actualiza el texto del header...
        grid.disabled = False
        if state["confirm_for"] is None:
            info.value = ""
            info.color = None
        
        selected_date = window["selected_date"]
        lab_name = lab_map.get(dd_lab.value, "(Selecciona Lab)")
        
        dia_es = DIAS_SEMANA[selected_date.weekday()]
        head_label.value = f"{dia_es} {selected_date.strftime('%d/%m')} · {lab_name}"
        
        if head_label.page: head_label.update()
        if info.page: info.update()
        
        # 1. Limpiamos el grid y mostramos "Cargando..."
        grid.controls.clear()
        grid.controls.append(
            ft.Row([ft.ProgressRing(), ft.Text("Cargando horario...")], 
                   alignment=ft.MainAxisAlignment.CENTER, height=200)
        )
        if grid.page: grid.update()
        
        # 2. ...y LUEGO manda a llamar la carga de datos en un hilo separado.
        page.run_thread(target=render_grid_in_thread, args=(selected_date,))


    def on_change_plantel(e: ft.ControlEvent):
        pid_str = e.control.value
        pid = int(pid_str) if pid_str and pid_str.isdigit() else None
        filtered_labs = [l for l in labs_cache if l.get("plantel_id") == pid] if pid is not None else []
        dd_lab.options = [ft.dropdown.Option(str(l["id"]), l["nombre"]) for l in filtered_labs if l.get("id")]
        dd_lab.value = str(filtered_labs[0]["id"]) if filtered_labs else None
        state["confirm_for"] = None
        if dd_lab.page: dd_lab.update()
        render() # <-- Esto ahora es asíncrono

    dd_plantel.on_change = on_change_plantel
    dd_lab.on_change = lambda e: (state.update({"confirm_for": None}), render())

    def close_filter_sheet(e):
        bs_filtros.open = False
        if bs_filtros.page: bs_filtros.update()

    bs_filtros = ft.BottomSheet(
        ft.Container(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("Filtros", size=18, weight=ft.FontWeight.BOLD),
                            ft.IconButton(icon=ft.Icons.CLOSE, on_click=close_filter_sheet),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    dd_plantel,
                    dd_lab,
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
        if bs_filtros.page: bs_filtros.update()

    def apply_filter_styles():
        is_mobile_now = state["is_mobile"]
        dd_plantel.width = None if is_mobile_now else 260
        dd_plantel.expand = is_mobile_now
        dd_lab.width = None if is_mobile_now else 320
        dd_lab.expand = is_mobile_now
        
        if dd_plantel.page: dd_plantel.update()
        if dd_lab.page: dd_lab.update()
        if grid.page: grid.update()

    def _on_resize(e):
        new_mobile = detect_mobile()
        if new_mobile != state["is_mobile"]:
            state["is_mobile"] = new_mobile
            apply_filter_styles()
            render() 
            if page: page.update()

    page.on_resize = _on_resize

    # --- Layout Final ---
    def build_header_controls():
        common_controls = [
            Icon(ft.Icons.CHEVRON_LEFT, "Día anterior", on_click=goto_prev),
            head_label,
            Icon(ft.Icons.CHEVRON_RIGHT, "Siguiente día", on_click=goto_next),
            ft.Container(expand=True),
        ]
        
        if not state["is_mobile"]:
            common_controls.extend([dd_plantel, dd_lab])

        return ft.Row(
            common_controls,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN, 
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            wrap=True,
            spacing=10
        )
    
    legend = ft.Row([
        ft.Chip(label=ft.Text("Disponible"), leading=ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE)),
        ft.Chip(label=ft.Text("Reservado"), leading=ft.Icon(ft.Icons.BLOCK)), 
        ft.Chip(label=ft.Text("Descanso"), leading=ft.Icon(ft.Icons.SCHEDULE))
    ], spacing=8, wrap=True) 

    def mobile_layout():
        main_column = ft.Column(
            [
                ft.Text("Reservas de Laboratorios", size=22, weight=ft.FontWeight.BOLD),
                Card(build_header_controls(), padding=14),
                legend,
                info,
                ft.Divider(height=1, color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK)),
                # Este Container se expande para llenar el espacio
                ft.Container(content=grid, expand=True, padding=ft.padding.only(top=10))
            ],
            expand=True,
            scroll=None, 
            spacing=15
        )
        
        fab = ft.FloatingActionButton(
            icon=ft.Icons.FILTER_LIST,
            tooltip="Filtros",
            on_click=open_filter_sheet,
            right=10,
            bottom=10,
        )
        
        return ft.Stack([main_column, fab], expand=True)

    def desktop_layout():
        return ft.Column([
            ft.Text("Reservas de Laboratorios", size=22, weight=ft.FontWeight.BOLD),
            Card(build_header_controls(), padding=14),
            legend,
            info,
            ft.Divider(height=1, color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK)),
            ft.Container(content=grid, expand=True, padding=ft.padding.only(top=10))
        ],
        expand=True,
        scroll=None,
        spacing=15
        )

    # --- MODIFICACIÓN ASÍNCRONA DE CARGA INICIAL ---
    # Esta función ahora hace TODO: obtiene datos Y actualiza la UI al final
    def load_initial_data_in_thread(e=None):
        nonlocal planteles_cache, labs_cache, lab_map
        
        try:
            planteles_data_async = api.get_planteles()
            labs_data_async = api.get_laboratorios()
            
            error_msg = ""
            
            if isinstance(planteles_data_async, list):
                planteles_cache = planteles_data_async
                dd_plantel.options = [ft.dropdown.Option(str(p["id"]), p["nombre"]) for p in planteles_cache if p.get("id")]
            else:
                error_detail = planteles_data_async.get("error", "Error") if isinstance(planteles_data_async, dict) else "Respuesta inesperada"
                error_msg += f"Error al cargar planteles: {error_detail}\n"

            if isinstance(labs_data_async, list):
                labs_cache = labs_data_async
                lab_map = {str(l.get("id", "")): l.get("nombre", "Nombre Desconocido") for l in labs_cache if l.get("id")}
            else:
                error_detail = labs_data_async.get("error", "Error") if isinstance(labs_data_async, dict) else "Respuesta inesperada"
                error_msg += f"Error al cargar laboratorios: {error_detail}"

            if error_msg:
                raise Exception(error_msg)

            if planteles_cache:
                first_plantel_id_str = str(planteles_cache[0].get("id","")) if planteles_cache else ""
                if first_plantel_id_str:
                    dd_plantel.value = first_plantel_id_str
                    # Simulamos el evento para cargar los labs y renderizar
                    on_change_plantel(SimpleControlEvent(control=dd_plantel)) 
                else:
                    info.value = "El primer plantel no tiene un ID válido."
                    info.color = ft.Colors.ERROR
            else:
                info.value = "No hay planteles configurados."
                info.color = ft.Colors.ERROR
            
            # Actualizamos la UI desde el hilo
            if info.page: info.update()
            if dd_plantel.page: dd_plantel.update()

        except Exception as e:
            print(f"CRITICAL ReservasView (load_initial_data_in_thread): {e}"); traceback.print_exc()
            info.value = f"Error crítico al cargar catálogos: {e}"
            info.color = ft.Colors.ERROR
            if info.page: info.update()

    # Aplicamos estilos y cargamos datos
    apply_filter_styles()
    # --- ¡CORRECCIÓN! Usando page.run_thread ---
    page.run_thread(target=load_initial_data_in_thread)

    if state["is_mobile"]:
        return mobile_layout()
    else:
        return desktop_layout()