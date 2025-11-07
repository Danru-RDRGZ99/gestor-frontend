import flet as ft
from api_client import ApiClient
from ui.components.cards import Card
from ui.components.inputs import TextField
from ui.components.buttons import Primary, Ghost, Danger, Icon, Tonal

# Objeto simple para manejar los datos que vienen de la API
class Laboratorio:
    def __init__(self, data):
        self.id = data.get("id")
        self.nombre = data.get("nombre")
        self.ubicacion = data.get("ubicacion")
        self.capacidad = data.get("capacidad")
        self.plantel_id = data.get("plantel_id")

def LaboratoriosView(page: ft.Page, api: ApiClient):
    
    # --- INICIO DE LA CORRECCIÓN 1 ---
    user_session = page.session.get("user_session") or {}
    u = user_session # 'u' es ahora el diccionario de sesión: {'rol': 'admin', ...}
    is_admin = u.get("rol") == "admin"
    # --- FIN DE LA CORRECCIÓN 1 ---

    state = {"editing_lab_id": None}

    # --- Controles del formulario (con layout responsivo) ---
    nombre = TextField("Nombre")
    nombre.col = {"sm": 12, "md": 6, "lg": 3} 

    ubicacion = TextField("Ubicación")
    ubicacion.col = {"sm": 12, "md": 6, "lg": 3}

    capacidad = TextField("Capacidad")
    capacidad.col = {"sm": 12, "md": 6, "lg": 2}
    
    # --- INICIO DE LA CORRECCIÓN 2 ---
    # Carga de datos robusta
    plantel_options = []
    planteles_data = api.get_planteles()
    if isinstance(planteles_data, list):
        plantel_options = [ft.dropdown.Option(str(p["id"]), p["nombre"]) for p in planteles_data if "id" in p]
    else:
        print(f"Error al cargar planteles: {planteles_data.get('error', 'Error desconocido')}")
    # --- FIN DE LA CORRECCIÓN 2 ---
    
    dd_plantel_add = ft.Dropdown(label="Plantel", options=plantel_options)
    dd_plantel_add.col = {"sm": 12, "md": 6, "lg": 2}

    info = ft.Text("")
    list_panel = ft.Column(spacing=12, scroll=ft.ScrollMode.ADAPTIVE, expand=True) 

    # --- Diálogo de confirmación de borrado ---
    def confirm_delete_click(e):
        lab_id_to_delete = page.dialog.data
        page.dialog.open = False
        page.update()

        if lab_id_to_delete:
            result = api.delete_laboratorio(lab_id_to_delete)
            # --- INICIO DE LA CORRECCIÓN 4 ---
            # Comprobar la respuesta de la API correctamente
            if result and result.get("success"):
                show_info_and_reload("Laboratorio eliminado correctamente.")
            else:
                error_msg = result.get("error", "Error desconocido") if isinstance(result, dict) else "Error"
                show_info_and_reload(f"Error: {error_msg}")
            # --- FIN DE LA CORRECCIÓN 4 ---

    delete_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirmar eliminación"),
        content=ft.Text("¿Estás seguro de que quieres eliminar este laboratorio? Esta acción no se puede deshacer."),
        actions=[
            Tonal("Cancelar", on_click=lambda e: (setattr(page.dialog, 'open', False), page.update())),
            Danger("Eliminar", on_click=confirm_delete_click),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    if delete_dialog not in page.overlay:
        page.overlay.append(delete_dialog)


    # --- Lógica de botones y formularios ---
    
    def clear_form(e=None):
        state["editing_lab_id"] = None
        nombre.value = ""
        ubicacion.value = ""
        capacidad.value = ""
        dd_plantel_add.value = None
        btn_save.text = "Agregar"
        btn_cancel.visible = False
        if form_card.content: # Comprobación de seguridad
            form_card.content.update() 

    def edit_lab_click(lab: Laboratorio):
        state["editing_lab_id"] = lab.id
        nombre.value = lab.nombre
        ubicacion.value = lab.ubicacion
        capacidad.value = str(lab.capacidad)
        dd_plantel_add.value = str(lab.plantel_id)
        btn_save.text = "Actualizar"
        btn_cancel.visible = True
        if form_card.content: # Comprobación de seguridad
            form_card.content.update()
        info.value = f"Editando: {lab.nombre}"
        if info.page: info.update()

    def delete_lab_click(lab: Laboratorio):
        page.dialog = delete_dialog
        page.dialog.data = lab.id
        page.dialog.open = True
        page.update()

    def show_info_and_reload(msg: str | None = None):
        """Muestra un mensaje y recarga la lista."""
        if msg is not None:
            info.value = msg
        if "Error" not in (msg or ""):
            clear_form()
        
        render_list() 
        if info.page: info.update()

    # --- INICIO DE LA CORRECCIÓN 3 ---
    def save_lab(e):
        """Maneja tanto la creación (POST) como la actualización (PUT)."""
        if not is_admin:
            show_info_and_reload("Acción no permitida."); return
        
        if not all([nombre.value, capacidad.value, dd_plantel_add.value]):
            show_info_and_reload("Completa nombre, capacidad y plantel"); 
            return
        
        try:
            lab_id = state.get("editing_lab_id")
            
            # 1. Empaquetar los datos en un diccionario (payload)
            payload = {
                "nombre": nombre.value.strip(),
                "ubicacion": (ubicacion.value or "").strip(),
                "capacidad": int(capacidad.value),
                "plantel_id": int(dd_plantel_add.value)
            }

            if lab_id is None:
                # 2. Llamar a 'create_laboratorio' con el payload
                result = api.create_laboratorio(payload)
                msg = "Laboratorio creado"
            else:
                # 3. Llamar a 'update_laboratorio' con lab_id y el payload
                result = api.update_laboratorio(lab_id, payload)
                msg = "Laboratorio actualizado"

            # 4. Comprobar la respuesta de la API
            if result and "error" not in result:
                show_info_and_reload(msg)
            else:
                error_msg = result.get("error", "Error desconocido") if isinstance(result, dict) else "Error"
                show_info_and_reload(f"Error: {error_msg}")
        
        except ValueError:
            show_info_and_reload("La capacidad debe ser un número")
        except Exception as ex:
            show_info_and_reload(f"Error inesperado: {ex}")
    # --- FIN DE LA CORRECCIÓN 3 ---

    # --- Renderizado de la lista ---
    def render_list():
        list_panel.controls.clear()
        try:
            # --- INICIO DE LA CORRECCIÓN 5 ---
            # 'planteles_data' ya se cargó al inicio.
            # Creamos el map a partir de la variable en el scope superior
            planteles_map = {str(p["id"]): p["nombre"] for p in planteles_data if isinstance(p, dict) and "id" in p}
            
            labs_data = api.get_laboratorios()
            if not isinstance(labs_data, list):
                 print(f"Error al cargar laboratorios: {labs_data.get('error', 'Error desconocido')}")
                 labs_data = [] # Asegurarse de que sea una lista para iterar
            # --- FIN DE LA CORRECCIÓN 5 ---

            if not labs_data:
                list_panel.controls.append(ft.Text("No hay laboratorios registrados."))
            
            for lab_dict in labs_data:
                lab = Laboratorio(lab_dict)
                plantel_nombre = planteles_map.get(str(lab.plantel_id), "N/A")
                title = ft.Text(lab.nombre, size=16, weight=ft.FontWeight.W_600)
                subtitle = ft.Text(f"Ubicación: {lab.ubicacion or 'N/A'} · Capacidad: {lab.capacidad} · Plantel: {plantel_nombre}", size=12, opacity=0.85)
                
                admin_actions = ft.Row(spacing=4, alignment=ft.MainAxisAlignment.END)
                if is_admin:
                    
                    # --- INICIO DE LA CORRECCIÓN 6 ---
                    # Pasamos icon_color como argumento, no como propiedad
                    edit_icon = Icon(
                        ft.Icons.EDIT_OUTLINED,
                        tooltip="Editar",
                        on_click=lambda _, l=lab: edit_lab_click(l) 
                    )
                    
                    delete_icon = Icon(
                        ft.Icons.DELETE_OUTLINED,
                        tooltip="Eliminar",
                        on_click=lambda _, l=lab: delete_lab_click(l), 
                        icon_color=ft.Colors.ERROR # Pasar como argumento
                    )
                    
                    admin_actions.controls.extend([edit_icon, delete_icon])
                    # --- FIN DE LA CORRECCIÓN 6 ---

                header = ft.Row(
                    [
                        ft.Column([title, subtitle], spacing=2, expand=True),
                        admin_actions
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.START
                )
                list_panel.controls.append(Card(header, padding=14))
        except Exception as e:
            print(f"Error al renderizar lista: {e}") # Imprimir en consola
            list_panel.controls.append(ft.Text(f"Error al cargar laboratorios: {e}"))
        
        if list_panel.page:
            list_panel.update()

    # --- Layout ---
    
    btn_save = Primary("Agregar", on_click=save_lab, height=44)
    btn_save.col = {"sm": 6, "lg": 1}

    btn_cancel = Ghost("Cancelar", on_click=clear_form, height=44)
    btn_cancel.visible = False
    btn_cancel.col = {"sm": 6, "lg": 1}

    form_controls = ft.ResponsiveRow(
        [
            nombre, 
            ubicacion, 
            capacidad, 
            dd_plantel_add, 
            ft.Row(
                [btn_save, btn_cancel], 
                alignment=ft.MainAxisAlignment.START
            )
        ],
        vertical_alignment=ft.CrossAxisAlignment.END, 
        visible=is_admin
    )
    form_card = Card(form_controls, padding=14)

    # Carga inicial
    render_list() 
    
    return ft.Column(
        [
            ft.Text("Laboratorios", size=20, weight=ft.FontWeight.BOLD),
            form_card, 
            info,
            ft.Divider(),
            list_panel, # Contenedor con scroll
        ],
        expand=True, alignment=ft.MainAxisAlignment.START, spacing=10
    )