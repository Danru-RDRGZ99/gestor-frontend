# VERSIÓN SIMPLIFICADA Y CORREGIDA - SIN DUPLICACIONES

import flet as ft
from datetime import datetime, date, time, timedelta
from api_client import ApiClient
from ui.components.buttons import Primary, Tonal, Icon, Danger, Ghost
from ui.components.cards import Card
from dataclasses import dataclass
import traceback

@dataclass
class SimpleControlEvent:
    control: ft.Control

def ReservasView(page: ft.Page, api: ApiClient):
    """
    Vista simplificada para reservas - versión móvil corregida
    """
    user_session = page.session.get("user_session") or {}
    user_data = user_session

    MOBILE_BREAKPOINT = 768
    state = {
        "confirm_for": None, 
        "is_mobile": page.width <= MOBILE_BREAKPOINT if page.width else False,
        "selected_date": date.today()
    }

    # CONTROLES PRINCIPALES
    dd_plantel = ft.Dropdown(label="Plantel", options=[], expand=True, filled=True)
    dd_lab = ft.Dropdown(label="Laboratorio", options=[], expand=True, filled=True)
    info = ft.Text("", size=14)
    grid = ft.Column(spacing=12, scroll=ft.ScrollMode.ADAPTIVE, expand=True)

    # BOTTOM SHEET PARA FILTROS
    bs_filters = ft.BottomSheet(
        ft.Container(
            ft.Column([
                ft.Row([
                    ft.Text("Filtrar", size=18, weight=ft.FontWeight.BOLD, expand=True),
                    ft.IconButton(ft.Icons.CLOSE, on_click=lambda e: setattr(bs_filters, 'open', False) or page.update())
                ]),
                ft.Divider(),
                dd_plantel,
                dd_lab,
                ft.FilledButton("Aplicar", on_click=lambda e: (setattr(bs_filters, 'open', False), render(), page.update())),
            ], spacing=15),
            padding=20,
        ),
        open=False,
    )
    page.overlay.append(bs_filters)

    # DATE PICKER
    date_picker = ft.DatePicker(
        first_date=date.today(),
        last_date=date.today() + timedelta(days=60),
    )
    date_picker.on_change = lambda e: (state.update({"selected_date": date_picker.value, "confirm_for": None}), render()) if date_picker.value else None
    page.overlay.append(date_picker)

    # CARGAR DATOS INICIALES
    planteles_cache = []
    labs_cache = []
    lab_map = {}

    try:
        planteles_data = api.get_planteles()
        labs_data = api.get_laboratorios()

        if isinstance(planteles_data, list):
            planteles_cache = planteles_data
            dd_plantel.options = [ft.dropdown.Option(str(p["id"]), p["nombre"]) for p in planteles_cache if p.get("id")]
        
        if isinstance(labs_data, list):
            labs_cache = labs_data
            lab_map = {str(l["id"]): l["nombre"] for l in labs_cache if l.get("id")}
            
    except Exception as e:
        return ft.Column([
            ft.Text("Error al cargar datos:", color=ft.Colors.ERROR),
            ft.Text(str(e), color=ft.Colors.ERROR)
        ])

    # FUNCIONES AUXILIARES
    def is_weekend(d): return d.weekday() >= 5
    
    def next_weekday(d, step=1):
        n = d + timedelta(days=step)
        while n.weekday() >= 5: n += timedelta(days=1 if step >= 0 else -1)
        return n

    day_names = ["Lun", "Mar", "Mié", "Jue", "Vie"]
    today = date.today()
    
    # FUNCIONES DE NAVEGACIÓN
    def goto_prev(e):
        state["selected_date"] = next_weekday(state["selected_date"], -1)
        state["confirm_for"] = None
        render()

    def goto_next(e):
        state["selected_date"] = next_weekday(state["selected_date"], 1)
        state["confirm_for"] = None
        render()

    def goto_today(e):
        state["selected_date"] = today if not is_weekend(today) else next_weekday(today)
        state["confirm_for"] = None
        render()

    def show_date_picker(e):
        date_picker.value = state["selected_date"]
        date_picker.pick_date()

    def open_filters(e):
        bs_filters.open = True
        page.update()

    # FUNCIONES DE RESERVA
    def do_create_reservation(lab_id, start_dt, end_dt):
        if user_data.get("rol") not in ["admin", "docente"]:
            info.value = "Solo administradores y docentes pueden crear reservas."
            info.color = ft.Colors.ERROR
            info.update()
            return

        info.value = "Creando reserva..."
        info.color = ft.Colors.BLUE
        grid.disabled = True
        page.update()

        payload = {
            "laboratorio_id": lab_id,
            "usuario_id": user_data.get("id"),
            "inicio": start_dt.isoformat(),
            "fin": end_dt.isoformat(),
        }
        result = api.create_reserva(payload)

        grid.disabled = False
        if result and "error" not in result:
            info.value = "Reserva creada con éxito."
            info.color = ft.Colors.GREEN
            state["confirm_for"] = None
            render()
        else:
            error_detail = result.get("error", "Error") if isinstance(result, dict) else "Error"
            info.value = f"Error: {error_detail}"
            info.color = ft.Colors.ERROR
            page.update()

    def do_cancel_reservation(rid):
        info.value = "Cancelando reserva..."
        info.color = ft.Colors.AMBER
        grid.disabled = True
        page.update()

        result = api.delete_reserva(rid)
        grid.disabled = False
        state["confirm_for"] = None

        if result and "error" not in result:
            info.value = "Reserva cancelada."
            info.color = ft.Colors.GREEN
            render()
        else:
            error_detail = result.get("error", "Error") if isinstance(result, dict) else "Error"
            info.value = f"Error: {error_detail}"
            info.color = ft.Colors.ERROR
            page.update()

    def ask_cancel(rid, label):
        state["confirm_for"] = rid
        info.value = f"Cancelar: {label}"
        info.color = ft.Colors.AMBER
        render()

    # RENDERIZADO DE DÍA
    def render_day_section(d, lab_id, slots, reservations):
        # Header del día
        header = ft.Container(
            ft.Row([
                ft.Icon(ft.Icons.CALENDAR_TODAY, size=18),
                ft.Text(f"{day_names[d.weekday()]} {d.strftime('%d/%m/%Y')}", size=16, weight=ft.FontWeight.BOLD, expand=True),
            ]),
            bgcolor=ft.Colors.PRIMARY_CONTAINER,
            padding=12,
            border_radius=8,
        )

        # Procesar slots
        reservas_map = {}
        for r in reservations:
            try:
                start_dt = datetime.fromisoformat(str(r["inicio"]).replace("Z", "+00:00")).replace(tzinfo=None)
                reservas_map[start_dt] = r
            except: pass

        tiles = []
        for slot in slots:
            try:
                start_dt = datetime.fromisoformat(str(slot["inicio"])).replace(tzinfo=None)
                end_dt = datetime.fromisoformat(str(slot["fin"])).replace(tzinfo=None)
                slot_type = slot.get("tipo", "no_habilitado")
                label = f"{start_dt.strftime('%H:%M')}–{end_dt.strftime('%H:%M')}"
            except: continue

            reservation = reservas_map.get(start_dt)
            
            if reservation:
                # Slot reservado
                user_name = reservation.get("usuario", {}).get("nombre", "N/A")
                current_user_id = user_data.get("id")
                reservation_user_id = reservation.get("usuario", {}).get("id")
                can_manage = str(current_user_id) == str(reservation_user_id) or user_data.get("rol") == "admin"
                
                if state["confirm_for"] == reservation["id"]:
                    # Confirmación de cancelación
                    tiles.append(ft.Column([
                        ft.Text("¿Cancelar reserva?", size=14, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            Danger("Sí, cancelar", on_click=lambda e, rid=reservation["id"]: do_cancel_reservation(rid), expand=True),
                            Ghost("No", on_click=lambda e: (state.update({"confirm_for": None}), render()), expand=True),
                        ])
                    ]))
                else:
                    tiles.append(Tonal(
                        f"🟡 {label} - {user_name}",
                        on_click=lambda e, rid=reservation["id"], lbl=label: ask_cancel(rid, lbl) if can_manage else None,
                        disabled=not can_manage,
                        expand=True,
                        height=44,
                    ))
                    
            elif slot_type in ["disponible", "libre"]:
                # Slot disponible
                can_reserve = user_data.get("rol") in ["admin", "docente"]
                tiles.append(Primary(
                    f"🟢 {label}",
                    on_click=lambda e, s=start_dt, f=end_dt, lid=lab_id: do_create_reservation(lid, s, f) if can_reserve else None,
                    disabled=not can_reserve,
                    expand=True,
                    height=44,
                ))
                
            else:
                # Slot no disponible
                tiles.append(Tonal(f"🔴 {label}", disabled=True, expand=True, height=44))

        content = ft.Column([header, ft.Column(tiles, spacing=6)], spacing=0)
        return ft.Container(content=Card(content, padding=0), margin=ft.margin.only(bottom=12))

    def render_grid():
        grid.controls.clear()
        
        if not dd_lab.value or not dd_lab.value.isdigit():
            info.value = "Selecciona un laboratorio válido."
            info.color = ft.Colors.AMBER
            page.update()
            return

        lab_id = int(dd_lab.value)
        current_date = state["selected_date"]
        if is_weekend(current_date):
            current_date = next_weekday(current_date)

        # Cargar datos
        horario = api.get_horario_laboratorio(lab_id, current_date, current_date)
        reservas = api.get_reservas(lab_id, current_date, current_date + timedelta(days=1))
        
        if not isinstance(horario, dict) or "error" in horario:
            info.value = "Error al cargar horario."
            info.color = ft.Colors.ERROR
            page.update()
            return

        slots_del_dia = horario.get(current_date.isoformat(), [])
        reservas_del_dia = [r for r in reservas if isinstance(reservas, list)] if isinstance(reservas, list) else []

        grid.controls.append(render_day_section(current_date, lab_id, slots_del_dia, reservas_del_dia))
        grid.disabled = False
        grid.update()

    def render():
        # Actualizar estado móvil
        state["is_mobile"] = page.width <= MOBILE_BREAKPOINT if page.width else False
        
        # Actualizar header
        lab_name = lab_map.get(dd_lab.value, "Selecciona lab")
        current_date = state["selected_date"]
        head_label.value = f"{day_names[current_date.weekday()]} {current_date.strftime('%d/%m')} · {lab_name}"
        head_label.update()

        # Mostrar controles apropiados
        if state["is_mobile"]:
            filter_group.visible = False
            mobile_nav.visible = True
            # USAR APP BAR EN LUGAR DE FAB
            if page.appbar is None:
                page.appbar = ft.AppBar(
                    title=ft.Text("Reservas"),
                    actions=[ft.IconButton(ft.Icons.FILTER_LIST, on_click=open_filters)],
                )
            else:
                page.appbar.actions = [ft.IconButton(ft.Icons.FILTER_LIST, on_click=open_filters)]
        else:
            filter_group.visible = True
            mobile_nav.visible = False
            page.appbar = None

        page.update()
        render_grid()

    # HANDLERS
    def on_plantel_change(e):
        plantel_id = int(e.control.value) if e.control.value and e.control.value.isdigit() else None
        labs_filtrados = [l for l in labs_cache if l.get("plantel_id") == plantel_id] if plantel_id else []
        dd_lab.options = [ft.dropdown.Option(str(l["id"]), l["nombre"]) for l in labs_filtrados if l.get("id")]
        dd_lab.value = str(labs_filtrados[0]["id"]) if labs_filtrados else None
        state["confirm_for"] = None
        render()

    def on_lab_change(e):
        state["confirm_for"] = None
        render()

    dd_plantel.on_change = on_plantel_change
    dd_lab.on_change = on_lab_change

    # INICIALIZAR FILTROS
    if planteles_cache:
        dd_plantel.value = str(planteles_cache[0]["id"])
        on_plantel_change(SimpleControlEvent(control=dd_plantel))

    # CONTROLES DE UI
    head_label = ft.Text("", size=16, weight=ft.FontWeight.BOLD)
    
    nav_group = ft.Row([
        Icon(ft.Icons.CHEVRON_LEFT, on_click=goto_prev),
        head_label,
        Icon(ft.Icons.CHEVRON_RIGHT, on_click=goto_next),
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    mobile_nav = ft.Card(
        ft.Container(
            ft.Row([
                ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=goto_prev, icon_size=20),
                ft.TextButton(
                    ft.Row([ft.Icon(ft.Icons.CALENDAR_TODAY), ft.Text("Fecha")]),
                    on_click=show_date_picker
                ),
                ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=goto_next, icon_size=20),
                ft.IconButton(ft.Icons.TODAY, on_click=goto_today, icon_size=20),
            ], alignment=ft.MainAxisAlignment.SPACE_AROUND),
            padding=10,
        ),
        visible=False
    )

    filter_group = ft.Row([dd_plantel, dd_lab], spacing=10, visible=not state["is_mobile"])

    # UI PRINCIPAL
    ui = ft.Column([
        ft.Text("Reservas de Laboratorios", size=20, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
        Card(ft.Column([nav_group, mobile_nav, filter_group], spacing=8), padding=12),
        ft.Container(ft.Column([
            ft.Text("Leyenda:", size=14, weight=ft.FontWeight.BOLD),
            ft.Column([
                ft.Row([ft.Text("🟢"), ft.Text("Disponible", size=12, expand=True)]),
                ft.Row([ft.Text("🟡"), ft.Text("Reservado", size=12, expand=True)]),
                ft.Row([ft.Text("🔴"), ft.Text("No disponible", size=12, expand=True)]),
            ], spacing=4)
        ], spacing=6), padding=8),
        info,
        ft.Divider(),
        ft.Container(grid, expand=True, padding=8),
    ], expand=True, scroll=ft.ScrollMode.ADAPTIVE)

    # CONFIGURAR PÁGINA
    page.appbar = ft.AppBar(title=ft.Text("Reservas"), actions=[ft.IconButton(ft.Icons.FILTER_LIST, on_click=open_filters)]) if state["is_mobile"] else None
    
    def on_resize(e):
        if state["is_mobile"] != (page.width <= MOBILE_BREAKPOINT if page.width else False):
            render()

    page.on_resize = on_resize

    page.add(ui)
    render()
    return ui