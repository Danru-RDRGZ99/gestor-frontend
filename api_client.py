import os
import requests
import flet as ft

class ApiClient:
    def __init__(self, page: ft.Page):
        self.page = page
        
        # --- 1. SOLUCIÓN: Usar un objeto Session ---
        # Esto guardará las cookies (para el captcha) y los headers (para el token)
        self.session = requests.Session() 
        
        raw_url = os.environ.get("BACKEND_URL", "https://gestor-de-laboratorios-production.up.railway.app")
        
        if not raw_url.startswith("http://") and not raw_url.startswith("https://"):
            print(f"⚠️  URL de backend ({raw_url}) sin esquema. Añadiendo https:// por defecto.")
            self.base_url = f"https://{raw_url}"
        else:
            self.base_url = raw_url
            
        print(f"🔗 Conectando a backend en: {self.base_url}")
        
    def _make_request(self, method, endpoint, **kwargs):
        """Método genérico para hacer requests al backend"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            # Usar self.session.request en lugar de requests.request
            response = self.session.request(method, url, **kwargs) 
            
            print(f"📡 Request: {method} {url} - Status: {response.status_code}")
            
            # --- Manejo de Errores Mejorado ---
            if response.ok: # Acepta 200, 201, 204
                if response.status_code == 204: # No Content (para DELETE)
                    return {"success": True} 
                return response.json() # Para 200, 201
            else:
                print(f"❌ Error {response.status_code}: {response.text}")
                try:
                    error_json = response.json()
                    return {"error": error_json.get("detail", response.text)}
                except requests.exceptions.JSONDecodeError:
                    return {"error": f"Error {response.status_code}: {response.text}"}
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Error de conexión con el backend en {url}")
            return {"error": "No se pudo conectar con el servidor backend"}
        except requests.exceptions.RequestException as e:
            print(f"❌ Error en request: {e}")
            return {"error": str(e)}
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            return {"error": "Error inesperado en la conexión"}
    
    # --- Métodos de CAPTCHA y Login ---

    def get_captcha_image(self):
        """Obtiene el string base64 de la imagen del captcha."""
        response = self._make_request("GET", "/captcha") 
        if response and "image_data" in response:
            return response.get("image_data")
        print(f"❌ Error obteniendo CAPTCHA: {response}")
        return None
    
    def login(self, username, password, captcha):
        """Login de usuario (con CAPTCHA). Llama al endpoint /token."""
        response_data = self._make_request("POST", "/token", 
                                json={"username": username, "password": password, "captcha": captcha})
        
        if response_data and "access_token" in response_data:
            token_val = f"Bearer {response_data.get('access_token')}"
            self.session.headers.update({"Authorization": token_val})
            print("INFO: Token de acceso (login normal) guardado en la Sesión del ApiClient.")
        
        return response_data

    def login_with_google(self, google_id_token: str):
        """Login con Google. Llama al endpoint /auth/google-token."""
        response_data = self._make_request("POST", "/auth/google-token",
                                json={"idToken": google_id_token})
        
        if response_data and "access_token" in response_data:
            token_val = f"Bearer {response_data.get('access_token')}"
            self.session.headers.update({"Authorization": token_val})
            print("INFO: Token de acceso (Google) guardado en la Sesión del ApiClient.")
            
        return response_data

    def register(self, user_data):
        """Registro de usuario"""
        return self._make_request("POST", "/register", json=user_data)
    
    # --- Métodos de Recursos (Laboratorios, Préstamos, etc.) ---

    def get_laboratorios(self):
        return self._make_request("GET", "/laboratorios")
    
    def get_laboratorio(self, lab_id):
        return self._make_request("GET", f"/laboratorios/{lab_id}")
    
    def create_laboratorio(self, data):
        return self._make_request("POST", "/laboratorios", json=data)
    
    def update_laboratorio(self, lab_id, data):
        return self._make_request("PUT", f"/laboratorios/{lab_id}", json=data)
    
    def delete_laboratorio(self, lab_id):
        return self._make_request("DELETE", f"/laboratorios/{lab_id}")
    
    def get_reservas(self):
        return self._make_request("GET", "/reservas")
    
    def create_reserva(self, data):
        return self._make_request("POST", "/reservas", json=data)
    
    def update_reserva(self, reserva_id, data):
        return self._make_request("PUT", f"/reservas/{reserva_id}", json=data)
    
    def delete_reserva(self, reserva_id):
        return self._make_request("DELETE", f"/reservas/{reserva_id}")
    
    def get_mis_prestamos(self):
        """Obtiene los préstamos del usuario actual (requiere token)"""
        return self._make_request("GET", "/prestamos/mis-solicitudes")

    def get_prestamos(self):
        return self._make_request("GET", "/prestamos")
    
    def create_prestamo(self, data):
        return self._make_request("POST", "/prestamos", json=data)
    
    def update_prestamo(self, prestamo_id, data):
        return self._make_request("PUT", f"/prestamos/{prestamo_id}", json=data)
    
    def delete_prestamo(self, prestamo_id):
        return self._make_request("DELETE", f"/prestamos/{prestamo_id}")
    
    def get_planteles(self):
        return self._make_request("GET", "/planteles")
    
    def create_plantel(self, data):
        return self._make_request("POST", "/planteles", json=data)
    
    # --- INICIO DE MÉTODOS PARA SETTINGS_VIEW ---

    def get_users(self, q: str = "", rol: str = ""):
        """
        Obtiene usuarios filtrados (Admin).
        (RENOMBRADO de get_usuarios y CON PARÁMETROS)
        """
        params = {}
        if q:
            params["q"] = q
        if rol:
            params["rol"] = rol
        return self._make_request("GET", "/usuarios", params=params)
    
    def update_profile(self, nombre: str, user: str, correo: str):
        """
        Actualiza el perfil del propio usuario.
        (RENOMBRADO de update_perfil y CORREGIDO)
        """
        data = {"nombre": nombre, "user": user, "correo": correo}
        return self._make_request("PUT", "/usuarios/me/profile", json=data)

    def change_password(self, old_password: str, new_password: str):
        """
        Cambia la contraseña del propio usuario.
        (NUEVO MÉTODO)
        """
        data = {"old_password": old_password, "new_password": new_password}
        return self._make_request("PUT", "/usuarios/me/password", json=data)

    def update_user_by_admin(self, user_id: int, update_data: dict):
        """
        Actualiza el perfil de otro usuario (Admin).
        (NUEVO MÉTODO)
        """
        # update_data debe ser {"nombre": ..., "user": ..., "correo": ..., "rol": ...}
        return self._make_request("PUT", f"/usuarios/{user_id}", json=update_data)

    def delete_user(self, user_id: int):
        """
        Elimina a un usuario (Admin).
        (NUEVO MÉTODO)
        """
        return self._make_request("DELETE", f"/usuarios/{user_id}")

    # (Método 'get_perfil' obsoleto, reemplazado por la sesión)
    
    # --- FIN DE MÉTODOS PARA SETTINGS_VIEW ---