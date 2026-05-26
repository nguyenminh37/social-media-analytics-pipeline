import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from serving_api.app import ServingApiApp


API_HOST = os.getenv("SERVING_API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("SERVING_API_PORT", "8081"))


def build_handler(app: ServingApiApp):
    class ApiHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            status_code, body = app.render_json("GET", self.path)
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args) -> None:  # noqa: A003
            return

    return ApiHandler


def main() -> None:
    app = ServingApiApp()
    server = ThreadingHTTPServer((API_HOST, API_PORT), build_handler(app))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
