import requests
import flet as ft
from datetime import datetime, date, time # <-- Añadido date y time
import base64 
from typing import Optional, List, Dict, Union, Tuple # Para typing hints

# URL base de tu API. Asegúrate que sea accesible desde donde corre Flet.
API_BASE_URL = "http://127.0.0.1:8000"

# Tipo de retorno genérico para manejar el éxito (List/Dict) o el error (Dict)
API_RESPONSE = Union[List, Dict, bool, None]

class ApiClient:
    """
    Cliente centralizado para interactuar con la API del Gestor de Laboratorios.
    """
    def __init__(self, page: ft.Page):
        self.page = page
        self.session = requests.Session()

    def _get_token(self) -> str | None:
        user_session = self.page.session.get("user_session")
        return user_session.get("access_token") if user_session else None

    def _get_auth_headers(self) -> dict:
        token = self._get_token()
        if not token: return {}
        return {"Authorization": f"Bearer {token}"}

    def _handle_request(self, method, endpoint, **kwargs) -> API_RESPONSE:
        try:
            url = f"{API_BASE_URL}{endpoint}"
            headers = kwargs.pop("headers", {})
            headers.update(self._get_auth_headers())
            response = self.session.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            if response.status_code == 204: return True
            if response.content:
                try: return response.json()
                except requests.exceptions.JSONDecodeError: return {"detail": "Respuesta inválida del servidor."}
            else: return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print("Token inválido o expirado. Redirigiendo al login.")
                if self.page.session: self.page.session.remove("user_session")
                self.page.go("/")
                return None
            elif e.response.status_code in (400, 403, 404, 409):
                try: return e.response.json()
                except requests.exceptions.JSONDecodeError: return {"detail": e.response.text or f"Error {e.response.status_code}"}
            else: return {"detail": f"Error inesperado del servidor ({e.response.status_code})"}
        except requests.exceptions.RequestException as e:
            print(f"Error de conexión con la API: {e}")
            return {"detail": "No se pudo conectar con el servidor."}
        return None

    # --- Auth & Users (Métodos de autenticación sin cambios) ---
    def get_captcha_image(self):
        try:
            url = f"{API_BASE_URL}/captcha?_={datetime.now().timestamp()}"
            response = self.session.get(url)
            response.raise_for_status()
            img_bytes = response.content
            return base64.b64encode(img_bytes).decode('utf-8')
        except requests.exceptions.RequestException as e:
            print(f"Error crítico al obtener CAPTCHA: {e}")
            return None

    def login_with_google(self, google_id_token: str):
        payload = {"idToken": google_id_token}
        return self._handle_request("post", "/auth/google-token", json=payload)

    def login(self, username, password, captcha):
        payload = {"username": username, "password": password, "captcha": captcha}
        return self._handle_request("post", "/token", json=payload)
    
    def register(self, nombre, correo, usuario, password, rol):
        payload = {"nombre": nombre, "correo": correo, "user": usuario, "password": password, "rol": rol}
        return self._handle_request("post", "/register", json=payload)

    def get_users(self, q="", rol=""):
        return self._handle_request("get", "/usuarios", params={"q": q, "rol": rol})
    
    def update_profile(self, nombre, user, correo):
        return self._handle_request("put", "/usuarios/me/profile", json={"nombre": nombre, "user": user, "correo": correo})
    
    def change_password(self, old_password, new_password):
        return self._handle_request("put", "/usuarios/me/password", json={"old_password": old_password, "new_password": new_password})
    
    def delete_user(self, user_id: int):
        return self._handle_request("delete", f"/usuarios/{user_id}")

    def update_user_by_admin(self, user_id: int, data: dict):
        return self._handle_request("put", f"/usuarios/{user_id}", json=data)


    # --- Planteles & Laboratorios (Sin cambios) ---
    def get_planteles(self): return self._handle_request("get", "/planteles")
    def add_plantel(self, nombre: str, direccion: str): return self._handle_request("post", "/planteles", json={"nombre": nombre, "direccion": direccion})
    def update_plantel(self, plantel_id: int, nombre: str, direccion: str): return self._handle_request("put", f"/planteles/{plantel_id}", json={"nombre": nombre, "direccion": direccion})
    def delete_plantel(self, plantel_id: int): return self._handle_request("delete", f"/planteles/{plantel_id}")
    def get_laboratorios(self): return self._handle_request("get", "/laboratorios")
    def add_laboratorio(self, nombre: str, ubicacion: str, capacidad: int, plantel_id: int): return self._handle_request("post", "/laboratorios", json={"nombre": nombre, "ubicacion": ubicacion, "capacidad": capacidad, "plantel_id": plantel_id})
    def update_laboratorio(self, lab_id: int, nombre: str, ubicacion: str, capacidad: int, plantel_id: int): return self._handle_request("put", f"/laboratorios/{lab_id}", json={"nombre": nombre, "ubicacion": ubicacion, "capacidad": capacidad, "plantel_id": plantel_id})
    def delete_laboratorio(self, lab_id: int): return self._handle_request("delete", f"/laboratorios/{lab_id}")


    # --- Recursos (Sin cambios) ---
    def get_recursos(self, plantel_id=None, lab_id=None, estado=None, tipo=None):
        params = {"plantel_id": plantel_id, "lab_id": lab_id, "estado": estado, "tipo": tipo}
        params = {k: v for k, v in params.items() if v is not None and v != ""}
        return self._handle_request("get", "/recursos", params=params)
    def get_recurso_tipos(self): return self._handle_request("get", "/recursos/tipos")
    def create_recurso(self, tipo: str, estado: str, laboratorio_id: int, specs: str = ""): return self._handle_request("post", "/recursos", json={"tipo": tipo, "specs": specs, "estado": estado, "laboratorio_id": laboratorio_id})
    def update_recurso(self, recurso_id: int, tipo: str, estado: str, laboratorio_id: int, specs: str = ""): return self._handle_request("put", f"/recursos/{recurso_id}", json={"tipo": tipo, "specs": specs, "estado": estado, "laboratorio_id": laboratorio_id})
    def delete_recurso(self, recurso_id: int): return self._handle_request("delete", f"/recursos/{recurso_id}")


    # --- HORARIOS Y REGLAS (NUEVOS MÉTODOS) ---

    def get_horario_laboratorio(self, lab_id: int, fecha_inicio: date, fecha_fin: date):
        """Obtiene los slots de horario calculados por el backend."""
        try:
            params = {"fecha_inicio": fecha_inicio.isoformat(), "fecha_fin": fecha_fin.isoformat()}
            return self._handle_request("get", f"/laboratorios/{lab_id}/horario", params=params)
        except Exception as e:
            print(f"Error en get_horario_laboratorio: {e}")
            return {"detail": f"Error de conexión al obtener horario: {e}"}

    def get_reglas_horario(self, lab_id: Optional[int] = None):
        """Obtiene todas las reglas de horario semanal."""
        params = {"laboratorio_id": lab_id} if lab_id is not None else {}
        return self._handle_request("get", "/admin/horarios/reglas", params=params)

    def create_regla_horario(self, data: dict):
        """Crea una nueva regla de horario semanal a partir de un diccionario de datos."""
        # Se envía el diccionario 'data' directamente como JSON
        return self._handle_request("post", "/admin/horarios/reglas", json=data)

    def update_regla_horario(self, regla_id: int, data: dict):
        """Actualiza una regla de horario semanal a partir de un diccionario de datos."""
        # Se envía el diccionario 'data' directamente como JSON
        return self._handle_request("put", f"/admin/horarios/reglas/{regla_id}", json=data)

    def delete_regla_horario(self, regla_id: int):
        """Elimina una regla de horario semanal."""
        return self._handle_request("delete", f"/admin/horarios/reglas/{regla_id}")
    
    # --- FIN NUEVOS MÉTODOS ---


    # --- Reservas (Sin cambios) ---
    def get_reservas(self, lab_id: int, start_dt: datetime, end_dt: datetime):
        params = {"start_dt": start_dt.isoformat(), "end_dt": end_dt.isoformat()}
        return self._handle_request("get", f"/reservas/{lab_id}", params=params)
    def create_reserva(self, lab_id: int, user_id: int, inicio: datetime, fin: datetime):
        payload = {"laboratorio_id": lab_id, "usuario_id": user_id, "inicio": inicio.isoformat(), "fin": fin.isoformat()}
        return self._handle_request("post", "/reservas", json=payload)
    def cancel_reserva(self, reserva_id: int): return self._handle_request("put", f"/reservas/{reserva_id}/cancelar")
    def get_mis_reservas(self): return self._handle_request("get", "/reservas/mis-reservas")


    # --- Préstamos (Sin cambios) ---
    def get_mis_prestamos(self): return self._handle_request("get", "/prestamos/mis-solicitudes")
    def get_todos_los_prestamos(self): return self._handle_request("get", "/admin/prestamos")
    def create_prestamo(self, prestamo_data: dict):
        if isinstance(prestamo_data.get("inicio"), datetime): prestamo_data["inicio"] = prestamo_data["inicio"].isoformat()
        if isinstance(prestamo_data.get("fin"), datetime): prestamo_data["fin"] = prestamo_data["fin"].isoformat()
        return self._handle_request("post", "/prestamos", json=prestamo_data)
    def update_prestamo_estado(self, prestamo_id: int, nuevo_estado: str): return self._handle_request("put", f"/admin/prestamos/{prestamo_id}/estado", params={"nuevo_estado": nuevo_estado})