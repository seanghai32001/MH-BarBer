import json
import os
from http.server import BaseHTTPRequestHandler
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen


class handler(BaseHTTPRequestHandler):
    def _proxy(self, method: str) -> None:
        backend_url = os.environ.get("BACKEND_URL", "").strip().rstrip("/")
        if not backend_url:
            self._send_json(500, {"detail": "BACKEND_URL មិនទាន់បានកំណត់ក្នុង Vercel Environment Variable ទេ។"})
            return

        # ទាញយក path និង query parameters ពី URL
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query, keep_blank_values=True)
        sub_path = query.pop("path", [""])[0].lstrip("/")

        target_url = f"{backend_url}/api/{sub_path}"
        if query:
            target_url = f"{target_url}?{urlencode(query, doseq=True)}"

        # អានទិន្នន័យ Body សម្រាប់ POST
        body = None
        if method == "POST":
            content_length = int(self.headers.get("Content-Length", "0") or 0)
            body = self.rfile.read(content_length) if content_length > 0 else b""

        # បញ្ជូន Headers សំខាន់ៗទៅកាន់ FastAPI Backend
        forward_headers = {
            "Content-Type": self.headers.get("Content-Type", "application/json"),
        }
        tg_init_data = self.headers.get("X-Telegram-Init-Data")
        if tg_init_data is not None:
            forward_headers["X-Telegram-Init-Data"] = tg_init_data

        req = Request(target_url, data=body, headers=forward_headers, method=method)

        try:
            with urlopen(req, timeout=25) as resp:
                resp_body = resp.read()
                content_type = resp.headers.get("Content-Type", "application/json")
                self._send_raw(resp.status, resp_body, content_type)
        except HTTPError as exc:
            # បញ្ជូន Error JSON (ដូចជា 400, 401, 409) ពី FastAPI ត្រឡប់ទៅ Frontend វិញ
            err_body = exc.read()
            content_type = exc.headers.get("Content-Type", "application/json") if exc.headers else "application/json"
            self._send_raw(exc.code, err_body, content_type)
        except URLError as exc:
            self._send_json(502, {"detail": f"មិនអាចតភ្ជាប់ទៅ Backend Server បានទេ: {exc.reason}"})
        except Exception as exc:
            self._send_json(500, {"detail": f"Proxy error: {str(exc)}"})

    def _send_raw(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store, no-cache, max-age=0")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: dict) -> None:
        self._send_raw(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self) -> None:
        self._proxy("GET")

    def do_POST(self) -> None:
        self._proxy("POST")