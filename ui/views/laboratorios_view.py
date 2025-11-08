import flet as ft
from api_client import ApiClient
from ui.components.cards import Card
from ui.components.inputs import TextField
from ui.components.buttons import Primary, Ghost, Danger, Icon, Tonal


# Modelo simple
class Laboratorio:
    def __init__(self, data):
        self.id = data.get("id")
        self.nombre = data.get("nombre")
        self.ubicacion = data.get("ubicacion")
        self.capacidad = data.get("capacidad")
        self.plantel_id = data.get("plantel_id")


def LaboratoriosView(page: ft.Page, api: ApiClient):

    # Detectar móvil
    is_mobile = page.width < 600

    # Autorización
    user_session = page.session.get("user_session") or {}
    is_admin = user_session.get("rol") == "admin"

    # Estado local
    state = {"editing_lab_id": None}

    # ========================================================================
    # FORM FIELDS
    # ========================================================================
    nombre = TextField("Nombre")
    ubicacion = TextField("Ubicación")
    capacidad = TextField("Capacidad")

    nombre.col = {"sm": 12, "md": 6, "lg": 3}
    ubicacion.col = {"sm": 12, "md": 6, "lg": 3}
    capacidad.col = {"sm": 12, "md": 6, "lg": 2}

    planteles_data = api.get_planteles()
    plantel_options = []

    if isinstance(planteles_data, list):
        plantel_options = [
            ft.dropdown.Option(str(p["id"]), p["nombre"])
            for p in planteles_data
        ]

    dd_plantel_add = ft.Dropdown(
        label="Plantel",
        options=plantel_options
    )
    dd_plantel_add.col = {"sm": 12, "md": 6, "lg": 2}

    info = ft.Text("")

    list_panel = ft.Column(
        spacing=12,
        scroll=ft.ScrollMode.ADAPTIVE
    )

    # ========================================================================
    #  ✅ BOTONES GLOBALES (un solo btn_save y btn_cancel)
    # ========================================================================
    btn_save = Primary("Agregar", height=44)
    btn_cancel = Ghost("Cancelar", height=44, visible=False)

    # ========================================================================
    #  DIÁLOGO ELIMINAR
    # ========================================================================
    def confirm_delete_click(e):
        lab_id = page.dialog.data
        page.dialog.open = False
        page.update()

        if lab_id:
            result = api.delete_laboratorio(lab_id)

            if result and result.get("success"):
                show_info_and_reload("Laboratorio eliminado.")
            else:
                show_info_and_reload("No se pudo eliminar.")
    
    delete_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirmar eliminación"),
        content=ft.Text("¿Eliminar laboratorio? Esta acción no puede deshacerse."),
        actions=[
            Tonal("Cancelar", on_click=lambda e: (setattr(page.dialog, "open", False), page.update())),
            Danger("Eliminar", on_click=confirm_delete_click),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    if delete_dialog not in page.overlay:
        page.overlay.append(delete_dialog)

    # ========================================================================
    #     MÉTODOS
    # ========================================================================
    def clear_form(e=None):
        state["editing_lab_id"] = None
        nombre.value = ""
        ubicacion.value = ""
        capacidad.value = ""
        dd_plantel_add.value = None

        btn_save.text = "Agregar"
        btn_cancel.visible = False
        btn_cancel.update()

        form_card.update()

    def edit_lab_click(lab: Laboratorio):
        state["editing_lab_id"] = lab.id

        nombre.value = lab.nombre
        ubicacion.value = lab.ubicacion
        capacidad.value = str(lab.capacidad)
        dd_plantel_add.value = str(lab.plantel_id)

        btn_save.text = "Actualizar"
        btn_cancel.visible = True
        btn_cancel.update()

        info.value = f"Editando: {lab.nombre}"
        info.update()
        form_card.update()

    def delete_lab_click(lab: Laboratorio):
        page.dialog = delete_dialog
        page.dialog.data = lab.id
        page.dialog.open = True
        page.update()

    def show_info_and_reload(msg=None):
        if msg:
            info.value = msg
            info.update()

        clear_form()
        render_list()

    def save_lab(e):
        if not is_admin:
            show_info_and_reload("Acción no permitida.")
            return

        if not all([nombre.value, capacidad.value, dd_plantel_add.value]):
            show_info_and_reload("Completa los campos obligatorios.")
            return

        try:
            payload = {
                "nombre": nombre.value.strip(),
                "ubicacion": (ubicacion.value or "").strip(),
                "capacidad": int(capacidad.value),
                "plantel_id": int(dd_plantel_add.value),
            }

            lab_id = state["editing_lab_id"]

            if lab_id is None:
                result = api.create_laboratorio(payload)
                msg = "Laboratorio creado"
            else:
                result = api.update_laboratorio(lab_id, payload)
                msg = "Laboratorio actualizado"

            if result and "error" not in result:
                show_info_and_reload(msg)
            else:
                show_info_and_reload(f"Error: {result.get('error', 'Error desconocido')}")

        except Exception as ex:
            show_info_and_reload(f"Error: {ex}")

    btn_save.on_click = save_lab
    btn_cancel.on_click = clear_form

    # ========================================================================
    #     LISTA
    # ========================================================================
    def render_list():
        list_panel.controls.clear()

        planteles_map = {str(p["id"]): p["nombre"] for p in planteles_data}

        labs_data = api.get_laboratorios()

        if not isinstance(labs_data, list):
            list_panel.controls.append(ft.Text("Error obteniendo laboratorios."))
            return

        if not labs_data:
            list_panel.controls.append(ft.Text("No hay laboratorios registrados."))
            return

        for ld in labs_data:
            lab = Laboratorio(ld)
            plantel_nombre = planteles_map.get(str(lab.plantel_id), "N/A")

            card = (
                laboratorio_card_mobile(lab, plantel_nombre)
                if is_mobile
                else laboratorio_card_web(lab, plantel_nombre)
            )

            list_panel.controls.append(card)

        if list_panel.page:
            list_panel.update()

    # ========================================================================
    # CARD WEB
    # ========================================================================
    def laboratorio_card_web(lab, plantel_nombre):

        title = ft.Text(lab.nombre, size=16, weight=ft.FontWeight.W_600)
        subtitle = ft.Text(
            f"Ubicación: {lab.ubicacion or 'N/A'} · Capacidad: {lab.capacidad} · Plantel: {plantel_nombre}",
            size=12,
            opacity=0.85,
        )

        actions = ft.Row(spacing=4)

        if is_admin:
            actions.controls.extend([
                Icon(ft.Icons.EDIT, on_click=lambda e: edit_lab_click(lab)),
                Icon(ft.Icons.DELETE, icon_color=ft.Colors.ERROR,
                     on_click=lambda e: delete_lab_click(lab)),
            ])

        return Card(
            ft.Row([ft.Column([title, subtitle], expand=True), actions]),
            padding=14,
        )

    # ========================================================================
    # CARD MÓVIL
    # ========================================================================
    def laboratorio_card_mobile(lab, plantel_nombre):

        title = ft.Text(lab.nombre, size=15, weight=ft.FontWeight.W_600)
        subtitle = ft.Text(
            f"Ubicación: {lab.ubicacion}\nCapacidad: {lab.capacidad}\nPlantel: {plantel_nombre}",
            size=11, opacity=0.85,
        )

        btns = ft.Row(
            [
                Primary("Editar", height=34, expand=True,
                        on_click=lambda e: edit_lab_click(lab)),
                Danger("Eliminar", height=34, expand=True,
                       on_click=lambda e: delete_lab_click(lab)),
            ],
            spacing=6,
        )

        return Card(
            ft.Container(
                ft.Column([title, subtitle, btns], spacing=6),
                border_radius=10
            ),
            padding=8
        )

    # ========================================================================
    # FORMULARIO FINAL (MÓVIL / WEB)
    # ========================================================================
    if is_mobile:
        nombre.height = 45
        ubicacion.height = 45
        capacidad.height = 45
        dd_plantel_add.height = 45
        btn_save.height = 40
        btn_cancel.height = 40

        form_card = Card(
            ft.Container(
                ft.Column(
                    [
                        ft.Text("Laboratorio", size=14, weight=ft.FontWeight.W_600),
                        nombre,
                        ubicacion,
                        capacidad,
                        dd_plantel_add,
                        btn_save,
                        btn_cancel,
                    ],
                    spacing=6,
                ),
                border_radius=10,
            ),
            padding=10,
        )

    else:
        form_card = Card(
            ft.ResponsiveRow(
                [
                    nombre,
                    ubicacion,
                    capacidad,
                    dd_plantel_add,
                    ft.Row([btn_save, btn_cancel]),
                ],
                vertical_alignment=ft.CrossAxisAlignment.END,
            ),
            padding=14,
        )

    # ========================================================================
    # LAYOUT
    # ========================================================================
    if is_mobile:
        layout = ft.ListView(
            controls=[
                ft.Text("Laboratorios", size=20, weight=ft.FontWeight.BOLD),
                form_card,
                info,
                ft.Divider(),
                list_panel,
            ],
            expand=True,
            spacing=12,
            padding=10,
        )
    else:
        layout = ft.Column(
            [
                ft.Text("Laboratorios", size=20, weight=ft.FontWeight.BOLD),
                form_card,
                info,
                ft.Divider(),
                ft.Container(list_panel, expand=True, padding=ft.padding.only(top=10)),
            ],
            expand=True,
            spacing=10,
        )

    # ✅ ya se puede renderizar la lista
    render_list()

    return layout
