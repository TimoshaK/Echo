"""Tests for echo.llm_client: redirect safety (SEC-03) and base_url validation (SEC-02)."""

import json
import unittest
import urllib.error
import urllib.request
from unittest import mock

from echo import llm_client
from echo.errors import InvalidBaseUrlError, SummaryApiError


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


LIVE_BASE_URL = "https://api.dslab.tech/v1"
TEST_KEY = "sk-test-1234567890"


class _FakeResponse:
    """Minimal stand-in for the http.client response used by urllib.

    `raw` is used for the empty-body case, where json.dumps would produce b'""'
    rather than a genuinely empty body.
    """

    def __init__(self, payload=None, raw=None):
        if raw is not None:
            self._body = raw
        else:
            self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class ValidateBaseUrlTests(unittest.TestCase):
    def test_live_operator_url_is_accepted(self):
        self.assertEqual(llm_client.validate_base_url(LIVE_BASE_URL), LIVE_BASE_URL)

    def test_trailing_slash_is_stripped(self):
        self.assertEqual(
            llm_client.validate_base_url("https://openrouter.ai/api/v1/"),
            "https://openrouter.ai/api/v1",
        )

    def test_surrounding_whitespace_is_tolerated(self):
        self.assertEqual(
            llm_client.validate_base_url("  %s  " % LIVE_BASE_URL), LIVE_BASE_URL
        )

    def test_scheme_comparison_is_case_insensitive(self):
        self.assertEqual(
            llm_client.validate_base_url("HTTPS://api.example.com/v1"),
            "HTTPS://api.example.com/v1",
        )

    def test_http_is_rejected_with_a_clear_message(self):
        with self.assertRaises(InvalidBaseUrlError) as ctx:
            llm_client.validate_base_url("http://api.example.com/v1")
        self.assertIn("https://", str(ctx.exception))
        self.assertIn("http", str(ctx.exception))

    def test_other_schemes_are_rejected(self):
        for url in (
            "ftp://api.example.com/v1",
            "file:///etc/passwd",
            "//api.example.com/v1",
        ):
            with self.subTest(url=url):
                with self.assertRaises(InvalidBaseUrlError):
                    llm_client.validate_base_url(url)

    def test_blank_values_are_rejected(self):
        for url in ("", "   ", None):
            with self.subTest(url=url):
                with self.assertRaises(InvalidBaseUrlError):
                    llm_client.validate_base_url(url)

    def test_missing_host_is_rejected(self):
        with self.assertRaises(InvalidBaseUrlError):
            llm_client.validate_base_url("https://")

    def test_userinfo_is_rejected(self):
        with self.assertRaises(InvalidBaseUrlError):
            llm_client.validate_base_url("https://user:pass@api.example.com/v1")


class PostChatTests(unittest.TestCase):
    def _config(self, base_url=LIVE_BASE_URL):
        return {
            "llm": {"base_url": base_url, "api_key": TEST_KEY, "model": "test-model"}
        }

    def test_invalid_base_url_never_reaches_the_network(self):
        with mock.patch.object(llm_client, "_http_opener") as opener:
            with self.assertRaises(InvalidBaseUrlError):
                llm_client.post_chat(self._config("http://api.example.com/v1"), {})
        opener.assert_not_called()

    def test_success_path_returns_stripped_content(self):
        response = _FakeResponse({"choices": [{"message": {"content": "  hello  "}}]})
        with mock.patch.object(llm_client, "_http_opener") as opener:
            opener.return_value.open.return_value = response
            self.assertEqual(llm_client.post_chat(self._config(), {}), "hello")

    def test_http_error_is_reported_with_code_and_redacted_detail(self):
        error = urllib.error.HTTPError(
            "%s/chat/completions" % LIVE_BASE_URL,
            401,
            "Unauthorized",
            {},
            _FakeResponse({"error": "bad key %s" % TEST_KEY}),
        )
        with mock.patch.object(llm_client, "_http_opener") as opener:
            opener.return_value.open.side_effect = error
            with self.assertRaises(SummaryApiError) as ctx:
                llm_client.post_chat(self._config(), {})
        self.assertEqual(ctx.exception.code, 401)
        self.assertNotIn(TEST_KEY, str(ctx.exception))
        self.assertIn("[REDACTED]", str(ctx.exception))

    def test_empty_error_body_falls_back_to_a_placeholder(self):
        error = urllib.error.HTTPError(
            "%s/chat/completions" % LIVE_BASE_URL,
            500,
            "Server Error",
            {},
            _FakeResponse(raw=b""),
        )
        with mock.patch.object(llm_client, "_http_opener") as opener:
            opener.return_value.open.side_effect = error
            with self.assertRaises(SummaryApiError) as ctx:
                llm_client.post_chat(self._config(), {})
        self.assertEqual(ctx.exception.code, 500)
        self.assertNotEqual(str(ctx.exception).strip(), "")

    def test_network_error_is_reported_with_code_zero(self):
        with mock.patch.object(llm_client, "_http_opener") as opener:
            opener.return_value.open.side_effect = urllib.error.URLError("dns blew up")
            with self.assertRaises(SummaryApiError) as ctx:
                llm_client.post_chat(self._config(), {})
        self.assertEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
