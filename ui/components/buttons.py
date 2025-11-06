import flet as ft
from typing import Optional, Any, Dict, Callable, Union

RADIUS=10
PAD=ft.Padding(12,10,12,10)

# Styles (remain unchanged)
PRIMARY=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=RADIUS), padding=PAD)
TONAL=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=RADIUS), padding=PAD)
OUTLINE=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=RADIUS), padding=PAD)
GHOST=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=RADIUS), padding=PAD)
DANGER=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=RADIUS), padding=PAD, bgcolor=ft.Colors.ERROR_CONTAINER, color=ft.Colors.ON_ERROR_CONTAINER)


# --- WRAPPER FUNCTION TO HANDLE RESPONSIVE LAYOUT AND GENERIC PROPS ---
def _wrap_in_container(control: ft.Control, col: Optional[Dict[str, Any]] = None, height: Optional[int] = None, **kwargs) -> ft.Control:
    """
    Wraps a button control in an ft.Container if 'col' is provided.
    Applies generic kwargs (like 'visible') to the *inner* control before wrapping.
    """
    
    # 1. Apply generic kwargs (like 'visible', 'data', etc.) to the inner control
    for k, v in kwargs.items():
        setattr(control, k, v)
        
    if col is None:
        return control
    
    # 2. Handle Responsive Wrap (Container receives 'col')
    control.width = None
    control.expand = True 
    
    return ft.Container(
        content=control,
        col=col,
        height=height, 
        padding=ft.padding.only(top=0), 
    )

# --- CUSTOM BUTTON FUNCTIONS (IMPLEMENTING **KWARGS) ---
# Note: 'width' is passed to the inner button's signature, but is unset if 'col' is used.

def Primary(text: str, on_click: Optional[Callable] = None, icon: Optional[ft.Icon] = None, 
            width: Optional[int] = 220, height: Optional[int] = 44, disabled: bool = False,
            col: Optional[Dict[str, Any]] = None, **kwargs):
    
    button = ft.FilledButton(text, icon=icon, on_click=on_click, width=width, height=height, style=PRIMARY, disabled=disabled)
    return _wrap_in_container(button, col, height, **kwargs)


def Tonal(text: str, on_click: Optional[Callable] = None, icon: Optional[ft.Icon] = None, 
          width: Optional[int] = 220, height: Optional[int] = 44, disabled: bool = False,
          col: Optional[Dict[str, Any]] = None, **kwargs):
    
    button = ft.FilledTonalButton(text, icon=icon, on_click=on_click, width=width, height=height, style=TONAL, disabled=disabled)
    return _wrap_in_container(button, col, height, **kwargs)


def Outline(text: str, on_click: Optional[Callable] = None, icon: Optional[ft.Icon] = None, 
            width: Optional[int] = 220, height: Optional[int] = 44, disabled: bool = False,
            col: Optional[Dict[str, Any]] = None, **kwargs):
    
    button = ft.OutlinedButton(text, icon=icon, on_click=on_click, width=width, height=height, style=OUTLINE, disabled=disabled)
    return _wrap_in_container(button, col, height, **kwargs)


def Ghost(text: str, on_click: Optional[Callable] = None, icon: Optional[ft.Icon] = None, 
          width: Optional[int] = 220, height: Optional[int] = 44, disabled: bool = False,
          col: Optional[Dict[str, Any]] = None, **kwargs):
    
    button = ft.TextButton(text, icon=icon, on_click=on_click, width=width, height=height, style=GHOST, disabled=disabled)
    return _wrap_in_container(button, col, height, **kwargs)


def Danger(text: str, on_click: Optional[Callable] = None, icon: Optional[ft.Icon] = ft.Icons.WARNING_AMBER, 
           width: Optional[int] = 220, height: Optional[int] = 44, disabled: bool = False,
           col: Optional[Dict[str, Any]] = None, **kwargs):
    
    button = ft.FilledButton(text, icon=icon, on_click=on_click, width=width, height=height, style=DANGER, disabled=disabled)
    return _wrap_in_container(button, col, height, **kwargs)


def Icon(icon: ft.Icon, tooltip: Optional[str] = None, on_click: Optional[Callable] = None,
         icon_color: Optional[str] = None): # <-- FIX: Accept icon_color
    
    # We pass all arguments directly to ft.IconButton
    return ft.IconButton(
        icon=icon, 
        tooltip=tooltip, 
        on_click=on_click,
        icon_color=icon_color # <-- FIX: Forward the argument
    )