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
    user_data = user_session

    # --- INICIO CAMBIO RESPONSIVO: Detección Móvil ---
    MOBILE_BREAKPOINT = 640 

    def get_is_mobile():
        return page.width is not None and page.width <= MOBILE_BREAKPOINT

    state = {"confirm_for": None, "is_mobile": get_is_mobile()}

    def update_mobile_state():
        new_is_mobile = get_is_mobile()
        if new_is_mobile != state["is_mobile"]:
            state["is_mobile"] = new_is_mobile
            state["confirm_for"] = None 
            print(f"INFO: Cambiando a layout {'MÓVIL' if new_is_mobile else 'WEB'}")
        else:
            state["is_mobile"] = new_is_mobile
    # --- FIN CAMBIO RESPONSIVO ---

    # --- Controles de Filtros ---
    # Los definimos aquí para que existan en todos los scopes
    dd_plantel = ft.Dropdown(label="Plantel", options=[])
    dd_lab = ft.Dropdown(label="Laboratorio", options=[])

    # --- Estado y UI ---
    info = ft.Text("")
    
    # Simplificamos el grid. El centrado lo hará el hijo.
    grid = ft.Column(spacing=12, scroll=ft.ScrollMode.ADAPTIVE, expand=True)

    # --- NUEVO: Definición del BottomSheet para filtros ---
    def close_filters(e):
        bs_filters.open = False
        bs_filters.update()

    bs_filters = ft.BottomSheet(
        ft.Container(
            ft.Column(
                [
                    ft.Text("Filtrar Laboratorios", size=18, weight=ft.FontWeight.BOLD),
                    dd_plantel, # Reutilizamos el control
                    dd_lab,     # Reutilizamos el control
                    ft.FilledButton("Aplicar y cerrar", on_click=close_filters)
                ],
                tight=True,
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            padding=ft.padding.symmetric(vertical=20, horizontal=16)
        ),
        on_dismiss=lambda e: print("Filtros cerrados"),
    )
    # Añadimos el sheet al overlay de la página
    page.overlay.append(bs_filters)

    # --- NUEVO: Definición del Botón Flotante (FAB) ---
    def open_filters(e):
        bs_filters.open = True
        bs_filters.update()

    fab_filter = ft.FloatingActionButton(
        icon=ft.Icons.FILTER_ALT_OUTLINED,
        tooltip="Filtrar laboratorios",
        on_click=open_filters,
        visible=False # Empezará oculto
    )
    # --- FIN SECCIONES NUEVAS ---

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
            error_detail = planteles_data.get("error", "Error") if isinstance(planteles_data, dict) else "Respuesta inesperada"
            error_loading_data = f"Error al cargar planteles: {error_detail}"

        if isinstance(labs_data, list):
            labs_cache = labs_data
            lab_map = {str(l.get("id", "")): l.get("nombre", "Nombre Desconocido") for l in labs_cache if l.get("id")}
        else:
            error_detail = labs_data.get("error", "Error") if isinstance(labs_data, dict) else "Respuesta inesperada"
            if error_loading_data: error_loading_data += f"\nError al cargar laboratorios: {error_detail}"
            else: error_loading_data = f"Error al cargar laboratorios: {error_detail}"

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

    def get_days_in_window(start_date: date):
        cur = start_date
        if is_weekend(cur): cur = next_weekday(cur)
        if state["is_mobile"]: return [cur]
        else: return five_weekdays_from(cur)

    def goto_next(e):
        days = get_days_in_window(window["start"]) 
        last_day = days[-1]
        window["start"] = next_weekday(last_day) 
        state["confirm_for"] = None
        render()

    def goto_prev(e):
        if state["is_mobile"]:
            window["start"] = next_weekday(window["start"], step=-1)
        else:
            prev_days = five_weekdays_before(window["start"])
            window["start"] = prev_days[0]
        state["confirm_for"] = None
        render()

    def slot_label(s: datetime, f: datetime): return f"{s.strftime('%H:%M')}–{f.strftime('%H:%M')}"

    # --- Acciones (Crear/Cancelar) ---
    def do_create_reservation(lab_id: int, s: datetime, f: datetime):
        if user_data.get("rol") not in ["admin", "docente"]:
            info.value = "Solo administradores y docentes pueden crear reservas."
            info.color = ft.Colors.ERROR; info.update(); return

        info.value = "Creando reserva, por favor espera..."; info.color = ft.Colors.BLUE_500
        grid.disabled = True; page.update(info, grid)

        payload = {
            "laboratorio_id": lab_id, "usuario_id": user_data.get("id"),
            "inicio": s.isoformat(), "fin": f.isoformat()
        }
        result = api.create_reserva(payload)
        
        grid.disabled = False; info.color = None

        if result and "error" not in result:
            info.value = "Reserva creada con éxito."; info.color = ft.Colors.GREEN_500
            state["confirm_for"] = None; render() 
        else:
            error_detail = result.get("error", "Error") if isinstance(result, dict) else "Error"
            info.value = f"Error al crear la reserva: {error_detail}"; info.color = ft.Colors.ERROR
            page.update(info, grid)

    def do_cancel_reservation(rid: int):
        info.value = "Cancelando reserva, por favor espera..."; info.color = ft.Colors.AMBER_700
        grid.disabled = True; page.update(info, grid)

        result = api.delete_reserva(rid)

        grid.disabled = False; info.color = None; state["confirm_for"] = None

        if result and "error" not in result:
            info.value = "Reserva cancelada exitosamente."; info.color = ft.Colors.GREEN_500
            render() 
        else:
            error_detail = result.get("error", "Error") if isinstance(result, dict) else "Error"
            info.value = f"Error al cancelar la reserva: {error_detail}"; info.color = ft.Colors.ERROR
            page.update(info, grid)

    def ask_inline_cancel(rid: int, etiqueta: str):
        state["confirm_for"] = rid
        info.value = f"Confirmar cancelación para {etiqueta}"; info.color = ft.Colors.AMBER_700
        render() 

    # --- Renderizado del Calendario (Día) ---
    def day_section(d: date, lid: int, slots_calculados: list[dict], day_reserveds: list[dict]):
        title = ft.Text(f"{day_names_short[d.weekday()]} {d.strftime('%d/%m')}", size=16, weight=ft.FontWeight.W_600)
        tiles = []
        
        is_mobile_view = state["is_mobile"]
        btn_width = None if is_mobile_view else 220
        
        # --- ¡INICIO DE LA CORRECCIÓN 1! ---
        # Volvemos a expandir los botones en móvil
        btn_expand = True if is_mobile_view else False
        # --- ¡FIN DE LA CORRECCIÓN 1! ---

        reservas_map = {}
        for r in day_reserveds:
            try:
                dt_aware_utc = datetime.fromisoformat(str(r.get('inicio')).replace('Z', '+00:00'))
                dt_naive_local = dt_aware_utc.astimezone(None).replace(tzinfo=None)
                reservas_map[dt_naive_local] = r
            except (ValueError, TypeError) as e:
                print(f"Error parsing date for reservation {r.get('id')}: {e}")

        for slot in slots_calculados:
            try:
                s_dt = datetime.fromisoformat(str(slot.get('inicio'))).replace(tzinfo=None)
                f_dt = datetime.fromisoformat(str(slot.get('fin'))).replace(tzinfo=None)
                k_tipo = slot.get('tipo', 'no_habilitado')
            except (ValueError, TypeError) as e:
                print(f"WARN: Skipping slot due to invalid date: {slot} | Error: {e}"); continue

            label = slot_label(s_dt, f_dt)
            found_res_data = reservas_map.get(s_dt) 

            # --- CASO 1: Slot Reservado ---
            if found_res_data:
                rid = found_res_data.get('id')
                user_info = found_res_data.get('usuario', {}) 
                nombre = user_info.get('nombre', 'N/A')
                current_user_id = user_data.get("id")
                current_user_rol = user_data.get("rol")
                is_owner = (str(current_user_id) == str(user_info.get('id')))
                is_admin = (current_user_rol == "admin")
                can_manage = is_owner or is_admin
                
                label = f"Reservado por {nombre}"

                if can_manage and state["confirm_for"] == rid:
                    tiles.append(ft.Row([
                        Danger("Confirmar", 
                               on_click=lambda _, _rid=rid: do_cancel_reservation(_rid) if _rid else None, 
                               width=None if is_mobile_view else 120, 
                               expand=btn_expand, # <-- Ahora es True en móvil
                               height=44),
                        Ghost("Volver", 
                              on_click=lambda e: (state.update({"confirm_for": None}), render()), 
                              width=72, height=44),
                    ]))
                else:
                    tiles.append(Tonal(
                        label,
                        tooltip="Haz clic para cancelar" if can_manage else "No puedes cancelar esta reserva",
                        on_click=lambda _, _rid=rid, _lab=label: ask_inline_cancel(_rid, _lab) if can_manage and _rid else None,
                        disabled=not can_manage, width=btn_width, expand=btn_expand, height=50
                    ))

            # --- CASO 2: Slot Disponible ---
            elif k_tipo in ["disponible", "libre"]:
                is_allowed_to_create = user_data.get("rol") in ["admin", "docente"]
                reserve_button = Primary(label,
                                         on_click=lambda _, ss=s_dt, ff=f_dt, _lid=lid: do_create_reservation(_lid, ss, ff) if is_allowed_to_create else None,
                                         disabled=not is_allowed_to_create, width=btn_width, expand=btn_expand, height=50)
                reserve_button.tooltip = "Solo admin/docente pueden reservar" if not is_allowed_to_create else None
                tiles.append(reserve_button)

            # --- CASO 3: Slot No Habilitado ---
            else:
                tiles.append(Tonal(f"{k_tipo.capitalize()} {label}", 
                                   disabled=True, width=btn_width, expand=btn_expand, height=50));

        # --- ¡INICIO DE LA CORRECCIÓN 2! ---
        if is_mobile_view:
            # En móvil: Columna normal. El 'grid' padre hace el scroll.
            # Quitamos el centrado de los botones.
            tiles_container = ft.Column(
                tiles, 
                spacing=8
                # horizontal_alignment=ft.CrossAxisAlignment.CENTER <-- QUITADO
            )
        else:
            # En web: Fila con scroll horizontal.
            tiles_container = ft.Row(tiles, scroll=ft.ScrollMode.AUTO, wrap=False, spacing=8)
            
        # Volvemos a alinear el Título a la izquierda (START)
        day_column = ft.Column(
            [title, tiles_container], 
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.START # <-- CAMBIADO A START
        )
        # --- ¡FIN DE LA CORRECCIÓN 2! ---
        
        card_padding = ft.padding.only(top=14, left=14, right=14, bottom=19)
        
        # Esta parte (el contenedor de la tarjeta) la dejamos como estaba,
        # para que la tarjeta ocupe todo el ancho
        card_content = Card(day_column, padding=card_padding)

        if is_mobile_view:
            # En móvil, envolvemos la tarjeta en un Row que se expande
            # y que la tarjeta dentro también se expande.
            return ft.Row(
                controls=[
                    ft.Container(
                        content=card_content,
                        expand=True, # La tarjeta ahora se expandirá dentro de este Container
                        padding=ft.padding.symmetric(horizontal=10) # Añade un pequeño padding lateral
                    )
                ],
                expand=True # El Row se expande para llenar el ancho
            )
        else:
            # En web, la devolvemos como estaba. También la expandimos para consistencia.
            return ft.Container(content=card_content, expand=True)


    # --- Renderizado del Grid (Contenedor de días) ---
    def render_grid():
        grid.controls.clear()
        if not dd_lab.value or not dd_lab.value.isdigit():
            info.value = "Selecciona un plantel y un laboratorio válido para ver la disponibilidad."; info.color = ft.Colors.AMBER_700
            if grid.page: page.update(info, grid) # Solo actualizar si ya está en la página
            return

        lid = int(dd_lab.value)
        days_to_display = get_days_in_window(window["start"]) 
        end_dt_range_api = days_to_display[-1] + timedelta(days=1) 

        # 1. Obtener Horario
        horario_result = api.get_horario_laboratorio(lid, days_to_display[0], days_to_display[-1])
        if not isinstance(horario_result, dict):
            info.value = f"Error al cargar horario: Respuesta inesperada"; info.color = ft.Colors.ERROR
            if grid.page: page.update(info, grid); return
        if "error" in horario_result:
            info.value = f"Error al cargar horario: {horario_result.get('error')}"; info.color = ft.Colors.ERROR
            if grid.page: page.update(info, grid); return

        # 2. Obtener Reservas
        api_result = api.get_reservas(lid, days_to_display[0], end_dt_range_api)
        all_reservas = []
        if isinstance(api_result, list): all_reservas = api_result
        else:
            info.value = f"Error al cargar reservas: {api_result.get('error', 'Error') if isinstance(api_result, dict) else 'Error'}"; info.color = ft.Colors.ERROR
            if grid.page: page.update(info, grid); return

        # 3. Mapear reservas por día
        reservations_by_day = {d: [] for d in days_to_display}
        for r in all_reservas:
            try:
                dt_aware_utc = datetime.fromisoformat(str(r.get('inicio')).replace('Z', '+00:00'))
                dkey = dt_aware_utc.astimezone(None).date()
                if dkey in reservations_by_day:
                    reservations_by_day[dkey].append(r)
            except (ValueError, TypeError) as e:
                print(f"Error parsing date {r.get('inicio')} in render_grid: {e}")

        # 4. Renderizar
        for d in days_to_display:
            slots_for_day = horario_result.get(d.isoformat(), [])
            reservations_for_day = reservations_by_day.get(d, [])
            grid.controls.append(day_section(
                d, lid, slots_for_day, reservations_for_day
            ))
        
        # Ocultar "cargando" y mostrar el grid
        grid.disabled = False
        if grid.page: grid.update()

    # --- Función Principal de Renderizado ---
    def render():
        # 1. Actualizar el estado (Móvil/Web)
        update_mobile_state() 
        
        # 2. Limpiar 'info' si no estamos confirmando
        if state["confirm_for"] is None:
            info.value = ""; info.color = None
            if info.page: info.update()

        # 3. Actualizar la etiqueta del header
        days = get_days_in_window(window["start"])
        lab_name = lab_map.get(dd_lab.value, "(Selecciona Lab)")
        if state["is_mobile"]:
            head_label.value = f"{days[0].strftime('%d/%m')} · {lab_name}"
        else:
            head_label.value = f"{days[0].strftime('%d/%m')} — {days[-1].strftime('%d/%m')} · {lab_name}"
        if head_label.page: head_label.update()
        
        # 4. Ajustar layout de filtros (Móvil vs Web)
        if state["is_mobile"]:
            # En móvil: Ocultar filtros de la tarjeta y mostrar el FAB
            filter_group.visible = False
            page.floating_action_button = fab_filter # Añadir FAB
            fab_filter.visible = True
        else:
            # En web: Mostrar filtros en la tarjeta y ocultar el FAB
            filter_group.visible = True
            page.floating_action_button = None # Quitar FAB
            fab_filter.visible = False
        
        if filter_group.page: filter_group.update()
        
        # En lugar de actualizar el FAB, actualizamos la PÁGINA
        # para registrar el cambio de (añadir/quitar) el FAB.
        if page: # 'page' siempre existe en este contexto
            page.update()

        # 5. Deshabilitar el grid (mostrará "cargando") y llamar a render_grid
        grid.disabled = True
        grid.controls.clear()
        if grid.page: grid.update()
        render_grid() # Esta función actualiza el grid al terminar

    # --- Manejadores de Eventos ---
    def on_change_plantel(e: ft.ControlEvent):
        pid_str = e.control.value
        pid = int(pid_str) if pid_str and pid_str.isdigit() else None
        filtered_labs = [l for l in labs_cache if l.get("plantel_id") == pid] if pid is not None else []
        dd_lab.options = [ft.dropdown.Option(str(l["id"]), l["nombre"]) for l in filtered_labs if l.get("id")]
        dd_lab.value = str(filtered_labs[0]["id"]) if filtered_labs else None
        
        state["confirm_for"] = None

        # Si e.control.page es None, es la llamada de inicialización.
        # No llames a update() ni a render().
        if e.control.page: 
            dd_lab.update() # Actualizar opciones de lab (para web/sheet)
            render() # Renderizar el grid con el nuevo lab
        
        # (El resto de la lógica de UX se movió a on_change_lab)

    def on_change_lab(e: ft.ControlEvent):
        state["confirm_for"] = None
        
        # Si e.control.page es None, es la llamada de inicialización.
        if e.control.page:
            render() # Llama al render principal
            
            # UX: Si estamos en móvil, cerramos el sheet al elegir lab
            if state["is_mobile"]: 
                close_filters(None)

    dd_plantel.on_change = on_change_plantel
    dd_lab.on_change = on_change_lab

    # --- Inicialización de la Vista ---
    if planteles_cache:
        first_plantel_id_str = str(planteles_cache[0].get("id","")) if planteles_cache else ""
        if first_plantel_id_str:
            dd_plantel.value = first_plantel_id_str
            # Esta llamada ahora es SEGURA.
            # Solo preparará los datos de dd_lab.value y dd_lab.options
            # porque e.control.page será None.
            on_change_plantel(SimpleControlEvent(control=dd_plantel))
        else:
            info.value = "El primer plantel no tiene un ID válido."; info.color = ft.Colors.ERROR
            head_label.value = "Error de Configuración"
    else:
        info.value = "No hay planteles configurados."; info.color = ft.Colors.ERROR
        head_label.value = "Error de Configuración"


    # --- Layout Final (Construido UNA VEZ) ---
    
    # 1. Grupo de Navegación
    nav_group = ft.Row(
        [
            Icon(ft.Icons.CHEVRON_LEFT, "Día anterior", on_click=goto_prev),
            head_label,
            Icon(ft.Icons.CHEVRON_RIGHT, "Siguiente día", on_click=goto_next),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN, 
        vertical_alignment=ft.CrossAxisAlignment.CENTER
    )
    
    # 2. Grupo de Filtros (para Web)
    # Usamos los controles dd_plantel y dd_lab definidos arriba
    # Ajustamos su 'expand' para que se vean bien
    dd_plantel.expand = 1
    dd_lab.expand = 1
    filter_group = ft.Row(
        [dd_plantel, dd_lab],
        spacing=10,
        visible=False # Render decide si se ve
    )
    
    # 3. Cabecera (Contenedor adaptable)
    header_controls_container = ft.Column(
        [
            nav_group,
            filter_group # Se mostrará/ocultará dinámicamente
        ],
        spacing=12
    )
    
    # 4. Leyenda
    legend = ft.Row([
        ft.Chip(label=ft.Text("Disponible"), leading=ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE)),
        ft.Chip(label=ft.Text("Reservado"), leading=ft.Icon(ft.Icons.BLOCK)), 
        ft.Chip(label=ft.Text("Descanso"), leading=ft.Icon(ft.Icons.SCHEDULE))
    ], 
    spacing=8, 
    # Hacemos que sea deslizable horizontalmente en móvil
    scroll=ft.ScrollMode.ADAPTIVE 
    )

    # --- Función para manejar el resize ---
    # (Esto es crucial para que el layout cambie sin recargar)
    def on_page_resize(e):
        current_is_mobile = state["is_mobile"]
        new_is_mobile = get_is_mobile()
        if current_is_mobile != new_is_mobile:
            # ¡El layout debe cambiar!
            # Llamamos a render() para que ajuste todo
            render()
    page.on_resize = on_page_resize
    
    # --- Llamada final para el primer renderizado ---
    # Ahora que todos los controles están definidos, llamamos a render()
    # para que muestre el estado inicial correcto.
    render()

    # Devolvemos la columna principal que contiene todo
    return ft.Column(
        controls=[
            ft.Text("Reservas de Laboratorios", size=22, weight=ft.FontWeight.BOLD),
            Card(header_controls_container, padding=14),
            legend,
            info,
            ft.Divider(height=1, color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK)),
            ft.Container(content=grid, expand=True, padding=ft.padding.only(top=10))
        ],
        expand=True,
        scroll=None,
        spacing=15
    )