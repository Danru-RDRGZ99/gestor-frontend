import flet as ft
from api_client import ApiClient
from ui.components.cards import Card
from ui.components.inputs import TextField
from ui.components.buttons import Primary, Ghost, Icon, Danger, Tonal # Añadidos Danger y Tonal

def PlantelesView(page: ft.Page, api: ApiClient):

    # --- INICIO DE LA CORRECCIÓN 1 ---
    user_session = page.session.get("user_session") or {}
    user_data = user_session # 'user_data' ES el diccionario de sesión
    is_admin = user_data.get("rol") == "admin"
    # --- FIN DE LA CORRECCIÓN 1 ---

    if not is_admin:
        return ft.Text("Acceso denegado. Solo para administradores.", color="red")

    # --- Estado y Controles de UI ---
    state = {"edit_for": None}

    nombre_tf = TextField("Nombre")
    direccion_tf = TextField("Dirección")

    info_txt = ft.Text("")
    list_panel = ft.Column(spacing=12, scroll=ft.ScrollMode.ADAPTIVE, expand=True) # Give scroll to list panel

    planteles_cache = []

    def render_list():
        nonlocal planteles_cache
        list_panel.controls.clear()
        
        # --- INICIO DE LA CORRECCIÓN 5 ---
        data = api.get_planteles()
        if isinstance(data, dict) and "error" in data:
            list_panel.controls.append(ft.Text(f"Error al cargar planteles: {data.get('error')}", color=ft.Colors.ERROR))
            planteles_cache = []
        elif not data or not isinstance(data, list):
            list_panel.controls.append(ft.Text("No hay planteles registrados."))
            planteles_cache = []
        else:
            planteles_cache = data # Guardar datos válidos
            for p_dict in planteles_cache:
                list_panel.controls.append(plantel_card(p_dict))
        # --- FIN DE LA CORRECCIÓN 5 ---
                
        # Update list_panel if it's already on the page
        if list_panel.page:
            list_panel.update()

    def reload_info(msg: str | None = None, update_page: bool = True):
        """Recarga la lista y opcionalmente actualiza un mensaje de información."""
        if msg is not None:
            info_txt.value = msg
            if "Error" in msg:
                info_txt.color = ft.Colors.ERROR
            else:
                info_txt.color = None # Color por defecto
            
            if update_page and info_txt.page: info_txt.update()
        
        render_list() # This updates controls *in memory*

    # --- INICIO DE LA CORRECCIÓN 2 ---
    def add_plantel(e):
        if not nombre_tf.value or not direccion_tf.value:
            reload_info("Completa los campos", update_page=True); return

        # Empaquetar datos en un diccionario
        payload = {
            "nombre": nombre_tf.value.strip(),
            "direccion": direccion_tf.value.strip()
        }
        # Llamar al método correcto del API client
        nuevo = api.create_plantel(payload) 

        # Comprobar la respuesta de error
        if nuevo and "error" not in nuevo:
            nombre_tf.value = ""; direccion_tf.value = ""
            if nombre_tf.page: nombre_tf.update()
            if direccion_tf.page: direccion_tf.update()
            reload_info(f"Plantel '{nuevo.get('nombre')}' guardado", update_page=True)
        else:
            error_msg = nuevo.get("error", "Error desconocido") if isinstance(nuevo, dict) else "Error"
            reload_info(f"Error al guardar: {error_msg}", update_page=True)
    # --- FIN DE LA CORRECCIÓN 2 ---

    # --- INICIO DE LA CORRECCIÓN 3 ---
    def save_edit(pid: int, n_val: str, d_val: str):
        if not n_val or not d_val:
            reload_info("Los campos no pueden estar vacíos en edición.", update_page=True); return

        # Empaquetar datos en un diccionario
        payload = {
            "nombre": n_val.strip(),
            "direccion": d_val.strip()
        }
        # Llamar al método 'update_plantel'
        actualizado = api.update_plantel(pid, payload)

        # Comprobar la respuesta de error
        if actualizado and "error" not in actualizado:
            state["edit_for"] = None
            reload_info("Plantel actualizado", update_page=True)
        else:
            error_msg = actualizado.get("error", "Error desconocido") if isinstance(actualizado, dict) else "Error"
            reload_info(f"Error al actualizar: {error_msg}", update_page=True)
    # --- FIN DE LA CORRECCIÓN 3 ---

    # --- INICIO DE LA CORRECCIÓN 4 ---
    def try_delete_plantel(pid: int):
        resultado = api.delete_plantel(pid)
        # Comprobar la respuesta de éxito de _make_request
        if resultado and resultado.get("success"):
            reload_info("Plantel eliminado", update_page=True)
        else:
            error_msg = resultado.get("error", "No se pudo eliminar") if isinstance(resultado, dict) else "Error"
            reload_info(f"{error_msg}. Asegúrate de que no tenga laboratorios asociados.", update_page=True)
    # --- FIN DE LA CORRECCIÓN 4 ---

    def open_edit(pid: int):
        state["edit_for"] = None if state["edit_for"] == pid else pid
        reload_info(msg="", update_page=True)

    # --- Renderizado de cada tarjeta de plantel ---
    def plantel_card(p: dict) -> ft.Control:
        title = ft.Text(f"{p.get('nombre', '')}", size=16, weight=ft.FontWeight.W_600)
        subtitle = ft.Text(p.get('direccion', '-'), size=12, opacity=0.85)

        # --- INICIO DE LA CORRECCIÓN 6 ---
        btns = ft.Row([
            Icon(ft.Icons.EDIT, "Editar", on_click=lambda e, pid=p['id']: open_edit(pid)),
            Icon(ft.Icons.DELETE, "Eliminar", 
                 on_click=lambda e, pid=p['id']: try_delete_plantel(pid), 
                 icon_color=ft.Colors.ERROR), # <-- Icon color añadido
        ], spacing=6)
        # --- FIN DE LA CORRECCIÓN 6 ---

        header = ft.Row([ft.Column([title, subtitle], spacing=2, expand=True), btns])

        content_column = ft.Column([header], spacing=10, key=f"plantel_{p['id']}")

        # --- Panel de edición inline ---
        if state["edit_for"] == p['id']:
            n_edit = TextField("Nombre", value=p['nombre'], expand=True) # Expand is ok inside the edit panel row
            d_edit = TextField("Dirección", value=p['direccion'], expand=True)
            actions = ft.Row([
                Primary("Guardar", on_click=lambda e, pid=p['id']: save_edit(pid, n_edit.value, d_edit.value), width=130),
                Ghost("Cancelar", on_click=lambda e, pid=p['id']: open_edit(pid), width=120),
            ])
            content_column.controls.append(ft.Column([ft.Divider(height=1, color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK)), n_edit, d_edit, actions], spacing=8))

        return Card(content_column, padding=14)

    # --- Layout de la Vista - Sección Agregar ---
    nombre_tf.col = {"sm": 12, "md": 5}
    direccion_tf.col = {"sm": 12, "md": 5}
    add_button = Primary("Agregar", on_click=add_plantel, height=44)
    add_button_container = ft.Container(add_button, col={"sm": 12, "md": 2}) # Container for alignment/sizing

    add_section_form = ft.ResponsiveRow(
        [
            nombre_tf,
            direccion_tf,
            add_button_container,
        ],
        vertical_alignment=ft.CrossAxisAlignment.END, # Align items based on bottom
        spacing=12
    )

    add_section = Card(
        ft.Column([
            ft.Text("Agregar Nuevo Plantel", size=16, weight=ft.FontWeight.W_600),
            add_section_form # Usar el ResponsiveRow
        ]),
        padding=14
    )


    # Carga inicial de datos
    render_list()

    return ft.Column(
        [
            ft.Text("Gestión de Planteles", size=22, weight=ft.FontWeight.BOLD),
            add_section,
            info_txt,
            ft.Divider(height=1, color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK)),
            ft.Container(content=list_panel, expand=True, padding=ft.padding.only(top=10)) # Wrap list_panel
        ],
        expand=True,
        alignment=ft.MainAxisAlignment.START,
        spacing=15
    )