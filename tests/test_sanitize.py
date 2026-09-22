"""Tests for echo.errors.sanitize_error_detail (SEC-05)."""

import time
import unittest

from echo.errors import (
    MAX_SANITIZE_INPUT,
    REDACTED,
    InvalidBaseUrlError,
    SummaryApiError,
    sanitize_error_detail,
)


class RedactionTests(unittest.TestCase):
    def test_configured_secret_is_removed(self):
        secret = "sk-abcdef1234567890"
        out = sanitize_error_detail('{"error":"bad key %s"}' % secret, secrets=(secret,))
        self.assertNotIn(secret, out)
        self.assertIn(REDACTED, out)

    def test_bearer_token_is_removed(self):
        out = sanitize_error_detail("Bearer abcdefghijklmnop")
        self.assertNotIn("abcdefghijklmnop", out)
        self.assertIn(REDACTED, out)

    def test_openai_style_key_is_removed(self):
        out = sanitize_error_detail("invalid key sk-live-abcdef123456")
        self.assertNotIn("sk-live-abcdef123456", out)

    def test_url_userinfo_password_is_removed(self):
        out = sanitize_error_detail("see https://user:hunter2@api.example.com/v1")
        self.assertNotIn("hunter2", out)

    def test_long_opaque_token_is_removed(self):
        token = "A" * 64
        self.assertNotIn(token, sanitize_error_detail("token %s rejected" % token))

    def test_short_secret_is_ignored(self):
        self.assertEqual(sanitize_error_detail("hello", secrets=("ab",)), "hello")

    def test_irrelevant_secret_does_not_change_text(self):
        self.assertEqual(sanitize_error_detail("hello", secrets=("zzzzzz",)), "hello")

    def test_secret_of_none_is_tolerated(self):
        self.assertEqual(sanitize_error_detail("hello", secrets=(None,)), "hello")


class BoundingTests(unittest.TestCase):
    def test_long_input_is_bounded_and_fast(self):
        # "ab " * 34000 is ~102 000 characters that survives redaction, so the
        # truncation branch is actually exercised. (A run of 100 000 identical
        # characters would be swallowed by the long-token rule instead.)
        started = time.monotonic()
        out = sanitize_error_detail("ab " * 34000)
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 2.0)
        # Truncation keeps `limit` chars, drops a trailing space, then appends
        # "..."; the finish criterion is "at most limit + 3".
        self.assertLessEqual(len(out), 303)
        self.assertTrue(out.endswith("..."))

    def test_long_opaque_run_is_fully_redacted_without_truncation(self):
        out = sanitize_error_detail("a" * 100000)
        self.assertNotIn("aaaaaaaaaa", out)
        self.assertLessEqual(len(out), 303)

    def test_input_is_capped_before_regex(self):
        self.assertEqual(MAX_SANITIZE_INPUT, 4000)

    def test_exact_limit_is_not_truncated(self):
        # A homogeneous run (e.g. "x" * 300) would be caught by the long-opaque-
        # token rule, so use filler that survives redaction yet stays exactly 300
        # characters; the limit itself must not be truncated.
        exact = "ab " * 99 + "xyz"
        self.assertEqual(len(exact), 300)
        self.assertEqual(sanitize_error_detail(exact, limit=300), exact)

    def test_whitespace_is_flattened(self):
        self.assertEqual(sanitize_error_detail("line1\n\nline2\t  x"), "line1 line2 x")

    def test_control_characters_are_stripped(self):
        self.assertNotIn("\x07", sanitize_error_detail("ding\x07bell"))

    def test_none_and_empty_return_empty_string(self):
        self.assertEqual(sanitize_error_detail(None), "")
        self.assertEqual(sanitize_error_detail(""), "")


class ErrorTypeTests(unittest.TestCase):
    def test_invalid_base_url_error_is_a_value_error(self):
        self.assertTrue(issubclass(InvalidBaseUrlError, ValueError))

    def test_invalid_base_url_error_is_not_a_summary_api_error(self):
        self.assertFalse(issubclass(InvalidBaseUrlError, SummaryApiError))


if __name__ == "__main__":
    unittest.main()
