import flet as ft
from api_client import ApiClient
from ui.components.cards import Card
from ui.components.inputs import TextField
from ui.components.buttons import Primary, Ghost, Danger, Icon, Tonal

# Objeto simple para manejar datos de la API
class Laboratorio:
    def __init__(self, data):
        self.id = data.get("id")
        self.nombre = data.get("nombre")
        self.ubicacion = data.get("ubicacion")
        self.capacidad = data.get("capacidad")
        self.plantel_id = data.get("plantel_id")

def LaboratoriosView(page: ft.Page, api: ApiClient):

    # Detectar MÓVIL REAL
    is_mobile = page.width < 600

    # Autorización
    user_session = page.session.get("user_session") or {}
    u = user_session
    is_admin = u.get("rol") == "admin"

    # Estado
    state = {"editing_lab_id": None}

    # ===========================
    # FORM FIELDS WEB
    # ===========================
    nombre = TextField("Nombre")
    nombre.col = {"sm": 12, "md": 6, "lg": 3}

    ubicacion = TextField("Ubicación")
    ubicacion.col = {"sm": 12, "md": 6, "lg": 3}

    capacidad = TextField("Capacidad")
    capacidad.col = {"sm": 12, "md": 6, "lg": 2}

    # Planteles
    plantel_options = []
    planteles_data = api.get_planteles()
    if isinstance(planteles_data, list):
        plantel_options = [
            ft.dropdown.Option(str(p["id"]), p["nombre"]) for p in planteles_data
        ]

    dd_plantel_add = ft.Dropdown(label="Plantel", options=plantel_options)
    dd_plantel_add.col = {"sm": 12, "md": 6, "lg": 2}

    info = ft.Text("")
    list_panel = ft.Column(spacing=12, scroll=ft.ScrollMode.ADAPTIVE)

    # ===========================
    # DIÁLOGO BORRAR
    # ===========================
    def confirm_delete_click(e):
        lab_id_to_delete = page.dialog.data
        page.dialog.open = False
        page.update()

        if lab_id_to_delete:
            result = api.delete_laboratorio(lab_id_to_delete)
            if result and result.get("success"):
                show_info_and_reload("Laboratorio eliminado.")
            else:
                show_info_and_reload("Error al eliminar.")

    delete_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirmar eliminación"),
        content=ft.Text("¿Eliminar laboratorio?"),
        actions=[
            Tonal("Cancelar", on_click=lambda e: (setattr(page.dialog, "open", False), page.update())),
            Danger("Eliminar", on_click=confirm_delete_click),
        ],
    )
    if delete_dialog not in page.overlay:
        page.overlay.append(delete_dialog)

    # ===========================
    # MÉTODOS
    # ===========================
    def clear_form(e=None):
        state["editing_lab_id"] = None
        nombre.value = ""
        ubicacion.value = ""
        capacidad.value = ""
        dd_plantel_add.value = None
        btn_save.text = "Agregar"
        btn_cancel.visible = False
        form_card.content.update()

    def edit_lab_click(lab: Laboratorio):
        state["editing_lab_id"] = lab.id
        nombre.value = lab.nombre
        ubicacion.value = lab.ubicacion
        capacidad.value = str(lab.capacidad)
        dd_plantel_add.value = str(lab.plantel_id)
        btn_save.text = "Actualizar"
        btn_cancel.visible = True
        form_card.content.update()
        info.value = f"Editando: {lab.nombre}"
        info.update()

    def delete_lab_click(lab: Laboratorio):
        page.dialog = delete_dialog
        page.dialog.data = lab.id
        page.dialog.open = True
        page.update()

    def show_info_and_reload(msg: str | None = None):
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
            show_info_and_reload("Completa nombre, capacidad y plantel.")
            return

        try:
            lab_id = state["editing_lab_id"]
            payload = {
                "nombre": nombre.value.strip(),
                "ubicacion": (ubicacion.value or "").strip(),
                "capacidad": int(capacidad.value),
                "plantel_id": int(dd_plantel_add.value),
            }

            if lab_id is None:
                result = api.create_laboratorio(payload)
                msg = "Laboratorio creado"
            else:
                result = api.update_laboratorio(lab_id, payload)
                msg = "Laboratorio actualizado"

            if result and "error" not in result:
                show_info_and_reload(msg)
            else:
                show_info_and_reload("Error al guardar.")
        except Exception as ex:
            show_info_and_reload(f"Error: {ex}")

    # ===========================
    # RENDER LIST
    # ===========================
    def render_list():
        list_panel.controls.clear()

        planteles_map = {str(p["id"]): p["nombre"] for p in planteles_data}

        labs_data = api.get_laboratorios()
        if not isinstance(labs_data, list):
            list_panel.controls.append(ft.Text("Error cargando laboratorios."))
            return

        if not labs_data:
            list_panel.controls.append(ft.Text("No hay laboratorios registrados."))
            return

        for ld in labs_data:
            lab = Laboratorio(ld)
            plantel_nombre = planteles_map.get(str(lab.plantel_id), "N/A")

            if is_mobile:
                card = laboratorio_card_mobile(lab, plantel_nombre)
            else:
                card = laboratorio_card_web(lab, plantel_nombre)

            list_panel.controls.append(card)

        list_panel.update()

    # ===========================
    # CARD WEB (normal)
    # ===========================
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
                Icon(ft.Icons.EDIT, tooltip="Editar", on_click=lambda e: edit_lab_click(lab)),
                Icon(ft.Icons.DELETE, tooltip="Eliminar", on_click=lambda e: delete_lab_click(lab), icon_color=ft.Colors.ERROR),
            ])

        header = ft.Row(
            [
                ft.Column([title, subtitle], expand=True),
                actions,
            ]
        )

        return Card(header, padding=14)

    # ===========================
    # CARD MÓVIL (compacta)
    # ===========================
    def laboratorio_card_mobile(lab, plantel_nombre):

        title = ft.Text(lab.nombre, size=15, weight=ft.FontWeight.W_600)
        subtitle = ft.Text(
            f"Ubicación: {lab.ubicacion or 'N/A'}\nCapacidad: {lab.capacidad}\nPlantel: {plantel_nombre}",
            size=11,
            opacity=0.85,
        )

        btns = ft.Row(
            [
                Primary("Editar", height=34, expand=True, on_click=lambda e: edit_lab_click(lab)),
                Danger("Eliminar", height=34, expand=True, on_click=lambda e: delete_lab_click(lab)),
            ],
            spacing=6,
        )

        content = ft.Column([title, subtitle, btns], spacing=6)

        return Card(
            ft.Container(content, border_radius=10),
            padding=8
        )

    # ===========================
    # FORMULARIO WEB Y MÓVIL
    # ===========================
    if is_mobile:
        # Campos móviles compactos
        nombre_m = TextField("Nombre", height=45)
        ubicacion_m = TextField("Ubicación", height=45)
        capacidad_m = TextField("Capacidad", height=45)

        # Vincular valores
        nombre = nombre_m
        ubicacion = ubicacion_m
        capacidad = capacidad_m
        dd_plantel_add.height = 45

        form_card = Card(
            ft.Container(
                ft.Column(
                    [
                        ft.Text("Agregar / Editar Laboratorio", size=14, weight=ft.FontWeight.W_600),
                        nombre,
                        ubicacion,
                        capacidad,
                        dd_plantel_add,
                        Primary("Agregar", height=40, on_click=save_lab),
                        Ghost("Cancelar", height=40, on_click=clear_form, visible=False),
                    ],
                    spacing=6
                ),
                border_radius=10,
            ),
            padding=10
        )

    else:
        btn_save = Primary("Agregar", on_click=save_lab, height=44)
        btn_cancel = Ghost("Cancelar", on_click=clear_form, height=44)
        btn_cancel.visible = False

        form_controls = ft.ResponsiveRow(
            [
                nombre,
                ubicacion,
                capacidad,
                dd_plantel_add,
                ft.Row([btn_save, btn_cancel])
            ],
            vertical_alignment=ft.CrossAxisAlignment.END,
        )

        form_card = Card(form_controls, padding=14)

    # ===========================
    # Cargar lista
    # ===========================
    render_list()

    # ===========================
    # RETORNO FINAL
    # ===========================
    if is_mobile:
        # ✅ Scroll completo para evitar que el teclado tape contenido
        return ft.ListView(
            controls=[
                ft.Text("Laboratorios", size=20, weight=ft.FontWeight.BOLD),
                form_card,
                info,
                ft.Divider(),
                list_panel,
            ],
            expand=True,
            spacing=12,
            padding=10
        )

    # ✅ Web normal
    return ft.Column(
        [
            ft.Text("Laboratorios", size=20, weight=ft.FontWeight.BOLD),
            form_card,
            info,
            ft.Divider(),
            ft.Container(list_panel, expand=True, padding=ft.padding.only(top=10)),
        ],
        expand=True,
        spacing=10
    )
