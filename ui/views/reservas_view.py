import flet as ft
from datetime import datetime, date, time, timedelta
from api_client import ApiClient
from ui.components.buttons import Primary, Tonal, Icon, Danger, Ghost
from ui.components.cards import Card
from dataclasses import dataclass
import traceback

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
    
    # --- ¡AQUÍ ESTÁ LA CORRECCIÓN! ---
    # El grid es scrollable, PERO NO expandible.
    # El Container que lo rodea será el que se expanda.
    grid = ft.Column(spacing=12, scroll=ft.ScrollMode.ADAPTIVE)
    # --- FIN DE LA CORRECCIÓN ---

    # --- Catálogos cacheados (inicializados vacíos) ---
    planteles_cache = []
    labs_cache = []
    lab_map: dict[str, str] = {}
    
    # --- Lógica del Calendario BASE ---
    def is_weekend(d: date) -> bool: return d.weekday() >= 5
    def next_weekday(d: date, step: int = 1):
        n = d + timedelta(days=step)
        while n.weekday() >= 5: n = n + timedelta(days=1 if step >= 0 else -1)
        return n

    today = date.today()
    window = {"start": today if not is_weekend(today) else next_weekday(today)}
    day_names_short = ["Lun", "Mar", "Mié", "Jue", "Vie"]
    head_label = ft.Text("", size=18, weight=ft.FontWeight.W_600)

    def five_weekdays_from(d: date):
        days = []; cur = d
        if is_weekend(cur): cur = next_weekday(cur)
        while len(days) < 5:
            if not is_weekend(cur): days.append(cur)
            cur += timedelta(days=1)
        return days

    def five_weekdays_before(end_exclusive: date):
        days = []; cur = end_exclusive - timedelta(days=1)
        while len(days) < 5:
            if not is_weekend(cur): days.insert(0, cur)
            cur -= timedelta(days=1)
        return days

    def goto_next():
        days = five_weekdays_from(window["start"])
        window["start"] = next_weekday(days[-1])
        state["confirm_for"] = None
        render()

    def goto_prev():
        prev_days = five_weekdays_before(window["start"])
        window["start"] = prev_days[0]
        state["confirm_for"] = None
        render()

    def slot_label(s: datetime, f: datetime): return f"{s.strftime('%H:%M')}–{f.strftime('%H:%M')}"
    # --- FIN Lógica Base ---

    # --- Acciones ---
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
        result = api.create_reserva(payload)

        grid.disabled = False
        info.color = None

        if result and "error" not in result:
            info.value = "Reserva creada con éxito."
            info.color = ft.Colors.GREEN_500
            state["confirm_for"] = None
            render() 
        else:
            error_detail = result.get("error", "Error desconocido") if isinstance(result, dict) else "Error"
            info.value = f"Error al crear la reserva: {error_detail}"
            info.color = ft.Colors.ERROR
            page.update(info, grid)

    def do_cancel_reservation(rid: int):
        info.value = "Cancelando reserva, por favor espera..."
        info.color = ft.Colors.AMBER_700
        grid.disabled = True
        page.update(info, grid)

        result = api.delete_reserva(rid)

        grid.disabled = False
        info.color = None
        state["confirm_for"] = None

        if result and "error" not in result:
            info.value = "Reserva cancelada exitosamente."
            info.color = ft.Colors.GREEN_500 
            render() 
        else:
            error_detail = result.get("error", "Error desconocido") if isinstance(result, dict) else "Error desconocido"
            info.value = f"Error al cancelar la reserva: {error_detail}"
            info.color = ft.Colors.ERROR
            page.update(info, grid)

    def ask_inline_cancel(rid: int, etiqueta: str):
        state["confirm_for"] = rid
        info.value = f"Confirmar cancelación para {etiqueta}"
        info.color = ft.Colors.AMBER_700
        render()

    # --- Renderizado del Calendario ---
    def day_section(d: date, lid: int, slots_calculados: list[dict], day_reserveds: list[dict]):
        title = ft.Text(f"{day_names_short[d.weekday()]} {d.strftime('%d/%m')}", size=16, weight=ft.FontWeight.W_600)
        tiles = []

        reservas_map = {}
        for r in day_reserveds:
            try:
                start_str = r.get('inicio')
                if start_str:
                    dt_aware_utc = datetime.fromisoformat(str(start_str).replace('Z', '+00:00'))
                    dt_aware_local = dt_aware_utc.astimezone(None)
                    dt_naive_local = dt_aware_local.replace(tzinfo=None)
                    reservas_map[dt_naive_local] = r
            except (ValueError, TypeError) as e:
                print(f"Error parsing date for reservation {r.get('id')}: {e}")

        for slot in slots_calculados:
            try:
                s_str = slot.get('inicio')
                f_str = slot.get('fin')
                if not s_str or not f_str:
                    print(f"WARN: Skipping slot due to missing date: {slot}")
                    continue
                
                s_dt = datetime.fromisoformat(str(s_str)).replace(tzinfo=None)
                f_dt = datetime.fromisoformat(str(f_str)).replace(tzinfo=None)
                k_tipo = slot.get('tipo', 'no_habilitado')
                
            except (ValueError, TypeError) as e:
                print(f"WARN: Skipping slot due to invalid date: {slot} | Error: {e}") 
                continue

            label = slot_label(s_dt, f_dt)
            found_res_data = reservas_map.get(s_dt) 

            # --- CASO 1: Slot Reservado ---
            if found_res_data:
                rid = found_res_data.get('id')
                user_info = found_res_data.get('usuario', {}) 
                reserving_user_id = user_info.get('id')
                nombre = user_info.get('nombre', 'N/A')

                current_user_id = user_data.get("id")
                current_user_rol = user_data.get("rol")

                is_owner = False
                if current_user_id is not None and reserving_user_id is not None:
                    is_owner = (str(current_user_id) == str(reserving_user_id))
                
                is_admin = (current_user_rol == "admin")
                can_manage = is_owner or is_admin
                
                label = f"Reservado por {nombre}"

                if can_manage and state["confirm_for"] == rid:
                    tiles.append(ft.Row([
                        Danger("Confirmar", on_click=lambda _, _rid=rid: do_cancel_reservation(_rid) if _rid else None, width=120, height=44),
                        Ghost("Volver", on_click=lambda e: (state.update({"confirm_for": None}), render()), width=72, height=44),
                    ]))
                else:
                    tiles.append(Tonal(
                        label,
                        tooltip="Haz clic para cancelar" if can_manage else "No puedes cancelar esta reserva",
                        on_click=lambda _, _rid=rid, _lab=label: ask_inline_cancel(_rid, _lab) if can_manage and _rid else None,
                        disabled=not can_manage, 
                        width=220, height=50
                    ))

            # --- CASO 2: Slot Disponible ---
            elif k_tipo in ["disponible", "libre"]:
                is_allowed_to_create = user_data.get("rol") in ["admin", "docente"]
                reserve_button = Primary(label,
                                         on_click=lambda _, ss=s_dt, ff=f_dt, _lid=lid: do_create_reservation(_lid, ss, ff) if is_allowed_to_create else None,
                                         disabled=not is_allowed_to_create,
                                         width=220, height=50)
                reserve_button.tooltip = "Solo admin/docente pueden reservar" if not is_allowed_to_create else None
                tiles.append(reserve_button)

            # --- CASO 3: Slot No Habilitado ---
            else:
                tiles.append(Tonal(f"{k_tipo.capitalize()} {label}", disabled=True, width=220, height=50));

        slot_container = ft.Column(tiles, spacing=10) if state["is_mobile"] else ft.Row(tiles, scroll=ft.ScrollMode.AUTO, wrap=False)
        day_column = ft.Column([title, slot_container], spacing=10)
        
        card_padding = ft.padding.only(top=14, left=14, right=14, bottom=19)
        return ft.Container(content=Card(day_column, padding=card_padding))


    def render_grid():
        grid.controls.clear()
        if not dd_lab.value or not dd_lab.value.isdigit():
            grid.controls.append(
                ft.Row([ft.Text("Selecciona un plantel y laboratorio para ver la disponibilidad.")], 
                       alignment=ft.MainAxisAlignment.CENTER)
            )
            if grid.page: grid.update()
            return

        grid.controls.append(
            ft.Row([ft.ProgressRing(), ft.Text("Cargando horario...")], 
                   alignment=ft.MainAxisAlignment.CENTER, height=200)
        )
        if grid.page: grid.update()

        lid = int(dd_lab.value)
        days_to_display = five_weekdays_from(window["start"])
        end_dt_range_api = days_to_display[-1] + timedelta(days=1)

        horario_result = api.get_horario_laboratorio(lid, days_to_display[0], days_to_display[-1])
        if isinstance(horario_result, dict) and "error" in horario_result:
            error_detail = horario_result.get("error", "Error desconocido")
            info.value = f"Error al cargar horario: {error_detail}"
            info.color = ft.Colors.ERROR
            print(f"ERROR render_grid (horario): {info.value}")
            if grid.page and info.page: info.update()
            return
        
        if not isinstance(horario_result, dict):
            info.value = f"Error al cargar horario: Respuesta inesperada del API ({type(horario_result)})"
            info.color = ft.Colors.ERROR
            print(f"ERROR render_grid (horario): {info.value}")
            if grid.page and info.page: info.update()
            return

        api_result = api.get_reservas(lid, days_to_display[0], end_dt_range_api)
        all_reservas = []
        if isinstance(api_result, list):
            all_reservas = api_result
        else:
            error_detail = api_result.get("error", "Error desconocido") if isinstance(api_result, dict) else "Error"
            info.value = f"Error al cargar reservas: {error_detail}"
            info.color = ft.Colors.ERROR
            print(f"ERROR render_grid (reservas): {info.value}")
            if grid.page and info.page: info.update()
            return

        reservations_by_day = {d: [] for d in days_to_display}
        for r in all_reservas:
            try:
                start_str = r.get('inicio')
                if start_str:
                    dt_aware_utc = datetime.fromisoformat(str(start_str).replace('Z', '+00:00'))
                    dt_aware_local = dt_aware_utc.astimezone(None)
                    dkey = dt_aware_local.date()
                    if dkey in reservations_by_day:
                        reservations_by_day[dkey].append(r)
            except (ValueError, TypeError) as e:
                print(f"Error parsing date {r.get('inicio')} in render_grid: {e} for reserva {r.get('id')}")

        grid.controls.clear()
        
        grid_controls = []
        for d in days_to_display:
            slots_for_day = horario_result.get(d.isoformat(), [])
            reservations_for_day = reservations_by_day.get(d, [])
            grid_controls.append(day_section(
                d, lid, slots_for_day, reservations_for_day
            ))
        
        if state["is_mobile"]:
            grid.controls = grid_controls
        else:
            grid.controls = [
                ft.Row(
                    controls=grid_controls,
                    scroll=ft.ScrollMode.ADAPTIVE,
                    expand=True,
                    vertical_alignment=ft.CrossAxisAlignment.START
                )
            ]

        if grid.page: grid.update()

    def render():
        grid.disabled = False
        if state["confirm_for"] is None:
            info.value = ""
            info.color = None
        
        days = five_weekdays_from(window["start"])
        lab_name = lab_map.get(dd_lab.value, "(Selecciona Lab)")
        head_label.value = f"{days[0].strftime('%d/%m')} — {days[-1].strftime('%d/%m')} · {lab_name}"
        
        if head_label.page: head_label.update()
        if info.page: info.update()
        render_grid()

    def on_change_plantel(e: ft.ControlEvent):
        pid_str = e.control.value
        pid = int(pid_str) if pid_str and pid_str.isdigit() else None
        filtered_labs = [l for l in labs_cache if l.get("plantel_id") == pid] if pid is not None else []
        dd_lab.options = [ft.dropdown.Option(str(l["id"]), l["nombre"]) for l in filtered_labs if l.get("id")]
        dd_lab.value = str(filtered_labs[0]["id"]) if filtered_labs else None
        state["confirm_for"] = None
        if dd_lab.page: dd_lab.update()
        render()

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
        
        grid.scroll = ft.ScrollMode.ADAPTIVE 
        
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
            Icon(ft.Icons.CHEVRON_LEFT, "Semana anterior", on_click=lambda e: goto_prev()),
            head_label,
            Icon(ft.Icons.CHEVRON_RIGHT, "Siguiente semana", on_click=lambda e: goto_next()),
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
        
        # El Stack permite superponer el FAB sobre el contenido
        return ft.Stack([main_column, fab], expand=True)

    def desktop_layout():
        return ft.Column([
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

    def load_initial_data(e=None):
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
                print(f"ERROR ReservasView (Planteles): {error_msg}")

            if isinstance(labs_data_async, list):
                labs_cache = labs_data_async
                lab_map = {str(l.get("id", "")): l.get("nombre", "Nombre Desconocido") for l in labs_cache if l.get("id")}
            else:
                error_detail = labs_data_async.get("error", "Error") if isinstance(labs_data_async, dict) else "Respuesta inesperada"
                error_msg += f"Error al cargar laboratorios: {error_detail}"
                print(f"ERROR ReservasView (Labs): {error_msg}")

            if error_msg:
                raise Exception(error_msg)

            if planteles_cache:
                first_plantel_id_str = str(planteles_cache[0].get("id","")) if planteles_cache else ""
                if first_plantel_id_str:
                    dd_plantel.value = first_plantel_id_str
                    if dd_plantel.page: dd_plantel.update()
                    on_change_plantel(SimpleControlEvent(control=dd_plantel)) 
                else:
                    info.value = "El primer plantel no tiene un ID válido."
                    info.color = ft.Colors.ERROR
                    if info.page: info.update()
            else:
                info.value = "No hay planteles configurados."
                info.color = ft.Colors.ERROR
                if info.page: info.update()
                
            if dd_plantel.page:
                dd_plantel.update()

        except Exception as e:
            print(f"CRITICAL ReservasView (async): {e}"); traceback.print_exc()
            info.value = f"Error crítico al cargar datos: {e}"
            info.color = ft.Colors.ERROR
            if info.page: info.update()

    # Aplicamos estilos y cargamos datos
    apply_filter_styles()
    page.run_thread(load_initial_data)

    if state["is_mobile"]:
        return mobile_layout()
    else:
        return desktop_layout()