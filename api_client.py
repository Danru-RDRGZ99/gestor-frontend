import os
import requests
import flet as ft
from datetime import date # <--- AÑADIDO para type hinting

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
        
        # La sesión (self.session) maneja los headers (token) automáticamente
        try:
            # Usar self.session.request en lugar de requests.request
            response = self.session.request(method, url, **kwargs) 
            
            print(f"📡 Request: {method} {url} - Status: {response.status_code}")
            
            # --- MANEJO DE RESPUESTAS MEJORADO ---
            
            # <--- ¡CORRECCIÓN 1: ACEPTAR 200 y 201! ---
            if response.status_code in [200, 201]: # 200 (OK) y 201 (Created) son éxito
                return response.json() # Éxito
            
            if response.status_code == 204: # Para DELETE exitoso
                return {"success": True} 

            # Si no es 200, 201 o 204, es un error
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

    def register(self, user_data: dict):
        """Registro de usuario. Espera un diccionario con los datos."""
        return self._make_request("POST", "/register", json=user_data)
    
    # --- Métodos de Laboratorios ---

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
    
    # --- Métodos para Reservas ---

    def get_reservas(self, lab_id: int, start_dt: date, end_dt: date):
        """
        Obtiene las reservas filtradas por lab y rango de fechas.
        Llama al endpoint: GET /reservas/{lab_id}
        """
        params = {
            "start_dt": str(start_dt), # Convierte date a string YYYY-MM-DD
            "end_dt": str(end_dt)
        }
        return self._make_request("GET", f"/reservas/{lab_id}", params=params)
    
    def create_reserva(self, data):
        # El código 201 (Created) será manejado como éxito por _make_request
        return self._make_request("POST", "/reservas", json=data)
    
    def update_reserva(self, reserva_id, data):
        return self._make_request("PUT", f"/reservas/{reserva_id}", json=data)
    
    # <--- ¡CORRECCIÓN 2: ARREGLAR DELETE! ---
    def delete_reserva(self, reserva_id):
        """Cancela una reserva. Llama al endpoint PUT /reservas/{id}/cancelar."""
        # El backend usa PUT y un endpoint especial, no DELETE
        return self._make_request("PUT", f"/reservas/{reserva_id}/cancelar")
    
    def get_horario_laboratorio(self, lab_id: int, start_dt: date, end_dt: date):
        """
        Calcula el horario disponible para un laboratorio en un rango de fechas.
        Llama al endpoint: GET /laboratorios/{lab_id}/horario
        """
        params = {
            "fecha_inicio": str(start_dt),
            "fecha_fin": str(end_dt)
        }
        return self._make_request("GET", f"/laboratorios/{lab_id}/horario", params=params)

    # --- INICIO: MÉTODO AÑADIDO (para Dashboard) ---
    def get_mis_reservas(self):
        """Obtiene las reservas del usuario actual (requiere token)."""
        # --- CORRECCIÓN 4 (Definitiva) ---
        # El endpoint no existía en el backend. Lo añadiremos como
        # "/reservas/mis-solicitudes" y lo llamaremos aquí.
        return self._make_request("GET", "/reservas/mis-solicitudes")
    # --- FIN: MÉTODO AÑADIDO ---


    # --- Métodos para Préstamos / Recursos (de prestamos_view.py) ---
    
    def get_mis_prestamos(self):
        """Obtiene los préstamos del usuario actual (requiere token)"""
        return self._make_request("GET", "/prestamos/mis-solicitudes")

    def get_todos_los_prestamos(self):
        """Obtiene TODOS los préstamos (admin)"""
        return self._make_request("GET", "/admin/prestamos")

    def create_prestamo(self, data: dict):
        # El código 201 (Created) será manejado como éxito por _make_request
        return self._make_request("POST", "/prestamos", json=data)

    def update_prestamo_estado(self, prestamo_id: int, new_status: str):
        """Actualiza el estado de un préstamo (admin)"""
        return self._make_request("PUT", f"/admin/prestamos/{prestamo_id}/estado?nuevo_estado={new_status}")
    
    def get_recursos(self, plantel_id: int = None, lab_id: int = None, estado: str = "", tipo: str = ""):
        """Obtiene recursos filtrados"""
        params = {}
        if plantel_id:
            params["plantel_id"] = plantel_id
        if lab_id:
            params["lab_id"] = lab_id
        if estado:
            params["estado"] = estado
        if tipo:
            params["tipo"] = tipo
        return self._make_request("GET", "/recursos", params=params)

    def get_recurso_tipos(self):
        """Obtiene la lista de tipos de recursos únicos"""
        return self._make_request("GET", "/recursos/tipos")

    def create_recurso(self, tipo: str, estado: str, laboratorio_id: int, specs: str):
        """Crea un nuevo recurso (admin)"""
        payload = {
            "tipo": tipo,
            "estado": estado,
            "laboratorio_id": laboratorio_id,
            "specs": specs
        }
        return self._make_request("POST", "/recursos", json=payload)

    def update_recurso(self, recurso_id: int, tipo: str, estado: str, laboratorio_id: int, specs: str):
        """Actualiza un recurso existente (admin)"""
        payload = {
            "tipo": tipo,
            "estado": estado,
            "laboratorio_id": laboratorio_id,
            "specs": specs
        }
        return self._make_request("PUT", f"/recursos/{recurso_id}", json=payload)

    def delete_recurso(self, recurso_id: int):
        """Elimina un recurso (admin)"""
        return self._make_request("DELETE", f"/recursos/{recurso_id}")

    # --- Métodos para Planteles ---
    
    def get_planteles(self):
        return self._make_request("GET", "/planteles")
    
    def create_plantel(self, data):
        return self._make_request("POST", "/planteles", json=data)
    
    # --- Métodos para Usuarios (de settings_view.py) ---

    def get_users(self, q: str = "", rol: str = None):
        """Obtiene usuarios filtrados (Admin)."""
        params = {}
        if q:
            params["q"] = q
        if rol is not None: # Permite enviar "" (vacío) pero no None
            params["rol"] = rol
        return self._make_request("GET", "/usuarios", params=params)
    
    def update_profile(self, nombre: str, user: str, correo: str):
        """Actualiza el perfil del usuario actual."""
        payload = {"nombre": nombre, "user": user, "correo": correo}
        return self._make_request("PUT", "/usuarios/me/profile", json=payload)

    def change_password(self, old_password: str, new_password: str):
        """Cambia la contraseña del usuario actual."""
        payload = {"old_password": old_password, "new_password": new_password}
        return self._make_request("PUT", "/usuarios/me/password", json=payload)

    def update_user_by_admin(self, user_id: int, data: dict):
        """Actualiza cualquier usuario (Admin)."""
        return self._make_request("PUT", f"/usuarios/{user_id}", json=data)

    def delete_user(self, user_id: int):
        """Elimina un usuario (Admin)."""
        return self._make_request("DELETE", f"/usuarios/{user_id}")

    # --- INICIO DE MÉTODOS PARA HORARIOS_ADMIN_VIEW ---

    def get_reglas_horario(self, laboratorio_id: int = None):
        """Obtiene las reglas de horario (Admin)."""
        params = {}
        if laboratorio_id is not None:
            params["laboratorio_id"] = laboratorio_id
        return self._make_request("GET", "/admin/horarios/reglas", params=params)

    def create_regla_horario(self, payload: dict):
        """Crea una nueva regla de horario (Admin)."""
        return self._make_request("POST", "/admin/horarios/reglas", json=payload)

    def update_regla_horario(self, regla_id: int, payload: dict):
        """Actualiza una regla de horario (Admin)."""
        return self._make_request("PUT", f"/admin/horarios/reglas/{regla_id}", json=payload)

    def delete_regla_horario(self, regla_id: int):
        """Elimina una regla de horario (Admin)."""
        return self._make_request("DELETE", f"/admin/horarios/reglas/{regla_id}")
    
    def delete_plantel(self, plantel_id: int) -> bool:
        try:
            response = self.session.delete(f"{self.base_url}/planteles/{plantel_id}")
            if response.status_code == 200:
                return True
            elif response.status_code == 404:
                print(f"❌ Plantel con ID {plantel_id} no encontrado")
                return False
            else:
                print(f"❌ Error al eliminar plantel: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Excepción al eliminar plantel: {e}")
            return False