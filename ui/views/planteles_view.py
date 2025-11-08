import flet as ft
from api_client import ApiClient
from ui.components.cards import Card
from ui.components.inputs import TextField
from ui.components.buttons import Primary, Ghost, Icon, Danger, Tonal


def PlantelesView(page: ft.Page, api: ApiClient):

    # Detectar si es móvil (responsive real)
    is_mobile = page.width < 600

    # --- Autorización ---
    user_session = page.session.get("user_session") or {}
    user_data = user_session
    is_admin = user_data.get("rol") == "admin"

    if not is_admin:
        return ft.Text("Acceso denegado. Solo para administradores.", color="red")

    # --- Estado y controles ---
    state = {"edit_for": None}

    nombre_tf = TextField("Nombre")
    direccion_tf = TextField("Dirección")
    info_txt = ft.Text("")
    list_panel = ft.Column(spacing=12, scroll=ft.ScrollMode.ADAPTIVE)

    planteles_cache = []

    # ------------------------------
    # Renderizado lista
    # ------------------------------
    def render_list():
        nonlocal planteles_cache
        list_panel.controls.clear()

        data = api.get_planteles()

        if isinstance(data, dict) and "error" in data:
            list_panel.controls.append(ft.Text(f"Error al cargar planteles: {data.get('error')}", color=ft.Colors.ERROR))
            planteles_cache = []
        elif not data or not isinstance(data, list):
            list_panel.controls.append(ft.Text("No hay planteles registrados."))
            planteles_cache = []
        else:
            planteles_cache = data
            for p in planteles_cache:
                if is_mobile:
                    list_panel.controls.append(plantel_card_mobile(p))
                else:
                    list_panel.controls.append(plantel_card(p))

        if list_panel.page:
            list_panel.update()

    # ------------------------------
    # Mensajes y recarga
    # ------------------------------
    def reload_info(msg: str | None = None, update_page: bool = True):
        if msg is not None:
            info_txt.value = msg
            info_txt.color = ft.Colors.ERROR if "Error" in msg else None
            if update_page and info_txt.page:
                info_txt.update()
        render_list()

    # ------------------------------
    # Crear plantel
    # ------------------------------
    def add_plantel(e):
        if not nombre_tf.value or not direccion_tf.value:
            reload_info("Completa los campos", update_page=True)
            return

        payload = {
            "nombre": nombre_tf.value.strip(),
            "direccion": direccion_tf.value.strip()
        }

        nuevo = api.create_plantel(payload)

        if nuevo and "error" not in nuevo:
            nombre_tf.value = ""
            direccion_tf.value = ""
            if nombre_tf.page:
                nombre_tf.update()
            if direccion_tf.page:
                direccion_tf.update()
            reload_info(f"Plantel '{nuevo.get('nombre')}' guardado", update_page=True)
        else:
            error_msg = nuevo.get("error", "Error desconocido") if isinstance(nuevo, dict) else "Error"
            reload_info(f"Error al guardar: {error_msg}", update_page=True)

    # ------------------------------
    # Guardar edición
    # ------------------------------
    def save_edit(pid: int, n_val: str, d_val: str):
        if not n_val or not d_val:
            reload_info("Los campos no pueden estar vacíos", update_page=True)
            return

        payload = {"nombre": n_val.strip(), "direccion": d_val.strip()}
        actualizado = api.update_plantel(pid, payload)

        if actualizado and "error" not in actualizado:
            state["edit_for"] = None
            reload_info("Plantel actualizado", update_page=True)
        else:
            error_msg = actualizado.get("error", "Error desconocido") if isinstance(actualizado, dict) else "Error"
            reload_info(f"Error al actualizar: {error_msg}", update_page=True)

    # ------------------------------
    # Eliminar plantel
    # ------------------------------
    def try_delete_plantel(pid: int):
        resultado = api.delete_plantel(pid)

        if resultado and resultado.get("success"):
            reload_info("Plantel eliminado", update_page=True)
        else:
            error_msg = resultado.get("error", "No se pudo eliminar") if isinstance(resultado, dict) else "Error"
            reload_info(f"{error_msg}. Verifica laboratorios asociados.", update_page=True)

    # ------------------------------
    # Activar edición
    # ------------------------------
    def open_edit(pid: int):
        state["edit_for"] = None if state["edit_for"] == pid else pid
        reload_info("", update_page=True)

    # -----------------------------------------------------
    # CARD WEB (original)
    # -----------------------------------------------------
    def plantel_card(p: dict):
        title = ft.Text(p.get("nombre", ""), size=16, weight=ft.FontWeight.W_600)
        subtitle = ft.Text(p.get("direccion", "-"), size=12, opacity=0.85)

        btns = ft.Row([
            Icon(ft.Icons.EDIT, "Editar", on_click=lambda e, pid=p['id']: open_edit(pid)),
            Icon(ft.Icons.DELETE, "Eliminar",
                 on_click=lambda e, pid=p['id']: try_delete_plantel(pid),
                 icon_color=ft.Colors.ERROR)
        ], spacing=6)

        content = ft.Column([ft.Row([ft.Column([title, subtitle], expand=True), btns])], spacing=10)

        if state["edit_for"] == p["id"]:
            n_edit = TextField("Nombre", value=p["nombre"])
            d_edit = TextField("Dirección", value=p["direccion"])

            actions = ft.Row([
                Primary("Guardar", on_click=lambda e: save_edit(p["id"], n_edit.value, d_edit.value)),
                Ghost("Cancelar", on_click=lambda e: open_edit(p["id"]))
            ])

            content.controls.append(
                ft.Column([
                    ft.Divider(),
                    n_edit,
                    d_edit,
                    actions
                ], spacing=8)
            )

        return Card(content, padding=14)

    # -----------------------------------------------------
    # CARD MÓVIL OPTIMIZADA
    # -----------------------------------------------------
    def plantel_card_mobile(p: dict):
        title = ft.Text(p.get("nombre", ""), size=15, weight=ft.FontWeight.W_600)
        subtitle = ft.Text(p.get("direccion", "-"), size=11, opacity=0.85)

        btns = ft.Row(
            [
                Primary("Editar", height=36, expand=True,
                        on_click=lambda e: open_edit(p["id"])),
                Danger("Eliminar", height=36, expand=True,
                       on_click=lambda e: try_delete_plantel(p["id"]))
            ],
            spacing=6
        )

        content = ft.Column([title, subtitle, btns], spacing=6)

        if state["edit_for"] == p["id"]:
            n_edit = TextField("Nombre", value=p["nombre"])
            d_edit = TextField("Dirección", value=p["direccion"])

            actions = ft.Column([
                Primary("Guardar", height=36, on_click=lambda e: save_edit(p["id"], n_edit.value, d_edit.value)),
                Ghost("Cancelar", height=36, on_click=lambda e: open_edit(p["id"]))
            ], spacing=6)

            content.controls.append(
                ft.Column([
                    ft.Divider(),
                    n_edit,
                    d_edit,
                    actions
                ], spacing=6)
            )

        return Card(
            ft.Container(content, border_radius=10),
            padding=8
        )

    # -----------------------------------------------------
    # FORMULARIO NEW PLANTEL
    # -----------------------------------------------------
    if is_mobile:
        add_section_form = ft.Column(
            [
                TextField("Nombre", height=45),
                TextField("Dirección", height=45),
                Primary("Agregar", on_click=add_plantel, height=40)
            ],
            spacing=6
        )

        add_section = Card(
            ft.Container(
                ft.Column([
                    ft.Text("Agregar Nuevo Plantel", size=14, weight=ft.FontWeight.W_600),
                    add_section_form
                ], spacing=6),
                border_radius=10
            ),
            padding=10
        )

    else:
        nombre_tf.col = {"sm": 12, "md": 5}
        direccion_tf.col = {"sm": 12, "md": 5}

        add_section_form = ft.ResponsiveRow(
            [
                nombre_tf,
                direccion_tf,
                ft.Container(
                    Primary("Agregar", on_click=add_plantel, height=44),
                    col={"sm": 12, "md": 2}
                )
            ],
            spacing=12
        )

        add_section = Card(
            ft.Column([
                ft.Text("Agregar Nuevo Plantel", size=16, weight=ft.FontWeight.W_600),
                add_section_form
            ]),
            padding=14
        )

    # ------------------------------
    # CARGAR LISTA
    # ------------------------------
    render_list()

    title_size = 20 if is_mobile else 22

    # -----------------------------------------------------
    # ✅ RETORNO FINAL — SCROLL GLOBAL EN MÓVIL
    # -----------------------------------------------------
    if is_mobile:
        return ft.ListView(
            controls=[
                ft.Text("Gestión de Planteles", size=title_size, weight=ft.FontWeight.BOLD),
                add_section,
                info_txt,
                ft.Divider(),
                list_panel
            ],
            expand=True,
            spacing=12,
            padding=10
        )

    # ✅ Version web normal
    return ft.Column(
        [
            ft.Text("Gestión de Planteles", size=title_size, weight=ft.FontWeight.BOLD),
            add_section,
            info_txt,
            ft.Divider(),
            ft.Container(list_panel, expand=True, padding=ft.padding.only(top=10))
        ],
        expand=True,
        spacing=15
    )