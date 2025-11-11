import flet as ft
import re
from api_client import ApiClient
from ui.components.cards import Card
# --- Imports necesarios ---
from ui.components.inputs import TextField # Asumiendo que usas tu TextField personalizado
from ui.components.buttons import Primary, Ghost, Danger, Icon, Tonal # Para diálogos y botones

EMAIL_RX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def SettingsView(page: ft.Page, api: ApiClient):
    """
    Vista para que el usuario actualice su perfil/contraseña
    y para que el admin gestione usuarios, con feedback visual mejorado.
    Versión adaptada para móvil.
    """
    # --- INICIO DE LA CORRECCIÓN ---
    # 'user_session' ES el diccionario de datos del usuario.
    user_session = page.session.get("user_session") or {}
    me = user_session # <-- ¡Esta es la corrección!
    # --- FIN DE LA CORRECCIÓN ---
    
    is_admin = me.get("rol") == "admin"

    if not me:
        return ft.Container(
            content=ft.Text("Inicia sesión para ver esta página.", color="red"),
            padding=20, alignment=ft.alignment.center
        )

    # --- Diálogos ---
    # Usaremos alert_dialog SÓLO para Feedback (Éxito/Error)
    alert_dialog = ft.AlertDialog(modal=True)

    # --- Dialog Helper Functions ---
    def close_dialog(e=None):
        if page.dialog: # Comprobación de seguridad
            page.dialog.open = False
        page.update()

    def close_dialog_and_reload(e=None):
        if page.dialog:
            page.dialog.open = False
        page.update()
        page.go(page.route)

    def show_feedback(title: str, message: str, icon: str, icon_color: str, reload_on_close: bool = False):
        page.dialog = alert_dialog
        alert_dialog.title = ft.Row([ft.Icon(icon, color=icon_color), ft.Text(title)])
        alert_dialog.content = ft.Text(message)
        alert_dialog.actions[:] = [ft.TextButton("OK", on_click=close_dialog_and_reload if reload_on_close else close_dialog)]
        alert_dialog.open = True
        page.update()

    # -------------------------------------
    # --- Pestaña: Mi Perfil y Contraseña - VERSIÓN MÓVIL ---
    # -------------------------------------
    # Campos adaptados para móvil
    tf_nombre = TextField(
        label="Nombre", 
        value=me.get("nombre", ""), 
        col={"xs": 12, "sm": 12, "md": 6}
    )
    tf_user = TextField(
        label="Usuario", 
        value=me.get("user", ""), 
        col={"xs": 12, "sm": 12, "md": 6}
    )
    tf_correo = TextField(
        label="Correo", 
        value=me.get("correo", ""), 
        col={"xs": 12}
    )
    
    # Campos de contraseña responsivos
    tf_pwd_actual = TextField(
        label="Contraseña actual", 
        password=True, 
        col={"xs": 12, "sm": 12, "md": 4}
    )
    tf_pwd_actual.can_reveal_password = True
    tf_pwd_nueva = TextField(
        label="Nueva contraseña", 
        password=True, 
        col={"xs": 12, "sm": 12, "md": 4}
    )
    tf_pwd_nueva.can_reveal_password = True
    tf_pwd_conf = TextField(
        label="Confirmar nueva", 
        password=True, 
        col={"xs": 12, "sm": 12, "md": 4}
    )
    tf_pwd_conf.can_reveal_password = True
    
    pr_profile = ft.ProgressRing(width=18, height=18, stroke_width=2.5, visible=False)
    btn_save_profile = Primary("Guardar Perfil", on_click=lambda e: save_profile())
    pr_password = ft.ProgressRing(width=18, height=18, stroke_width=2.5, visible=False)
    btn_change_password = Primary("Actualizar Contraseña", on_click=lambda e: change_password())
    
    def save_profile():
        btn_save_profile.disabled = True
        pr_profile.visible = True
        page.update()
        nombre = tf_nombre.value.strip()
        user = tf_user.value.strip()
        correo = tf_correo.value.strip().lower()
        error_msg = None
        if not all([nombre, user, correo]): error_msg = ("Campos incompletos", "Por favor, completa nombre, usuario y correo.")
        elif not EMAIL_RX.match(correo): error_msg = ("Formato inválido", "El formato del correo electrónico no es válido.")
        if error_msg: show_feedback(error_msg[0], error_msg[1], ft.Icons.WARNING, ft.Colors.AMBER)
        else:
            updated_user = api.update_profile(nombre, user, correo)
            if updated_user:
                user_session["user"] = updated_user
                page.session.set("user_session", user_session)
                show_feedback("Éxito", "Tu perfil ha sido actualizado correctamente.", ft.Icons.CHECK_CIRCLE, ft.Colors.GREEN, reload_on_close=True)
            else: show_feedback("Error", "No se pudo actualizar. El usuario o correo puede que ya exista.", ft.Icons.ERROR, ft.Colors.RED)
        btn_save_profile.disabled = False
        pr_profile.visible = False
        page.update()
        
    def change_password():
        btn_change_password.disabled = True
        pr_password.visible = True
        page.update()
        cur, new, cfm = tf_pwd_actual.value, tf_pwd_nueva.value, tf_pwd_conf.value
        error_msg = None
        if not all([cur, new, cfm]): error_msg = ("Campos incompletos", "Por favor, completa todos los campos de contraseña.")
        elif new != cfm: error_msg = ("Error de coincidencia", "La nueva contraseña y su confirmación no coinciden.")
        elif len(new) < 6: error_msg = ("Contraseña débil", "La nueva contraseña debe tener al menos 6 caracteres.")
        if error_msg: show_feedback(error_msg[0], error_msg[1], ft.Icons.WARNING, ft.Colors.AMBER)
        else:
            result = api.change_password(cur, new)
            if result:
                tf_pwd_actual.value = ""; tf_pwd_nueva.value = ""; tf_pwd_conf.value = ""
                show_feedback("Éxito", "Tu contraseña ha sido actualizada.", ft.Icons.CHECK_CIRCLE, ft.Colors.GREEN)
            else: show_feedback("Error", "La contraseña actual no es correcta.", ft.Icons.ERROR, ft.Colors.RED)
        btn_change_password.disabled = False
        pr_password.visible = False
        page.update()

    # Layout responsivo para perfil
    perfil_card = Card(
        ft.ResponsiveRow([
            ft.Column([
                ft.Text("Mi Perfil", size=16, weight=ft.FontWeight.W_600),
                tf_nombre,
                tf_user,
                tf_correo,
                ft.Container(
                    ft.Row([pr_profile, btn_save_profile], 
                          alignment=ft.MainAxisAlignment.END, 
                          spacing=10),
                    padding=ft.padding.only(top=10)
                )
            ], col={"xs": 12})
        ], spacing=12, run_spacing=12)
    )

    # Layout responsivo para contraseña
    pass_card = Card(
        ft.ResponsiveRow([
            ft.Column([
                ft.Text("Cambiar Contraseña", size=16, weight=ft.FontWeight.W_600),
                tf_pwd_actual,
                tf_pwd_nueva,
                tf_pwd_conf,
                ft.Container(
                    ft.Row([pr_password, btn_change_password], 
                          alignment=ft.MainAxisAlignment.END, 
                          spacing=10),
                    padding=ft.padding.only(top=10)
                )
            ], col={"xs": 12})
        ], spacing=12, run_spacing=12)
    )
    
    personal_settings_content = ft.Column([perfil_card, pass_card], spacing=20)

    # -------------------------------------
    # --- Pestaña: Administrar Usuarios (Admin Only) - VERSIÓN MÓVIL ---
    # -------------------------------------
    admin_search_tf = TextField(
        label="Buscar por nombre, usuario o correo", 
        col={"xs": 12, "sm": 8, "md": 6}
    )
    admin_search_tf.prefix_icon = ft.Icons.SEARCH
    
    admin_role_dd = ft.Dropdown(
        label="Filtrar por Rol",
        options=[
            ft.dropdown.Option("", "Todos"),
            ft.dropdown.Option("admin", "Admin"),
            ft.dropdown.Option("docente", "Docente"),
            ft.dropdown.Option("estudiante", "Estudiante"),
        ],
        col={"xs": 12, "sm": 4, "md": 3}
    )
    
    admin_users_list = ft.ListView(spacing=10, expand=True)

    def render_user_list():
        admin_users_list.controls.clear()
        query = admin_search_tf.value or ""
        role = admin_role_dd.value or ""
        users = api.get_users(q=query, rol=role) or []
        if not users: 
            admin_users_list.controls.append(
                ft.Container(
                    ft.Text("No se encontraron usuarios.", text_align=ft.TextAlign.CENTER),
                    padding=20,
                    alignment=ft.alignment.center
                )
            )
        else:
            for user in users:
                if user.get('id') != me.get('id'): 
                    admin_users_list.controls.append(user_tile(user))
        if admin_users_list.page: admin_users_list.update()

    # --- MODIFICACIÓN: 'user_tile' adaptada para móvil ---
    def user_tile(u: dict):
        user_id = u.get('id')

        # --- Controles de edición (específicos para esta tarjeta) ---
        tf_nombre_inline = TextField(label="Nombre", value=u.get('nombre'), col={"xs": 12})
        tf_user_inline = TextField(label="Usuario", value=u.get('user'), col={"xs": 12})
        tf_correo_inline = TextField(label="Correo", value=u.get('correo'), col={"xs": 12})
        rol_inline_dd = ft.Dropdown(
            label="Rol",
            value=u.get('rol'),
            options=[
                ft.dropdown.Option("admin", "Admin"),
                ft.dropdown.Option("docente", "Docente"),
                ft.dropdown.Option("estudiante", "Estudiante"),
            ],
            col={"xs": 12}
        )
        pr_inline = ft.ProgressRing(width=16, height=16, stroke_width=2, visible=False)
        save_btn_inline = Primary("Guardar", on_click=lambda e: save_inline_edit(e))
        cancel_btn_inline = Tonal("Cancelar", on_click=lambda e: cancel_inline_edit(e))

        # --- Controles de eliminación (específicos para esta tarjeta) ---
        pr_delete_inline = ft.ProgressRing(width=16, height=16, stroke_width=2, visible=False)
        confirm_btn_delete = Danger("Sí, Eliminar", on_click=lambda e: confirm_inline_delete(e))
        cancel_btn_delete = Tonal("Cancelar", on_click=lambda e: cancel_inline_delete(e))

        # --- Contenedor del formulario de edición (oculto) ---
        edit_form_container = ft.ResponsiveRow(
            controls=[
                ft.Column([
                    ft.Divider(height=10),
                    tf_nombre_inline,
                    tf_user_inline,
                    tf_correo_inline,
                    rol_inline_dd,
                    ft.Container(
                        ft.Row(
                            [pr_inline, cancel_btn_inline, save_btn_inline], 
                            alignment=ft.MainAxisAlignment.END,
                            spacing=10,
                            wrap=True
                        ),
                        padding=ft.padding.only(top=10)
                    )
                ], col={"xs": 12})
            ],
            visible=False,
            opacity=0,
            animate_opacity=200,
            animate_size=200,
            spacing=10,
            run_spacing=10
        )

        # --- Contenedor de confirmación de borrado (oculto) ---
        delete_confirm_container = ft.Container(
            content=ft.Column(
                [
                    ft.Text("¿Seguro que quieres eliminar a este usuario? Esta acción no se puede deshacer.",
                            style=ft.TextThemeStyle.BODY_MEDIUM, 
                            color=ft.Colors.ERROR, 
                            weight=ft.FontWeight.BOLD),
                    ft.Row(
                        [pr_delete_inline, cancel_btn_delete, confirm_btn_delete],
                        alignment=ft.MainAxisAlignment.END,
                        spacing=10,
                        wrap=True
                    )
                ],
                spacing=10
            ),
            padding=ft.padding.only(top=10),
            visible=False,
            opacity=0,
            animate_opacity=200,
            animate_size=200,
            border=ft.border.only(top=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT))
        )
        
        # --- Fila de información (la que se ve siempre) - Adaptada para móvil ---
        info_column = ft.Column(
            [
                ft.Text(f"{u.get('nombre', '')}", 
                       weight=ft.FontWeight.BOLD,
                       size=16),
                ft.Text(f"Usuario: {u.get('user', '')}", size=14),
                ft.Text(f"Correo: {u.get('correo', '')}", size=14),
                ft.Container(
                    ft.Chip(
                        label=ft.Text(f"Rol: {u.get('rol', '').capitalize()}"),
                        padding=5
                    ),
                    padding=ft.padding.only(top=5)
                )
            ], 
            expand=True, 
            spacing=4
        )
        
        edit_btn_inline = ft.IconButton(
            ft.Icons.EDIT_OUTLINED,
            tooltip="Editar Usuario",
            on_click=lambda e: toggle_edit(e),
            icon_size=20
        )
        delete_btn_inline = ft.IconButton(
            ft.Icons.DELETE_OUTLINE,
            tooltip="Eliminar Usuario",
            icon_color=ft.Colors.ERROR,
            on_click=lambda e: toggle_delete(e),
            icon_size=20
        )
        
        # Layout responsivo para la fila de información
        info_row = ft.ResponsiveRow([
            ft.Column([info_column], col={"xs": 8, "sm": 9}, expand=True),
            ft.Column([
                ft.Row([edit_btn_inline, delete_btn_inline], spacing=5)
            ], col={"xs": 4, "sm": 3}, 
               horizontal_alignment=ft.CrossAxisAlignment.END)
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER)

        # --- Contenedor principal de la tarjeta ---
        card_content = ft.Column(
            [
                info_row, 
                edit_form_container,
                delete_confirm_container
            ],
            spacing=0
        )

        # --- Funciones de Lógica Interna (Closures) ---
        def toggle_edit(e):
            """Muestra/oculta el formulario de edición. Oculta el de borrado."""
            was_visible = edit_form_container.visible
            # Oculta ambos
            edit_form_container.visible = False
            edit_form_container.opacity = 0
            delete_confirm_container.visible = False
            delete_confirm_container.opacity = 0

            if not was_visible:
                # Muestra el de edición
                edit_form_container.visible = True
                edit_form_container.opacity = 1
                # Resetea los campos a los valores originales
                tf_nombre_inline.value = u.get('nombre')
                tf_user_inline.value = u.get('user')
                tf_correo_inline.value = u.get('correo')
                rol_inline_dd.value = u.get('rol')
            card_content.update()

        def cancel_inline_edit(e):
            """Llama a toggle_edit para ocultar y resetear."""
            toggle_edit(e)

        def save_inline_edit(e):
            """Lógica de guardado."""
            pr_inline.visible = True
            save_btn_inline.disabled = True
            cancel_btn_inline.disabled = True
            card_content.update()

            nombre = tf_nombre_inline.value.strip()
            user = tf_user_inline.value.strip()
            correo = tf_correo_inline.value.strip().lower()
            rol = rol_inline_dd.value

            error_msg = None
            if not all([user_id, nombre, user, correo, rol]): error_msg = ("Campos Incompletos", "Todos los campos son obligatorios.")
            elif not EMAIL_RX.match(correo): error_msg = ("Formato Inválido", "El formato del correo no es válido.")

            if error_msg:
                show_feedback(error_msg[0], error_msg[1], ft.Icons.WARNING, ft.Colors.AMBER)
                pr_inline.visible = False
                save_btn_inline.disabled = False
                cancel_btn_inline.disabled = False
                card_content.update()
            else:
                try:
                    update_data = {"nombre": nombre, "user": user, "correo": correo, "rol": rol}
                    updated_user = api.update_user_by_admin(user_id, update_data)
                    
                    if updated_user:
                        edit_form_container.visible = False # Oculta el formulario
                        show_feedback("Usuario Actualizado", f"Los datos de '{nombre}' se guardaron.", ft.Icons.CHECK_CIRCLE, ft.Colors.GREEN)
                        render_user_list() # Recarga toda la lista de usuarios
                    else:
                        show_feedback("Error", "No se pudo actualizar. El usuario o correo puede ya existir.", ft.Icons.ERROR, ft.Colors.RED)
                        pr_inline.visible = False
                        save_btn_inline.disabled = False
                        cancel_btn_inline.disabled = False
                        card_content.update()
                except Exception as ex:
                    show_feedback("Error Inesperado", str(ex), ft.Icons.ERROR, ft.Colors.RED)
                    pr_inline.visible = False
                    save_btn_inline.disabled = False
                    cancel_btn_inline.disabled = False
                    card_content.update()

        def toggle_delete(e):
            """Muestra/oculta la confirmación de borrado. Oculta la de edición."""
            was_visible = delete_confirm_container.visible
            # Oculta ambos
            edit_form_container.visible = False
            edit_form_container.opacity = 0
            delete_confirm_container.visible = False
            delete_confirm_container.opacity = 0

            if not was_visible:
                # Muestra el de borrado
                delete_confirm_container.visible = True
                delete_confirm_container.opacity = 1
            card_content.update()
        
        def cancel_inline_delete(e):
            """Llama a toggle_delete para ocultar."""
            toggle_delete(e)

        def confirm_inline_delete(e):
            """Lógica de borrado."""
            pr_delete_inline.visible = True
            confirm_btn_delete.disabled = True
            cancel_btn_delete.disabled = True
            card_content.update()
            
            try:
                result = api.delete_user(user_id)
                if result:
                    # No necesitamos ocultar el form, render_user_list() lo elimina
                    show_feedback("Usuario Eliminado", f"El usuario '{u.get('nombre')}' ha sido eliminado.", ft.Icons.CHECK_CIRCLE, ft.Colors.GREEN)
                    render_user_list() # Recarga toda la lista
                else:
                    show_feedback("Error", "No se pudo eliminar el usuario. Puede tener préstamos/reservas activas.", ft.Icons.ERROR, ft.Colors.RED)
                    pr_delete_inline.visible = False
                    confirm_btn_delete.disabled = False
                    cancel_btn_delete.disabled = False
                    card_content.update()
            except Exception as ex:
                show_feedback("Error Inesperado", str(ex), ft.Icons.ERROR, ft.Colors.RED)
                pr_delete_inline.visible = False
                confirm_btn_delete.disabled = False
                cancel_btn_delete.disabled = False
                card_content.update()

        return ft.Card(
            content=ft.Container(
                content=card_content,
                padding=16,
                margin=ft.margin.symmetric(vertical=4)
            ),
            elevation=2.0
        )

    def handle_search_change(e): render_user_list()
    admin_search_tf.on_change = handle_search_change
    admin_role_dd.on_change = lambda e: render_user_list()

    # --- Admin Tab Content - Versión Móvil ---
    admin_settings_content = ft.Column(
        [
            ft.ResponsiveRow([
                ft.Column([admin_search_tf], col={"xs": 12, "sm": 8}),
                ft.Column([admin_role_dd], col={"xs": 12, "sm": 4})
            ], spacing=10, run_spacing=10),
            ft.Divider(height=20),
            admin_users_list
        ],
        expand=True
    )

    # -------------------------------------
    # --- Layout General con Tabs - Versión Móvil ---
    # -------------------------------------
    tabs_list = [
        ft.Tab(
            text="Mi Cuenta",
            icon=ft.Icons.PERSON_OUTLINE,
            content=ft.Container(
                ft.Column([
                    personal_settings_content
                ], scroll=ft.ScrollMode.ADAPTIVE),
                padding=ft.padding.symmetric(vertical=10, horizontal=5)
            )
        ),
    ]

    if is_admin:
        tabs_list.append(
            ft.Tab(
                text="Administrar Usuarios",
                icon=ft.Icons.PEOPLE_ALT_OUTLINED,
                content=ft.Container(
                    ft.Column([
                        admin_settings_content
                    ], scroll=ft.ScrollMode.ADAPTIVE),
                    padding=ft.padding.symmetric(vertical=10, horizontal=5)
                )
            )
        )
        render_user_list()

    tabs = ft.Tabs(
        selected_index=0, 
        tabs=tabs_list, 
        expand=1,
        scrollable=True  # Tabs scrollables en móvil
    )

    return ft.Container(
        ft.Column(
            [
                ft.Container(
                    ft.Text("Ajustes", size=22, weight=ft.FontWeight.BOLD),
                    padding=ft.padding.symmetric(horizontal=10, vertical=5),
                    alignment=ft.alignment.center
                ),
                tabs,
            ],
            expand=True,
            spacing=15,
        ),
        padding=ft.padding.symmetric(horizontal=5)
    )