from __future__ import annotations

import flet as ft
from api_client import ApiClient
from ui.components.cards import Card
from ui.components.inputs import TextField
from ui.components.buttons import Primary, Ghost, Danger, Icon, Tonal
import traceback # Importamos traceback

# Modelo simple
class Laboratorio:
    def __init__(self, data):
        self.id = data.get("id")
        self.nombre = data.get("nombre")
        self.ubicacion = data.get("ubicacion")
        self.capacidad = data.get("capacidad")
        self.plantel_id = data.get("plantel_id")


def LaboratoriosView(page: ft.Page, api: ApiClient):

    is_mobile = page.width < 600
    user_session = page.session.get("user_session") or {}
    is_admin = user_session.get("rol") == "admin"
    state = {"editing_lab_id": None}

    # --- MODIFICACIÓN 1: Carga Asíncrona ---
    # Definimos los 'caches' y contenedores vacíos primero
    planteles_cache = []
    
    # ========================================================================
    # FORM FIELDS (Definidos pero sin opciones)
    # ========================================================================
    nombre = TextField("Nombre")
    ubicacion = TextField("Ubicación")
    capacidad = TextField("Capacidad")

    nombre.col = {"sm": 12, "md": 6, "lg": 3}
    ubicacion.col = {"sm": 12, "md": 6, "lg": 3}
    capacidad.col = {"sm": 12, "md": 6, "lg": 2}

    # Las opciones se cargarán asíncronamente
    dd_plantel_add = ft.Dropdown(
        label="Plantel",
        options=[] 
    )
    dd_plantel_add.col = {"sm": 12, "md": 6, "lg": 2}

    info = ft.Text("")

    # --- MODIFICACIÓN 2: Corrección de Layout Móvil ---
    # Quitamos el scroll. El ListView padre se encargará de scrollear.
    list_panel = ft.Column(
        spacing=12,
        # scroll=ft.ScrollMode.ADAPTIVE <-- ELIMINADO
        # Añadimos un indicador de carga inicial
        controls=[
            ft.Row([ft.ProgressRing(), ft.Text("Cargando laboratorios...")], alignment=ft.MainAxisAlignment.CENTER)
        ]
    )
    # --- FIN MODIFICACIÓN 2 ---

    btn_save = Primary("Agregar", height=44)
    btn_cancel = Ghost("Cancelar", height=44, visible=False)

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
        # En lugar de solo render_list, llamamos a la carga completa
        # para asegurarnos de que los datos estén frescos.
        page.run_thread(load_initial_data)

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

    def render_list():
        # Esta función ahora SÓLO renderiza, no obtiene datos
        # Asume que 'planteles_cache' y 'labs_data' ya existen
        list_panel.controls.clear()

        # Obtenemos los laboratorios (esto sí puede ser síncrono
        # PORQUE esta función se llama desde un HILO)
        labs_data = api.get_laboratorios()
        
        # Construimos el mapa con los planteles ya cacheados
        planteles_map = {str(p["id"]): p["nombre"] for p in planteles_cache}

        if not isinstance(labs_data, list):
            list_panel.controls.append(ft.Text("Error obteniendo laboratorios."))
            if list_panel.page: list_panel.update()
            return

        if not labs_data:
            list_panel.controls.append(ft.Text("No hay laboratorios registrados."))
            if list_panel.page: list_panel.update()
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
        
        # Solo muestra botones si es admin
        admin_controls = [btns] if is_admin else []

        return Card(
            ft.Container(
                ft.Column([title, subtitle] + admin_controls, spacing=6),
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
    
    # Ocultar el formulario si no es admin
    form_card.visible = is_admin

    # ========================================================================
    # LAYOUT
    # ========================================================================
    if is_mobile:
        # El layout es un ListView que scrollea todo
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
        # El layout es una Columna con la lista expandida
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

    # --- MODIFICACIÓN 3: Carga Asíncrona de Datos ---
    # Esta es la nueva función que carga los datos en segundo plano
    def load_initial_data(e=None):
        nonlocal planteles_cache # Necesitamos modificar la variable externa
        
        try:
            planteles_data_async = api.get_planteles()

            if isinstance(planteles_data_async, list):
                planteles_cache = planteles_data_async
                
                # Preparamos las opciones para el dropdown
                plantel_options_async = [
                    ft.dropdown.Option(str(p["id"]), p["nombre"])
                    for p in planteles_cache
                ]
                dd_plantel_add.options = plantel_options_async
                
                # Actualizamos el dropdown en la UI
                if dd_plantel_add.page:
                    dd_plantel_add.update()
                
                # Ahora que tenemos los planteles, renderizamos la lista
                render_list()

            else:
                raise Exception(f"Error al cargar planteles: {planteles_data_async.get('error', 'Respuesta inválida')}")

        except Exception as e:
            print(f"CRITICAL LaboratoriosView (async): {e}")
            traceback.print_exc()
            list_panel.controls.clear()
            list_panel.controls.append(ft.Text(f"Error crítico al cargar datos: {e}", color=ft.Colors.ERROR))
            if list_panel.page:
                list_panel.update()

    # Le decimos a la página que ejecute la carga de datos en un hilo separado
    page.run_thread(load_initial_data)
    # --- FIN MODIFICACIÓN 3 ---

    return layout