import flet as ft
from typing import Optional, List, Union, Tuple, Dict, Any, Callable
from datetime import datetime, timedelta, time 

# --- GENERADOR DE HORAS (NECESARIO PARA LA VISTA DE HORARIOS) ---
def generate_time_options(start_time: time, end_time: time, interval_min: int = 30) -> List[Tuple[str, str]]:
    """
    Genera una lista de tuplas (valor ISO, texto mostrado) para intervalos de tiempo.
    El valor ISO es 'HH:MM:SS' para la API.
    """
    options = []
    current_dt = datetime.combine(datetime.today().date(), start_time)
    end_dt = datetime.combine(datetime.today().date(), end_time)
    delta = timedelta(minutes=interval_min)

    # Sumamos un minuto extra al final para asegurar que se capture el último slot (ej. 23:30)
    # Ya que el slot representa un inicio.
    while current_dt <= end_dt: 
        iso_value = current_dt.strftime("%H:%M:%S")
        display_text = current_dt.strftime("%I:%M %p").replace(" 0", " ").strip()
        
        options.append((iso_value, display_text))
        current_dt += delta
        
        if delta.total_seconds() <= 0: break
    
    return options

# --- CUSTOM TEXTFIELD (CLASE WRAPPER CON @PROPERTY) ---

class CustomTextField(ft.Container):
    
    def __init__(self, 
                 label: str, 
                 value: str = "", 
                 password: bool = False, 
                 expand: Union[bool, int] = False, 
                 width: Optional[int] = None, 
                 read_only: bool = False, 
                 can_reveal: bool = True,
                 col: Optional[Dict[str, Any]] = None, 
                 horizontal_padding: Optional[float] = None,
                 **kwargs):
        
        # 1. Crear el control interno ft.TextField
        self.tf = ft.TextField(
            label=label, 
            value=value, 
            password=password, 
            can_reveal_password=can_reveal, 
            read_only=read_only,
            **kwargs 
        )
        
        # 2. Inicializar el control base (ft.Container)
        super().__init__()
        
        # 3. Aplicar layout responsivo al contenedor externo
        if col:
            self.col = col
            self.tf.width = None 
            self.tf.expand = True 
        else:
            # Si no hay 'col', el TextField interno maneja su propio tamaño
            self.tf.expand = expand
            self.tf.width = width
             
        # 4. Aplicar padding si se especifica (al contenedor)
        if horizontal_padding is not None:
             self.padding = ft.padding.symmetric(horizontal=horizontal_padding)
             
        # 5. Establecer el TextField como el contenido
        self.content = self.tf
    
    # 6. Implementar @property para reenviar .value al control interno
    @property
    def value(self):
        return self.tf.value

    @value.setter
    def value(self, new_value):
        self.tf.value = new_value

    def update(self):
         self.tf.update()
         super().update()
        
TextField = CustomTextField # Renombra para usarlo en otras vistas


# --- CUSTOM DROPDOWN (MODIFICADO CON CLASE WRAPPER @PROPERTY) ---
# Se necesita una estructura similar para Dropdown si se usa 'col'

class CustomDropdown(ft.Container):
    def __init__(self, label:str, options:List[Union[str, Tuple]], width:Optional[int]=None, value:Optional[str]=None, col: Optional[Dict[str, Any]] = None, **kwargs):
        
        opts = [ft.dropdown.Option(o[0], text=o[1]) if isinstance(o,tuple) and len(o) == 2 else ft.dropdown.Option(o) for o in options]
        
        self.inner_dd = ft.Dropdown(
            label=label, 
            options=opts, 
            value=value,
            **kwargs
        )
        
        super().__init__()

        if col:
            self.col = col
            self.inner_dd.width = None
            self.inner_dd.expand = True
            # Añadir padding para alinear verticalmente con TextField
            self.padding = ft.padding.only(top=10)
        else:
            self.inner_dd.width = width
            self.inner_dd.expand = False

        self.content = self.inner_dd

    @property
    def value(self):
        return self.inner_dd.value

    @value.setter
    def value(self, new_value):
        self.inner_dd.value = new_value

    def update(self):
         self.inner_dd.update()
         super().update()

Dropdown = CustomDropdown


# --- Resto de funciones ---
def DateBadge(date_str:str, width=160):
    return ft.TextField(value=date_str, read_only=True, width=width, text_align=ft.TextAlign.CENTER)

def SearchBox(placeholder:str="Buscar", on_change=None, width:int=260):
    return ft.TextField(hint_text=placeholder, prefix_icon=ft.Icons.SEARCH, on_change=on_change, width=width, dense=True)