# Archivo: ui/views/reservas_view.py
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
    """
    Vista para la gestión de reservas de laboratorios.
    Utiliza el endpoint /laboratorios/{lab_id}/horario para obtener los slots.
    """
    user_session = page.session.get("user_session") or {}
    user_data = user_session.get("user", {})

    # --- Controles de Filtros ---
    dd_plantel = ft.Dropdown(label="Plantel", width=260, options=[])
    dd_lab = ft.Dropdown(label="Laboratorio", width=320, options=[])

    # --- Estado y UI ---
    info = ft.Text("")
    grid = ft.Column(spacing=12, scroll=ft.ScrollMode.ADAPTIVE, expand=True)
    state = {"confirm_for": None}

    # --- Catálogos cacheados ---
    planteles_cache = []
    labs_cache = []
    lab_map: dict[str, str] = {}
    error_loading_data = None

    try:
        planteles_data = api.get_planteles()
        labs_data = api.get_laboratorios()

        if isinstance(planteles_data, list):
            planteles_cache = planteles_data
            dd_plantel.options = [ft.dropdown.Option(str(p["id"]), p["nombre"]) for p in planteles_cache if p.get("id")]
        else:
            error_detail = planteles_data.get("detail", "Error") if isinstance(planteles_data, dict) else "Respuesta inesperada"
            error_loading_data = f"Error al cargar planteles: {error_detail}"
            print(f"ERROR ReservasView (Planteles): {error_loading_data}")

        if isinstance(labs_data, list):
            labs_cache = labs_data
            lab_map = {str(l.get("id", "")): l.get("nombre", "Nombre Desconocido") for l in labs_cache if l.get("id")}
        else:
            error_detail = labs_data.get("detail", "Error") if isinstance(labs_data, dict) else "Respuesta inesperada"
            if error_loading_data: error_loading_data += f"\nError al cargar laboratorios: {error_detail}"
            else: error_loading_data = f"Error al cargar laboratorios: {error_detail}"
            print(f"ERROR ReservasView (Labs): {error_loading_data}")

    except Exception as e:
        error_loading_data = f"Excepción al cargar datos iniciales: {e}"
        print(f"CRITICAL ReservasView: {error_loading_data}"); traceback.print_exc()

    if error_loading_data:
        return ft.Column([
            ft.Text("Reservas de Laboratorios", size=22, weight=ft.FontWeight.BOLD),
            ft.Text("Error al cargar datos necesarios:", color=ft.Colors.ERROR, weight=ft.FontWeight.BOLD),
            ft.Text(error_loading_data, color=ft.Colors.ERROR)
        ])

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

        # Al crear, pasamos el datetime "naive" (local)
        # La API debe interpretarlo correctamente o convertirlo a UTC si es necesario.
        result = api.create_reserva(lab_id, user_data["id"], s, f)

        grid.disabled = False
        info.color = None

        if result and result.get("id"):
            info.value = "Reserva creada con éxito."
            state["confirm_for"] = None
            render()
        else:
            error_detail = result.get("detail") if isinstance(result, dict) else "Error desconocido"
            info.value = f"Error al crear la reserva: {error_detail}"
            info.color = ft.Colors.ERROR
            page.update(info, grid)

    def do_cancel_reservation(rid: int):
        info.value = "Cancelando reserva, por favor espera..."
        info.color = ft.Colors.AMBER_700
        grid.disabled = True
        page.update(info, grid)

        result = api.cancel_reserva(rid)

        grid.disabled = False
        info.color = None
        state["confirm_for"] = None

        if isinstance(result, dict) and result.get('id'):
            info.value = "Reserva cancelada."
            render()
        else:
            error_detail = result.get("detail") if isinstance(result, dict) else str(result)
            if error_detail is None: error_detail = "Error desconocido"
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
                    # --- CORRECCIÓN ZONA HORARIA (Reservas) ---
                    # 1. Parsear la fecha UTC (con 'Z') a un objeto 'aware'
                    dt_aware_utc = datetime.fromisoformat(str(start_str).replace('Z', '+00:00'))
                    # 2. Convertir de UTC a la zona horaria local del sistema
                    dt_aware_local = dt_aware_utc.astimezone(None)
                    # 3. Hacerla 'naive' (sin tzinfo) para usarla como llave
                    dt_naive_local = dt_aware_local.replace(tzinfo=None)
                    
                    reservas_map[dt_naive_local] = r
                    
            except (ValueError, TypeError) as e:
                print(f"Error parsing date for reservation {r.get('id')}: {e}")

        for slot in slots_calculados:
            try:
                # --- CORRECCIÓN ZONA HORARIA (Horario) ---
                s_str = slot.get('inicio')
                f_str = slot.get('fin')
                
                if not s_str or not f_str:
                    print(f"WARN: Skipping slot due to missing date: {slot}")
                    continue
                
                # Asumimos que el /horario devuelve timestamps "naive" (locales)
                # Por lo tanto, NO reemplazamos 'Z'
                s_dt = datetime.fromisoformat(str(s_str)).replace(tzinfo=None)
                f_dt = datetime.fromisoformat(str(f_str)).replace(tzinfo=None)
                
                k_tipo = slot.get('tipo', 'no_habilitado')
                
            except (ValueError, TypeError) as e:
                print(f"WARN: Skipping slot due to invalid date: {slot} | Error: {e}") 
                continue

            label = slot_label(s_dt, f_dt)
            # Ahora s_dt (local naive) debería coincidir con las llaves (local naive) de reservas_map
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
                
                label = f"Reservado por {nombre}" # Etiqueta correcta

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

        day_column = ft.Column([title, ft.Row(tiles, scroll=ft.ScrollMode.AUTO, wrap=False)], spacing=10)
        card_padding = ft.padding.only(top=14, left=14, right=14, bottom=19)
        return ft.Container(content=Card(day_column, padding=card_padding))


    def render_grid():
        grid.controls.clear()
        if not dd_lab.value or not dd_lab.value.isdigit():
            info.value = "Selecciona un plantel y un laboratorio válido para ver la disponibilidad."
            info.color = ft.Colors.AMBER_700
            if grid.page: grid.update()
            return

        lid = int(dd_lab.value)
        days_to_display = five_weekdays_from(window["start"])
        end_dt_range_api = days_to_display[-1] + timedelta(days=1)

        # 1. Obtener Horario
        horario_result = api.get_horario_laboratorio(lid, days_to_display[0], days_to_display[-1])
        if not isinstance(horario_result, dict):
            error_detail = horario_result.get("detail") if isinstance(horario_result, dict) else "Error desconocido"
            info.value = f"Error al cargar horario: {error_detail}"
            info.color = ft.Colors.ERROR
            print(f"ERROR render_grid (horario): {info.value}")
            if grid.page and info.page: info.update()
            return

        # 2. Obtener Reservas
        api_result = api.get_reservas(lid, days_to_display[0], end_dt_range_api)
        all_reservas = []
        if isinstance(api_result, list):
            all_reservas = api_result
        else:
            error_detail = api_result.get("detail") if isinstance(api_result, dict) else "Error desconocido"
            info.value = f"Error al cargar reservas: {error_detail}"
            info.color = ft.Colors.ERROR
            print(f"ERROR render_grid (reservas): {info.value}")
            if grid.page and info.page: info.update()
            return

        # 3. Mapear reservas por día
        reservations_by_day = {d: [] for d in days_to_display}
        for r in all_reservas:
            try:
                start_str = r.get('inicio')
                if start_str:
                    # Convertir la fecha UTC a local y luego a 'date' para la agrupación
                    dt_aware_utc = datetime.fromisoformat(str(start_str).replace('Z', '+00:00'))
                    dt_aware_local = dt_aware_utc.astimezone(None)
                    dkey = dt_aware_local.date() # Usar la fecha local
                    
                    if dkey in reservations_by_day:
                        reservations_by_day[dkey].append(r)
            except (ValueError, TypeError) as e:
                print(f"Error parsing date {r.get('inicio')} in render_grid: {e} for reserva {r.get('id')}")

        # 4. Renderizar
        for d in days_to_display:
            slots_for_day = horario_result.get(d.isoformat(), [])
            reservations_for_day = reservations_by_day.get(d, [])
            grid.controls.append(day_section(
                d, lid, slots_for_day, reservations_for_day
            ))

        if grid.page: grid.update()

    def render():
        grid.disabled = False
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

    # --- Inicialización ---
    if planteles_cache:
        first_plantel_id_str = str(planteles_cache[0].get("id","")) if planteles_cache else ""
        if first_plantel_id_str:
             dd_plantel.value = first_plantel_id_str
             on_change_plantel(SimpleControlEvent(control=dd_plantel)) # Llama para cargar labs y renderizar
        else:
             info.value = "El primer plantel no tiene un ID válido."
             info.color = ft.Colors.ERROR
             days = five_weekdays_from(window["start"])
             head_label.value = f"{days[0].strftime('%d/%m')} — {days[-1].strftime('%d/%m')} · (Sin Laboratorio)"
             if info.page: info.update()
             if head_label.page: head_label.update()

    else:
        info.value = "No hay planteles configurados."
        info.color = ft.Colors.ERROR
        days = five_weekdays_from(window["start"])
        head_label.value = f"{days[0].strftime('%d/%m')} — {days[-1].strftime('%d/%m')} · (Sin Laboratorio)"
        if info.page: info.update()
        if head_label.page: head_label.update()


    # --- Layout Final ---
    header_controls = ft.Row(
        [
            Icon(ft.Icons.CHEVRON_LEFT, "Semana anterior", on_click=lambda e: goto_prev()),
            head_label,
            Icon(ft.Icons.CHEVRON_RIGHT, "Siguiente semana", on_click=lambda e: goto_next()),
            ft.Container(expand=True),
            dd_plantel,
            dd_lab
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER
    )
    
    # ========================================================
    # --- INICIO CORRECCIÓN ft.Chip ---
    legend = ft.Row([
        ft.Chip(label=ft.Text("Disponible"), leading=ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE)),
        ft.Chip(label=ft.Text("Reservado"), leading=ft.Icon(ft.Icons.BLOCK)), # <-- CORREGIDO
        ft.Chip(label=ft.Text("Descanso"), leading=ft.Icon(ft.Icons.SCHEDULE))
    ], spacing=8)
    # --- FIN CORRECCIÓN ft.Chip ---
    # ========================================================

    return ft.Column([
        ft.Text("Reservas de Laboratorios", size=22, weight=ft.FontWeight.BOLD),
        Card(header_controls, padding=14),
        legend,
        info,
        ft.Divider(height=1, color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK)),
        ft.Container(content=grid, expand=True, padding=ft.padding.only(top=10))
    ],
    expand=True,
    scroll=None,
    spacing=15
    )