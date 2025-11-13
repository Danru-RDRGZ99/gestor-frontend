"""
Google OAuth2 Login Component for Flet
Handles Google authentication flow
"""

import flet as ft
import json
from typing import Callable


class GoogleLoginDialog:
    """
    Dialog for Google OAuth2 authentication.
    
    Usage:
        dialog = GoogleLoginDialog(page, api_client, on_success_callback)
        dialog.show()
    """
    
    def __init__(
        self,
        page: ft.Page,
        api_client,
        on_success: Callable,
        on_error: Callable = None,
        on_close: Callable = None,
    ):
        self.page = page
        self.api_client = api_client
        self.on_success = on_success
        self.on_error = on_error or self._default_error_handler
        self.on_close = on_close
        
        self.id_token_field = ft.TextField(
            label="Google ID Token",
            hint_text="Pega aquí el ID token de Google",
            multiline=True,
            min_lines=3,
            max_lines=5,
            width=450,
            text_size=11,
        )
        
        self.status_text = ft.Text(
            "",
            color=ft.Colors.ORANGE_400,
            size=12,
        )
        
        self.dialog = ft.AlertDialog(
            title=ft.Text("Iniciar sesión con Google"),
            content=ft.Column([
                ft.Text(
                    "1. Se abrirá Google Sign-In en tu navegador\n"
                    "2. Completa la autenticación\n"
                    "3. Copia el ID Token que se mostrará\n"
                    "4. Pégalo abajo y presiona 'Continuar'",
                    size=12,
                ),
                ft.Divider(height=20),
                self.id_token_field,
                self.status_text,
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("Cancelar", on_click=self._on_cancel),
                ft.FilledButton("Continuar", on_click=self._on_submit),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
    
    def _default_error_handler(self, message: str):
        """Default error handler - just prints to console"""
        print(f"Google Login Error: {message}")
    
    def _on_cancel(self, e):
        """Handle dialog cancel"""
        self.dialog.open = False
        self.page.update()
        # notify caller that dialog closed
        try:
            if callable(self.on_close):
                self.on_close()
        except Exception:
            pass
    
    def _on_submit(self, e):
        """Handle token submission"""
        token = self.id_token_field.value.strip()
        
        if not token:
            self.status_text.value = "❌ Por favor pega el ID Token"
            self.status_text.color = ft.Colors.RED_400
            self.page.update()
            return
        
        # Authenticate with backend
        self._authenticate(token)
    
    def _authenticate(self, token: str):
        """Authenticate with the backend using the token"""
        self.status_text.value = "⏳ Verificando..."
        self.status_text.color = ft.Colors.BLUE_400
        self.page.update()
        
        try:
            result = self.api_client.login_with_google(token)
            
            if result and "access_token" in result:
                # Successful login
                self.status_text.value = "✅ ¡Autenticación exitosa!"
                self.status_text.color = ft.Colors.GREEN_400
                
                # Store user session
                user_info = result.get("user", {})
                self.page.session.set("user_session", {
                    "user": user_info.get("user", "usuario"),
                    "rol": user_info.get("rol", ""),
                    "id": user_info.get("id"),
                    "nombre": user_info.get("nombre", ""),
                    "correo": user_info.get("correo", ""),
                })
                
                self.page.update()
                
                # Close dialog and call success callback
                self.dialog.open = False
                self.page.update()
                self.on_success()
                # notify caller that dialog closed
                try:
                    if callable(self.on_close):
                        self.on_close()
                except Exception:
                    pass
            else:
                # Authentication failed
                error_msg = result.get("error", "Error desconocido") if isinstance(result, dict) else str(result)
                self.status_text.value = f"❌ {error_msg}"
                self.status_text.color = ft.Colors.RED_400
                self.page.update()
                self.on_error(error_msg)
                try:
                    if callable(self.on_close):
                        self.on_close()
                except Exception:
                    pass
                
        except Exception as e:
            error_msg = str(e)
            self.status_text.value = f"❌ Error: {error_msg}"
            self.status_text.color = ft.Colors.RED_400
            self.page.update()
            self.on_error(error_msg)
    
    def show(self):
        """Show the dialog"""
        self.id_token_field.value = ""
        self.status_text.value = ""
        self.page.dialog = self.dialog
        self.dialog.open = True
        self.page.update()


class GoogleLoginButton(ft.OutlinedButton):
    """
    Styled Google Login Button with built-in OAuth flow
    """
    
    def __init__(self, on_click_handler: Callable, **kwargs):
        super().__init__(
            text="Iniciar sesión con Google",
            icon=ft.Icons.LOGIN,
            on_click=on_click_handler,
            width=kwargs.get("width", 260),
            height=kwargs.get("height", 44),
        )
