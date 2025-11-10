# VERSIÓN CORREGIDA - SELECTOR DE FECHA Y FILTROS FUNCIONALES

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
    Versión móvil optimizada.
    """
    user_session = page.session.get("user_session") or {}
    user_data = user_session

    MOBILE_BREAKPOINT = 768

    def get_is_mobile():
        return page.width is not None and page.width <= MOBILE_BREAKPOINT

    state = {
        "confirm_for": None, 
        "is_mobile": get_is_mobile(),
        "selected_date": date.today()
    }

    def update_mobile_state():
        new_is_mobile = get_is_mobile()
        if new_is_mobile != state["is_mobile"]:
            state["is_mobile"] = new_is_mobile
            state["confirm_for"] = None
            print(f"INFO: Cambiando a layout {'MÓVIL' if new_is_mobile else 'WEB'}")
        else:
            state["is_mobile"] = new_is_mobile

    # CONTROLES DE FILTRO MEJORADOS PARA MÓVIL
    dd_plantel = ft.Dropdown(
        label="Plantel",
        options=[],
        expand=True,
        filled=True,
        text_size=14
    )
    
    dd_lab = ft.Dropdown(
        label="Laboratorio", 
        options=[],
        expand=True,
        filled=True,
        text_size=14
    )

    info = ft.Text("", size=14)
    grid = ft.Column(spacing=12, scroll=ft.ScrollMode.ADAPTIVE, expand=True)

    # BOTTOM SHEET MEJORADO PARA FILTROS
    def close_filters(e):
        bs_filters.open = False
        page.update()

    def apply_filters(e):
        state["confirm_for"] = None
        bs_filters.open = False
        render()
        page.update()

    bs_filters = ft.BottomSheet(
        ft.Container(
            ft.Column(
                [
                    ft.Row([
                        ft.Text("Filtrar Laboratorios", 
                               size=18, 
                               weight=ft.FontWeight.BOLD,
                               expand=True),
                        ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            on_click=close_filters,
                            icon_size=20
                        )
                    ]),
                    ft.Divider(height=1),
                    ft.Container(height=10),
                    dd_plantel,
                    dd_lab,
                    ft.Container(height=10),
                    ft.Row([
                        ft.FilledButton(
                            "Aplicar filtros", 
                            on_click=apply_filters,
                            expand=True,
                            height=45
                        ),
                    ]),
                ],
                tight=True,
                spacing=12,
            ),
            padding=ft.padding.all(20),
        ),
        open=False,
        dismissible=True,
    )
    page.overlay.append(bs_filters)

    def open_filters(e):
        bs_filters.open = True
        page.update()

    # FAB MEJORADO - asegurar que sea visible
    fab_filter = ft.FloatingActionButton(
        icon=ft.Icons.FILTER_LIST,
        text="Filtrar",
        tooltip="Filtrar laboratorios",
        on_click=open_filters,
        visible=False,
        bgcolor=ft.Colors.PRIMARY,
        shape=ft.RoundedRectangleBorder(radius=10),
    )

    # DATE PICKER CORREGIDO
    date_picker = ft.DatePicker(
        first_date=date.today(),
        last_date=date.today() + timedelta(days=60),
    )
    
    def handle_date_change(e):
        if date_picker.value:
            state["selected_date"] = date_picker.value
            state["confirm_for"] = None
            render()
    
    date_picker.on_change = handle_date_change
    
    def show_date_picker(e):
        date_picker.value = state["selected_date"]
        date_picker.pick_date()

    page.overlay.append(date_picker)

    # CARGAR DATOS INICIALES
    planteles_cache = []
    labs_cache = []
    lab_map = {}
    error_loading_data = None

    try:
        planteles_data = api.get_planteles()
        labs_data = api.get_laboratorios()

        if isinstance(planteles_data, list):
            planteles_cache = planteles_data
            dd_plantel.options = [
                ft.dropdown.Option(str(p["id"]), p["nombre"])
                for p in planteles_cache
                if p.get("id")
            ]
        else:
            error_detail = (
                planteles_data.get("error", "Error")
                if isinstance(planteles_data, dict)
                else "Respuesta inesperada"
            )
            error_loading_data = f"Error al cargar planteles: {error_detail}"

        if isinstance(labs_data, list):
            labs_cache = labs_data
            lab_map = {
                str(l.get("id", "")): l.get("nombre", "Nombre Desconocido")
                for l in labs_cache
                if l.get("id")
            }
        else:
            error_detail = (
                labs_data.get("error", "Error")
                if isinstance(labs_data, dict)
                else "Respuesta inesperada"
            )
            if error_loading_data:
                error_loading_data += f"\nError al cargar laboratorios: {error_detail}"
            else:
                error_loading_data = f"Error al cargar laboratorios: {error_detail}"

    except Exception as e:
        error_loading_data = f"Excepción al cargar datos iniciales: {e}"
        print(f"CRITICAL ReservasView: {error_loading_data}")
        traceback.print_exc()

    if error_loading_data:
        return ft.Column(
            [
                ft.Text("Reservas de Laboratorios", size=22, weight=ft.FontWeight.BOLD),
                ft.Text(
                    "Error al cargar datos necesarios:",
                    color=ft.Colors.ERROR,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Text(error_loading_data, color=ft.Colors.ERROR),
            ]
        )

    def is_weekend(d: date) -> bool:
        return d.weekday() >= 5

    def next_weekday(d: date, step: int = 1):
        n = d + timedelta(days=step)
        while n.weekday() >= 5:
            n = n + timedelta(days=1 if step >= 0 else -1)
        return n

    today = date.today()
    window = {"start": today if not is_weekend(today) else next_weekday(today)}

    day_names_short = ["Lun", "Mar", "Mié", "Jue", "Vie"]
    day_names_full = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
    
    head_label = ft.Text("", size=16, weight=ft.FontWeight.W_600)

    # FUNCIONES DE NAVEGACIÓN MEJORADAS PARA MÓVIL
    def goto_next(e):
        if state["is_mobile"]:
            state["selected_date"] = next_weekday(state["selected_date"])
        else:
            days = get_days_in_window(window["start"])
            last_day = days[-1]
            window["start"] = next_weekday(last_day)
        state["confirm_for"] = None
        render()

    def goto_prev(e):
        if state["is_mobile"]:
            state["selected_date"] = next_weekday(state["selected_date"], step=-1)
        else:
            prev_days = five_weekdays_before(window["start"])
            window["start"] = prev_days[0]
        state["confirm_for"] = None
        render()

    def goto_today(e):
        state["selected_date"] = today if not is_weekend(today) else next_weekday(today)
        state["confirm_for"] = None
        render()

    def get_days_in_window(start_date: date):
        if state["is_mobile"]:
            cur = state["selected_date"]
            if is_weekend(cur):
                cur = next_weekday(cur)
            return [cur]
        else:
            cur = start_date
            if is_weekend(cur):
                cur = next_weekday(cur)
            return five_weekdays_from(cur)

    def five_weekdays_from(d: date):
        days = []
        cur = d
        if is_weekend(cur):
            cur = next_weekday(cur)
        while len(days) < 5:
            if not is_weekend(cur):
                days.append(cur)
            cur += timedelta(days=1)
        return days

    def five_weekdays_before(end_exclusive: date):
        days = []
        cur = end_exclusive - timedelta(days=1)
        while len(days) < 5:
            if not is_weekend(cur):
                days.insert(0, cur)
            cur -= timedelta(days=1)
        return days

    def slot_label(s: datetime, f: datetime):
        return f"{s.strftime('%H:%M')}–{f.strftime('%H:%M')}"

    # FUNCIONES DE RESERVA
    def do_create_reservation(lab_id: int, s: datetime, f: datetime):
        if user_data.get("rol") not in ["admin", "docente"]:
            info.value = "Solo administradores y docentes pueden crear reservas."
            info.color = ft.Colors.ERROR
            info.update()
            return

        info.value = "Creando reserva, por favor espera..."
        info.color = ft.Colors.BLUE_500
        grid.disabled = True
        page.update(info, grid)

        payload = {
            "laboratorio_id": lab_id,
            "usuario_id": user_data.get("id"),
            "inicio": s.isoformat(),
            "fin": f.isoformat(),
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
            error_detail = (
                result.get("error", "Error")
                if isinstance(result, dict)
                else "Error"
            )
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
            error_detail = (
                result.get("error", "Error")
                if isinstance(result, dict)
                else "Error"
            )
            info.value = f"Error al cancelar la reserva: {error_detail}"
            info.color = ft.Colors.ERROR
            page.update(info, grid)

    def ask_inline_cancel(rid: int, etiqueta: str):
        state["confirm_for"] = rid
        info.value = f"Confirmar cancelación para {etiqueta}"
        info.color = ft.Colors.AMBER_700
        render()

    # SECCIÓN DE DÍA MEJORADA PARA MÓVIL
    def day_section(d: date, lid: int, slots_calculados: list[dict], day_reserveds: list[dict]):
        is_mobile_view = state["is_mobile"]
        
        # Header mejorado para móvil
        day_header = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.CALENDAR_TODAY, size=16),
                ft.Text(
                    f"{day_names_full[d.weekday()]} {d.strftime('%d/%m/%Y')}",
                    size=16,
                    weight=ft.FontWeight.W_600,
                    expand=True,
                ),
            ]),
            bgcolor=ft.Colors.PRIMARY_CONTAINER,
            padding=12,
            border_radius=ft.border_radius.only(top_left=12, top_right=12),
        )

        tiles = []
        reservas_map = {}
        
        for r in day_reserveds:
            try:
                dt_aware_utc = datetime.fromisoformat(str(r.get("inicio")).replace("Z", "+00:00"))
                dt_naive_local = dt_aware_utc.astimezone(None).replace(tzinfo=None)
                reservas_map[dt_naive_local] = r
            except (ValueError, TypeError) as e:
                print(f"Error parsing date for reservation {r.get('id')}: {e}")

        for slot in slots_calculados:
            try:
                s_dt = datetime.fromisoformat(str(slot.get("inicio"))).replace(tzinfo=None)
                f_dt = datetime.fromisoformat(str(slot.get("fin"))).replace(tzinfo=None)
                k_tipo = slot.get("tipo", "no_habilitado")
            except (ValueError, TypeError) as e:
                print(f"WARN: Skipping slot due to invalid date: {slot} | Error: {e}")
                continue

            label = slot_label(s_dt, f_dt)
            found_res_data = reservas_map.get(s_dt)

            if found_res_data:
                rid = found_res_data.get("id")
                user_info = found_res_data.get("usuario", {})
                nombre = user_info.get("nombre", "N/A")
                current_user_id = user_data.get("id")
                current_user_rol = user_data.get("rol")
                is_owner = str(current_user_id) == str(user_info.get("id"))
                is_admin = current_user_rol == "admin"
                can_manage = is_owner or is_admin

                # Versión móvil compacta
                display_label = f"🟡 {label} - {nombre}" if is_mobile_view else f"Reservado por {nombre}"

                if can_manage and state["confirm_for"] == rid:
                    # Botones de confirmación adaptados a móvil
                    if is_mobile_view:
                        confirm_row = ft.Column([
                            ft.Text("¿Cancelar reserva?", size=14, weight=ft.FontWeight.BOLD),
                            ft.Row([
                                Danger(
                                    "Sí, cancelar",
                                    on_click=lambda _, _rid=rid: do_cancel_reservation(_rid),
                                    expand=True,
                                    height=40,
                                ),
                                Ghost(
                                    "No",
                                    on_click=lambda e: (state.update({"confirm_for": None}), render()),
                                    expand=True,
                                    height=40,
                                ),
                            ])
                        ], spacing=8)
                        tiles.append(confirm_row)
                    else:
                        tiles.append(
                            ft.Row([
                                Danger("Confirmar", on_click=lambda _, _rid=rid: do_cancel_reservation(_rid)),
                                Ghost("Volver", on_click=lambda e: (state.update({"confirm_for": None}), render())),
                            ])
                        )
                else:
                    btn = Tonal(
                        display_label,
                        tooltip="Toca para cancelar" if can_manage else "No puedes cancelar esta reserva",
                        on_click=lambda _, _rid=rid, _lab=label: ask_inline_cancel(_rid, _lab) if can_manage and _rid else None,
                        disabled=not can_manage,
                        expand=is_mobile_view,
                        height=44 if is_mobile_view else 50,
                    )
                    tiles.append(btn)

            elif k_tipo in ["disponible", "libre"]:
                is_allowed_to_create = user_data.get("rol") in ["admin", "docente"]
                display_label = f"🟢 {label}" if is_mobile_view else label
                
                reserve_button = Primary(
                    display_label,
                    on_click=lambda _, ss=s_dt, ff=f_dt, _lid=lid: do_create_reservation(_lid, ss, ff) if is_allowed_to_create else None,
                    disabled=not is_allowed_to_create,
                    expand=is_mobile_view,
                    height=44 if is_mobile_view else 50,
                )
                reserve_button.tooltip = "Solo admin/docente pueden reservar" if not is_allowed_to_create else None
                tiles.append(reserve_button)

            else:
                display_label = f"🔴 {label}" if is_mobile_view else f"{k_tipo.capitalize()} {label}"
                tiles.append(
                    Tonal(
                        display_label,
                        disabled=True,
                        expand=is_mobile_view,
                        height=44 if is_mobile_view else 50,
                    )
                )

        # Contenedor de slots adaptado a móvil
        if is_mobile_view:
            tiles_container = ft.Column(
                tiles, 
                spacing=8, 
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH
            )
        else:
            tiles_container = ft.Row(
                tiles, scroll=ft.ScrollMode.AUTO, wrap=False, spacing=8
            )

        day_content = ft.Column([day_header, tiles_container], spacing=0)

        # CORRECCIÓN: Usar Container en lugar de Card para aplicar margin
        if is_mobile_view:
            card_container = ft.Container(
                content=Card(day_content, padding=0),
                margin=ft.margin.only(bottom=12)
            )
        else:
            card_container = Card(day_content, padding=0)

        return card_container

    def render_grid():
        grid.controls.clear()
        if not dd_lab.value or not dd_lab.value.isdigit():
            info.value = "Selecciona un plantel y un laboratorio válido para ver la disponibilidad."
            info.color = ft.Colors.AMBER_700
            if grid.page:
                page.update(info, grid)
            return

        lid = int(dd_lab.value)
        days_to_display = get_days_in_window(window["start"])
        end_dt_range_api = days_to_display[-1] + timedelta(days=1)

        # Cargar horario y reservas
        horario_result = api.get_horario_laboratorio(
            lid, days_to_display[0], days_to_display[-1]
        )
        if not isinstance(horario_result, dict):
            info.value = "Error al cargar horario: Respuesta inesperada"
            info.color = ft.Colors.ERROR
            if grid.page:
                page.update(info, grid)
            return
        if "error" in horario_result:
            info.value = f"Error al cargar horario: {horario_result.get('error')}"
            info.color = ft.Colors.ERROR
            if grid.page:
                page.update(info, grid)
            return

        api_result = api.get_reservas(lid, days_to_display[0], end_dt_range_api)
        all_reservas = []
        if isinstance(api_result, list):
            all_reservas = api_result
        else:
            info.value = f"Error al cargar reservas: {api_result.get('error', 'Error') if isinstance(api_result, dict) else 'Error'}"
            info.color = ft.Colors.ERROR
            if grid.page:
                page.update(info, grid)
            return

        reservations_by_day = {d: [] for d in days_to_display}
        for r in all_reservas:
            try:
                dt_aware_utc = datetime.fromisoformat(str(r.get("inicio")).replace("Z", "+00:00"))
                dkey = dt_aware_utc.astimezone(None).date()
                if dkey in reservations_by_day:
                    reservations_by_day[dkey].append(r)
            except (ValueError, TypeError) as e:
                print(f"Error parsing date {r.get('inicio')} in render_grid: {e}")

        for d in days_to_display:
            slots_for_day = horario_result.get(d.isoformat(), [])
            reservations_for_day = reservations_by_day.get(d, [])
            grid.controls.append(day_section(d, lid, slots_for_day, reservations_for_day))

        grid.disabled = False
        if grid.page:
            grid.update()

    def render():
        update_mobile_state()

        if state["confirm_for"] is None:
            info.value = ""
            info.color = None
            if info.page:
                info.update()

        days = get_days_in_window(window["start"])
        lab_name = lab_map.get(dd_lab.value, "(Selecciona Lab)")
        
        if state["is_mobile"]:
            current_date = state["selected_date"]
            head_label.value = f"{day_names_short[current_date.weekday()]} {current_date.strftime('%d/%m')} · {lab_name}"
        else:
            head_label.value = f"{days[0].strftime('%d/%m')} — {days[-1].strftime('%d/%m')} · {lab_name}"
        
        if head_label.page:
            head_label.update()

        # Mostrar/ocultar controles según el modo - CORREGIDO
        if state["is_mobile"]:
            filter_group.visible = False
            mobile_date_selector.visible = True
            # CONFIGURACIÓN CORREGIDA DEL FAB
            page.floating_action_button = fab_filter
            page.floating_action_button_location = ft.FloatingActionButtonLocation.CENTER_DOCKED
            fab_filter.visible = True
        else:
            filter_group.visible = True
            mobile_date_selector.visible = False
            page.floating_action_button = None
            fab_filter.visible = False

        if filter_group.page:
            filter_group.update()
        if mobile_date_selector.page:
            mobile_date_selector.update()

        page.update()

        grid.disabled = True
        grid.controls.clear()
        if grid.page:
            grid.update()
        render_grid()

    # HANDLERS PARA FILTROS
    def on_change_plantel(e: ft.ControlEvent):
        pid_str = e.control.value
        pid = int(pid_str) if pid_str and pid_str.isdigit() else None
        filtered_labs = [l for l in labs_cache if l.get("plantel_id") == pid] if pid is not None else []
        dd_lab.options = [
            ft.dropdown.Option(str(l["id"]), l["nombre"])
            for l in filtered_labs
            if l.get("id")
        ]
        dd_lab.value = str(filtered_labs[0]["id"]) if filtered_labs else None

        state["confirm_for"] = None

        if e.control.page:
            dd_lab.update()
            render()

    def on_change_lab(e: ft.ControlEvent):
        state["confirm_for"] = None
        if e.control.page:
            render()
            if state["is_mobile"]:
                close_filters(None)

    dd_plantel.on_change = on_change_plantel
    dd_lab.on_change = on_change_lab

    # INICIALIZACIÓN
    if planteles_cache:
        first_plantel_id_str = str(planteles_cache[0].get("id", "")) if planteles_cache else ""
        if first_plantel_id_str:
            dd_plantel.value = first_plantel_id_str
            on_change_plantel(SimpleControlEvent(control=dd_plantel))
        else:
            info.value = "El primer plantel no tiene un ID válido."
            info.color = ft.Colors.ERROR
            head_label.value = "Error de Configuración"
    else:
        info.value = "No hay planteles configurados."
        info.color = ft.Colors.ERROR
        head_label.value = "Error de Configuración"

    # NAVEGACIÓN MEJORADA PARA MÓVIL
    nav_group = ft.Row(
        [
            Icon(ft.Icons.CHEVRON_LEFT, "Día anterior", on_click=goto_prev),
            head_label,
            Icon(ft.Icons.CHEVRON_RIGHT, "Siguiente día", on_click=goto_next),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # SELECTOR DE FECHA MÓVIL - MEJORADO
    mobile_date_selector = ft.Card(
        ft.Container(
            ft.Row([
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_LEFT,
                    on_click=goto_prev,
                    icon_size=20,
                    tooltip="Día anterior"
                ),
                ft.TextButton(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CALENDAR_TODAY, size=18),
                        ft.Text("Seleccionar fecha", size=14, weight=ft.FontWeight.W_500),
                    ], tight=True),
                    on_click=show_date_picker,
                    style=ft.ButtonStyle(
                        color=ft.Colors.PRIMARY,
                        padding=ft.padding.symmetric(horizontal=16, vertical=8)
                    )
                ),
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_RIGHT,
                    on_click=goto_next,
                    icon_size=20,
                    tooltip="Siguiente día"
                ),
                ft.IconButton(
                    icon=ft.Icons.TODAY,
                    tooltip="Ir a hoy",
                    on_click=goto_today,
                    icon_size=20
                ),
            ], 
            alignment=ft.MainAxisAlignment.SPACE_AROUND,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
            ),
            padding=12,
        ),
        visible=False,
        margin=ft.margin.only(bottom=8)
    )

    # GRUPOS DE CONTROLES
    dd_plantel.expand = 1
    dd_lab.expand = 1
    filter_group = ft.Row([dd_plantel, dd_lab], spacing=10, visible=False)

    header_controls_container = ft.Column(
        [nav_group, mobile_date_selector, filter_group], 
        spacing=8
    )

    # LEYENDA ADAPTADA A MÓVIL
    legend_items = [
        ("🟢 Disponible", "Horarios disponibles para reservar"),
        ("🟡 Reservado", "Horarios ya reservados"),
        ("🔴 No disponible", "Horarios no disponibles")
    ]

    legend = ft.Column([
        ft.Text("Leyenda:", size=14, weight=ft.FontWeight.W_500),
        ft.Column([
            ft.Row([
                ft.Text(emoji, size=16),
                ft.Text(label, size=12, expand=True),
            ], spacing=8)
            for emoji, label in legend_items
        ], spacing=4)
    ], spacing=8) if state["is_mobile"] else ft.Row([
        ft.Chip(label=ft.Text("Disponible"), leading=ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE)),
        ft.Chip(label=ft.Text("Reservado"), leading=ft.Icon(ft.Icons.BLOCK)),
        ft.Chip(label=ft.Text("Descanso"), leading=ft.Icon(ft.Icons.SCHEDULE)),
    ], spacing=8, scroll=ft.ScrollMode.ADAPTIVE)

    def on_page_resize(e):
        current_is_mobile = state["is_mobile"]
        new_is_mobile = get_is_mobile()
        if current_is_mobile != new_is_mobile:
            render()

    page.on_resize = on_page_resize

    # INTERFAZ DE USUARIO FINAL
    ui = ft.Column(
        controls=[
            ft.Text("Reservas de Laboratorios", 
                   size=20, 
                   weight=ft.FontWeight.BOLD,
                   text_align=ft.TextAlign.CENTER),
            Card(header_controls_container, padding=12),
            ft.Container(
                content=legend,
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                visible=True
            ),
            info,
            ft.Divider(height=1, color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK)),
            ft.Container(
                content=grid, 
                expand=True, 
                padding=ft.padding.symmetric(horizontal=8, vertical=8)
            ),
        ],
        expand=True,
        scroll=ft.ScrollMode.ADAPTIVE,
        spacing=12,
    )

    # CONFIGURACIÓN INICIAL DEL FAB
    page.floating_action_button = fab_filter
    page.floating_action_button_location = ft.FloatingActionButtonLocation.CENTER_DOCKED

    page.add(ui)
    render()
    return ui