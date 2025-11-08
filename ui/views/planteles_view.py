import flet as ft
from api_client import ApiClient
from ui.components.cards import Card
# Asumo que tienes un botón 'Primary'
from ui.components.buttons import Primary 

def PlantelesView(page: ft.Page, api: ApiClient):

    # --- Controles del Formulario ---
    nombre_field = ft.TextField(label="Nombre", expand=False) # 'expand' se maneja por 'col'
    direccion_field = ft.TextField(label="Dirección", expand=False)
    
    # Contenedor para la lista de planteles
    lista_planteles_col = ft.Column(spacing=10)
    
    # --- Lógica de API (A REEMPLAZAR POR LA TUYA) ---
    
    def cargar_planteles():
        """
        Esta función debe cargar los planteles desde tu API
        y construir las tarjetas.
        """
        print("Cargando planteles...")
        lista_planteles_col.controls.clear()
        
        # --- INICIO: EJEMPLO (BORRA ESTO Y USA TU API) ---
        # Simulación de datos de tu API
        try:
            # Descomenta la siguiente línea cuando tengas tu API
            # planteles_data = api.get_planteles()
            
            # Datos de ejemplo basados en tu captura
            planteles_data = [
                {"id": 1, "nombre": "UNE (CENTRO)", "direccion": "Av. Teónimos 10, San Juan de Ocotán, 45010 Guadalajara, Jal."},
                {"id": 2, "nombre": "UNE (TLAJOMULCO)", "direccion": "Av. Adolfo López Mateos Sur 10100, Los Gavilanes, 45645 Los Gavilanes, Jal."},
            ]
            
            if not planteles_data:
                lista_planteles_col.controls.append(ft.Text("No hay planteles registrados."))
            else:
                for plantel in planteles_data:
                    lista_planteles_col.controls.append(
                        build_plantel_card(plantel)
                    )
        except Exception as e:
            print(f"Error cargando planteles: {e}")
            lista_planteles_col.controls.append(
                ft.Text(f"Error al cargar planteles: {e}", color=ft.Colors.ERROR)
            )
        # --- FIN: EJEMPLO ---
            
        page.update()

    def agregar_plantel(e):
        """
        Esta función debe tomar los datos del formulario
        y enviarlos a la API para crear uno nuevo.
        """
        nombre = nombre_field.value
        direccion = direccion_field.value
        
        if not nombre or not direccion:
            page.snack_bar = ft.SnackBar(ft.Text("Completa nombre y dirección."), bgcolor=ft.Colors.ERROR)
            page.snack_bar.open = True
            page.update()
            return
            
        print(f"Agregando plantel: {nombre}, {direccion}")
        
        # --- INICIO: LÓGICA DE API (CONECTA LA TUYA) ---
        # try:
        #   api.create_plantel({"nombre": nombre, "direccion": direccion})
        #   nombre_field.value = ""
        #   direccion_field.value = ""
        #   page.snack_bar = ft.SnackBar(ft.Text("Plantel agregado con éxito."))
        #   page.snack_bar.open = True
        #   cargar_planteles() # Recarga la lista
        # except Exception as e:
        #   page.snack_bar = ft.SnackBar(ft.Text(f"Error: {e}"), bgcolor=ft.Colors.ERROR)
        #   page.snack_bar.open = True
        #   page.update()
        # --- FIN: LÓGICA DE API ---
        
        # Simulación de éxito (BORRA ESTO)
        nombre_field.value = ""
        direccion_field.value = ""
        page.snack_bar = ft.SnackBar(ft.Text("Plantel agregado (simulación)."))
        page.snack_bar.open = True
        cargar_planteles() # Recarga la lista
        

    def editar_plantel(plantel: dict):
        # Aquí iría tu lógica para abrir un modal o cambiar el formulario a modo "editar"
        print(f"Editando plantel {plantel.get('id')}")
        page.snack_bar = ft.SnackBar(ft.Text(f"Editando {plantel.get('nombre')}..."))
        page.snack_bar.open = True
        page.update()

    def eliminar_plantel(plantel: dict):
        # Aquí iría tu lógica para confirmar y eliminar
        print(f"Eliminando plantel {plantel.get('id')}")
        page.snack_bar = ft.SnackBar(ft.Text(f"Eliminando {plantel.get('nombre')}..."))
        page.snack_bar.open = True
        page.update()
        # Después de eliminar, deberías llamar a cargar_planteles()


    # --- Constructores de UI ---
    
    def build_form() -> ft.ResponsiveRow:
        """
        Construye el formulario responsivo.
        """
        return ft.ResponsiveRow(
            controls=[
                # Campo Nombre
                ft.Container(
                    content=nombre_field,
                    col={"xs": 12, "md": 5} # Móvil: 12/12, Web: 5/12
                ),
                # Campo Dirección
                ft.Container(
                    content=direccion_field,
                    col={"xs": 12, "md": 5} # Móvil: 12/12, Web: 5/12
                ),
                # Botón Agregar
                ft.Container(
                    content=Primary("Agregar", on_click=agregar_plantel, height=45),
                    # Alinear el botón en web
                    alignment=ft.alignment.center_right if page.width >= 768 else ft.alignment.top_left,
                    col={"xs": 12, "md": 2} # Móvil: 12/12, Web: 2/12
                )
            ],
            vertical_alignment=ft.CrossAxisAlignment.START
        )

    def build_plantel_card(plantel: dict) -> Card:
        """
        Construye la tarjeta para un solo plantel en la lista.
        """
        return Card(
            content=ft.Row(
                controls=[
                    # Columna de Nombre y Dirección (expandida)
                    ft.Column(
                        [
                            ft.Text(plantel.get("nombre", "N/A"), weight=ft.FontWeight.BOLD),
                            ft.Text(plantel.get("direccion", "N/A"), size=12, opacity=0.8),
                        ],
                        spacing=2,
                        expand=True
                    ),
                    # Botones de Acción
                    ft.IconButton(
                        icon=ft.icons.EDIT_OUTLINED,
                        on_click=lambda e, p=plantel: editar_plantel(p),
                        tooltip="Editar"
                    ),
                    ft.IconButton(
                        icon=ft.icons.DELETE_OUTLINED,
                        icon_color=ft.Colors.ERROR,
                        on_click=lambda e, p=plantel: eliminar_plantel(p),
                        tooltip="Eliminar"
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            )
        )

    # --- Carga Inicial ---
    cargar_planteles()

    # --- Layout Principal ---
    
    form_card = Card(
        content=ft.Column(
            [
                ft.Text("Agregar Nuevo Plantel", size=16, weight=ft.FontWeight.BOLD),
                build_form(),
            ],
            spacing=15
        ),
        padding=20
    )
    
    # Esta es la vista que se retorna
    return ft.Column(
        [
            form_card,
            ft.Divider(height=10, opacity=0),
            lista_planteles_col,
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO, # <--- IMPORTANTE: Permite scroll en móvil
    )