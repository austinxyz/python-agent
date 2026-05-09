"""Google ID token verification — auth_service.verify_google_token."""
import pytest

from app.services import auth_service


class TestVerifyGoogleToken:
    def test_requires_token(self):
        with pytest.raises(ValueError, match="id_token is required"):
            auth_service.verify_google_token("", audience="some-aud")

    def test_requires_audience(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
        with pytest.raises(ValueError, match="GOOGLE_CLIENT_ID not configured"):
            auth_service.verify_google_token("some-token")

    def test_uses_env_audience_when_unspecified(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "env-aud-123")
        captured = {}

        def fake_verify(token, request, audience):
            captured["aud"] = audience
            return {"sub": "x", "email": "a@b", "name": "A", "picture": None}

        monkeypatch.setattr(
            "google.oauth2.id_token.verify_oauth2_token", fake_verify
        )
        claims = auth_service.verify_google_token("tok")
        assert captured["aud"] == "env-aud-123"
        assert claims["sub"] == "x"

    def test_invalid_token_raises_valueerror_with_safe_message(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "aud")

        def fake_verify(token, request, audience):
            raise ValueError("Token expired or invalid")

        monkeypatch.setattr(
            "google.oauth2.id_token.verify_oauth2_token", fake_verify
        )
        with pytest.raises(ValueError, match="google token verification failed"):
            auth_service.verify_google_token("bad-token")

    def test_explicit_audience_overrides_env(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "env-aud")
        captured = {}

        def fake_verify(token, request, audience):
            captured["aud"] = audience
            return {"sub": "x"}

        monkeypatch.setattr(
            "google.oauth2.id_token.verify_oauth2_token", fake_verify
        )
        auth_service.verify_google_token("tok", audience="explicit-aud")
        assert captured["aud"] == "explicit-aud"
