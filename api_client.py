import os
import requests
import flet as ft

class ApiClient:
    def __init__(self, page: ft.Page):
        self.page = page
        # URL del backend en Railway
        raw_url = os.environ.get("BACKEND_URL", "https://gestor-de-laboratorios-production.up.railway.app")
        
        # --- INICIO DE LA CORRECCIÓN ---
        # Nos aseguramos de que la URL tenga el esquema (http/https)
        if not raw_url.startswith("http://") and not raw_url.startswith("https://"):
            print(f"⚠️  URL de backend ({raw_url}) sin esquema. Añadiendo https:// por defecto.")
            self.base_url = f"https://{raw_url}"
        else:
            self.base_url = raw_url
        # --- FIN DE LA CORRECCIÓN ---
            
        print(f"🔗 Conectando a backend en: {self.base_url}")
        
    def _make_request(self, method, endpoint, **kwargs):
        """Método genérico para hacer requests al backend"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(method, url, **kwargs)
            print(f"📡 Request: {method} {url} - Status: {response.status_code}")
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Error {response.status_code}: {response.text}")
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
    
    # ... el resto de tus métodos permanecen igual
    def login(self, username, password, captcha):
        """
        Login de usuario (con CAPTCHA).
        Llama al endpoint /token del backend.
        """
        return self._make_request("POST", "/token", 
                                json={"username": username, "password": password, "captcha": captcha})
    
    def register(self, user_data):
        """Registro de usuario"""
        return self._make_request("POST", "/register", json=user_data)
    
    # Métodos para laboratorios
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
    
    # Métodos para reservas
    def get_reservas(self):
        return self._make_request("GET", "/reservas")
    
    def create_reserva(self, data):
        return self._make_request("POST", "/reservas", json=data)
    
    def update_reserva(self, reserva_id, data):
        return self._make_request("PUT", f"/reservas/{reserva_id}", json=data)
    
    def delete_reserva(self, reserva_id):
        return self._make_request("DELETE", f"/reservas/{reserva_id}")
    
    # Métodos para préstamos
    def get_prestamos(self):
        return self._make_request("GET", "/prestamos")
    
    def create_prestamo(self, data):
        return self._make_request("POST", "/prestamos", json=data)
    
    def update_prestamo(self, prestamo_id, data):
        return self._make_request("PUT", f"/prestamos/{prestamo_id}", json=data)
    
    def delete_prestamo(self, prestamo_id):
        return self._make_request("DELETE", f"/prestamos/{prestamo_id}")
    
    # Métodos para planteles
    def get_planteles(self):
        return self._make_request("GET", "/planteles")
    
    def create_plantel(self, data):
        return self._make_request("POST", "/planteles", json=data)
    
    # Métodos para usuarios
    def get_usuarios(self):
        return self._make_request("GET", "/usuarios")
    
    def get_perfil(self):
        return self._make_request("GET", "/perfil")
    
    def update_perfil(self, data):
        return self._make_request("PUT", "/perfil", json=data)