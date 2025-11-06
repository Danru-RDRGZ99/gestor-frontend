import os
import requests
import flet as ft

class ApiClient:
    def __init__(self, page: ft.Page):
        self.page = page
        
        # --- 1. AÑADIDO: Almacén para el token ---
        self.token = None 
        
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
        
        # --- 2. AÑADIDO: Lógica para enviar el token ---
        headers = kwargs.pop("headers", {})
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        # --- FIN LÓGICA DE TOKEN ---

        try:
            # Pasa los headers actualizados a la petición
            response = requests.request(method, url, headers=headers, **kwargs) 
            print(f"📡 Request: {method} {url} - Status: {response.status_code}")
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Error {response.status_code}: {response.text}")
                # Devuelve el error JSON del backend si existe
                try:
                    return {"error": response.json().get("detail", response.text)}
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
    
    # ... (get_captcha_image y get_captcha siguen igual) ...
    def get_captcha_image(self):
        """Obtener imagen CAPTCHA del backend - método específico para captcha_view"""
        try:
            url = f"{self.base_url}/captcha"
            response = requests.get(url)
            print(f"📡 CAPTCHA Request: GET {url} - Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ CAPTCHA obtenido correctamente")
                return data.get("image_data")
            else:
                print(f"❌ Error obteniendo CAPTCHA: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Error en get_captcha_image: {e}")
            return None
    
    def get_captcha(self):
        """Obtener CAPTCHA del backend (método alternativo)"""
        return self._make_request("GET", "/captcha")
    
    def verify_captcha(self, captcha_text, captcha_id):
        """Verificar CAPTCHA"""
        return self._make_request("POST", "/verify-captcha", 
                                json={"text": captcha_text, "id": captcha_id})
    
    def login(self, username, password, captcha):
        """
        Login de usuario (con CAPTCHA).
        Llama al endpoint /token del backend.
        """
        response_data = self._make_request("POST", "/token", 
                                json={"username": username, "password": password, "captcha": captcha})
        
        # --- 3. AÑADIDO: Guardar el token si el login es exitoso ---
        if response_data and "access_token" in response_data:
            self.token = response_data.get("access_token")
            print("INFO: Token de acceso guardado en ApiClient.")
        # --- FIN GUARDAR TOKEN ---
        
        return response_data
    
    def register(self, user_data):
        """Registro de usuario"""
        return self._make_request("POST", "/register", json=user_data)
    
    # ... (Métodos de laboratorios siguen igual) ...
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
    
    # ... (Métodos de reservas siguen igual) ...
    def get_reservas(self):
        return self._make_request("GET", "/reservas")
    
    def create_reserva(self, data):
        return self._make_request("POST", "/reservas", json=data)
    
    def update_reserva(self, reserva_id, data):
        return self._make_request("PUT", f"/reservas/{reserva_id}", json=data)
    
    def delete_reserva(self, reserva_id):
        return self._make_request("DELETE", f"/reservas/{reserva_id}")
    
    # --- 4. AÑADIDO: El método que faltaba ---
    # (Basado en tu main.py)
    def get_mis_prestamos(self):
        """Obtiene los préstamos del usuario actual (requiere token)"""
        return self._make_request("GET", "/prestamos/mis-solicitudes")
    # --- FIN MÉTODO AÑADIDO ---

    # Métodos para préstamos
    def get_prestamos(self):
        return self._make_request("GET", "/prestamos")
    
    def create_prestamo(self, data):
        return self._make_request("POST", "/prestamos", json=data)
    
    def update_prestamo(self, prestamo_id, data):
        return self._make_request("PUT", f"/prestamos/{prestamo_id}", json=data)
    
    def delete_prestamo(self, prestamo_id):
        return self._make_request("DELETE", f"/prestamos/{prestamo_id}")
    
    # ... (El resto de métodos siguen igual) ...
    def get_planteles(self):
        return self._make_request("GET", "/planteles")
    
    def create_plantel(self, data):
        return self._make_request("POST", "/planteles", json=data)
    
    def get_usuarios(self):
        return self._make_request("GET", "/usuarios")
    
    def get_perfil(self):
        return self._make_request("GET", "/perfil")
    
    def update_perfil(self, data):
        return self._make_request("PUT", "/perfil", json=data)
}