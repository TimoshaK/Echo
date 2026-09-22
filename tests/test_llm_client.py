"""Tests for echo.llm_client: redirect safety (SEC-03) and base_url validation (SEC-02)."""

import unittest
import urllib.error
import urllib.request

from echo import llm_client


class SafeRedirectHandlerTests(unittest.TestCase):
    ORIGIN = "https://api.example.com/v1/chat/completions"
    TOKEN = "sk-test-1234567890"

    def _request(self, method="POST"):
        return urllib.request.Request(
            self.ORIGIN,
            data=b"{}" if method == "POST" else None,
            headers={"Authorization": "Bearer %s" % self.TOKEN},
            method=method,
        )

    def _redirect(self, newurl, code=302, method="POST"):
        handler = llm_client.SafeRedirectHandler()
        return handler.redirect_request(
            self._request(method), None, code, "Found", {}, newurl
        )

    def test_cross_host_redirect_strips_authorization(self):
        new_req = self._redirect("https://evil.example.net/v1/chat/completions")
        self.assertIsNotNone(new_req)
        self.assertNotIn("Authorization", new_req.headers)

    def test_same_origin_redirect_keeps_authorization(self):
        new_req = self._redirect("https://api.example.com/v2/chat/completions")
        self.assertIsNotNone(new_req)
        self.assertIn("Authorization", new_req.headers)

    def test_port_change_strips_authorization(self):
        handler = llm_client.SafeRedirectHandler()
        req = urllib.request.Request(
            "https://api.example.com:443/v1/chat/completions",
            data=b"{}",
            headers={"Authorization": "Bearer %s" % self.TOKEN},
            method="POST",
        )
        new_req = handler.redirect_request(
            req,
            None,
            302,
            "Found",
            {},
            "https://api.example.com:8443/v1/chat/completions",
        )
        self.assertNotIn("Authorization", new_req.headers)

    def test_scheme_downgrade_strips_authorization(self):
        new_req = self._redirect("http://api.example.com/v1/chat/completions")
        self.assertNotIn("Authorization", new_req.headers)

    def test_get_307_cross_host_strips_authorization(self):
        new_req = self._redirect(
            "https://evil.example.net/v1/chat/completions", code=307, method="GET"
        )
        self.assertNotIn("Authorization", new_req.headers)

    def test_post_307_is_refused_by_the_stdlib(self):
        with self.assertRaises(urllib.error.HTTPError):
            self._redirect("https://evil.example.net/v1/chat/completions", code=307)


class CrossOriginTests(unittest.TestCase):
    def test_cross_origin_matrix(self):
        cases = [
            ("https://api.example.com/v1", "https://evil.example.net/v2", True),
            ("https://api.example.com/v1", "https://api.example.com/v2", False),
            ("https://api.example.com:443/v1", "https://api.example.com:8443/v1", True),
            ("https://api.example.com/v1", "http://api.example.com/v1", True),
            ("https://API.example.com/v1", "https://api.example.com/v1", False),
        ]
        for origin, target, expected in cases:
            with self.subTest(origin=origin, target=target):
                self.assertIs(llm_client._is_cross_origin(origin, target), expected)


class OpenerIsolationTests(unittest.TestCase):
    def test_opener_is_cached_and_global_state_is_untouched(self):
        first = llm_client._http_opener()
        second = llm_client._http_opener()
        self.assertIs(first, second)
        self.assertTrue(
            any(isinstance(h, llm_client.SafeRedirectHandler) for h in first.handlers)
        )
        self.assertIsNone(urllib.request._opener)


if __name__ == "__main__":
    unittest.main()
