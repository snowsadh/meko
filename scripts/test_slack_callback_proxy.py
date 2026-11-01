import http.client
import threading
import unittest
from unittest.mock import Mock, patch

from slack_callback_proxy import CallbackHandler, ThreadingHTTPServer


class CallbackProxyTest(unittest.TestCase):
    def test_only_callback_is_forwarded_and_redirect_is_preserved(self):
        backend = Mock()
        response = backend.getresponse.return_value
        response.status = 307
        response.read.return_value = b""
        response.getheader.side_effect = lambda key: {
            "Location": "http://localhost:3000/dashboard/example",
        }.get(key)
        server = ThreadingHTTPServer(("127.0.0.1", 0), CallbackHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with patch("slack_callback_proxy.HTTPConnection", return_value=backend) as factory:
                for path in ("/", "/docs", "/api/auth/login", "/api/slack/oauth/callback/other"):
                    client = http.client.HTTPConnection(*server.server_address)
                    client.request("GET", path)
                    reply = client.getresponse()
                    self.assertEqual(reply.status, 404)
                    reply.read()
                    client.close()
                factory.assert_not_called()
                client = http.client.HTTPConnection(*server.server_address)
                path = "/api/slack/oauth/callback?state=synthetic&code=synthetic"
                client.request("GET", path)
                reply = client.getresponse()
                self.assertEqual(reply.status, 307)
                self.assertEqual(reply.getheader("Location"), "http://localhost:3000/dashboard/example")
                self.assertEqual(reply.getheader("Cache-Control"), "no-store")
                reply.read()
                client.close()
                factory.assert_called_once_with("127.0.0.1", 8000, timeout=30)
                backend.request.assert_called_once_with("GET", path)
                backend.close.assert_called_once()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
