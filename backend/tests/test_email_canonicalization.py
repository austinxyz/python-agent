"""Email canonicalization invariant.

Per spec: every email read/write must `.strip().lower()`.
"""
from app.services.auth_service import canonicalize_email


class TestCanonicalizeEmail:
    def test_lowercases_uppercase(self):
        assert canonicalize_email("AUSTIN@GMAIL.COM") == "austin@gmail.com"

    def test_strips_whitespace(self):
        assert canonicalize_email("  austin@gmail.com  ") == "austin@gmail.com"
        assert canonicalize_email("\tlinda@gmail.com\n") == "linda@gmail.com"

    def test_combines_strip_and_lower(self):
        assert canonicalize_email("  Austin@Gmail.COM  ") == "austin@gmail.com"

    def test_already_canonical_unchanged(self):
        assert canonicalize_email("uncle@example.com") == "uncle@example.com"

    def test_empty_string_returns_empty(self):
        assert canonicalize_email("") == ""
        assert canonicalize_email("   ") == ""
