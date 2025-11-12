import os
import requests
import flet as ft
from datetime import date

class ApiClient:
    def __init__(self, page: ft.Page):
        self.page = page
        self.session = requests.Session()
        raw_url = os.environ.get("BACKEND_URL", "https://gestor-de-laboratorios-production.up.railway.app")
        if not raw_url.startswith("http://") and not raw_url.startswith("https://"):
            self.base_url = f"https://{raw_url}"
        else:
            self.base_url = raw_url

    def _make_request(self, method, endpoint, **kwargs):
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, **kwargs)
            print(f"📡 Request: {method} {url} - Status: {response.status_code}")
            if response.status_code in [200, 201]:
                return response.json()
            if response.status_code == 204:
                return {"success": True}
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

    def get_captcha_image(self):
        response = self._make_request("GET", "/captcha")
        if response and "image_data" in response:
            return response.get("image_data")
        print(f"❌ Error obteniendo CAPTCHA: {response}")
        return None

    def login(self, username, password, captcha):
        response_data = self._make_request("POST", "/token", json={"username": username, "password": password, "captcha": captcha})
        if response_data and "access_token" in response_data:
            token_val = f"Bearer {response_data.get('access_token')}"
            self.session.headers.update({"Authorization": token_val})
        return response_data

    def login_with_google(self, google_id_token: str):
        response_data = self._make_request("POST", "/auth/google-token", json={"idToken": google_id_token})
        if response_data and "access_token" in response_data:
            token_val = f"Bearer {response_data.get('access_token')}"
            self.session.headers.update({"Authorization": token_val})
        return response_data

    def register(self, user_data: dict):
        return self._make_request("POST", "/register", json=user_data)

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

    def get_reservas(self, lab_id: int, start_dt: date, end_dt: date):
        params = {"start_dt": str(start_dt), "end_dt": str(end_dt)}
        return self._make_request("GET", f"/reservas/{lab_id}", params=params)

    def create_reserva(self, data):
        return self._make_request("POST", "/reservas", json=data)

    def update_reserva(self, reserva_id, data):
        return self._make_request("PUT", f"/reservas/{reserva_id}", json=data)

    def delete_reserva(self, reserva_id):
        return self._make_request("PUT", f"/reservas/{reserva_id}/cancelar")

    def get_horario_laboratorio(self, lab_id: int, start_dt: date, end_dt: date):
        params = {"fecha_inicio": str(start_dt), "fecha_fin": str(end_dt)}
        return self._make_request("GET", f"/laboratorios/{lab_id}/horario", params=params)

    def get_mis_reservas(self):
        return self._make_request("GET", "/reservas/mis-solicitudes")

    def get_mis_prestamos(self):
        return self._make_request("GET", "/prestamos/mis-solicitudes")

    def get_todos_los_prestamos(self):
        return self._make_request("GET", "/admin/prestamos")

    def create_prestamo(self, data: dict):
        return self._make_request("POST", "/prestamos", json=data)

    def update_prestamo_estado(self, prestamo_id: int, new_status: str):
        return self._make_request("PUT", f"/admin/prestamos/{prestamo_id}/estado?nuevo_estado={new_status}")

    def get_recursos(self, plantel_id: int = None, lab_id: int = None, estado: str = "", tipo: str = ""):
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
        return self._make_request("GET", "/recursos/tipos")

    def create_recurso(self, tipo: str, estado: str, laboratorio_id: int, specs: str):
        payload = {"tipo": tipo, "estado": estado, "laboratorio_id": laboratorio_id, "specs": specs}
        return self._make_request("POST", "/recursos", json=payload)

    def update_recurso(self, recurso_id: int, tipo: str, estado: str, laboratorio_id: int, specs: str):
        payload = {"tipo": tipo, "estado": estado, "laboratorio_id": laboratorio_id, "specs": specs}
        return self._make_request("PUT", f"/recursos/{recurso_id}", json=payload)

    def delete_recurso(self, recurso_id: int):
        return self._make_request("DELETE", f"/recursos/{recurso_id}")

    def get_planteles(self):
        return self._make_request("GET", "/planteles")

    def create_plantel(self, data):
        return self._make_request("POST", "/planteles", json=data)

    def get_users(self, q: str = "", rol: str = None):
        params = {}
        if q:
            params["q"] = q
        if rol is not None:
            params["rol"] = rol
        return self._make_request("GET", "/usuarios", params=params)

    def update_profile(self, nombre: str, user: str, correo: str):
        payload = {"nombre": nombre, "user": user, "correo": correo}
        return self._make_request("PUT", "/usuarios/me/profile", json=payload)

    def change_password(self, old_password: str, new_password: str):
        payload = {"old_password": old_password, "new_password": new_password}
        return self._make_request("PUT", "/usuarios/me/password", json=payload)

    def update_user_by_admin(self, user_id: int, data: dict):
        return self._make_request("PUT", f"/usuarios/{user_id}", json=data)

    def delete_user(self, user_id: int):
        return self._make_request("DELETE", f"/usuarios/{user_id}")

    def get_reglas_horario(self, laboratorio_id: int = None):
        params = {}
        if laboratorio_id is not None:
            params["laboratorio_id"] = laboratorio_id
        return self._make_request("GET", "/admin/horarios/reglas", params=params)

    def create_regla_horario(self, payload: dict):
        return self._make_request("POST", "/admin/horarios/reglas", json=payload)

    def update_regla_horario(self, regla_id: int, payload: dict):
        return self._make_request("PUT", f"/admin/horarios/reglas/{regla_id}", json=payload)

    def delete_regla_horario(self, regla_id: int):
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

    def get_prestamos_activos(self, include_all: bool = True):
        activos = {"pendiente", "aprobado", "entregado"}
        data = self.get_todos_los_prestamos() if include_all else self.get_mis_prestamos()
        if not isinstance(data, list):
            return []
        return [p for p in data if p.get("estado") in activos]

    def get_recursos_ocupados_ids(self, include_all: bool = True):
        activos = self.get_prestamos_activos(include_all=include_all)
        ids = set()
        for p in activos:
            r = p.get("recurso") or {}
            rid = r.get("id")
            if rid is not None:
                ids.add(rid)
        return ids
