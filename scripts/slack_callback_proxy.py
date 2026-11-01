"""Expose only Slack's OAuth callback to a local HTTPS tunnel.

Run `python3 scripts/slack_callback_proxy.py`, then point cloudflared at
http://127.0.0.1:8010. The application and all other API paths stay private.
Request URLs contain temporary OAuth credentials, so never log them.
"""

from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

CALLBACK = "/api/slack/oauth/callback"


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if urlsplit(self.path).path != CALLBACK:
            self.send_error(404)
            return
        if len(self.path) > 8192:
            self.send_error(414)
            return
        connection = HTTPConnection("127.0.0.1", 8000, timeout=30)
        try:
            connection.request("GET", self.path)
            response = connection.getresponse()
            body = response.read()
            self.send_response(response.status)
            for name in ("Content-Type", "Location"):
                if value := response.getheader(name):
                    self.send_header(name, value)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        except OSError:
            self.send_error(502)
        finally:
            connection.close()

    def log_message(self, *_):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8010), CallbackHandler).serve_forever()
